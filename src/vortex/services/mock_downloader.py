import logging

from vortex.infrastructure.providers.base import HistoricalDataResult
from .download_job import DownloadJob
from .base_downloader import BaseDownloader
from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration


class MockDownloader(BaseDownloader):

    def _process_job(self, job: DownloadJob):
        config = LoggingConfiguration(
            entry_msg=f"(Mock) Processing {job}",
            entry_level=logging.INFO,
            success_msg=f"(Mock) Processed {job}",
            success_level=logging.DEBUG
        )
        with LoggingContext(config):
            return HistoricalDataResult.OK
