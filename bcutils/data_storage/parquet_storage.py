from contracts import StockContract, FutureContract
from data_storage.data_storage import DataStorage
from period import Period
from price_series import PriceSeries


class ParquetStorage(DataStorage):
    def __init__(self, dry_run: bool):
        super().__init__(dry_run)
        raise NotImplemented

    def load_futures(self, contract: FutureContract, period: Period) -> PriceSeries:
        raise NotImplemented

    def load_stock(self, contract: StockContract, period: Period) -> PriceSeries:
        raise NotImplemented

    def persist_futures(self, downloaded_data: PriceSeries, contract: FutureContract, period: Period):
        raise NotImplemented

    def persist_stock(self, df, contract: StockContract, period):
        raise NotImplemented
