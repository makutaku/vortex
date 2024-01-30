import re


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


CONTRACT_PATTERN = r"[A-Za-z]{2}[FGHJKMNQUVXZ]\d{2}"
MONTH_LIST = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']


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


def get_code_from_year(year):
    year_code = str(year)[-2:]
    return year_code


def market_code_from_contract(contract):
    market_code = contract[:-3] if re.match(CONTRACT_PATTERN, contract) else contract
    return market_code
