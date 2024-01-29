#!/usr/bin/env python

import calendar
import enum
import io
import json
import logging
import os
import os.path
import time
import urllib.parse
from datetime import datetime, timedelta
from itertools import cycle
from random import randint

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import CONTRACT_MAP
import re

CONTRACT_PATTERN = r"[A-Za-z]{2}[FGHJKMNQUVXZ]\d{2}"

BARCHART_CLOSE_COLUMN = "Last"

CLOSE_COLUMN = "Close"

BARCHART_DATE_TIME_COLUMN = 'Time'
DATE_TIME_COLUMN = 'DATETIME'

SOURCE_TIME_ZONE = 'US/Central'

BARCHART_PASSWORD = "BARCHART_PASSWORD"
BARCHART_USERNAME = "BARCHART_USERNAME"
BARCHART_DRY_RUN = "BARCHART_DRY_RUN"
BARCHART_END_YEAR = "BARCHART_END_YEAR"
BARCHART_START_YEAR = "BARCHART_START_YEAR"
BARCHART_OUTPUT_DIR = "BARCHART_OUTPUT_DIR"

MIN_DAYS_TO_TRIGGER_UPDATE = timedelta(days=7)


class Period(enum.Enum):
    Minute_1 = '1m'
    Minute_2 = '2m'
    Minute_5 = '5m'
    Minute_15 = '15m'
    Minute_30 = '30m'
    Hourly = '1h'
    Daily = '1d'
    Weekly = '1W'
    Monthly = '1M'
    Quarterly = '3M'

    def to_string(self):
        return self.value

    def max_historical_days(self):
        trading_days_per_week = 5
        trading_hours_per_day = 7

        hour_bars_in_period = {
            '1m': 1.0 / 60,
            '2m': 1.0 / 30,
            '5m': 1.0 / 12,
            '15m': 1.0 / 4,
            '30m': 1.0 / 2,
            '1h': 1.0,
            '1d': trading_hours_per_day * 1.0,  # Adjust for trading hours per day
            '1W': trading_days_per_week * trading_hours_per_day * 1.0,  # Adjust for trading hours per day
            '1M': trading_days_per_week * trading_hours_per_day * 1.0 * 4,  # Adjust for trading hours per day
            '3M': trading_days_per_week * trading_hours_per_day * 1.0 * 4 * 3,  # Adjust for trading hours per day
        }

        # Calculate the minimum number of days to cover 10,000 bars
        days_required = 10000 * hour_bars_in_period[self.value] / trading_hours_per_day

        return int(days_required)


class InstrumentType(enum.StrEnum):
    Future = 'future'
    Stock = 'stock'


class HistoricalDataResult(enum.Enum):
    NONE = 1
    OK = 2
    EXISTS = 3
    EXCEED = 4
    LOW = 5


MONTH_LIST = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
BARCHART_URL = 'https://www.barchart.com/'
BARCHART_LOGIN_URL = BARCHART_URL + 'login'
BARCHART_LOGOUT_URL = BARCHART_URL + 'logout'
BARCHART_DOWNLOAD_URL = BARCHART_URL + 'my/download'
BARCHART_ALLOWANCE_URL = BARCHART_DOWNLOAD_URL


def month_from_contract_letter(contract_letter):
    """
    Returns month number (1 is January) from contract letter

    :param contract_letter:
    :return:
    """
    try:
        month_number = MONTH_LIST.index(contract_letter)
    except ValueError:
        return None

    return month_number + 1


def create_bc_session(config_obj: dict, do_login=True):
    # start a session
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    if do_login is True and \
            BARCHART_USERNAME not in config_obj or \
            BARCHART_PASSWORD not in config_obj:
        raise Exception('Barchart credentials are required')

    if do_login:
        if BARCHART_USERNAME not in config_obj or BARCHART_PASSWORD not in config_obj:
            raise Exception('Barchart credentials are required')
        login(config_obj, session)

    return session


