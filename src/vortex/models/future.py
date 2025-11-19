import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta


from .instrument import Instrument


@dataclass
class Future(Instrument):
    MONTH_LIST = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

    futures_code: str
    year: int
    month_code: str
    month: int = field(init=False)
    symbol: str = field(init=False)
    tick_date: datetime
    days_count: int

    def __post_init__(self):
        self.month = Future.get_month_from_code(self.month_code)
        year_code = Future.get_code_for_year(self.year)
        self.symbol = f"{self.futures_code}{self.month_code}{year_code}"

    def __str__(self) -> str:
        return f"F|{self.id}|{self.symbol}"

    def is_dated(self):
        return True

    def get_code(self):
        return self.futures_code

    def get_symbol(self):
        return self.symbol

    def get_date_range(self, tz):
        # for expired contracts the end date would be the expiry date;
        # for KISS' sake, lets assume expiry is last date of contract month
        last_day_of_the_month = calendar.monthrange(self.year, self.month)[1]
        end = datetime(self.year, self.month, last_day_of_the_month)

        # let's add some days to end,
        # so that we can detect later that there's no need to update the data:
        end = end  # + EXPIRATION_THRESHOLD

        # assumption no.2: lets set start date at <duration> days before end date
        duration = timedelta(days=self.days_count)
        start = end - duration

        start = tz.localize(start)
        end = tz.localize(end)

        return start, end

    @staticmethod
    def get_code_for_month(month: int) -> str:
        return Future.MONTH_LIST[month - 1]

    @staticmethod
    def get_month_from_code(month_code: str) -> int:
        try:
            return Future.MONTH_LIST.index(month_code) + 1
        except ValueError:
            raise ValueError(
                f"Invalid month code '{month_code}'. "
                f"Valid codes are: {', '.join(Future.MONTH_LIST)}"
            )

    @staticmethod
    def get_code_for_year(year: int) -> str:
        year_code = str(year)[-2:]
        return year_code
