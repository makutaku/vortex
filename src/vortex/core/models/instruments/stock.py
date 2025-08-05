from dataclasses import dataclass

from .instrument import Instrument


@dataclass
class Stock(Instrument):
    symbol: str

    def __str__(self) -> str:
        return f"S|{self.id}|{self.symbol}"

    def is_dated(self):
        return False

    def get_code(self):
        return self.symbol

    def get_symbol(self):
        return self.symbol
