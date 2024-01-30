import logging
import os
import time
from datetime import timezone, datetime, timedelta
from random import randint


def random_sleep(dry_run):
    time.sleep(0 if dry_run else randint(7, 15))


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
