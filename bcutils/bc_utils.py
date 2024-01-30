#!/usr/bin/env python

import logging
import os
import os.path
import re
from datetime import datetime, timedelta
from itertools import cycle

import pytz

from bcutils.bc_api import BARCHART_PASSWORD, BARCHART_USERNAME, logout, create_bc_session, \
    download_stock_historic_prices, download_futures_historic_prices, MAX_HISTORICAL_BARS_PER_DOWNLOAD
from bcutils.config_utils import get_instrument_type, get_instrument_backfill_date, get_earliest_tick_date, \
    get_days_count, build_inverse_map, get_contract_instrument
from bcutils.contract_utils import get_contract_month, get_contract_year, get_code_from_year, \
    market_code_from_contract
from bcutils.date_utils import reverse_date_iterator, calculate_date_range, convert_download_range_to_datetime
from bcutils.instrument_type import InstrumentType
from bcutils.logging_utils import init_logging
from bcutils.more_utils import HistoricalDataResult
from bcutils.period import Period
from bcutils.storage_utils import resolve_output_directory, make_file_path_for_futures, \
    make_file_path_for_stock, file_is_placeholder_for_no_hourly_data, is_data_update_needed
from bcutils.utils import random_sleep, create_full_path
from config import CONTRACT_MAP

BARCHART_DRY_RUN = "BARCHART_DRY_RUN"
BARCHART_END_YEAR = "BARCHART_END_YEAR"
BARCHART_START_YEAR = "BARCHART_START_YEAR"
BARCHART_OUTPUT_DIR = "BARCHART_OUTPUT_DIR"


def parse_stock_contract_code(input_string):
    pattern = re.compile(r'([A-Z]+)([0-9]+[mhdWM])((?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01]))$')
    match = pattern.match(input_string)

    if match:
        symbol = match.group(1)
        period_str = match.group(2)
        date_str = match.group(3)

        try:
            period = Period(period_str)
            date = pytz.UTC.localize(datetime.strptime(date_str, '%Y%m%d'))
            return symbol, period, date
        except ValueError:
            return None
    else:
        return None


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

    return download_futures_historic_prices(contract, dry_run, end_date, file_path, period, session, start_date)


def save_prices_for_stock(
        contract,
        end_date,
        session,
        path,
        inv_map,
        backfill_date,
        period=Period.Hourly,
        dry_run=False):
    logging.info(f"Considering downloading historic {period.value} prices for '{contract}'")

    instrument = get_contract_instrument(contract, inv_map)
    days = period.max_historical_days(MAX_HISTORICAL_BARS_PER_DOWNLOAD)

    # we need to work out a date range for which we want the prices
    start_date = end_date - timedelta(days=days)

    file_path = make_file_path_for_stock(instrument, path, period)
    create_full_path(file_path)

    # do we have this file already?
    if os.path.isfile(file_path):
        logging.info(f"Data for stock '{contract}' already downloaded, evaluating ...")
        if not is_data_update_needed(contract, start_date, end_date, backfill_date, file_path):
            return HistoricalDataResult.EXISTS

    return download_stock_historic_prices(contract, dry_run, end_date, file_path, period, session, start_date)


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


def save_prices_for_contract(contract, contract_map, download_dir, dry_run, force_daily, inv_contract_map, session):
    logging.info(f"Processing contract {contract} ...")

    period = None
    end_date = None
    stock_tokens = parse_stock_contract_code(contract)
    if stock_tokens:
        contract, period, end_date = stock_tokens

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
        result = save_prices_for_stock(contract, end_date, session, download_dir, inv_contract_map, backfill_date,
                                       period=period, dry_run=dry_run)

    logging.info(f"Processed contract {contract}\n")
    return result


def get_instrument_config(contract, contract_map, inv_contract_map):
    market_code = market_code_from_contract(contract)
    instr = inv_contract_map[market_code]
    instr_config = contract_map[instr]
    return instr_config


def build_contract_list(start_year, end_year, contract_map=None):
    start_date, end_date = convert_download_range_to_datetime(start_year, end_year)
    contracts_per_instrument = {}
    contract_list = []
    count = 0

    if contract_map is None:
        contract_map = CONTRACT_MAP

    periods = [Period.Hourly, Period.Daily, Period.Minute_30]

    for instr in contract_map.keys():

        config_obj = contract_map[instr]
        futures_code = config_obj.get('code', 'none')
        if futures_code == 'none':
            continue
        roll_cycle = config_obj.get('cycle', None)
        instrument_type = get_instrument_type(config_obj)
        instrument_list = []
        backfill_date = get_instrument_backfill_date(config_obj)
        instr_start_date = start_date if start_date > backfill_date else backfill_date
        instr_end_date = end_date

        if instrument_type == InstrumentType.Future and roll_cycle:
            for year in range(start_year, end_year):
                year_code = get_code_from_year(year)
                for month_code in list(roll_cycle):
                    instrument_list.append(f"{futures_code}{month_code}{year_code}")
        elif instrument_type == InstrumentType.Stock:
            for period in periods:
                step_in_days = period.max_historical_days(MAX_HISTORICAL_BARS_PER_DOWNLOAD)
                for step_end_date in reverse_date_iterator(instr_start_date, instr_end_date,
                                                           timedelta(days=step_in_days)):
                    instrument_list.append(f"{futures_code}{period.to_string()}{step_end_date.strftime('%Y%m%d')}")

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
        start_year=int(bc_config.get(BARCHART_START_YEAR, "2007")),
        end_year=int(bc_config.get(BARCHART_END_YEAR, "2012")),
        dry_run=bc_config.get(BARCHART_DRY_RUN, "False") == "True")

    logging.info(f"Done!")
