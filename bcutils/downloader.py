import logging
from datetime import timedelta, datetime
from itertools import cycle

import pytz

from config_utils import InstrumentType, InstrumentConfig
from contracts import FutureContract, StockContract
from data_providers.bc_data_provider import BarchartDataProvider
from data_providers.data_provider import HistoricalDataResult, DataProvider, LowDataError, AllowanceLimitExceeded
from data_storage.data_storage import DataStorage
from download_job import DownloadJob, StockDownloadJob, FutureDownloadJob
from logging_utils import LoggingContext
from period import Period
from utils import date_range_generator, calculate_date_range, convert_download_range_to_datetime


class Downloader:

    def __init__(self, data_storage, data_provider):
        self.data_storage: DataStorage = data_storage
        self.data_provider: DataProvider = data_provider

    def process_download_job(self, job: DownloadJob):
        with LoggingContext(
                entry_msg=f"Processing download job for {job}",
                entry_level=logging.INFO,
                success_msg=f"Processed download job for {job}",
                success_level=logging.DEBUG):

            start_date = job.start_date
            end_date = job.end_date

            # do we have this data already?
            existing_download = None
            try:
                existing_download = job.load()
                logging.debug(f"Loaded existing data: {existing_download}")
                if existing_download.is_data_coverage_acceptable(start_date, end_date):
                    logging.info(f"Existing data {existing_download.df.shape} satisfies requested range. "
                                 f"Skipping download.")
                    return HistoricalDataResult.EXISTS
                logging.debug(f"Existing data {existing_download.df.shape} does NOT satisfy requested range. "
                              f"Getting more data.")
            except FileNotFoundError:
                logging.debug(f"Existing data was NOT found. Starting fresh download.")
                pass

            new_download = job.fetch()
            if not new_download:
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")

            merged_download = new_download.merge(existing_download)
            job.persist(merged_download)
            logging.info(f"Persisted data: {merged_download}")
            return HistoricalDataResult.OK

    def process_download_jobs(self, job_list: list[DownloadJob]) -> None:
        low_data = []
        downloads_processed = 0

        with LoggingContext(
                entry_msg=f"--------------------------- processing {len(job_list)} jobs ---------------------------",
                entry_level=logging.INFO,
                failure_msg=f"Failed to completely process scheduled downloads"):

            for job in job_list:
                try:
                    self.process_download_job(job)
                except LowDataError:
                    logging.error(f"Downloaded data is too low. {job}")
                    low_data.append(job)
                    continue
                finally:
                    downloads_processed += 1
                    logging.info(f"--------------------------- {downloads_processed}/{len(job_list)} jobs processed ---------------------------")

            if low_data:
                formatted_jobs = [f"({j})" for j in low_data]
                logging.warning(f"Low/poor data found for: {formatted_jobs}, maybe check config")

    def logout(self):
        self.data_provider.logout()

    def create_download_jobs(self, contract_map, start_year: int, end_year: int) -> list[DownloadJob]:
        start_date, end_date = convert_download_range_to_datetime(start_year, end_year)
        contracts_per_instrument = {}
        job_list = []
        count = 0

        for instr in contract_map.keys():
            config_obj: InstrumentConfig = contract_map[instr]
            futures_code = config_obj.code

            instrument_job_list = []
            roll_cycle = config_obj.cycle
            instrument_type = config_obj.asset_class
            periods = config_obj.periods
            tick_date = config_obj.tick_date
            backfill_date = config_obj.start_date
            instr_start_date = max(start_date, backfill_date)

            # if that end_date is in the future, then we may as well make it today...
            instr_end_date = min(end_date, pytz.UTC.localize(datetime.utcnow()))

            if instrument_type == InstrumentType.Future and roll_cycle:
                supported_periods = self.data_provider.get_futures_timeframes()
                days_count = config_obj.days_count
                for year in range(start_year, end_year):
                    for month_code in list(roll_cycle):
                        futures_contract = FutureContract(instr, futures_code, year, month_code, tick_date, days_count)
                        contract_start_date, contract_end_date = calculate_date_range(days_count,
                                                                                      futures_contract.month,
                                                                                      year)
                        contract_start_date = max(contract_start_date, instr_start_date)
                        contract_end_date = min(contract_end_date, instr_end_date)
                        if contract_start_date > contract_end_date:
                            continue

                        for period in periods:
                            if period not in supported_periods:
                                logging.warning(
                                    f"{self.data_provider} does not support {period} for {futures_contract}")
                                continue

                            # intraday data only goes back to a certain date, depending on the exchange
                            # if our dates are before that date, skip intraday timeframes
                            if period != Period.Daily and tick_date is not None and contract_start_date < tick_date:
                                continue

                            job = FutureDownloadJob(self.data_provider, self.data_storage,
                                                    futures_contract, period, contract_start_date, contract_end_date)
                            instrument_job_list.append(job)

            elif instrument_type == InstrumentType.Stock:
                supported_periods = self.data_provider.get_stock_timeframes()
                stock_contract = StockContract(instr, futures_code)
                for period in periods:

                    if period not in supported_periods:
                        logging.warning(f"{self.data_provider} does not support {period} for {stock_contract}")
                        continue

                    # intraday data only goes back to a certain date, depending on the exchange
                    # if our dates are before that date, skip intraday timeframes
                    if period != Period.Daily and tick_date is not None and instr_start_date < tick_date:
                        instr_start_date = tick_date

                    timedelta_value: timedelta = period.get_delta_time() * BarchartDataProvider.MAX_BARS_PER_DOWNLOAD

                    for (step_star_date, step_end_date) in (
                            date_range_generator(instr_start_date, instr_end_date, timedelta_value)):
                        download_job = StockDownloadJob(self.data_provider, self.data_storage,
                                                        stock_contract, period, step_star_date, step_end_date)
                        instrument_job_list.append(download_job)

            contracts_per_instrument[instr] = instrument_job_list[::-1]
            count = count + len(instrument_job_list)

        logging.info(f'Instrument count: {count}')
        pool = cycle(contract_map.keys())

        while len(job_list) < count:
            try:
                instr = next(pool)
            except StopIteration:
                continue
            if instr not in contracts_per_instrument:
                continue
            instr_list = contracts_per_instrument[instr]
            config_obj = contract_map[instr]
            roll_cycle = config_obj.cycle

            if not roll_cycle:
                max_count = 1
            else:
                if len(roll_cycle) > 10:
                    max_count = 3
                elif len(roll_cycle) > 7:
                    max_count = 2
                else:
                    max_count = 1

            for _ in range(0, max_count):
                if len(instr_list) > 0:
                    download_job = instr_list.pop()
                    logging.info(f"Scheduled: {download_job}")
                    job_list.append(download_job)

        return job_list

    def download(self, contract_map, start_year, end_year):
        logging.info(f"Download from {start_year} to {end_year} ...")
        try:
            job_list = self.create_download_jobs(contract_map, start_year, end_year)
            self.process_download_jobs(job_list)
        except AllowanceLimitExceeded as e:  # absorbing exception by design
            logging.error(f"{e}")
