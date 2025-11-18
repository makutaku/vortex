import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import cycle
from typing import Dict, List, Optional, Union

from vortex.core.instruments import InstrumentConfig, InstrumentType
from vortex.exceptions.providers import AllowanceLimitExceededError, DataNotFoundError
from vortex.infrastructure.providers.base import DataProvider, HistoricalDataResult
from vortex.infrastructure.storage.data_storage import DataStorage
from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.instrument import Instrument
from vortex.models.price_series import LOW_DATA_THRESHOLD
from vortex.models.stock import Stock
from vortex.utils.logging_utils import LoggingConfiguration, LoggingContext
from vortex.utils.utils import (
    date_range_generator,
    generate_year_month_tuples,
    get_first_and_last_day_of_years,
    is_list_of_strings,
    merge_dicts,
    total_elements_in_dict_of_lists,
)

from .download_job import DownloadJob


@dataclass
class DownloadConfiguration:
    """Configuration for download operations."""

    instruments: Union[str, List[str], Dict]
    start_year: int
    end_year: int

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.start_year > self.end_year:
            raise ValueError(
                f"Start year ({self.start_year}) cannot be greater than end year ({self.end_year})"
            )

        if self.start_year < 1900 or self.end_year > 2100:
            raise ValueError("Years must be between 1900 and 2100")

    def load_contract_map(self) -> Dict:
        """Load and return the contract map from instruments configuration."""
        if is_list_of_strings(self.instruments):
            return merge_dicts(
                InstrumentConfig.load_from_json(file) for file in self.instruments
            )
        elif isinstance(self.instruments, str):
            return InstrumentConfig.load_from_json(self.instruments)
        elif isinstance(self.instruments, dict):
            return self.instruments
        else:
            raise TypeError(f"Unsupported instruments type: {type(self.instruments)}")


