import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from itertools import cycle
from typing import List, Dict

import pytz

from config_utils import InstrumentConfig, InstrumentType
from contracts import FutureContract, StockContract, Forex
from data_providers.bc_data_provider import BarchartDataProvider
from data_providers.data_provider import DataProvider, LowDataError, AllowanceLimitExceeded, NotFoundError
from data_storage.data_storage import DataStorage
from download_job import DownloadJob, FutureDownloadJob, StockDownloadJob, ForexDownloadJob
from logging_utils import LoggingContext
from period import Period
from utils import calculate_date_range, date_range_generator, total_elements_in_dict_of_lists, \
    get_first_and_last_day_of_years
from utils import is_list_of_strings, merge_dicts


class BaseDownloader(ABC):

    def __init__(self, data_storage, data_provider):
        self.data_storage: DataStorage = data_storage
        self.data_provider: DataProvider = data_provider

    def login(self):
        self.data_provider.login()

    def logout(self):
        self.data_provider.logout()

    def download(self, instr_configs_or_market_metadata_files, start_year, end_year):
        logging.info(f"Download from {start_year} to {end_year} ...")
        try:
            if is_list_of_strings(instr_configs_or_market_metadata_files):
                market_metadata_files = instr_configs_or_market_metadata_files
                contract_map = merge_dicts(InstrumentConfig.load_from_json(file) for file in market_metadata_files)
            elif isinstance(instr_configs_or_market_metadata_files, str):
                contract_map = InstrumentConfig.load_from_json(instr_configs_or_market_metadata_files)
            elif isinstance(instr_configs_or_market_metadata_files, dict):
                contract_map = instr_configs_or_market_metadata_files
            else:
                raise TypeError(instr_configs_or_market_metadata_files)

            job_list = self._create_jobs(contract_map, start_year, end_year)
            self._process_jobs(job_list)

        except AllowanceLimitExceeded as e:  # absorbing exception by design
            logging.error(f"{e}")

    def _create_jobs(self, configs, start_year: int, end_year: int) -> List[DownloadJob]:

        start_date, end_date = get_first_and_last_day_of_years(start_year, end_year - 1)
        jobs_per_instrument: Dict[str, List[DownloadJob]] = {}

        for instr in configs.keys():
            config: InstrumentConfig = configs[instr]
            jobs = self._create_instrument_jobs(instr, config, start_date, end_date)
            jobs_per_instrument[instr] = jobs[::-1]

        return self._schedule_jobs(configs, jobs_per_instrument)

    def _create_instrument_jobs(self, instr, config: InstrumentConfig, start_date, end_date) -> List[DownloadJob]:

        futures_code = config.code
        roll_cycle = config.cycle
        instrument_type = config.asset_class
        periods = config.periods
        tick_date = config.tick_date
        backfill_date = config.start_date

        instr_start_date = max(start_date, backfill_date)

        # if that end_date is in the future, then we may as well make it today...
        instr_end_date = min(end_date, pytz.UTC.localize(datetime.utcnow()))

        if instrument_type == InstrumentType.Future:
            days_count = config.days_count
            return self._create_future_jobs(futures_code, instr, instr_start_date, instr_end_date, periods, tick_date,
                                            roll_cycle, days_count)
        elif instrument_type == InstrumentType.Stock:
            return self._create_stock_jobs(futures_code, instr, instr_end_date, instr_start_date, periods, tick_date)
        elif instrument_type == InstrumentType.Forex:
            return self._create_forex_jobs(futures_code, instr, instr_end_date, instr_start_date, periods, tick_date)
        else:
            raise ValueError(f"Instrument type '{instrument_type}' is not supported.")

    def _create_future_jobs(self, futures_code, instr, start_date: datetime, end_date: datetime, periods,
                            tick_date, roll_cycle, days_count) -> List[FutureDownloadJob]:

        if not roll_cycle:
            raise ValueError(f"{instr} does not have a roll_cycle. Only dated future is currently supported.")

        jobs = []
        supported_periods = self.data_provider.get_futures_timeframes()
        start_year = start_date.year
        end_year = end_date.year

        for year in range(start_year, end_year + 1):
            for month_code in list(roll_cycle):
                futures_contract = FutureContract(instr, futures_code, year, month_code, tick_date, days_count)
                contract_start_date, contract_end_date = calculate_date_range(days_count,
                                                                              futures_contract.month,
                                                                              year)
                contract_start_date = max(contract_start_date, start_date)
                contract_end_date = min(contract_end_date, end_date)
                if contract_start_date > contract_end_date:
                    continue

                for period in periods:
                    if period not in supported_periods:
                        logging.warning(
                            f"{self.data_provider} does not support {period} for {futures_contract}")
                        continue

                    # intraday data only goes back to a certain date, depending on the exchange
                    # if our dates are before that date, skip intraday timeframes
                    if period.is_intraday and tick_date and contract_start_date < tick_date:
                        continue

                    job = FutureDownloadJob(self.data_provider, self.data_storage,
                                            futures_contract, period, contract_start_date, contract_end_date)
                    jobs.append(job)

        return jobs

    def _create_stock_jobs(self, futures_code, instr, instr_end_date, instr_start_date,
                           periods, tick_date) -> List[StockDownloadJob]:

        supported_periods = self.data_provider.get_stock_timeframes()
        stock_contract = StockContract(instr, futures_code)
        jobs = []

        for period in periods:

            if period not in supported_periods:
                logging.warning(f"{self.data_provider} does not support {period} for {stock_contract}")
                continue

            # intraday data only goes back to a certain date, depending on the exchange
            # if our dates are before that date, skip intraday timeframes
            if period != Period.Daily and tick_date is not None and instr_start_date < tick_date:
                instr_start_date = tick_date

            timedelta_value: timedelta = period.get_delta_time() * BarchartDataProvider.MAX_BARS_PER_DOWNLOAD

            for (step_start_date, step_end_date) in (
                    date_range_generator(instr_start_date, instr_end_date, timedelta_value)):
                job = StockDownloadJob(self.data_provider, self.data_storage,
                                       stock_contract, period, step_start_date, step_end_date)
                jobs.append(job)

        return jobs

    def _create_forex_jobs(self, futures_code, instr, instr_end_date, instr_start_date,
                           periods, tick_date) -> List[ForexDownloadJob]:

        supported_periods = self.data_provider.get_forex_timeframes()
        stock_contract = Forex(instr, futures_code)
        jobs = []

        for period in periods:

            if period not in supported_periods:
                logging.warning(f"{self.data_provider} does not support {period} for {stock_contract}")
                continue

            # intraday data only goes back to a certain date, depending on the exchange
            # if our dates are before that date, skip intraday timeframes
            if period != Period.Daily and tick_date is not None and instr_start_date < tick_date:
                instr_start_date = tick_date

            timedelta_value: timedelta = period.get_delta_time() * BarchartDataProvider.MAX_BARS_PER_DOWNLOAD

            for (step_start_date, step_end_date) in (
                    date_range_generator(instr_start_date, instr_end_date, timedelta_value)):
                job = ForexDownloadJob(self.data_provider, self.data_storage,
                                       stock_contract, period, step_start_date, step_end_date)
                jobs.append(job)

        return jobs

    def _schedule_jobs(self, contract_map, jobs_per_instrument: Dict[str, List[DownloadJob]]) -> List[DownloadJob]:

        scheduled: List[DownloadJob] = []
        count = total_elements_in_dict_of_lists(jobs_per_instrument)
        logging.info(f'Instrument count: {count}')

        pool = cycle(contract_map.keys())
        while len(scheduled) < count:
            try:
                instr = next(pool)
            except StopIteration:
                continue
            if instr not in jobs_per_instrument:
                continue
            instr_list = jobs_per_instrument[instr]
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
                    job = instr_list.pop()
                    logging.info(f"Scheduled: {job}")
                    scheduled.append(job)

        return scheduled

    def _process_jobs(self, job_list: list[DownloadJob]) -> None:

        low_data = []
        not_found = []
        downloads_processed = 0

        with LoggingContext(
                entry_msg=f"--------------------------- processing {len(job_list)} jobs ---------------------------",
                entry_level=logging.INFO,
                failure_msg=f"Failed to completely process scheduled downloads"):

            for job in job_list:
                try:
                    self._process_job(job)
                except LowDataError:
                    logging.warning(f"Downloaded data is too low. {job}")
                    low_data.append(job)
                    continue
                except NotFoundError:
                    logging.warning(f"Instrument not found. Check starting date. {job}")
                    not_found.append(job)
                    continue
                finally:
                    downloads_processed += 1
                    logging.info(f"--------------------------- "
                                 f"{downloads_processed}/{len(job_list)} jobs processed ---------------------------")

            if low_data:
                formatted_jobs = [f"({j})" for j in low_data]
                logging.warning(f"Low/poor data found for: {formatted_jobs}, maybe check config")

            if not_found:
                formatted_jobs = [f"({j})" for j in not_found]
                logging.warning(f"Data not found for: {formatted_jobs}, maybe check config")

    @abstractmethod
    def _process_job(self, job):
        pass
