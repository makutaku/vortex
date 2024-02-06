#!/usr/bin/env python
import logging
import os
import os.path
import time

from config_utils import InstrumentConfig
from data_providers.bc_data_provider import BarchartDataProvider
from data_storage.data_storage import CsvDataStorage
from downloader import Downloader
from logging_utils import init_logging, LoggingContext

BARCHART_PASSWORD = "BARCHART_PASSWORD"
BARCHART_USERNAME = "BARCHART_USERNAME"
BARCHART_DRY_RUN = "BARCHART_DRY_RUN"
BARCHART_END_YEAR = "BARCHART_END_YEAR"
BARCHART_START_YEAR = "BARCHART_START_YEAR"
BARCHART_OUTPUT_DIR = "BARCHART_OUTPUT_DIR"
BARCHART_INPUT_DIR = "BARCHART_INPUT_DIR"
DAILY_DOWNLOAD_LIMIT = "DAILY_DOWNLOAD_LIMIT"
RANDOM_SLEEP_IN_SEC = "RANDOM_SLEEP_IN_SEC"
LOGGING_LEVEL = "LOGGING_LEVEL"


def resolve_directory(directory):
    if directory is None:
        download_directory = os.getcwd()
    else:
        download_directory = directory
    if not os.path.exists(download_directory) or not os.path.isdir(download_directory):
        raise Exception(f"Output directory '{download_directory}' does not exist.")
    return download_directory


if __name__ == "__main__":

    try:
        env_vars = [
            BARCHART_USERNAME,
            BARCHART_PASSWORD,
            BARCHART_INPUT_DIR,
            BARCHART_OUTPUT_DIR,
            BARCHART_START_YEAR,
            BARCHART_END_YEAR,
            BARCHART_DRY_RUN,
            DAILY_DOWNLOAD_LIMIT,
            RANDOM_SLEEP_IN_SEC,
            LOGGING_LEVEL,
        ]
        bc_config = {v: os.environ.get(v) for v in env_vars if v in os.environ}

        log_level_str = bc_config.get(LOGGING_LEVEL, "info")
        init_logging(logging.getLevelName(log_level_str.upper()))

        with LoggingContext(entry_msg=f"Starting ...",
                            exit_msg=f"Done!"
                            ):
            #logging.debug(f"Environment variables:{bc_config}")

            dry_run = bc_config.get(BARCHART_DRY_RUN, "False") == "True"

            download_dir = resolve_directory(bc_config.get(BARCHART_OUTPUT_DIR, "./data"))
            logging.debug(f"download_dir={download_dir}")
            bc_data_storage = CsvDataStorage(download_dir, dry_run)

            username = bc_config.get(BARCHART_USERNAME, None)
            password = bc_config.get(BARCHART_PASSWORD, None)
            daily_download_limit = int(bc_config.get(DAILY_DOWNLOAD_LIMIT, "100"))
            random_sleep_in_sec = int(v) if (v := bc_config.get(RANDOM_SLEEP_IN_SEC, "10")) else None
            logging.debug(f"daily_download_limit={daily_download_limit}")
            logging.debug(f"random_sleep_in_sec={random_sleep_in_sec}")
            bc_data_provider = BarchartDataProvider(username, password, dry_run,
                                                    max_allowance=daily_download_limit,
                                                    sleep_random_seconds=random_sleep_in_sec)

            bc_csv_downloader = Downloader(bc_data_storage, bc_data_provider)

            start_year = int(bc_config.get(BARCHART_START_YEAR, "2023"))
            end_year = int(bc_config.get(BARCHART_END_YEAR, "2024"))

            input_dir = resolve_directory(bc_config.get(BARCHART_INPUT_DIR, "./"))
            logging.debug(f"input_dir={input_dir}")
            config_file_name = 'config.json'
            config_file_path = os.path.join(os.path.dirname(input_dir), config_file_name)
            logging.debug(f"config_file_path={config_file_path}")
            configuration = InstrumentConfig.load_from_json(config_file_path)

            bc_csv_downloader.download(configuration, start_year, end_year)
            bc_csv_downloader.logout()
    except Exception as e:
        logging.error("Unhandled exception.", e)
        time.sleep(60)
        raise e
