#!/usr/bin/env python
import logging

from .data_providers.bc_data_provider import BarchartDataProvider
from .data_providers.data_provider import NotFoundError
from .data_providers.ib_data_provider import IbkrDataProvider
from .data_providers.yf_data_provider import YahooDataProvider
from .data_storage.csv_storage import CsvStorage
from .data_storage.parquet_storage import ParquetStorage
from .downloaders.updating_downloader import UpdatingDownloader
from .initialization.session_config import OsEnvironSessionConfig, SessionConfig
from .utils.logging_utils import init_logging, LoggingContext


def get_function_by_name(name: str):
    # Check if the function exists in the global namespace
    if name in globals() and callable(globals()[name]):
        # Get the function object by name
        func = globals()[name]
        return func

    raise ValueError(f"Function '{name}' does not exist")


def create_barchart_downloader(cfg: SessionConfig) -> UpdatingDownloader:
    data_storage = CsvStorage(cfg.download_directory, cfg.dry_run)
    backup_data_storage = ParquetStorage(cfg.download_directory, cfg.dry_run) if cfg.backup_data else None
    data_provider = BarchartDataProvider(
        username=cfg.username,
        password=cfg.password,
        daily_download_limit=cfg.daily_download_limit)
    return UpdatingDownloader(data_storage, data_provider, backup_data_storage,
                              force_backup=cfg.force_backup, random_sleep_in_sec=cfg.random_sleep_in_sec,
                              dry_run=cfg.dry_run)


def create_yahoo_downloader(cfg: OsEnvironSessionConfig) -> UpdatingDownloader:
    data_storage = CsvStorage(cfg.download_directory, cfg.dry_run)
    backup_data_storage = ParquetStorage(cfg.download_directory, cfg.dry_run) if cfg.backup_data else None
    data_provider = YahooDataProvider()
    return UpdatingDownloader(data_storage, data_provider, backup_data_storage,
                              force_backup=cfg.force_backup, random_sleep_in_sec=cfg.random_sleep_in_sec,
                              dry_run=cfg.dry_run)


def create_ibkr_downloader(cfg: OsEnvironSessionConfig) -> UpdatingDownloader:
    data_storage = CsvStorage(cfg.download_directory, cfg.dry_run)
    backup_data_storage = ParquetStorage(cfg.download_directory, cfg.dry_run) if cfg.backup_data else None
    data_provider = IbkrDataProvider(ipaddress=cfg.provider_host, port=cfg.provider_port)
    return UpdatingDownloader(data_storage, data_provider, backup_data_storage,
                              force_backup=cfg.force_backup, random_sleep_in_sec=cfg.random_sleep_in_sec,
                              dry_run=cfg.dry_run)


def main():
    try:
        # config = SessionConfig(
        #     username=os.environ.get(BarchartVars.BCU_USERNAME.value),
        #     password=os.environ.get(BarchartVars.BCU_PASSWORD.value),
        #     download_directory=tempfile.gettempdir(),
        #     start_year=2005, end_year=2007, dry_run=True)

        config = OsEnvironSessionConfig()

        init_logging(config.log_level)

        with LoggingContext(entry_msg=f"Starting ...", exit_msg=f"Done!"):
            # downloader = create_barchart_downloader(config)
            # downloader = create_yahoo_downloader(config)
            func = get_function_by_name(config.downloader_factory)
            downloader = func(config)

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
