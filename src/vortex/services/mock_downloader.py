import logging

from vortex.providers.data_provider import HistoricalDataResult
from .download_job import DownloadJob
from .base_downloader import BaseDownloader
from vortex.utils.logging_utils import LoggingContext


class MockDownloader(BaseDownloader):

    def _process_job(self, job: DownloadJob):
        with LoggingContext(
                entry_msg=f"(Mock) Processing {job}",
                entry_level=logging.INFO,
                success_msg=f"(Mock) Processed {job}",
                success_level=logging.DEBUG):
            return HistoricalDataResult.OK
