import logging
import os
import time
from datetime import timezone, datetime, date, timedelta
from random import randint
from typing import Dict, Any, List, Optional, Tuple, Union, Generator

from dateutil import parser

from vortex.models.period import Period


def random_sleep(n: int = 15) -> None:
    secs = randint(1, 1 + n)
    logging.info(f"Waiting for {secs}s to avoid bot detection ...")
    time.sleep(secs)


def create_full_path(file_path: str) -> str:
    # Get the directory part of the file path
    directory = os.path.dirname(file_path)

    # Create the full path if it doesn't exist
    if not os.path.exists(directory):
        logging.info(f"Creating directory '{directory}'")
        os.makedirs(directory)

    return file_path


def get_first_and_last_day_of_years(start_year: int, end_year: int, tz: timezone = timezone.utc) -> Tuple[datetime, datetime]:
    start_date = datetime(start_year, 1, 1, tzinfo=tz)
    end_date = datetime(end_year, 12, 31, 23, 59, 59, tzinfo=tz)

    return start_date, end_date


def date_range_generator(start_date: datetime, end_date: datetime, delta: Optional[timedelta]) -> Generator[Tuple[datetime, datetime], None, None]:

    if start_date > end_date:
        raise ValueError(f"start_date must come before end_date")

    if delta is None:
        yield start_date, end_date
        return

    current_date = start_date
    while current_date < end_date:
        yield current_date, min(current_date + delta, end_date)
        current_date += delta


def reverse_date_range_generator(start_date: datetime, end_date: datetime, delta: Optional[timedelta]) -> Generator[Tuple[datetime, datetime], None, None]:

    if delta is None:
        yield start_date, end_date
        return

    current_date = end_date
    while current_date > start_date:
        yield max(current_date - delta, start_date), current_date
        current_date -= delta


#
# def calculate_date_range(days, month, year):
#
#     # for expired contracts the end date would be the expiry date;
#     # for KISS’ sake, lets assume expiry is last date of contract month
#     last_day_of_the_month = calendar.monthrange(year, month)[1]
#     end = datetime(year, month, last_day_of_the_month)
#
#     # assumption no.2: lets set start date at <duration> days before end date
#     duration = timedelta(days=days)
#     start = end - duration
#
#     start = pytz.UTC.localize(start)
#     end = pytz.UTC.localize(end)
#
#     return start, end


def convert_date_strings_to_datetime(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    output_dict = {}

    for key, value in input_dict.items():
        if key.endswith("_date"):
            try:
                # Convert the value to a datetime object
                value = parser.isoparse(value).astimezone(timezone.utc) if value else None
            except ValueError:
                # Handle invalid datetime strings gracefully
                logging.warning(f"Unable to convert '{value}' to datetime for key '{key}'")
        elif key == "period":
            try:
                # Convert the value to a datetime object
                value = Period(value) if value else None
            except ValueError:
                # Handle invalid datetime strings gracefully
                logging.warning(f"Unable to convert '{value}' to Period for key '{key}'")

        output_dict[key] = value

    return output_dict


def is_list_of_strings(variable: Any) -> bool:
    if isinstance(variable, list):
        return all(isinstance(item, str) for item in variable)
    return False


def merge_dicts(list_of_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged_dict = {}
    for d in list_of_dicts:
        for key, value in d.items():
            if key in merged_dict:
                raise ValueError(f"Duplicate key found: {key}")
            merged_dict[key] = value
    return merged_dict


def get_absolute_path(directory: str) -> str:
    return os.path.abspath(os.path.expanduser(directory))


def total_elements_in_dict_of_lists(dictionary: Dict[str, List[Any]]) -> int:
    if not dictionary:
        return 0

    total_elements = 0
    for value in dictionary.values():
        if isinstance(value, list):
            total_elements += len(value)
        else:
            raise ValueError("Dictionary values must be lists")

    return total_elements


def generate_year_month_tuples(start_date: Union[datetime, date], end_date: Union[datetime, date]) -> Generator[Tuple[int, int], None, None]:
    # Ensure both start_date and end_date are of type datetime.date
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    # Ensure start_date is set to the beginning of its month to include the entire range
    start_date = date(start_date.year, start_date.month, 1)

    # Yield each year and month tuple only as needed, until the current date exceeds the end date
    while start_date <= end_date:
        yield start_date.year, start_date.month
        # Calculate the first day of the next month
        # Check if the current month is December
        if start_date.month == 12:
            # Move to January of the next year
            start_date = date(start_date.year + 1, 1, 1)
        else:
            # Move to the next month in the same year
            start_date = date(start_date.year, start_date.month + 1, 1)
