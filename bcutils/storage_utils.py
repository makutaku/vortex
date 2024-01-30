import io
import logging
import os
from datetime import timedelta

import pandas as pd

from bcutils.period import Period

BARCHART_CLOSE_COLUMN = "Last"
CLOSE_COLUMN = "Close"
BARCHART_DATE_TIME_COLUMN = 'Time'
DATE_TIME_COLUMN = 'DATETIME'
SOURCE_TIME_ZONE = 'US/Central'


def save_price_data(file_path, period, data):
    if period in [Period.Daily, Period.Weekly, Period.Monthly, Period.Quarterly]:
        date_format = '%Y-%m-%d'
    else:
        date_format = '%m/%d/%Y %H:%M'

    iostr = io.StringIO(data)
    new_df = pd.read_csv(iostr, skipfooter=1, engine='python')
    logging.info(f"Received data {new_df.shape} from Barchart")
    new_df = new_df.rename(columns={BARCHART_DATE_TIME_COLUMN: DATE_TIME_COLUMN})
    new_df[DATE_TIME_COLUMN] = pd.to_datetime(new_df[DATE_TIME_COLUMN], format=date_format)
    new_df.set_index(DATE_TIME_COLUMN, inplace=True)
    new_df.index = new_df.index.tz_localize(tz=SOURCE_TIME_ZONE).tz_convert('UTC')
    new_df = new_df.rename(columns={BARCHART_CLOSE_COLUMN: CLOSE_COLUMN})

    # If data already exists, merge new data with existing data
    if os.path.isfile(file_path):
        logging.info(f"Merging with existing data from {file_path}")
        existing_df = pd.read_csv(file_path)
        logging.info(f"Loaded existing data: {existing_df.shape}")
        existing_df[DATE_TIME_COLUMN] = pd.to_datetime(existing_df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
        existing_df.set_index(DATE_TIME_COLUMN, inplace=True)
        new_df = (pd.concat([existing_df, new_df]).
              reset_index().
              drop_duplicates(subset='DATETIME', keep='last').
              set_index(DATE_TIME_COLUMN))

    logging.info(f"Writing data {new_df.shape} to: {file_path}")
    new_df.to_csv(file_path, date_format='%Y-%m-%dT%H:%M:%S%z')
    return len(new_df) < 3


def resolve_output_directory(save_directory):
    if save_directory is None:
        download_dir = os.getcwd()
    else:
        download_dir = save_directory
    if not os.path.exists(download_dir) or not os.path.isdir(download_dir):
        raise Exception(f"Output directory '{download_dir}' does not exist.")
    return download_dir


def make_file_path_for_futures(month, year, instrument, path):
    date_code = str(year) + '{0:02d}'.format(month)
    filename = f"{instrument}_{date_code}00.csv"
    full_path = f"{path}/futures/{filename}"
    return full_path


def make_file_path_for_stock(symbol, path, period):
    filename = f"{symbol}.csv"
    full_path = f"{path}/stocks/{period.value}/{filename}"
    return full_path


def file_is_placeholder_for_no_hourly_data(path):
    size = os.path.getsize(path)
    if size < 150:
        df = pd.read_csv(path)
        df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
        df.set_index(DATE_TIME_COLUMN, inplace=True)
        if len(df) == 2 and check_row_date(df.index[-1]) and check_row_date(df.index[-2]):
            return True

    return False


def check_row_date(row_date):
    return row_date.year == 1970 and row_date.month == 1 and row_date.day == 1


def is_data_update_needed(contract, start_date, end_date, backfill_date, file_path):
    df = pd.read_csv(file_path)
    df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
    df.set_index(DATE_TIME_COLUMN, inplace=True)
    if len(df) > 0:
        first_date = df.index[0].to_pydatetime()
        last_date = df.index[-1].to_pydatetime()
        logging.info(f"Existing data for stock '{contract}' is from {first_date} to {last_date}")

        start_date_diff = first_date - start_date
        end_date_diff = end_date - last_date

        if (end_date_diff < MIN_DAYS_TO_TRIGGER_UPDATE and
                (start_date_diff < MIN_DAYS_TO_TRIGGER_UPDATE or (first_date - backfill_date) < timedelta(days=1))):
            logging.info(f"Data for stock '{contract}' is older than backfill_date, skipping")
            return False

        logging.info(f"Data for stock '{contract}' is earlier than backfill_date, not skipping")
    else:
        logging.info(f"Data for stock '{contract}' already downloaded but low data, not skipping")

    return True


MIN_DAYS_TO_TRIGGER_UPDATE = timedelta(days=7)
