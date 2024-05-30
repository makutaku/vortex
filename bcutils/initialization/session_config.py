import logging
import os
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import List

from utils.utils import get_absolute_path

DEFAULT_MARKET_METADATA_FILE: str = "../config.json"
DEFAULT_DOWNLOAD_DIRECTORY: str = "~/bc-utils/data"
DEFAULT_DAILY_DOWNLOAD_LIMIT: int = 100
DEFAULT_START_YEAR: int = 2000
DEFAULT_END_YEAR: int = 2025
DEFAULT_DRY_RUN: bool = False
DEFAULT_RANDOM_SLEEP_IN_SEC: int = 10
DEFAULT_LOGGING_LEVEL: str = "INFO"
DEFAULT_DOWNLOADER_FACTORY: str = "create_barchart_downloader"
PATH_SEPARATOR: str = ','


class BarchartVars(Enum):
    BCU_PROVIDER_HOST = "BCU_PROVIDER_HOST"
    BCU_PROVIDER_PORT = "BCU_PROVIDER_PORT"
    BCU_USERNAME = "BCU_USERNAME"
    BCU_PASSWORD = "BCU_PASSWORD"
    BCU_CONFIG_FILE = "BCU_CONFIG_FILE"
    BCU_OUTPUT_DIR = "BCU_OUTPUT_DIR"
    BCU_START_YEAR = "BCU_START_YEAR"
    BCU_END_YEAR = "BCU_END_YEAR"
    BCU_DAILY_DOWNLOAD_LIMIT = "BCU_DAILY_DOWNLOAD_LIMIT"
    BCU_DRY_RUN = "BCU_DRY_RUN"
    BCU_LOGGING_LEVEL = "BCU_LOGGING_LEVEL"
    BCU_RANDOM_SLEEP_IN_SEC = "BCU_RANDOM_SLEEP_IN_SEC"
    BCU_BACKUP_DATA = "BCU_BACKUP_DATA"
    BCU_FORCE_BACKUP = "BCU_FORCE_BACKUP"
    BCU_DOWNLOADER = "BCU_DOWNLOADER"


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
    force_backup: bool = False
    downloader_factory: str = DEFAULT_DOWNLOADER_FACTORY

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

        self.username = bc_config.get(BarchartVars.BCU_USERNAME.value, None)
        self.password = bc_config.get(BarchartVars.BCU_PASSWORD.value, None)
        self.provider_host = bc_config.get(BarchartVars.BCU_PROVIDER_HOST.value, None)
        self.provider_port = bc_config.get(BarchartVars.BCU_PROVIDER_PORT.value, "8888")

        market_metadata_files = \
            bc_config.get(BarchartVars.BCU_CONFIG_FILE.value, DEFAULT_MARKET_METADATA_FILE).split(PATH_SEPARATOR)
        self.market_metadata_files = [SessionConfig.verify_file_exists(file) for file in market_metadata_files]

        download_directory = bc_config.get(BarchartVars.BCU_OUTPUT_DIR.value, DEFAULT_DOWNLOAD_DIRECTORY)
        self.download_directory = SessionConfig.verify_directory_exists(download_directory)

        self.start_year = int(x) \
            if (x := bc_config.get(BarchartVars.BCU_START_YEAR.value, None)) \
            else self.start_year

        self.end_year = int(x) \
            if (x := bc_config.get(BarchartVars.BCU_END_YEAR.value, None)) \
            else self.end_year

        self.daily_download_limit = int(x) \
            if (x := bc_config.get(BarchartVars.BCU_DAILY_DOWNLOAD_LIMIT.value, None)) \
            else self.daily_download_limit

        self.dry_run = (x == "True") if (x := bc_config.get(BarchartVars.BCU_DRY_RUN.value, None)) \
            else self.dry_run

        self.backup_data = (x == "True") if (x := bc_config.get(BarchartVars.BCU_BACKUP_DATA.value, None)) \
            else self.backup_data

        self.force_backup = (x == "True") if (x := bc_config.get(BarchartVars.BCU_FORCE_BACKUP.value, None)) \
            else self.force_backup

        self.downloader_factory = bc_config.get(BarchartVars.BCU_DOWNLOADER.value,
                                                DEFAULT_DOWNLOADER_FACTORY)

        self.log_level = logging.getLevelName(
            bc_config.get(BarchartVars.BCU_LOGGING_LEVEL.value, self.log_level).upper())

        self.random_sleep_in_sec = int(x) \
            if (x := bc_config.get(BarchartVars.BCU_RANDOM_SLEEP_IN_SEC.value, None)) \
            else self.random_sleep_in_sec
