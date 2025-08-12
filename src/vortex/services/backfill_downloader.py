import logging

from vortex.infrastructure.providers.base import HistoricalDataResult
from .download_job import DownloadJob
from .base_downloader import BaseDownloader
from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration


class BackfillDownloader(BaseDownloader):

    def _process_job(self, job: DownloadJob):
        config = LoggingConfiguration(
            entry_msg=f"(Backfill) Processing {job}",
            entry_level=logging.INFO,
            success_msg=f"(Backfill) Processed {job}",
            success_level=logging.DEBUG
        )
        with LoggingContext(config):
            new_download = job.fetch()
            if not new_download:
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")
            job.persist(new_download)
            logging.info(f"Persisted data: {new_download}")
            return HistoricalDataResult.OK
