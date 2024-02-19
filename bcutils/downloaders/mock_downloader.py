import logging

from data_providers.data_provider import HistoricalDataResult
from download_job import DownloadJob
from downloaders.base_downloader import BaseDownloader
from utils.logging_utils import LoggingContext


class MockDownloader(BaseDownloader):

    def _process_job(self, job: DownloadJob):
        with LoggingContext(
                entry_msg=f"(Mock) Processing {job}",
                entry_level=logging.INFO,
                success_msg=f"(Mock) Processed {job}",
                success_level=logging.DEBUG):
            return HistoricalDataResult.OK
