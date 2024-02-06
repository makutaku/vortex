import enum
import json
import logging
from datetime import datetime, timedelta

import pytz

from logging_utils import LoggingContext
from period import Period
from utils import convert_date_strings_to_datetime


class InstrumentType(enum.StrEnum):
    Future = 'future'
    Stock = 'stock'


class InstrumentConfig:
    def __init__(self,
                 asset_class: str,
                 name: str,
                 code: str,
                 tick_date: datetime | None = None,
                 start_date: datetime | None = None,
                 periods: str = None,
                 cycle: str | None = None,
                 days_count: int | None = None):
        self.name = name
        self.code = code
        # we want to push tick_date slightly into the future to try and resolve issues around the switchover date
        self.tick_date = tick_date + timedelta(days=90) if tick_date else None
        self.start_date = start_date if start_date else datetime(year=2000, month=1, day=1, tzinfo=pytz.UTC)
        self.periods = Period.get_periods_from_str(periods) if periods is not None else [Period.Daily]
        self.cycle = cycle
        self.asset_class = InstrumentType(asset_class)
        self.days_count = days_count if days_count else 120

    @staticmethod
    def load_from_json(file_path: str):
        with LoggingContext(entry_msg=f"Loading config from '{file_path}'",
                            entry_level=logging.DEBUG,
                            success_msg=f"Loaded config from '{file_path}'",
                            failure_msg=f"Failed to load config from '{file_path}'"):
            with open(file_path, 'r') as file:
                config_data = json.load(file)

            config_dict = {}
            for class_name, instruments in config_data.items():
                for instrument_name, details in instruments.items():
                    details['name'] = instrument_name
                    details['asset_class'] = class_name
                    details = convert_date_strings_to_datetime(details)
                    config_dict[instrument_name] = InstrumentConfig(**details)

            return config_dict

# # Example usage:
# file_path = 'path/to/your/config.json'
# configuration = load_configuration_from_json(file_path)
#
# # Accessing instrument details
# amzn_config = configuration['AMZN']
# print(amzn_config.name)            # Output: AMZN
# print(amzn_config.code)            # Output: AMZN
# print(amzn_config.tick_date)       # Output: 2008-05-05
# print(amzn_config.start_date)      # Output: 1997-05-15
# print(amzn_config.periods)         # Output: 30m,15m,5m
# print(amzn_config.cycle)           # Output: None (assuming it's not specified for AMZN)
