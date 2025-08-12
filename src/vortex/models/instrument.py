from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Instrument(ABC):
    id: str

    @abstractmethod
    def __str__(self) -> str:
        return f"{self.id}"

    @abstractmethod
    def get_code(self) -> str:
        pass

    @abstractmethod
    def get_symbol(self) -> str:
        pass

    @abstractmethod
    def is_dated(self) -> bool:
        pass
