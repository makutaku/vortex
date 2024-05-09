import logging
from datetime import timedelta

from data_providers.data_provider import HistoricalDataResult
from downloaders.base_downloader import BaseDownloader
from downloaders.download_job import DownloadJob
from instruments.price_series import LOW_DATA_THRESHOLD
from utils.logging_utils import LoggingContext
from utils.utils import random_sleep


class UpdatingDownloader(BaseDownloader):

    def __init__(self, data_storage, data_provider, backup_data_storage=None, force_backup=False,
                 random_sleep_in_sec=None, dry_run=False):
        super().__init__(data_storage, data_provider, backup_data_storage, force_backup)
        self.dry_run = dry_run
        self.random_sleep_in_sec = random_sleep_in_sec if random_sleep_in_sec > 0 else None

    def _process_job(self, job: DownloadJob):
        with LoggingContext(
                entry_msg=f"Processing {job}",
                entry_level=logging.INFO,
                success_msg=f"Processed {job}",
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

                    if self.force_backup and self.backup_data_storage:
                        job.persist(existing_download)

                    return HistoricalDataResult.EXISTS
                logging.debug(f"Existing data {existing_download.df.shape} does NOT satisfy requested range. "
                              f"Getting more data.")

                # In order to avoid fetching data that we already have, and also to avoid creating holes,
                # we use last row date as a magnet for new job start date, subtracting some days to avoid
                # missing any data:
                new_start = existing_download.metadata.last_row_date - LOW_DATA_THRESHOLD
                if job.start_date >= existing_download.metadata.start_date:
                    job.start_date = new_start

                # avoid holes:
                if job.end_date < existing_download.metadata.start_date:
                    job.end_date = existing_download.metadata.start_date

            except FileNotFoundError as e:
                logging.debug(f"Existing data was NOT found. Starting fresh download.")
                pass

            self.pretend_not_a_bot()
            new_download = job.fetch()
            if not new_download:
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")

            merged_download = new_download.merge(existing_download)
            job.persist(merged_download)
            logging.info(f"Persisted data: {merged_download}")
            return HistoricalDataResult.OK

    def pretend_not_a_bot(self):
        if self.random_sleep_in_sec is not None:
            # cursory attempt to not appear like a bot
            random_sleep(self.random_sleep_in_sec)
        else:
            logging.warning("Random sleep is disabled. Enable to avoid bot detection.")