def login(config_obj, session):
    logging.info(f"Logging in ...")
    # GET the login page, scrape to get CSRF token
    resp = session.get(BARCHART_LOGIN_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    tag = soup.find(type='hidden')
    csrf_token = tag.attrs['value']
    logging.info(f"GET {BARCHART_LOGIN_URL}, status: {resp.status_code}, CSRF token: {csrf_token}")
    # login to site
    payload = build_login_payload(csrf_token, config_obj)
    resp = session.post(BARCHART_LOGIN_URL, data=payload)
    logging.info(f"POST {BARCHART_LOGIN_URL}, status: {resp.status_code}")
    if resp.url == BARCHART_LOGIN_URL:
        raise Exception('Invalid Barchart credentials')
    logging.info(f"Logged in.")


def build_login_payload(csrf_token, config_obj):
    payload = {
        'email': config_obj[BARCHART_USERNAME],
        'password': config_obj[BARCHART_PASSWORD],
        '_token': csrf_token
    }
    return payload


def save_prices_for_future(
        contract,
        session,
        path,
        inv_map,
        period=Period.Hourly,
        tick_date=None,
        days=120,
        dry_run=False):
    logging.info(f"Considering downloading historic {period.value} prices for {contract}")

    year = get_contract_year(contract)
    month = get_contract_month(contract)
    instrument = get_contract_instrument(contract, inv_map)
    file_path = make_file_path_for_futures(month, year, instrument, path)
    create_full_path(file_path)

    # do we have this file already?
    if os.path.isfile(file_path):
        if file_is_placeholder_for_no_hourly_data(file_path):
            logging.info("Placeholder found indicating missing hourly data, switching to daily")
            period = Period.Daily
        else:
            logging.info(f"Data for contract '{contract}' already downloaded, skipping")
            return HistoricalDataResult.EXISTS

    # we need to work out a date range for which we want the prices
    start_date, end_date = calculate_date_range(days, month, year)

    # hourly data only goes back to a certain date, depending on the exchange
    # if our dates are before that date, switch to daily prices
    if tick_date is not None and start_date < tick_date:
        logging.info(f"Switching to daily prices for '{contract}', "
                     f"{start_date.strftime('%Y-%m-%d')} is before "
                     f"{tick_date.strftime('%Y-%m-%d')}")
        period = Period.Daily

    logging.info(f"Getting historic {period.value} prices for contract '{contract}', "
                 f"from {start_date.strftime('%Y-%m-%d')} "
                 f"to {end_date.strftime('%Y-%m-%d')}")

    # open historic data download page for required contract
    url = get_historic_quote_futures_url(contract)
    hist_resp = session.get(url)
    logging.info(f"GET {url}, status {hist_resp.status_code}")

    if hist_resp.status_code != 200:
        logging.info(f"No downloadable data available for contract '{contract}'")
        return HistoricalDataResult.NONE

    # check allowance
    xsf_token = extract_xsrf_token(hist_resp)
    allowance, xsf_token = check_allowance(session, url, xsf_token)

    if allowance.get('error') is not None:
        return HistoricalDataResult.EXCEED

    if not allowance['success']:
        logging.info(f"No downloadable data available for contract '{contract}'")
        return HistoricalDataResult.NONE

    if dry_run:
        logging.info(f"Skipping data download: dry_run")
        return HistoricalDataResult.OK

    hist_csrf_token = scrape_csrf_token(hist_resp)
    low_data = download_data(xsf_token, hist_csrf_token, contract, period, session, start_date, end_date, url,
                             file_path)

    logging.info(f"Finished downloading historic {period.value} prices for contract '{contract}'")

    return HistoricalDataResult.LOW if low_data else HistoricalDataResult.OK


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


def save_prices_for_stock(
        contract,
        session,
        path,
        inv_map,
        backfill_date,
        period=Period.Hourly,
        dry_run=False):
    logging.info(f"Considering downloading historic {period.value} prices for '{contract}'")

    # Fetch current month and year
    current_date = datetime.now()
    month = current_date.month
    year = current_date.year
    instrument = get_contract_instrument(contract, inv_map)
    days = period.max_historical_days()

    # we need to work out a date range for which we want the prices
    start_date, end_date = calculate_date_range(days, month, year)

    file_path = make_file_path_for_stock(instrument, path, period)
    create_full_path(file_path)

    # do we have this file already?
    if os.path.isfile(file_path):
        logging.info(f"Data for stock '{contract}' already downloaded, evaluating ...")
        if not is_data_update_needed(contract, start_date, end_date, backfill_date, file_path):
            return HistoricalDataResult.EXISTS

    logging.info(f"Getting historic {period.value} prices for stock '{contract}', "
                 f"from {start_date.strftime('%Y-%m-%d')} "
                 f"to {end_date.strftime('%Y-%m-%d')}")

    # open historic data download page for required contract
    url = get_historic_quote_stocks_url(contract)
    hist_resp = session.get(url)
    logging.info(f"GET {url}, status {hist_resp.status_code}")

    if hist_resp.status_code != 200:
        logging.info(f"No downloadable data available for stock '{contract}'")
        return HistoricalDataResult.NONE

    # check allowance
    xsf_token = extract_xsrf_token(hist_resp)
    allowance, xsf_token = check_allowance(session, url, xsf_token)

    if allowance.get('error') is not None:
        return HistoricalDataResult.EXCEED

    if not allowance['success']:
        logging.info(f"No downloadable data available for stock '{contract}'")
        return HistoricalDataResult.NONE

    if dry_run:
        logging.info(f"Skipping data download: dry_run")
        return HistoricalDataResult.OK

    hist_csrf_token = scrape_csrf_token(hist_resp)
    low_data = download_data(xsf_token, hist_csrf_token, contract, period, session, start_date, end_date, url,
                             file_path)

    logging.info(f"Finished downloading historic {period.value} prices for stock '{contract}'")

    return HistoricalDataResult.LOW if low_data else HistoricalDataResult.OK


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

    import pytz
    timezone = pytz.UTC
    start_date = timezone.localize(start_date)
    end_date = timezone.localize(end_date)

    return start_date, end_date


def make_file_path_for_futures(month, year, instrument, path):
    date_code = str(year) + '{0:02d}'.format(month)
    filename = f"{instrument}_{date_code}00.csv"
    full_path = f"{path}/futures/{filename}"
    return full_path


def make_file_path_for_stock(symbol, path, period):
    filename = f"{symbol}.csv"
    full_path = f"{path}/stocks/{period.value}/{filename}"
    return full_path


def create_full_path(file_path):
    # Get the directory part of the file path
    directory = os.path.dirname(file_path)

    # Create the full path if it doesn't exist
    if not os.path.exists(directory):
        logging.info(f"Creating directory '{directory}'")
        os.makedirs(directory)

    return file_path


def get_contract_instrument(contract, inv_map):
    market_code = market_code_from_contract(contract)
    instrument = inv_map[market_code]
    return instrument


def market_code_from_contract(contract):
    market_code = contract[:-3] if re.match(CONTRACT_PATTERN, contract) else contract
    return market_code


def month_code_from_contract(contract):
    market_code = contract[-3] if re.match(CONTRACT_PATTERN, contract) else None
    return market_code


def year_code_from_contract(contract):
    year_code = int(contract[-2:]) if re.match(CONTRACT_PATTERN, contract) else None
    return year_code


def get_contract_month(contract):
    month_code = month_code_from_contract(contract)
    month = month_from_contract_letter(month_code)
    return month


def get_contract_year(contract):
    year_code = year_code_from_contract(contract)
    if year_code > 30:
        year = 1900 + year_code
    else:
        year = 2000 + year_code
    return year


def download_data(xsrf_token, hist_csrf_token, contract, period, session, start_date, end_date, url, full_path):
    resp = request_download(xsrf_token, hist_csrf_token, contract, period, session, url, start_date, end_date)
    low_data = False
    if resp.status_code == 200:
        if 'Error retrieving data' not in resp.text:
            low_data = save_price_data(full_path, period, resp.text)
        else:
            logging.info(f"Barchart error retrieving data for '{full_path}'")

    return low_data


def request_download(xsrf_token, hist_csrf_token, contract, period, session, url, start_date, end_date):
    headers = build_download_request_headers(url, xsrf_token)
    payload = build_download_request_payload(hist_csrf_token, contract, period, start_date, end_date)
    resp = session.post(BARCHART_DOWNLOAD_URL, headers=headers, data=payload)
    logging.info(f"POST {BARCHART_DOWNLOAD_URL}, "
                 f"status: {resp.status_code}, "
                 f"data length: {len(resp.content)}")
    return resp


def check_allowance(session, url, xsf_token):
    logging.info("Checking allowance")
    headers = build_allowance_request_headers(url, xsf_token)
    payload = build_allowance_payload()
    resp = session.post(BARCHART_ALLOWANCE_URL, headers=headers, data=payload)
    xsf_token = extract_xsrf_token(resp)
    allowance = json.loads(resp.text)
    logging.info(f"POST {BARCHART_ALLOWANCE_URL}, "
                 f"status: {resp.status_code}, "
                 f"allowance success: {allowance.get('success', 'NO')}, "
                 f"allowance count: {allowance.get('count', 'N/A')}")
    return allowance, xsf_token


def build_allowance_request_headers(url, xsf_token):
    headers = build_download_request_headers(url, xsf_token)
    return headers


def build_allowance_payload():
    payload = {'onlyCheckPermissions': 'true'}
    return payload


def build_download_request_payload(hist_csrf_token, contract, period, start_date, end_date):
    payload = {'_token': hist_csrf_token,
               'fileName': contract + '_Daily_Historical Data',
               'symbol': contract,
               'fields': 'tradeTime.format(Y-m-d),openPrice,highPrice,lowPrice,lastPrice,volume',
               'startDate': start_date.strftime("%Y-%m-%d"),
               'endDate': end_date.strftime("%Y-%m-%d"),
               'orderBy': 'tradeTime',
               'orderDir': 'asc',
               'method': 'historical',
               'limit': '10000',
               'customView': 'true',
               'pageTitle': 'Historical Data'}
    if period == Period.Daily:
        payload['type'] = 'eod'
        payload['period'] = Period.Daily
    elif period == Period.Hourly:
        payload['type'] = 'minutes'
        payload['interval'] = 60
    elif period == Period.Minute_30:
        payload['type'] = 'minutes'
        payload['interval'] = 30
    elif period == Period.Minute_15:
        payload['type'] = 'minutes'
        payload['interval'] = 15
    elif period == Period.Minute_5:
        payload['type'] = 'minutes'
        payload['interval'] = 5
    else:
        raise NotImplemented
    return payload


def build_download_request_headers(url, xsrf_token):
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': url,
        'x-xsrf-token': xsrf_token
    }
    return headers


