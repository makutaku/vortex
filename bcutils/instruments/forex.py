from dataclasses import dataclass

from instruments.instrument import Instrument


@dataclass
class Forex(Instrument):
    symbol: str

    def __str__(self) -> str:
        return f"C|{self.id}|{self.symbol}"

    def is_dated(self):
        return False

    def get_code(self):
        return self.symbol

    def get_symbol(self):
        return self.symbol
