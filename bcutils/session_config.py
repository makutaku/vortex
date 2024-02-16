import logging
import os
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import List

from utils import get_absolute_path

DEFAULT_MARKET_METADATA_FILE: str = "../config.json"
DEFAULT_DOWNLOAD_DIRECTORY: str = "~/bc-utils/data"
DEFAULT_DAILY_DOWNLOAD_LIMIT: int = 100
DEFAULT_START_YEAR: int = 2020
DEFAULT_END_YEAR: int = 2023
DEFAULT_DRY_RUN: bool = False
DEFAULT_RANDOM_SLEEP_IN_SEC: int = 10
DEFAULT_LOGGING_LEVEL: str = "INFO"
PATH_SEPARATOR: str = ','


class BarchartVars(Enum):
    BARCHART_USERNAME = "BARCHART_USERNAME"
    BARCHART_PASSWORD = "BARCHART_PASSWORD"
    BARCHART_MARKET_FILES = "BARCHART_MARKET_FILES"
    BARCHART_OUTPUT_DIR = "BARCHART_OUTPUT_DIR"
    BARCHART_START_YEAR = "BARCHART_START_YEAR"
    BARCHART_END_YEAR = "BARCHART_END_YEAR"
    BARCHART_DAILY_DOWNLOAD_LIMIT = "BARCHART_DAILY_DOWNLOAD_LIMIT"
    BARCHART_DRY_RUN = "BARCHART_DRY_RUN"
    BARCHART_LOGGING_LEVEL = "BARCHART_LOGGING_LEVEL"
    BARCHART_RANDOM_SLEEP_IN_SEC = "BARCHART_RANDOM_SLEEP_IN_SEC"
    BARCHART_BACKUP_DATA = "BARCHART_BACKUP_DATA"


@dataclass(frozen=False)
class SessionConfig(ABC):
    username: str = None
    password: str = None
    market_metadata_files: List[str] = None
    download_directory: str = DEFAULT_DOWNLOAD_DIRECTORY
    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_END_YEAR
    daily_download_limit: int = DEFAULT_DAILY_DOWNLOAD_LIMIT
    dry_run: bool = DEFAULT_DRY_RUN
    log_level: str = DEFAULT_LOGGING_LEVEL
    random_sleep_in_sec: int = DEFAULT_RANDOM_SLEEP_IN_SEC
    backup_data: bool = False

    def __post_init__(self):
        self.market_metadata_files = self.market_metadata_files \
            if self.market_metadata_files else [DEFAULT_MARKET_METADATA_FILE]
        self.market_metadata_files = [self.verify_file_exists(file) for file in self.market_metadata_files]

        self.download_directory = (
            self.verify_directory_exists(self.download_directory)
            if self.download_directory else None
        )

    @staticmethod
    def verify_directory_exists(directory: str):
        directory = get_absolute_path(directory)
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise IsADirectoryError(f"Directory '{directory}' does not exist.")
        return directory

    @staticmethod
    def verify_file_exists(file_path: str):
        file_path = get_absolute_path(file_path)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"File '{file_path}' does not exist.")
        return file_path


@dataclass(frozen=False)
class OsEnvironSessionConfig(SessionConfig):

    def __post_init__(self):
        env_vars = [member.value for member in BarchartVars]
        bc_config = {v: os.environ.get(v) for v in env_vars if v in os.environ}

        self.username = bc_config.get(BarchartVars.BARCHART_USERNAME.value, None)
        self.password = bc_config.get(BarchartVars.BARCHART_PASSWORD.value, None)

        market_metadata_files = \
            bc_config.get(BarchartVars.BARCHART_MARKET_FILES.value, DEFAULT_MARKET_METADATA_FILE).split(PATH_SEPARATOR)
        self.market_metadata_files = [SessionConfig.verify_file_exists(file) for file in market_metadata_files]

        download_directory = bc_config.get(BarchartVars.BARCHART_OUTPUT_DIR.value, DEFAULT_DOWNLOAD_DIRECTORY)
        self.download_directory = SessionConfig.verify_directory_exists(download_directory)

        self.start_year = int(x) \
            if (x := bc_config.get(BarchartVars.BARCHART_START_YEAR.value, None)) \
            else self.start_year

        self.end_year = int(x) \
            if (x := bc_config.get(BarchartVars.BARCHART_END_YEAR.value, None)) \
            else self.end_year

        self.daily_download_limit = int(x) \
            if (x := bc_config.get(BarchartVars.BARCHART_DAILY_DOWNLOAD_LIMIT.value, None)) \
            else self.daily_download_limit

        self.dry_run = (x == "True") if (x := bc_config.get(BarchartVars.BARCHART_DRY_RUN.value, None)) \
            else self.dry_run

        self.backup_data = (x == "True") if (x := bc_config.get(BarchartVars.BARCHART_BACKUP_DATA.value, None)) \
            else self.backup_data

        self.log_level = logging.getLevelName(
            bc_config.get(BarchartVars.BARCHART_LOGGING_LEVEL.value, self.log_level).upper())

        self.random_sleep_in_sec = int(x) \
            if (x := bc_config.get(BarchartVars.BARCHART_RANDOM_SLEEP_IN_SEC.value, None)) \
            else self.random_sleep_in_sec
