import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AbstractContract(ABC):
    instrument: str

    @abstractmethod
    def __str__(self) -> str:
        return f"{self.instrument}"

    @abstractmethod
    def get_symbol(self):
        pass

    @abstractmethod
    def is_dated(self):
        pass


@dataclass
class FutureContract(AbstractContract):
    MONTH_LIST = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']

    futures_code: str
    year: int
    month_code: str
    month: int = field(init=False)
    contract_code: str = field(init=False)
    tick_date: datetime
    days_count: int

    def __post_init__(self):
        self.contract_code = self.make_contract_code()
        self.month = FutureContract.get_month_from_code(self.month_code)

    def __str__(self) -> str:
        return f"F|{self.instrument}|{self.contract_code}"

    def is_dated(self):
        return True

    def make_contract_code(self) -> str:
        year_code = FutureContract.get_code_for_year(self.year)
        return f"{self.futures_code}{self.month_code}{year_code}"

    def get_symbol(self):
        return self.contract_code

    @staticmethod
    def get_code_for_month(month: int) -> str:
        return FutureContract.MONTH_LIST[month]

    @staticmethod
    def get_month_from_code(month_code: str) -> int:
        return FutureContract.MONTH_LIST.index(month_code) + 1

    @staticmethod
    def get_code_for_year(year: int) -> str:
        year_code = str(year)[-2:]
        return year_code


@dataclass
class StockContract(AbstractContract):
    contract_code: str

    def __str__(self) -> str:
        return f"S|{self.instrument}|{self.contract_code}"

    def is_dated(self):
        return False

    def get_symbol(self):
        return self.contract_code


@dataclass
class Forex(AbstractContract):
    contract_code: str

    def __str__(self) -> str:
        return f"C|{self.instrument}|{self.contract_code}"

    def is_dated(self):
        return False

    def get_symbol(self):
        return self.contract_code
