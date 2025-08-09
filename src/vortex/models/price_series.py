import logging
import os
from abc import ABC
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import pytz
from pandas import DataFrame

from .metadata import Metadata
from .columns import DATETIME_COLUMN_NAME, DATETIME_INDEX_NAME

EXPIRATION_THRESHOLD = timedelta(days=7)
LOW_DATA_THRESHOLD = timedelta(days=3)
FUTURES_SOURCE_TIME_ZONE = 'US/Central'
STOCK_SOURCE_TIME_ZONE = 'America/New_York'


def _normalize_datetime_for_comparison(dt):
    """
    Normalize datetime for timezone-aware comparison.
    
    If the datetime is timezone-naive, assume it's in UTC.
    If it's timezone-aware, convert to UTC for consistent comparison.
    
    Args:
        dt: datetime object (timezone-aware or timezone-naive)
        
    Returns:
        timezone-aware datetime in UTC
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Timezone-naive datetime - assume UTC
        return pytz.UTC.localize(dt)
    else:
        # Timezone-aware datetime - convert to UTC
        return dt.astimezone(pytz.UTC)


@dataclass
class PriceSeries(ABC):
    df: DataFrame
    metadata: Metadata

    def __str__(self):
        return f"{self.df.shape}, {self.metadata}"

    def is_data_coverage_acceptable(self, start_date, end_date) -> bool:
        df = self.df
        if len(df) > 0:
            logging.debug(
                f"Current range: {self.metadata.start_date.strftime('%Y-%m-%d')} - {self.metadata.end_date.strftime('%Y-%m-%d')}")
            logging.debug(
                f"Desired range: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")

            # Normalize all datetimes for timezone-aware comparison
            normalized_start_date = _normalize_datetime_for_comparison(start_date)
            normalized_end_date = _normalize_datetime_for_comparison(end_date)
            normalized_metadata_start = _normalize_datetime_for_comparison(self.metadata.start_date)
            normalized_metadata_end = _normalize_datetime_for_comparison(self.metadata.end_date)
            normalized_last_row_date = _normalize_datetime_for_comparison(self.metadata.last_row_date)

            if normalized_metadata_end - normalized_last_row_date > EXPIRATION_THRESHOLD:
                logging.debug(f"Coverage is acceptable. Last search indicates no more data is available, "
                              f"since last bar is {EXPIRATION_THRESHOLD} behind the end of the "
                              f"previous download request.")
                return True

            # We pretend existing data is larger in order avoid too frequent updates.
            trigger_threshold = self.metadata.period.get_bar_time_delta()
            start_date_diff = (normalized_metadata_start - trigger_threshold) - normalized_start_date
            end_date_diff = normalized_end_date - (normalized_metadata_end + trigger_threshold)
            # If either diff is positive then existing data is missing enough bars to cover requested range.
            if end_date_diff.days < 0 and start_date_diff.days < 0:
                logging.debug(f"Coverage is acceptable since range of existing data "
                              f"is within {trigger_threshold} tolerance when comparing with requested range.")
                return True

        else:
            logging.debug(f"Low data.")

        logging.debug(f"Coverage NOT acceptable.")
        return False

    def merge(self, existing_download):
        if not existing_download:
            return self

        if (self.metadata.start_date > existing_download.metadata.end_date or
                self.metadata.end_date < existing_download.metadata.start_date):
            return self

        merged_df = PriceSeries.df_merge(existing_download.df, self.df)

        merged_metadata = Metadata(
            self.metadata.symbol,
            self.metadata.period,
            min(self.metadata.start_date, existing_download.metadata.start_date),
            max(self.metadata.end_date, existing_download.metadata.end_date),
            merged_df.index[0].to_pydatetime(),
            merged_df.index[-1].to_pydatetime(),
            data_provider=self.metadata.data_provider,
            expiration_date=self.metadata.expiration_date
        )
        merged_download = PriceSeries(merged_df, merged_metadata)
        logging.info(f"Merged loaded data into remotely fetched data:  "
                     f"{existing_download.df.shape} + {self.df.shape} -> {merged_download.df.shape}")

        return merged_download

    @staticmethod
    def df_merge(existing_df, new_df, keep='last', index=DATETIME_COLUMN_NAME):
        merged_df = (pd.concat([existing_df, new_df]).
                     reset_index().
                     drop_duplicates(subset=index, keep=keep).
                     set_index(index).
                     sort_index())
        return merged_df


def file_is_placeholder_for_no_hourly_data(path):
    size = os.path.getsize(path)
    if size < 150:
        df = pd.read_csv(path)
        if is_placeholder_for_no_data(df):
            return True

    return False


def is_placeholder_for_no_data(df):
    df[DATETIME_COLUMN_NAME] = pd.to_datetime(df[DATETIME_COLUMN_NAME], format='%Y-%m-%dT%H:%M:%S%z')
    df = df.set_index(DATETIME_COLUMN_NAME, inplace=False)
    return len(df) == 2 and check_row_date(df.index[-1]) and check_row_date(df.index[-2])


def check_row_date(row_date):
    return row_date.year == 1970 and row_date.month == 1 and row_date.day == 1