def save_price_data(file_path, period, data):

    if period in [Period.Daily, Period.Weekly, Period.Monthly, Period.Quarterly]:
        date_format = '%Y-%m-%d'
    else:
        date_format = '%m/%d/%Y %H:%M'

    iostr = io.StringIO(data)
    df = pd.read_csv(iostr, skipfooter=1, engine='python')
    df = df.rename(columns={BARCHART_DATE_TIME_COLUMN: DATE_TIME_COLUMN})
    df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format=date_format)
    df.set_index(DATE_TIME_COLUMN, inplace=True)
    df.index = df.index.tz_localize(tz=SOURCE_TIME_ZONE).tz_convert('UTC')
    df = df.rename(columns={BARCHART_CLOSE_COLUMN: CLOSE_COLUMN})

    # If data already exists, merge new data with existing data
    if os.path.isfile(file_path):
        existing_df = pd.read_csv(file_path)
        existing_df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
        existing_df.set_index(DATE_TIME_COLUMN, inplace=True)
        existing_df.update(df)
        df = existing_df

    logging.info(f"writing data to: {file_path}")
    df.to_csv(file_path, date_format='%Y-%m-%dT%H:%M:%S%z')
    return len(df) < 3


def extract_xsrf_token(hist_resp):
    return urllib.parse.unquote(hist_resp.cookies['XSRF-TOKEN'])


