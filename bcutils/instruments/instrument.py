from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Instrument(ABC):
    id: str

    @abstractmethod
    def __str__(self) -> str:
        return f"{self.id}"

    @abstractmethod
    def get_code(self):
        pass

    @abstractmethod
    def get_symbol(self):
        pass

    @abstractmethod
    def is_dated(self):
        pass
