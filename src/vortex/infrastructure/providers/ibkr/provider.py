import logging
import time
from datetime import timedelta, datetime
from functools import singledispatchmethod
from retrying import retry
from typing import Optional

import pandas as pd
from ib_insync import IB, util
from ib_insync import Stock as IB_Stock, Future as IB_Future, Forex as IB_Forex
from pandas import DataFrame

from ..base import DataProvider
from ..interfaces import ConnectionManagerProtocol, IBKRConnectionManager
from ..config import IBKRProviderConfig, CircuitBreakerConfig
from vortex.models.columns import (
    DATETIME_INDEX_NAME, OPEN_COLUMN, HIGH_COLUMN, 
    LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN,
    validate_required_columns, get_provider_expected_columns,
    standardize_dataframe_columns
)
from vortex.exceptions.providers import DataNotFoundError, VortexConnectionError as ConnectionError, AuthenticationError
from vortex.core.error_handling.strategies import ErrorHandlingStrategy
from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.period import Period, FrequencyAttributes
from vortex.models.price_series import FUTURES_SOURCE_TIME_ZONE
from vortex.models.stock import Stock
from vortex.core.constants import ProviderConstants


class IbkrDataProvider(DataProvider):
    PROVIDER_NAME = "InteractiveBrokers"

    def __init__(self, 
                 config: Optional[IBKRProviderConfig] = None,
                 connection_manager: Optional[ConnectionManagerProtocol] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 raw_storage: Optional['RawDataStorage'] = None):
        """Initialize IBKR provider with configuration and dependency injection.
        
        Args:
            config: Provider configuration (uses defaults if not provided)
            connection_manager: Optional connection manager (will be created if not provided)
            circuit_breaker_config: Optional circuit breaker configuration
            raw_storage: Optional raw data storage for raw data trail
        """
        # Initialize base with circuit breaker config and raw data storage
        super().__init__(circuit_breaker_config, raw_storage)
        
        # Store configuration
        self.config = config or IBKRProviderConfig()
        if not self.config.validate():
            raise ValueError("Invalid IBKR provider configuration")
        
        # Initialize IB client
        self.ib = IB()
        
        # Inject connection manager with sensible default
        self._connection_manager = connection_manager or IBKRConnectionManager(
            self.ib, self.config.host, self.config.port, 
            self.config.client_id or ProviderConstants.IBKR.DEFAULT_CLIENT_ID
        )
        
        self.logger.info(
            f"Initialized {self.PROVIDER_NAME} provider",
            extra={
                'provider': self.PROVIDER_NAME,
                'host': self.config.host,
                'port': self.config.port,
                'connection_timeout': self.config.connection_timeout
            }
        )
        
        # Don't auto-connect in constructor - require explicit login call

    def get_name(self) -> str:
        return IbkrDataProvider.PROVIDER_NAME

    @retry(wait_exponential_multiplier=2000,
           stop_max_attempt_number=5,
           retry_on_exception=lambda exc: not isinstance(exc, AuthenticationError))
    def login(self):
        """Login to IBKR using injected connection manager with standardized error handling."""
        try:
            success = self._connection_manager.connect(timeout=self.config.connection_timeout)
            if not success:
                raise ConnectionError("ibkr", f"Failed to establish connection to {self.config.host}:{self.config.port}")
            
        except Exception as e:
            # Create standardized connection error
            connection_error = self._create_connection_error(
                f"Failed to connect to IBKR at {self.config.host}:{self.config.port} - {e}",
                "login"
            )
            raise connection_error from e

    def logout(self):
        """Logout from IBKR using injected connection manager with standardized error handling."""
        try:
            # Use injected connection manager
            self._connection_manager.disconnect()
        except Exception as e:
            # Use standardized error handling for logout - log but continue
            self._handle_provider_error(
                e,
                "logout",
                strategy=ErrorHandlingStrategy.LOG_AND_CONTINUE
            )
    
    def validate_configuration(self) -> bool:
        """Validate IBKR provider configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return self.config.validate()
    
    def get_required_config_fields(self) -> list[str]:
        """Get list of required configuration fields for IBKR provider.
        
        Returns:
            List of required configuration field names
        """
        return ['host', 'port']

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        return [
            FrequencyAttributes(Period.Monthly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 month', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Weekly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 week', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Daily,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 day', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Hourly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 hour', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Minute_30,
                                min_start=timedelta(days=365),
                                properties={'bar_size': '30 mins', 'duration': '1 Y'}),
            FrequencyAttributes(Period.Minute_15,
                                min_start=timedelta(days=365),
                                properties={'bar_size': '15 mins', 'duration': '1 Y'}),
            FrequencyAttributes(Period.Minute_5,
                                min_start=timedelta(days=90),
                                properties={'bar_size': '5 mins', 'duration': '90 D'}),
            FrequencyAttributes(Period.Minute_1,
                                min_start=timedelta(days=7),
                                properties={'bar_size': '1 min', 'duration': '7 D'}),
        ]

    @singledispatchmethod
    def _fetch_historical_data(self, stock: Stock, frequency_attributes: FrequencyAttributes, start, end) -> DataFrame:
        ib_contract = IB_Stock(stock.get_symbol(), 'SMART', 'USD')
        return self.fetch_historical_data_for_symbol(ib_contract, frequency_attributes)

    @_fetch_historical_data.register
    def _(self, future: Future, frequency_attributes: FrequencyAttributes, start, end) -> DataFrame:
        tokens = future.futures_code.split(".")
        exchange = tokens[0]
        symbol = tokens[1]
        last_contract_month = datetime(year=future.year, month=future.month, day=1).strftime("%Y%m")
        ib_contract = IB_Future(symbol=symbol,
                                lastTradeDateOrContractMonth=last_contract_month,
                                exchange=exchange,
                                multiplier="37500",
                                localSymbol=future.futures_code,
                                currency="USD")

        # COTTON, TT, NYMEX, USD, 50000, 1, FALSE
        # COFFEE, KC, NYBOT, USD, 37500, 100, FALSE

        return self.fetch_historical_data_for_symbol(ib_contract, frequency_attributes)

    @_fetch_historical_data.register
    def _(self, forex: Forex, frequency_attributes: FrequencyAttributes, start, end) -> DataFrame:
        ib_contract = IB_Forex(pair=forex.get_symbol())
        return self.fetch_historical_data_for_symbol(ib_contract, frequency_attributes, "MIDPOINT")

    def fetch_historical_data_for_symbol(self, contract, frequency_attributes: FrequencyAttributes,
                                         what_to_show="TRADES") -> DataFrame:
        """Fetch historical data from IBKR with standardized error handling."""
        try:
            # If live data is available a request for delayed data would be ignored by TWS.
            self.ib.reqMarketDataType(self.config.market_data_type)

            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=frequency_attributes.properties['duration'],
                barSizeSetting=frequency_attributes.properties['bar_size'],
                whatToShow=what_to_show,
                useRTH=self.config.use_rth_only,
                formatDate=2,
                timeout=self.config.historical_data_timeout,
            )
            
            df = util.df(bars)
            logging.debug(f"Received data {df.shape} from {self.get_name()}")
            
            # Save raw data for data trail before processing
            if self._raw_storage and not df.empty:
                try:
                    # Convert raw DataFrame to CSV for raw data storage
                    raw_csv = df.to_csv()
                    
                    # Use the original instrument for raw data storage
                    raw_instrument = instrument
                    
                    request_metadata = {
                        'data_source': 'ibkr_tws',
                        'contract_type': contract.__class__.__name__,
                        'exchange': getattr(contract, 'exchange', 'SMART'),
                        'currency': getattr(contract, 'currency', 'USD'),
                        'duration': frequency_attributes.properties['duration'],
                        'bar_size': frequency_attributes.properties['bar_size'],
                        'what_to_show': what_to_show,
                        'use_rth': self.config.use_rth_only,
                        'original_columns': list(df.columns),
                        'data_shape': list(df.shape)
                    }
                    
                    self._save_raw_data(
                        instrument=raw_instrument,
                        raw_response=raw_csv,
                        request_metadata=request_metadata
                    )
                except Exception as raw_error:
                    logging.warning(f"Failed to save IBKR data trail: {raw_error}")

            # Process data without validation - validation will be handled by _validate_fetched_data()
            if df.empty:
                return df  # Return empty DataFrame, let validation handle it properly

            # Standardize columns using the centralized mapping system
            df = standardize_dataframe_columns(df, 'ibkr')

            # Handle datetime column - should be mapped to DATETIME_INDEX_NAME by standardize_dataframe_columns
            datetime_col = None
            if DATETIME_INDEX_NAME in df.columns:
                datetime_col = DATETIME_INDEX_NAME
            else:
                # Fallback: try to find the datetime column that was mapped
                datetime_candidates = [col for col in df.columns if 'date' in col.lower()]
                if datetime_candidates:
                    datetime_col = datetime_candidates[0]
            
            if datetime_col and not frequency_attributes.frequency.is_intraday():
                df[datetime_col] = (pd.to_datetime(df[datetime_col], format='%Y-%m-%d', errors='coerce')
                                   .dt.tz_localize(FUTURES_SOURCE_TIME_ZONE).dt.tz_convert('UTC'))

            if datetime_col:
                df.set_index(datetime_col, inplace=True)
                df.index.name = DATETIME_INDEX_NAME
            
            # Return processed data - validation is handled by base class wrapper
            # Note: IBKR-specific processing is complete at this point

            return df
            
        except Exception as e:
            if isinstance(e, DataNotFoundError):
                raise  # Re-raise our standardized error
                
            # Handle IBKR-specific errors with standardized error handling
            symbol = str(contract)
            return self._handle_provider_error(
                e,
                "fetch_historical_data",
                strategy=ErrorHandlingStrategy.FAIL_FAST,
                symbol=symbol,
                frequency=frequency_attributes.frequency
            )

    def to_ibkr_finance_bar_size(self, period: Period) -> str:
        """Convert period to IBKR bar size with configurable mappings."""
        default_intervals = {
            Period.Minute_1: '1 min',
            Period.Minute_2: '2 mins',
            Period.Minute_5: '5 mins',
            Period.Minute_15: '15 mins',
            Period.Minute_30: '30 mins',
            Period.Hourly: '1 hour',
            Period.Daily: '1 day',
            Period.Weekly: '1 week',
            Period.Monthly: '1 month',
            Period.Quarterly: '3 months'
        }
        # Allow custom interval mappings via instance configuration
        ibkr_intervals = getattr(self, 'custom_bar_sizes', default_intervals)
        return ibkr_intervals.get(period)

    def to_ibkr_finance_duration_str(self, period: Period) -> str:
        """Convert period to IBKR duration string with configurable mappings."""
        default_duration_lookup = dict(
            [
                (Period.Quarterly, "50 Y"),
                (Period.Monthly, "50 Y"),
                (Period.Weekly, "50 Y"),
                (Period.Daily, "50 Y"),
                (Period.Hourly, "1 Y"),
                (Period.Minute_30, "1 Y"),
                (Period.Minute_15, "1 Y"),
                (Period.Minute_5, "90 D"),
                (Period.Minute_1, "7 D"),
            ]
        )
        # Allow custom duration mappings via instance configuration
        duration_lookup = getattr(self, 'custom_durations', default_duration_lookup)
        return duration_lookup.get(period)
