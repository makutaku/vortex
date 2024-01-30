import json
import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

from bcutils.more_utils import HistoricalDataResult
from bcutils.period import Period
from bcutils.storage_utils import save_price_data

SELF_IMPOSED_MAX_DAILY_DOWNLOADS = 150
MAX_HISTORICAL_BARS_PER_DOWNLOAD = 20000
BARCHART_PASSWORD = "BARCHART_PASSWORD"
BARCHART_USERNAME = "BARCHART_USERNAME"
BARCHART_URL = 'https://www.barchart.com/'
BARCHART_LOGIN_URL = BARCHART_URL + 'login'
BARCHART_LOGOUT_URL = BARCHART_URL + 'logout'
BARCHART_DOWNLOAD_URL = BARCHART_URL + 'my/download'
BARCHART_ALLOWANCE_URL = BARCHART_DOWNLOAD_URL


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


def request_download(xsrf_token, hist_csrf_token, contract, period, session, url, start_date, end_date):
    headers = build_download_request_headers(url, xsrf_token)
    payload = build_download_request_payload(hist_csrf_token, contract, period, start_date, end_date)
    resp = session.post(BARCHART_DOWNLOAD_URL, headers=headers, data=payload)
    logging.info(f"POST {BARCHART_DOWNLOAD_URL}, "
                 f"status: {resp.status_code}, "
                 f"data length: {len(resp.content)}")
    return resp


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


def logout(session):
    logging.info(f"Logging out ...")
    resp = session.get(BARCHART_LOGOUT_URL, timeout=10)
    logging.info(f"GET {BARCHART_LOGOUT_URL}, status: {resp.status_code}")
    logging.info(f"Logged out.")


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


def download_data(xsrf_token, hist_csrf_token, contract, period, session, start_date, end_date, url, full_path):
    resp = request_download(xsrf_token, hist_csrf_token, contract, period, session, url, start_date, end_date)
    low_data = False
    if resp.status_code == 200:
        if 'Error retrieving data' not in resp.text:
            low_data = save_price_data(full_path, period, resp.text)
        else:
            logging.info(f"Barchart error retrieving data for '{full_path}'")

    return low_data


def get_allowance_token(session, url, xsf_token):
    allowance, xsf_token = check_allowance(session, url, xsf_token)
    if allowance.get('error') is not None or int(allowance.get('count', '0')) > SELF_IMPOSED_MAX_DAILY_DOWNLOADS:
        return HistoricalDataResult.EXCEED, xsf_token
    if not allowance['success']:
        logging.info(f"No downloadable data available for stock")
        return HistoricalDataResult.NONE, xsf_token

    return HistoricalDataResult.OK, xsf_token


def download_stock_historic_prices(contract, dry_run, end_date, file_path, period, session, start_date):
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

    result, xsf_token = get_allowance_token(session, url, xsf_token)
    if result != HistoricalDataResult.OK:
        return result

    if dry_run:
        logging.info(f"Skipping data download: dry_run")
        return HistoricalDataResult.OK

    hist_csrf_token = scrape_csrf_token(hist_resp)
    low_data = download_data(xsf_token, hist_csrf_token, contract, period, session, start_date, end_date, url,
                             file_path)
    logging.info(f"Finished downloading historic {period.value} prices for stock '{contract}'")
    return HistoricalDataResult.LOW if low_data else HistoricalDataResult.OK


def download_futures_historic_prices(contract, dry_run, end_date, file_path, period, session, start_date):
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

    result, xsf_token = get_allowance_token(session, url, xsf_token)
    if result != HistoricalDataResult.OK:
        return result

    if dry_run:
        logging.info(f"Skipping data download: dry_run")
        return HistoricalDataResult.OK

    hist_csrf_token = scrape_csrf_token(hist_resp)
    low_data = download_data(xsf_token, hist_csrf_token, contract, period, session, start_date, end_date, url,
                             file_path)
    logging.info(f"Finished downloading historic {period.value} prices for contract '{contract}'")
    return HistoricalDataResult.LOW if low_data else HistoricalDataResult.OK