class BaseDownloader(ABC):
    def __init__(
        self,
        data_storage: DataStorage,
        data_provider: DataProvider,
        backup_data_storage: Optional[DataStorage] = None,
        force_backup: bool = False,
    ) -> None:
        self.data_storage: DataStorage = data_storage
        self.data_provider: DataProvider = data_provider
        self.backup_data_storage = backup_data_storage
        self.force_backup = force_backup

    def login(self) -> None:
        self.data_provider.login()

    def logout(self) -> None:
        self.data_provider.logout()

    def download(self, config: DownloadConfiguration) -> None:
        """Download data using the provided configuration."""
        logging.info(f"Download from {config.start_year} to {config.end_year} ...")
        try:
            contract_map = config.load_contract_map()
            job_list = self._create_jobs(
                contract_map, config.start_year, config.end_year
            )
            self._process_jobs(job_list)
        except AllowanceLimitExceededError as e:  # absorbing exception by design
            logging.error(f"{e}")

    def download_legacy(
        self,
        instr_configs_or_market_metadata_files: Union[str, List[str], Dict],
        start_year: int,
        end_year: int,
    ) -> None:
        """Legacy download method - use download() with DownloadConfiguration instead."""
        config = DownloadConfiguration(
            instruments=instr_configs_or_market_metadata_files,
            start_year=start_year,
            end_year=end_year,
        )
        self.download(config)

    def _create_jobs(
        self, configs, start_year: int, end_year: int
    ) -> List[DownloadJob]:
        start, end = get_first_and_last_day_of_years(start_year, end_year - 1)
        jobs_per_instrument: Dict[str, List[DownloadJob]] = {}

        for instr in configs.keys():
            config: InstrumentConfig = configs[instr]
            if config.periods is not None and len(config.periods) == 0:
                logging.debug(f"Skipping {instr} because it has been disabled.")
                continue

            jobs = self._create_instrument_jobs(instr, config, start, end)
            jobs_per_instrument[instr] = jobs[::-1]

        return self._schedule_jobs(configs, jobs_per_instrument)

    def _create_instrument_jobs(
        self, instr: str, config: InstrumentConfig, start: datetime, end: datetime
    ) -> List[DownloadJob]:
        logging.debug(f"Creating jobs for {instr}")

        futures_code = config.code
        roll_cycle = config.cycle
        instrument_type = config.asset_class
        periods = config.periods
        tick_date = config.tick_date

        # if start is before instrument became available, use the latter
        start = max(start, config.start_date) if config.start_date else start

        # if end is in the future, then we cap it since we will never get prices that didn't happen yet!
        now_at_exchange = datetime.now(config.tz)
        end = min(end, now_at_exchange)

        if instrument_type == InstrumentType.Future:
            days_count = config.days_count
            jobs = self._create_future_jobs(
                futures_code,
                instr,
                start,
                end,
                periods,
                tick_date,
                roll_cycle,
                days_count,
                config.tz,
            )
        elif instrument_type == InstrumentType.Stock:
            stock = Stock(instr, futures_code)
            jobs = self.create_jobs_for_undated_instrument(
                stock, start, end, periods, tick_date
            )
        elif instrument_type == InstrumentType.Forex:
            forex = Forex(instr, futures_code)
            jobs = self.create_jobs_for_undated_instrument(
                forex, start, end, periods, tick_date
            )
        else:
            raise ValueError(f"Instrument type '{instrument_type}' is not supported.")

        logging.debug(f"Created {len(jobs)} jobs for {instr}")
        return jobs

    def _create_future_jobs(
        self,
        futures_code: str,
        instr: str,
        start: datetime,
        end: datetime,
        periods: List,
        tick_date: Optional[datetime],
        roll_cycle: List[str],
        days_count: int,
        tz,
    ) -> List[DownloadJob]:
        if not roll_cycle:
            raise ValueError(
                f"{instr} does not have a roll_cycle. "
                "Futures are dated instruments and require roll cycle."
            )

        jobs = []

        # When looking for futures contracts, we have to consider that although they may expire
        # in the future, they might have prices today. Therefore, by adding contract length
        # we will include these contracts. Beyond days_count, their prices didn't start yet.
        future_end_date = end + timedelta(days=days_count)

        year_month_gen = generate_year_month_tuples(start, future_end_date)
        for year, month in year_month_gen:
            month_code = Future.get_code_for_month(month)
            if month_code in list(roll_cycle):
                future = Future(
                    instr, futures_code, year, month_code, tick_date, days_count
                )
                periods = self.filter_periods(future, periods)
                instr_jobs = self.create_jobs_for_dated_instrument(
                    future, periods, start, end, tz
                )
                for instr_job in instr_jobs:
                    jobs.append(instr_job)

        return jobs

    def filter_periods(self, instrument: Instrument, periods: List) -> List:
        supported_periods = self.data_provider.get_supported_timeframes()
        filtered_periods = []
        for period in periods:
            if period not in supported_periods:
                logging.warning(
                    f"{self.data_provider} does not support {period} for {instrument}"
                )
                continue
            else:
                filtered_periods.append(period)
        return filtered_periods

    def create_jobs_for_dated_instrument(
        self, future: Future, periods: List, start: datetime, end: datetime, tz
    ) -> List[DownloadJob]:
        _jobs = []
        contract_start_date, contract_end_date = future.get_date_range(tz)
        start = max(start, contract_start_date)
        end = min(end, contract_end_date)
        if (end - start) < LOW_DATA_THRESHOLD:
            return _jobs

        tick_date = future.tick_date

        for period in periods:
            # intraday data only goes back to a certain date, depending on the exchange
            # if our dates are before that date, skip intraday timeframes
            if period.is_intraday() and tick_date and start < tick_date:
                continue

            provider_min_start = self.data_provider.get_min_start(period)
            if provider_min_start and start < provider_min_start:
                continue

            job = DownloadJob(
                self.data_provider,
                self.data_storage,
                future,
                period,
                start,
                end,
                self.backup_data_storage,
            )
            logging.debug(f"Created: {job}")
            _jobs.append(job)

        return _jobs

    def create_jobs_for_undated_instrument(
        self,
        instrument: Instrument,
        start: datetime,
        end: datetime,
        periods: Optional[List],
        tick_date: Optional[datetime],
    ) -> List[DownloadJob]:
        jobs = []
        supported_periods = self.data_provider.get_supported_timeframes()
        periods = periods if periods is not None else supported_periods

        for period in periods:
            if period not in supported_periods:
                logging.warning(
                    f"{self.data_provider} does not support {period} for {instrument} @{period}"
                )
                continue

            # intraday data only goes back to a certain date, depending on the exchange
            # if our dates are before that date, skip intraday timeframes
            # if period.is_intraday() and tick_date: # and start < tick_date:
            # logging.debug(f"Skipping {period} for {instrument} because  start={start} < tick_date={tick_date}")
            # continue
            start = (
                max(start, tick_date) if period.is_intraday() and tick_date else start
            )

            provider_min_start = self.data_provider.get_min_start(period)
            if provider_min_start and provider_min_start > end:
                logging.warning(
                    f"{self.data_provider} does not support start before {provider_min_start} "
                    f"for {instrument} @{period}"
                )
                # nothing to do.
                continue

            start = max(start, provider_min_start) if provider_min_start else start

            timedelta_value: timedelta = self.data_provider.get_max_range(period)

            for step_start_date, step_end_date in date_range_generator(
                start, end, timedelta_value
            ):
                job = DownloadJob(
                    self.data_provider,
                    self.data_storage,
                    instrument,
                    period,
                    step_start_date,
                    step_end_date,
                    backup_data_storage=self.backup_data_storage,
                )
                logging.debug(f"Created: {job}")
                jobs.append(job)

        return jobs

    def _schedule_jobs(
        self, contract_map, jobs_per_instrument: Dict[str, List[DownloadJob]]
    ) -> List[DownloadJob]:
        scheduled: List[DownloadJob] = []
        count = total_elements_in_dict_of_lists(jobs_per_instrument)
        logging.info(f"Total jobs to schedule: {count}")

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

    def _process_jobs(self, job_list: List[DownloadJob]) -> None:
        not_found = []
        jobs_processed = 0
        jobs_downloaded = 0

        config = LoggingConfiguration(
            entry_msg=f"--------------------------- processing {len(job_list)} jobs ---------------------------",
            entry_level=logging.INFO,
            failure_msg="Failed to completely process scheduled downloads",
        )
        with LoggingContext(config):
            for job in job_list:
                try:
                    result = self._process_job(job)
                    jobs_downloaded += 1 if result == HistoricalDataResult.OK else 0
                except DataNotFoundError:
                    logging.warning(f"Instrument not found. Check starting date. {job}")
                    not_found.append(job)
                    continue
                finally:
                    jobs_processed += 1
                    logging.info(
                        "--------------------------- "
                        f"{jobs_processed}/{len(job_list)} jobs processed ----  "
                        f"{jobs_downloaded} downloads -----------------------"
                    )

            if not_found:
                formatted_jobs = [f"({j})" for j in not_found]
                logging.warning(
                    f"Data not found for: {formatted_jobs}, maybe check config"
                )

    @abstractmethod
    def _process_job(self, job: DownloadJob) -> HistoricalDataResult:
        pass
