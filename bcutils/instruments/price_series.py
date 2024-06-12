import logging
import os
from abc import ABC
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd
from pandas import DataFrame

from data_storage.metadata import Metadata
from instruments.columns import DATE_TIME_COLUMN

EXPIRATION_THRESHOLD = timedelta(days=7)
LOW_DATA_THRESHOLD = timedelta(days=3)
FUTURES_SOURCE_TIME_ZONE = 'US/Central'
STOCK_SOURCE_TIME_ZONE = 'America/New_York'


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
                f"Actual range: {self.metadata.start_date.strftime('%Y-%m-%d')} - {self.metadata.end_date.strftime('%Y-%m-%d')}")
            logging.debug(
                f"Expected range: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")

            if self.metadata.end_date - self.metadata.last_row_date > EXPIRATION_THRESHOLD:
                logging.debug(f"Coverage is acceptable. Last search indicates no more data is available, "
                              f"since last bar is {EXPIRATION_THRESHOLD} behind the end of the "
                              f"previous download request.")
                return True

            # We pretend existing data is larger in order avoid too frequent updates.
            trigger_threshold = self.metadata.period.get_bar_time_delta()
            start_date_diff = (self.metadata.start_date - trigger_threshold) - start_date
            end_date_diff = end_date - (self.metadata.end_date + trigger_threshold)
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
    def df_merge(existing_df, new_df, keep='last', index=DATE_TIME_COLUMN):
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
    df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
    df = df.set_index(DATE_TIME_COLUMN, inplace=False)
    return len(df) == 2 and check_row_date(df.index[-1]) and check_row_date(df.index[-2])


def check_row_date(row_date):
    return row_date.year == 1970 and row_date.month == 1 and row_date.day == 1
