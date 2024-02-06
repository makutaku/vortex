import calendar
import logging
import os
import time
from datetime import timezone, datetime, timedelta
from random import randint

import pytz
from dateutil import parser


def random_sleep(n=15):
    secs = randint(1, 1 + n)
    logging.info(f"Waiting for {secs}s to pretend this is not a robot ...")
    time.sleep(secs)


def create_full_path(file_path):
    # Get the directory part of the file path
    directory = os.path.dirname(file_path)

    # Create the full path if it doesn't exist
    if not os.path.exists(directory):
        logging.info(f"Creating directory '{directory}'")
        os.makedirs(directory)

    return file_path


def last_day_of_year(year, timezone_info=timezone.utc):
    # Create a datetime object for the first day of the next year
    next_year = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

    # Subtract one day to get the last day of the input year
    last_day = next_year - timedelta(days=1)

    # Convert to the specified timezone
    last_day_tz_aware = last_day.astimezone(timezone_info)

    return last_day_tz_aware


def date_range_generator(start_date, end_date, delta):
    current_date = start_date
    while current_date < end_date:
        yield current_date, min(current_date + delta, end_date)
        current_date += delta


def reverse_date_range_generator(start_date, end_date, delta):
    current_date = end_date
    while current_date > start_date:
        yield max(current_date - delta, start_date), current_date
        current_date -= delta


def calculate_date_range(days, month, year):
    # for expired contracts the end date would be the expiry date;
    # for KISS sake, lets assume expiry is last date of contract month
    last_day_of_the_month = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day_of_the_month)

    # assumption no.2: lets set start date at <day_count> days before end date
    day_count = timedelta(days=days)
    start_date = end_date - day_count

    start_date = pytz.UTC.localize(start_date)
    end_date = pytz.UTC.localize(end_date)

    return start_date, end_date


def convert_download_range_to_datetime(start_year, end_year):
    first_day_of_start_year = last_day_of_year(start_year - 1) + timedelta(days=1)
    start_date = first_day_of_start_year
    last_day_of_end_year = last_day_of_year(end_year)
    utc_now = datetime.now(timezone.utc)
    end_date = utc_now if last_day_of_end_year > utc_now else last_day_of_end_year
    return start_date, end_date


def convert_date_strings_to_datetime(input_dict):
    output_dict = {}

    for key, value in input_dict.items():
        if key.endswith("_date"):
            try:
                # Convert the value to a datetime object
                value = parser.isoparse(value).astimezone(timezone.utc) if value else None
            except ValueError:
                # Handle invalid datetime strings gracefully
                logging.warning(f"Unable to convert '{value}' to datetime for key '{key}'")
        output_dict[key] = value

    return output_dict

