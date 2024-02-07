#!/usr/bin/env python
import logging
import time

from data_providers.bc_data_provider import BarchartDataProvider
from data_providers.yh_data_provider import YahooDataProvider
from data_storage.csv_storage import CsvStorage
from data_storage.parquet_storage import ParquetStorage
from downloader import Downloader
from logging_utils import init_logging, LoggingContext
from session_config import SessionConfig


def create_barchart_csv_downloader(cfg: SessionConfig) -> Downloader:
    data_storage = CsvStorage(cfg.download_dir, cfg.dry_run)
    data_provider = BarchartDataProvider(
        username=cfg.username,
        password=cfg.password,
        dry_run=cfg.dry_run,
        daily_download_limit=cfg.daily_download_limit,
        random_sleep_in_sec=cfg.random_sleep_in_sec)
    return Downloader(data_storage, data_provider)


def create_yahoo_parquet_downloader(cfg: SessionConfig) -> Downloader:
    data_storage = ParquetStorage(cfg.dry_run)
    data_provider = YahooDataProvider()
    return Downloader(data_storage, data_provider)


if __name__ == "__main__":

    try:
        session_cfg = SessionConfig()
        init_logging(session_cfg.log_level)
        with LoggingContext(entry_msg=f"Starting ...", exit_msg=f"Done!"):
            downloader = create_barchart_csv_downloader(session_cfg)
            # downloader.download("./config.json", 2000, 2020)
            downloader.download(session_cfg.market_metadata_files, session_cfg.start_year, session_cfg.end_year)
            downloader.logout()
    except Exception as e:
        logging.error("Unhandled exception.", e)
        time.sleep(60)
        raise e

