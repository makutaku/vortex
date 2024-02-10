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
    logging.info(f"Waiting for {secs}s to avoid bot detection ...")
    time.sleep(secs)


def create_full_path(file_path):
    # Get the directory part of the file path
    directory = os.path.dirname(file_path)

    # Create the full path if it doesn't exist
    if not os.path.exists(directory):
        logging.info(f"Creating directory '{directory}'")
        os.makedirs(directory)

    return file_path


def get_first_and_last_day_of_years(start_year, end_year, tz=timezone.utc):
    start_date = datetime(start_year, 1, 1, tzinfo=tz)
    end_date = datetime(end_year, 12, 31, 23, 59, 59, tzinfo=tz)

    return start_date, end_date


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


def is_list_of_strings(variable):
    if isinstance(variable, list):
        return all(isinstance(item, str) for item in variable)
    return False


def merge_dicts(list_of_dicts):
    merged_dict = {}
    for d in list_of_dicts:
        for key, value in d.items():
            if key in merged_dict:
                raise ValueError(f"Duplicate key found: {key}")
            merged_dict[key] = value
    return merged_dict


def get_absolute_path(directory: str) -> str:
    return os.path.abspath(os.path.expanduser(directory))


def total_elements_in_dict_of_lists(dictionary):
    if not dictionary:
        return 0

    total_elements = 0
    for value in dictionary.values():
        if isinstance(value, list):
            total_elements += len(value)
        else:
            raise ValueError("Dictionary values must be lists")

    return total_elements