def scrape_csrf_token(hist_resp):
    hist_soup = BeautifulSoup(hist_resp.text, 'html.parser')
    hist_tag = hist_soup.find(name='meta', attrs={'name': 'csrf-token'})
    hist_csrf_token = hist_tag.attrs['content']
    return hist_csrf_token


def get_historic_quote_futures_url(contract):
    url = f"{BARCHART_URL}futures/quotes/{contract}/historical-download"
    return url


def get_historic_quote_stocks_url(symbol):
    url = f"{BARCHART_URL}stocks/quotes/{symbol}/historical-download"
    return url


def get_barchart_downloads(
        session,
        contract_map=None,
        save_directory=None,
        start_year=1950,
        end_year=2025,
        dry_run=False,
        force_daily=False):
    logging.info(f"Processing downloads from {start_year} to {end_year} ...")
    logging.info(f"directory: {save_directory}  dry_run: {dry_run}  force_daily: {force_daily}")

    low_data_contracts = []

    if contract_map is None:
        contract_map = CONTRACT_MAP

    inv_contract_map = build_inverse_map(contract_map)

    try:
        init_logging()

        download_dir = resolve_output_directory(save_directory)
        contract_list = build_contract_list(start_year, end_year, contract_map=contract_map)

        for contract in contract_list:

            result = save_prices_for_contract(contract, contract_map, download_dir, dry_run, force_daily,
                                              inv_contract_map, session)
            if result == HistoricalDataResult.EXISTS:
                continue
            if result == HistoricalDataResult.NONE:
                continue
            if result == HistoricalDataResult.LOW:
                low_data_contracts.append(contract)
                continue
            if result == HistoricalDataResult.EXCEED:
                logging.info('Max daily download reached, aborting')
                break

            # cursory attempt to not appear like a bot
            random_sleep(dry_run)

        if low_data_contracts:
            logging.warning(f"Low/poor data found for: {low_data_contracts}, maybe check config")

        logout(session)

    except Exception as e:  # absorbing exception by design
        logging.error(f"Error {e}")


