#!/usr/bin/env python
import logging

from data_providers.bc_data_provider import BarchartDataProvider
from data_providers.data_provider import NotFoundError
from data_providers.yh_data_provider import YahooDataProvider
from data_storage.csv_storage import CsvStorage
from data_storage.parquet_storage import ParquetStorage
from downloaders.updating_downloader import UpdatingDownloader
from logging_utils import init_logging, LoggingContext
from session_config import OsEnvironSessionConfig, SessionConfig


def create_barchart_csv_downloader(cfg: SessionConfig) -> UpdatingDownloader:
    data_storage = CsvStorage(cfg.download_directory, cfg.dry_run)
    data_provider = BarchartDataProvider(
        username=cfg.username,
        password=cfg.password,
        dry_run=cfg.dry_run,
        daily_download_limit=cfg.daily_download_limit,
        random_sleep_in_sec=cfg.random_sleep_in_sec)
    return UpdatingDownloader(data_storage, data_provider)


def create_yahoo_parquet_downloader(cfg: OsEnvironSessionConfig) -> UpdatingDownloader:
    data_storage = ParquetStorage(cfg.dry_run)
    data_provider = YahooDataProvider()
    return UpdatingDownloader(data_storage, data_provider)


def main():
    try:
        # config = SessionConfig(
        #     username=os.environ.get(BarchartVars.BARCHART_USERNAME.value),
        #     password=os.environ.get(BarchartVars.BARCHART_PASSWORD.value),
        #     download_directory=tempfile.gettempdir(),
        #     start_year=2005, end_year=2007, dry_run=True)

        config = OsEnvironSessionConfig()

        init_logging(config.log_level)

        with LoggingContext(entry_msg=f"Starting ...", exit_msg=f"Done!"):
            downloader = create_barchart_csv_downloader(config)
            downloader.download(config.market_metadata_files, config.start_year, config.end_year)
            downloader.logout()
    except NotFoundError as e:
        logging.error(e)
    except NotADirectoryError as e:
        logging.error(e)
    except FileNotFoundError as e:
        logging.error(e)
    except Exception as e:
        logging.exception("Unhandled exception.", e)
        raise e


if __name__ == "__main__":
    main()
