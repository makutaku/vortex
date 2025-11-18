import logging

from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.utils.logging_utils import LoggingConfiguration, LoggingContext

from .base_downloader import BaseDownloader
from .download_job import DownloadJob


class BackfillDownloader(BaseDownloader):
    def _process_job(self, job: DownloadJob):
        config = LoggingConfiguration(
            entry_msg=f"(Backfill) Processing {job}",
            entry_level=logging.INFO,
            success_msg=f"(Backfill) Processed {job}",
            success_level=logging.DEBUG,
        )
        with LoggingContext(config):
            try:
                new_download = job.fetch()
            except ValueError as e:
                # Handle invalid data from provider
                logging.error(f"Provider returned invalid data: {str(e)}")
                return HistoricalDataResult.NONE

            if not new_download:
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")
            job.persist(new_download)
            logging.info(f"Persisted data: {new_download}")
            return HistoricalDataResult.OK