def resolve_output_directory(save_directory):
    if save_directory is None:
        download_dir = os.getcwd()
    else:
        download_dir = save_directory
    if not os.path.exists(download_dir) or not os.path.isdir(download_dir):
        raise Exception(f"Output directory '{download_dir}' does not exist.")
    return download_dir


def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


def save_prices_for_contract(contract, contract_map, download_dir, dry_run, force_daily, inv_contract_map, session):
    logging.info(f"Processing contract {contract} ...")

    result = HistoricalDataResult.NONE
    instr_config = get_instrument_config(contract, contract_map, inv_contract_map)
    instrument_type = get_instrument_type(instr_config)
    backfill_date = get_instrument_backfill_date(instr_config)

    if instrument_type == InstrumentType.Future:
        # calculate the earliest date for which we have hourly data
        tick_date = get_earliest_tick_date(force_daily, instr_config)
        days_count = get_days_count(instr_config)
        result = save_prices_for_future(contract, session, download_dir, inv_contract_map, period=Period.Hourly,
                                        tick_date=tick_date, days=days_count, dry_run=dry_run)
    elif instrument_type == InstrumentType.Stock:
        # calculate the earliest date for which we have hourly data
        # days_count = get_days_count(instr_config)
        instrument_type = get_instrument_type(instr_config)
        result = save_prices_for_stock(contract, session, download_dir, inv_contract_map, backfill_date,
                                       period=Period.Minute_30, dry_run=dry_run)

    logging.info(f"Processed contract {contract}\n")
    return result


def get_instrument_config(contract, contract_map, inv_contract_map):
    market_code = market_code_from_contract(contract)
    instr = inv_contract_map[market_code]
    instr_config = contract_map[instr]
    return instr_config


def random_sleep(dry_run):
    time.sleep(0 if dry_run else randint(7, 15))


def get_days_count(instr_config):
    if 'days_count' in instr_config:
        days_count = instr_config['days_count']
    else:
        days_count = 120
    return days_count


