import logging

from data_providers.data_provider import HistoricalDataResult
from download_job import DownloadJob
from downloaders.base_downloader import BaseDownloader
from logging_utils import LoggingContext


class UpdatingDownloader(BaseDownloader):

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
                    return HistoricalDataResult.EXISTS
                logging.debug(f"Existing data {existing_download.df.shape} does NOT satisfy requested range. "
                              f"Getting more data.")
            except FileNotFoundError as e:
                logging.debug(f"Existing data was NOT found. Starting fresh download.", e)
                pass

            new_download = job.fetch()
            if not new_download:
                return HistoricalDataResult.NONE
            logging.info(f"Fetched remote data: {new_download}")

            merged_download = new_download.merge(existing_download)
            job.persist(merged_download)
            logging.info(f"Persisted data: {merged_download}")
            return HistoricalDataResult.OK
