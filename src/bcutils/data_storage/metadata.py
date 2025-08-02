import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from ..instruments.columns import VOLUME_COLUMN
from ..instruments.period import Period
from ..utils.utils import convert_date_strings_to_datetime


@dataclass
class Metadata:
    symbol: str
    period: Period
    start_date: datetime
    end_date: datetime
    first_row_date: datetime
    last_row_date: datetime
    data_provider: str = None
    expiration_date: datetime = None
    created_date: datetime = datetime.utcnow()

    def __str__(self):
        return (f"{self.symbol}, {self.period.value}, "
                f"{self.start_date.strftime('%Y-%m-%d')}, {self.end_date.strftime('%Y-%m-%d')}")

    @staticmethod
    def create_metadata(df, provider_name, symbol, period: Period, start, end):
        df = df.sort_index()
        first_row_date = df.index[0].to_pydatetime()
        last_row_date = df.index[-1].to_pydatetime()
        expiration_date = None
        if df[VOLUME_COLUMN].iloc[-1] == 0:
            logging.debug(
                f"Detected possible contract expiration: last bar has volume 0. Adjusting expected end date.")
            expiration_date = last_row_date
        metadata = Metadata(symbol, period, start, end, first_row_date, last_row_date,
                            data_provider=provider_name,
                            expiration_date=expiration_date)
        return metadata


def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (str, int, float)):
        return obj  # Serialize strings, ints, and floats as-is
    elif isinstance(obj, Enum):
        return obj.value
    raise TypeError("Type not serializable")


class MetadataHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.metadata_file = os.path.join(os.path.dirname(file_path), f'{os.path.basename(file_path)}.json')

    def set_metadata(self, new_metadata: Metadata):
        # Save the new metadata to the file (overwriting previous metadata)
        with open(self.metadata_file, 'w') as json_file:
            json.dump(asdict(new_metadata), json_file, default=default_serializer, indent=2)

    def get_metadata(self) -> Metadata:
        with open(self.metadata_file, 'r') as json_file:
            metadata_dict = json.load(json_file)
            metadata_dict = convert_date_strings_to_datetime(metadata_dict)
            return Metadata(**metadata_dict)

#
# # Example usage:
# file_path = '/path/to/your/file.txt'
#
# # Create a MetadataHandler instance
# metadata_handler = MetadataHandler(file_path)
#
# # Create a Metadata instance
# new_metadata = Metadata(author='John Doe', created_date='2024-02-03')
#
# # Set metadata
# metadata_handler.set_metadata(new_metadata)
#
# # Get metadata
# retrieved_metadata = metadata_handler.get_metadata()
# print(f"Retrieved metadata: {retrieved_metadata}")
