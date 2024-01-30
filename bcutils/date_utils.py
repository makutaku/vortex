import calendar
from datetime import datetime, timedelta, timezone

import pytz

from bcutils.utils import last_day_of_year


def reverse_date_iterator(start, end, step):
    current = end
    while current >= start:
        yield current
        current -= step


def calculate_date_range(days, month, year):
    # for expired contracts the end date would be the expiry date;
    # for KISS sake, lets assume expiry is last date of contract month
    last_day_of_the_month = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day_of_the_month)
    # but, if that end_date is in the future, then we may as well make it today...
    now = datetime.now()
    if now.date() < end_date.date():
        end_date = now
    # assumption no.2: lets set start date at <day_count> days before end date
    day_count = timedelta(days=days)
    start_date = end_date - day_count

    timezone = pytz.UTC
    start_date = timezone.localize(start_date)
    end_date = timezone.localize(end_date)

    return start_date, end_date


def convert_download_range_to_datetime(start_year, end_year):
    first_day_of_start_year = last_day_of_year(start_year - 1) + timedelta(days=1)
    start_date = first_day_of_start_year
    last_day_of_end_year = last_day_of_year(end_year)
    utc_now = datetime.now(timezone.utc)
    end_date = utc_now if last_day_of_end_year > utc_now else last_day_of_end_year
    return start_date, end_date
