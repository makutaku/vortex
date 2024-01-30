from datetime import datetime, timedelta

import pytz

from bcutils.contract_utils import market_code_from_contract
from bcutils.instrument_type import InstrumentType


def get_instrument_type(instr_config):
    return InstrumentType(instr_config.get('type', InstrumentType.Future.value))


def get_instrument_backfill_date(instr_config):
    backfill_date_str = instr_config.get('backfill_date', "2000-01-01")
    backfill_date = datetime.strptime(backfill_date_str, '%Y-%m-%d')
    timezone = pytz.UTC
    return timezone.localize(backfill_date)


def get_earliest_tick_date(force_daily, instr_config):
    if force_daily is True:
        tick_date = datetime.utcnow()
    elif 'tick_date' in instr_config:
        tick_date = datetime.strptime(instr_config['tick_date'], '%Y-%m-%d')
        tick_date = pytz.UTC.localize(tick_date)
        # we want to push this date slightly into the future to try and resolve issues around
        # the switchover date
        tick_date = tick_date + timedelta(days=90)
    else:
        tick_date = None
    return tick_date


def get_days_count(instr_config):
    if 'days_count' in instr_config:
        days_count = instr_config['days_count']
    else:
        days_count = 120
    return days_count


def build_inverse_map(contract_map):
    return {v['code']: k for k, v in contract_map.items()}


def get_contract_instrument(contract, inv_map):
    market_code = market_code_from_contract(contract)
    instrument = inv_map[market_code]
    return instrument
