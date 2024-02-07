import logging
import os

BARCHART_PASSWORD = "BARCHART_PASSWORD"
BARCHART_USERNAME = "BARCHART_USERNAME"
BARCHART_DRY_RUN = "BARCHART_DRY_RUN"
BARCHART_END_YEAR = "BARCHART_END_YEAR"
BARCHART_START_YEAR = "BARCHART_START_YEAR"
BARCHART_OUTPUT_DIR = "BARCHART_OUTPUT_DIR"
DAILY_DOWNLOAD_LIMIT = "DAILY_DOWNLOAD_LIMIT"
RANDOM_SLEEP_IN_SEC = "RANDOM_SLEEP_IN_SEC"
LOGGING_LEVEL = "LOGGING_LEVEL"
MARKET_METADATA_FILES = "MARKET_METADATA_FILES"


class SessionConfig:
    def __init__(self):
        env_vars = [
            BARCHART_USERNAME,
            BARCHART_PASSWORD,
            BARCHART_OUTPUT_DIR,
            BARCHART_START_YEAR,
            BARCHART_END_YEAR,
            BARCHART_DRY_RUN,
            DAILY_DOWNLOAD_LIMIT,
            RANDOM_SLEEP_IN_SEC,
            LOGGING_LEVEL,
            MARKET_METADATA_FILES
        ]
        bc_config = {v: os.environ.get(v) for v in env_vars if v in os.environ}

        self.dry_run = bc_config.get(BARCHART_DRY_RUN, "False") == "True"
        log_level_str = bc_config.get(LOGGING_LEVEL, "info")
        self.log_level = logging.getLevelName(log_level_str.upper())
        self.download_dir = SessionConfig.resolve_directory(bc_config.get(BARCHART_OUTPUT_DIR, "./data"))
        self.username = bc_config.get(BARCHART_USERNAME, None)
        self.password = bc_config.get(BARCHART_PASSWORD, None)
        self.daily_download_limit = int(bc_config.get(DAILY_DOWNLOAD_LIMIT, "100"))
        self.random_sleep_in_sec = int(v) if (v := bc_config.get(RANDOM_SLEEP_IN_SEC, "10")) else None
        self.start_year = int(bc_config.get(BARCHART_START_YEAR, "2023"))
        self.end_year = int(bc_config.get(BARCHART_END_YEAR, "2024"))

        market_metadata_files = bc_config.get(MARKET_METADATA_FILES, "./config.json").split(',')
        for file in market_metadata_files:
            SessionConfig.ensure_file_exists(file)
        self.market_metadata_files = market_metadata_files

    @staticmethod
    def resolve_directory(directory):
        if directory is None:
            download_directory = os.getcwd()
        else:
            download_directory = directory
        if not os.path.exists(download_directory) or not os.path.isdir(download_directory):
            raise Exception(f"Output directory '{download_directory}' does not exist.")
        return download_directory

    @staticmethod
    def ensure_file_exists(file_path: str):
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"File '{file_path}' does not exist.")
