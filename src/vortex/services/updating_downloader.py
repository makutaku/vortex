import logging
from typing import Optional

from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.models.price_series import LOW_DATA_THRESHOLD
from vortex.utils.logging_utils import LoggingConfiguration, LoggingContext
from vortex.utils.utils import random_sleep

from .base_downloader import BaseDownloader
from .download_job import DownloadJob

# Optional metrics - graceful fallback if not available
try:
    from vortex.infrastructure.metrics import get_metrics

    _metrics_available = True
except ImportError:
    _metrics_available = False


class UpdatingDownloader(BaseDownloader):
    def __init__(
        self,
        data_storage,
        data_provider,
        backup_data_storage=None,
        force_backup: bool = False,
        random_sleep_in_sec: Optional[float] = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(data_storage, data_provider, backup_data_storage, force_backup)
        self.dry_run = dry_run
        self.random_sleep_in_sec = (
            random_sleep_in_sec
            if random_sleep_in_sec is not None and random_sleep_in_sec > 0
            else None
        )
        self._metrics = get_metrics() if _metrics_available else None

    def _process_job(self, job: DownloadJob) -> HistoricalDataResult:
        config = LoggingConfiguration(
            entry_msg=f"Processing {job}",
            entry_level=logging.INFO,
            success_msg=f"Processed {job}",
            success_level=logging.DEBUG,
        )
        with LoggingContext(config):
            start_date = job.start_date
            end_date = job.end_date

            # do we have this data already?
            existing_download = None
            try:
                existing_download = job.load()
                logging.debug(f"Loaded existing data: {existing_download}")
                if existing_download.is_data_coverage_acceptable(start_date, end_date):
                    logging.info(
                        f"Existing data {existing_download.df.shape} satisfies requested range. "
                        "Skipping download."
                    )

                    if self.force_backup and self.backup_data_storage:
                        job.persist(existing_download)

                    return HistoricalDataResult.EXISTS
                logging.debug(
                    f"Existing data {existing_download.df.shape} does NOT satisfy requested range. "
                    "Getting more data."
                )

                # In order to avoid fetching data that we already have, and also to avoid creating holes,
                # we use last row date as a magnet for new job start date, subtracting some days to avoid
                # missing any data:
                new_start = (
                    existing_download.metadata.last_row_date - LOW_DATA_THRESHOLD
                )
                if job.start_date >= existing_download.metadata.start_date:
                    job.start_date = new_start

                # avoid holes:
                if job.end_date < existing_download.metadata.start_date:
                    job.end_date = existing_download.metadata.start_date

            except FileNotFoundError:
                logging.debug("Existing data was NOT found. Starting fresh download.")

            self.pretend_not_a_bot()
            try:
                new_download = job.fetch()
            except ValueError as e:
                # Handle invalid data from provider
                logging.error(f"Provider returned invalid data: {str(e)}")
                if self._metrics:
                    provider_name = (
                        getattr(
                            self.data_provider, "__class__", type(self.data_provider)
                        )
                        .__name__.lower()
                        .replace("dataprovider", "")
                    )
                    self._metrics.record_download(
                        provider_name, job.instrument.symbol, 0, False
                    )
                return HistoricalDataResult.NONE

            if not new_download:
                # Record failed download
                if self._metrics:
                    provider_name = (
                        getattr(
                            self.data_provider, "__class__", type(self.data_provider)
                        )
                        .__name__.lower()
                        .replace("dataprovider", "")
                    )
                    self._metrics.record_download(
                        provider_name, job.instrument.symbol, 0, False
                    )
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")

            # Record successful download metrics
            if self._metrics and new_download.df is not None:
                provider_name = (
                    getattr(self.data_provider, "__class__", type(self.data_provider))
                    .__name__.lower()
                    .replace("dataprovider", "")
                )
                row_count = len(new_download.df)
                self._metrics.record_download(
                    provider_name, job.instrument.symbol, row_count, True
                )

            merged_download = new_download.merge(existing_download)
            job.persist(merged_download)
            logging.info(f"Persisted data: {merged_download}")
            return HistoricalDataResult.OK

    def pretend_not_a_bot(self) -> None:
        if self.random_sleep_in_sec is not None:
            # cursory attempt to not appear like a bot
            random_sleep(self.random_sleep_in_sec)
        else:
            logging.warning("Random sleep is disabled. Enable to avoid bot detection.")