def get_instrument_type(instr_config):
    return InstrumentType(instr_config.get('type', InstrumentType.Future.value))


def get_instrument_backfill_date(instr_config):
    backfill_date_str = instr_config.get('backfill_date', "2000-01-01")
    backfill_date = datetime.strptime(backfill_date_str, '%Y-%m-%d')
    import pytz
    timezone = pytz.UTC
    return timezone.localize(backfill_date)


def get_earliest_tick_date(force_daily, instr_config):
    if force_daily is True:
        tick_date = datetime.now()
    elif 'tick_date' in instr_config:
        tick_date = datetime.strptime(instr_config['tick_date'], '%Y-%m-%d')
        # we want to push this date slightly into the future to try and resolve issues around
        # the switchover date
        tick_date = tick_date + timedelta(days=90)
    else:
        tick_date = None
    return tick_date


def logout(session):
    logging.info(f"Logging out ...")
    resp = session.get(BARCHART_LOGOUT_URL, timeout=10)
    logging.info(f"GET {BARCHART_LOGOUT_URL}, status: {resp.status_code}")
    logging.info(f"Logged out.")


def build_contract_list(start_year, end_year, contract_map=None):
    contracts_per_instrument = {}
    contract_list = []
    count = 0

    if contract_map is None:
        contract_map = CONTRACT_MAP

    for instr in contract_map.keys():
        config_obj = contract_map[instr]
        futures_code = config_obj.get('code', 'none')
        if futures_code == 'none':
            continue
        roll_cycle = config_obj.get('cycle', None)
        instrument_type = get_instrument_type(config_obj)
        instrument_list = []

        if instrument_type == InstrumentType.Future and roll_cycle:
            for year in range(start_year, end_year):
                for month_code in list(roll_cycle):
                    instrument_list.append(f"{futures_code}{month_code}{str(year)[-2:]}")
        elif instrument_type == InstrumentType.Stock:
            instrument_list.append(futures_code)

        contracts_per_instrument[instr] = instrument_list
        count = count + len(instrument_list)

    logging.info(f'Instrument count: {count}')

    pool = cycle(contract_map.keys())

    while len(contract_list) < count:
        try:
            instr = next(pool)
        except StopIteration:
            continue
        if instr not in contracts_per_instrument:
            continue
        instr_list = contracts_per_instrument[instr]
        config_obj = contract_map[instr]
        roll_cycle = config_obj.get('cycle', None)

        if not roll_cycle:
            max_count = 1
        else:
            if len(roll_cycle) > 10:
                max_count = 3
            elif len(roll_cycle) > 7:
                max_count = 2
            else:
                max_count = 1

        for _ in range(0, max_count):
            if len(instr_list) > 0:
                contract_list.append(instr_list.pop())

    # return ['CTH21', 'CTK21', 'CTN21', 'CTU21', 'CTZ21', 'CTH22']

    logging.info(f"Contract list: {contract_list}")
    return contract_list


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


def build_inverse_map(contract_map):
    return {v['code']: k for k, v in contract_map.items()}


if __name__ == "__main__":
    init_logging()
    logging.info(f"Starting ...")

    env_vars = [
        BARCHART_USERNAME,
        BARCHART_PASSWORD,
        BARCHART_OUTPUT_DIR,
        BARCHART_START_YEAR,
        BARCHART_END_YEAR,
        BARCHART_DRY_RUN,
    ]
    bc_config = {v: os.environ.get(v) for v in env_vars if v in os.environ}

    bc_session = create_bc_session(config_obj=bc_config)
    get_barchart_downloads(
        bc_session,
        contract_map=CONTRACT_MAP,
        save_directory=bc_config.get(BARCHART_OUTPUT_DIR, "./data"),
        start_year=int(bc_config.get(BARCHART_START_YEAR, "2023")),
        end_year=int(bc_config.get(BARCHART_END_YEAR, "2024")),
        dry_run=bc_config.get(BARCHART_DRY_RUN, "False") == "True")

    logging.info(f"Done!")
