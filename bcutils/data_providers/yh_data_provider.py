from data_providers.data_provider import DataProvider
from price_series import PriceSeries


class YahooDataProvider(DataProvider):

    def __init__(self):
        raise NotImplemented()

    def get_name(self) -> str:
        raise NotImplemented()

    def fetch_futures_historical_data(self, symbol: str, period, start_date, end_date) -> PriceSeries:
        raise NotImplemented()

    def fetch_stock_historical_data(self, symbol: str, period, start_date, end_date) -> PriceSeries:
        raise NotImplemented()

    def fetch_forex_historical_data(self, symbol: str, period, start_date, end_date) -> PriceSeries:
        pass

    def get_futures_timeframes(self):
        raise NotImplemented()

    def get_stock_timeframes(self):
        raise NotImplemented()

    def get_forex_timeframes(self):
        raise NotImplemented()
