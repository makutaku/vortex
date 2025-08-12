"""Download command implementation."""

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Local imports (organized by hierarchy)
from vortex.core.config import ConfigManager
from ..utils.config_utils import (
    get_or_create_config_manager, 
    ensure_provider_configured,
    get_default_date_range,
    get_provider_config_with_defaults
)
from ..utils.download_utils import (
    load_assets_from_file,
    get_default_assets_file,
    create_downloader_components,
    parse_date_range,
    parse_symbols_list,
    count_download_jobs,
    format_download_summary
)
from vortex.infrastructure.storage.csv_storage import CsvStorage
from vortex.infrastructure.storage.parquet_storage import ParquetStorage
from vortex.services.updating_downloader import UpdatingDownloader
from vortex.services.download_job import DownloadJob
from vortex.exceptions import (
    CLIError, MissingArgumentError, InvalidCommandError,
    ConfigurationError, DataProviderError, DataStorageError
)
from vortex.core.instruments import InstrumentConfig, DEFAULT_CONTRACT_DURATION_IN_DAYS
from vortex.models.stock import Stock
from vortex.models.period import Period
from vortex.core.logging_integration import get_module_logger, get_module_performance_logger
from vortex.infrastructure.plugins import get_provider_registry
from ..completion import complete_provider, complete_symbol, complete_symbols_file, complete_assets_file, complete_date
from ..utils.provider_utils import get_available_providers, get_provider_config_from_vortex_config
from ..utils.instrument_parser import parse_instruments
from ..ux import get_ux, enhanced_error_handler, validate_symbols

console = Console()
ux = get_ux()
logger = get_module_logger()
perf_logger = get_module_performance_logger()


@dataclass
class DownloadExecutionConfig:
    """Configuration for download execution."""
    config_manager: ConfigManager
    provider: str
    symbols: List[str]
    instrument_configs: dict
    start_date: datetime
    end_date: datetime
    output_dir: Path
    backup: bool
    force: bool
    chunk_size: int
    dry_run: bool


@dataclass
class JobExecutionContext:
    """Context for executing a single download job."""
    downloader: object  # UpdatingDownloader instance
    instrument: object  # Instrument instance
    period: object  # Period instance
    start_date: datetime
    end_date: datetime
    symbol: str
    provider: str
    job_count: int
    total_jobs: int
    progress: object  # Progress tracking instance


def load_config_instruments(assets_file_path: Path) -> dict:
    """Load instrument configurations from assets JSON file."""
    try:
        instrument_configs = InstrumentConfig.load_from_json(str(assets_file_path))
        return instrument_configs
    except Exception as e:
        console.print(f"[red]Error loading assets file '{assets_file_path}': {e}[/red]")
        raise click.Abort()

@click.command()
@enhanced_error_handler
@click.option(
    "--provider", "-p",
    type=str,
    default=None,
    help="Data provider to use (default: from config, yahoo if not set - free, no credentials required)",
    shell_complete=complete_provider
)
@click.option(
    "--symbol", "-s",
    multiple=True,
    help="Symbol(s) to download (can be used multiple times)",
    shell_complete=complete_symbol
)
@click.option(
    "--symbols-file",
    type=click.Path(exists=True, path_type=Path),
    help="File containing symbols (one per line)",
    shell_complete=complete_symbols_file
)
@click.option(
    "--assets", "--assets-file",
    type=click.Path(exists=True, path_type=Path),
    help="Custom assets file with instruments to download",
    shell_complete=complete_assets_file
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date (YYYY-MM-DD). Default: 30 days ago",
    shell_complete=complete_date
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date (YYYY-MM-DD). Default: today",
    shell_complete=complete_date
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    help="Output directory. Default: ./data"
)
@click.option(
    "--backup/--no-backup",
    default=False,
    help="Create Parquet backup files"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-download even if data exists"
)
@click.option(
    "--chunk-size",
    type=click.IntRange(1, 365),
    default=30,
    help="Days per download chunk (1-365)"
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt"
)
@click.pass_context
def download(
    ctx: click.Context,
    provider: str,
    symbol: tuple,
    symbols_file: Optional[Path],
    assets: Optional[Path],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    output_dir: Optional[Path],
    backup: bool,
    force: bool,
    chunk_size: int,
    yes: bool,
) -> None:
    """Download financial data for specified instruments.
    
    \b
    Examples:
        vortex download -s AAPL -s GOOGL                    # Uses yahoo (default)
        vortex download --symbol TSLA MSFT --yes            # Uses yahoo (default)
        vortex download --symbols-file symbols.txt          # Uses yahoo (default)
        vortex download -p barchart -s GCM25 --start-date 2024-01-01  
        vortex download -p ibkr -s TSLA --start-date 2024-01-01
        
    \b
    Default Assets:
        When no symbols are specified, Vortex loads default instruments from:
        - config/assets/yahoo.json - Default instruments for Yahoo Finance
        - config/assets/barchart.json - Default instruments for Barchart.com  
        - config/assets/ibkr.json - Default instruments for Interactive Brokers
        - config/assets/default.json - General fallback
        
        Use --assets to provide your own custom assets file.
        
    \b
    Installation:
        # Fast installation with uv (recommended)
        uv pip install -e .
        
        # Run without installation
        uv run vortex download --help
    """
    # Setup and validation phase
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    provider = _resolve_provider(config_manager, provider)
    _validate_provider(provider)
    
    # Set default dates and paths
    start_date, end_date, output_dir = _set_defaults(start_date, end_date, output_dir)
    
    # Parse and validate symbols/instruments
    symbols, instrument_configs = _resolve_symbols_and_configs(
        provider, symbol, symbols_file, assets
    )
    
    # Final validation
    symbols = _validate_inputs(symbols, start_date, end_date, output_dir)
    
    # User confirmation
    show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
    if not yes and not ux.confirm("Proceed with download?", True):
        ux.print_warning("Download cancelled")
        return
    
    # Execute download
    exec_config = DownloadExecutionConfig(
        config_manager=config_manager,
        provider=provider,
        symbols=symbols,
        instrument_configs=instrument_configs,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        backup=backup,
        force=force,
        chunk_size=chunk_size,
        dry_run=ctx.obj.get('dry_run', False)
    )
    _execute_and_report_results(exec_config)

def _resolve_provider(config_manager: ConfigManager, provider: str) -> str:
    """Resolve the provider, using default if none specified."""
    if provider is None:
        provider = config_manager.get_default_provider()
        ux.print_info(f"Using default provider: {provider}")
    return provider


def _validate_provider(provider: str) -> None:
    """Validate that the provider exists in the plugin registry."""
    try:
        registry = get_provider_registry()
        registry.get_plugin(provider)  # This will raise PluginNotFoundError if not found
    except Exception as e:
        available_providers = get_available_providers()
        ux.print_error(f"Provider '{provider}' not found")
        ux.print_info(f"Available providers: {', '.join(available_providers)}")
        ux.print_info("💡 Use 'vortex providers --list' to see all available providers")
        raise click.Abort()


def _set_defaults(start_date: Optional[datetime], end_date: Optional[datetime], 
                  output_dir: Optional[Path]) -> tuple[datetime, datetime, Path]:
    """Set default values for dates and output directory."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    if not output_dir:
        output_dir = Path("./data")
    return start_date, end_date, output_dir


class SymbolResolver:
    """Handles symbol and configuration resolution using Chain of Responsibility pattern."""
    
    def __init__(self, provider: str):
        self.provider = provider
        self._setup_chain()
    
    def _setup_chain(self):
        """Setup the chain of responsibility for symbol resolution."""
        self.assets_handler = AssetsFileHandler()
        self.direct_symbols_handler = DirectSymbolsHandler()
        self.default_assets_handler = DefaultAssetsHandler(self.provider)
        
        # Chain the handlers
        self.assets_handler.set_next(self.direct_symbols_handler)
        self.direct_symbols_handler.set_next(self.default_assets_handler)
    
    def resolve(self, symbol: tuple, symbols_file: Optional[Path], assets: Optional[Path]) -> tuple[List[str], dict]:
        """Resolve symbols and configurations using the handler chain."""
        context = SymbolResolutionContext(
            symbol=symbol,
            symbols_file=symbols_file,
            assets=assets,
            provider=self.provider
        )
        
        return self.assets_handler.handle(context)

class SymbolResolutionContext:
    """Context object for symbol resolution."""
    
    def __init__(self, symbol: tuple, symbols_file: Optional[Path], assets: Optional[Path], provider: str):
        self.symbol = symbol
        self.symbols_file = symbols_file
        self.assets = assets
        self.provider = provider

class SymbolResolutionHandler:
    """Base handler for symbol resolution chain."""
    
    def __init__(self):
        self.next_handler = None
    
    def set_next(self, handler):
        """Set the next handler in the chain."""
        self.next_handler = handler
        return handler
    
    def handle(self, context: SymbolResolutionContext) -> tuple[List[str], dict]:
        """Handle symbol resolution or pass to next handler."""
        result = self._try_resolve(context)
        if result is not None:
            return result
        
        if self.next_handler:
            return self.next_handler.handle(context)
        
        # Final fallback - raise error
        ux.print_error(f"No symbols specified and no default assets found for {context.provider}")
        ux.print_info("💡 Try: vortex download -p yahoo -s AAPL")
        raise MissingArgumentError("symbol", "download")
    
    def _try_resolve(self, context: SymbolResolutionContext) -> tuple[List[str], dict]:
        """Try to resolve symbols. Return None if this handler can't handle the request."""
        raise NotImplementedError

class AssetsFileHandler(SymbolResolutionHandler):
    """Handle symbol resolution from user-specified assets file."""
    
    def _try_resolve(self, context: SymbolResolutionContext) -> tuple[List[str], dict]:
        if not context.assets:
            return None
        
        instrument_configs = load_config_instruments(context.assets)
        symbols = list(instrument_configs.keys())
        ux.print_success(f"Loaded {len(symbols)} instruments from {context.assets}")
        return symbols, instrument_configs

class DirectSymbolsHandler(SymbolResolutionHandler):
    """Handle symbol resolution from direct symbol input or symbols file."""
    
    def _try_resolve(self, context: SymbolResolutionContext) -> tuple[List[str], dict]:
        symbols = parse_instruments(context.symbol, context.symbols_file)
        if symbols:
            return symbols, None
        return None

class DefaultAssetsHandler(SymbolResolutionHandler):
    """Handle symbol resolution from default provider assets."""
    
    def __init__(self, provider: str):
        super().__init__()
        self.provider = provider
    
    def _try_resolve(self, context: SymbolResolutionContext) -> tuple[List[str], dict]:
        try:
            default_assets_file = get_default_assets_file(self.provider)
            if default_assets_file is None:
                return None
            instrument_configs = load_config_instruments(default_assets_file)
            symbols = list(instrument_configs.keys())
            ux.print_success(f"Loaded {len(symbols)} instruments from default {default_assets_file}")
            return symbols, instrument_configs
        except (FileNotFoundError, PermissionError, ValueError, KeyError):
            return None

def _resolve_symbols_and_configs(
    provider: str, symbol: tuple, symbols_file: Optional[Path], assets: Optional[Path]
) -> tuple[List[str], dict]:
    """Parse and validate symbols and instrument configurations."""
    resolver = SymbolResolver(provider)
    return resolver.resolve(symbol, symbols_file, assets)


def _validate_inputs(symbols: List[str], start_date: datetime, end_date: datetime, 
                     output_dir: Path) -> List[str]:
    """Validate symbols, date range, and create output directory."""
    # Validate symbols
    validated_symbols = validate_symbols(symbols)
    if not validated_symbols:
        ux.print_error("No valid symbols to download")
        raise click.Abort()
    
    # Validate date range
    if start_date >= end_date:
        raise InvalidCommandError(
            "download",
            f"Start date ({start_date.date()}) must be before end date ({end_date.date()})"
        )
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return validated_symbols


def _execute_and_report_results(config: DownloadExecutionConfig) -> None:
    """Execute the download and report results."""
    try:
        success_count = execute_download(config)
        
        if success_count == len(config.symbols):
            ux.print_success(f"Download completed! All {success_count} symbols successful")
        else:
            ux.print_warning(f"Download completed with issues: {success_count}/{len(config.symbols)} symbols successful")
            ux.print_info(f"💡 Check logs for details on failed symbols")
        
    except Exception as e:
        ux.print_error(f"Download failed: {e}")
        logger.error("Download process failed", error=str(e))
        raise click.Abort()


def show_download_summary(
    provider: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    output_dir: Path,
    backup: bool,
    force: bool
) -> None:
    """Display download summary table."""
    table = Table(title="Download Summary")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Provider", provider.upper())
    table.add_row("Symbols", f"{len(symbols)} symbols")
    table.add_row("Date Range", f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    table.add_row("Output Directory", str(output_dir))
    table.add_row("Backup Files", "Yes" if backup else "No")
    table.add_row("Force Re-download", "Yes" if force else "No")
    
    console.print(table)
    
    # Show symbols list
    if len(symbols) <= 10:
        console.print(f"[dim]Symbols: {', '.join(symbols)}[/dim]")
    else:
        console.print(f"[dim]Symbols: {', '.join(symbols[:5])} ... and {len(symbols)-5} more[/dim]")

def execute_download(config: DownloadExecutionConfig) -> int:
    """Execute the actual download process."""
    
    if config.dry_run:
        console.print("[yellow]DRY RUN: Would download data but no changes will be made[/yellow]")
        return len(config.symbols)
    
    # Setup phase
    instrument_configs = _ensure_instrument_configs(config.instrument_configs, config.symbols)
    download_config = get_download_config(config.config_manager, config.output_dir, config.backup, config.force)
    downloader = create_downloader(config.provider, download_config)
    
    # Count total jobs
    total_jobs = _count_total_jobs(config.symbols, instrument_configs)
    
    # Process downloads
    return _process_all_downloads(
        downloader, config.symbols, instrument_configs, config.start_date, config.end_date, 
        config.provider, total_jobs
    )


def _ensure_instrument_configs(instrument_configs: dict, symbols: List[str]) -> dict:
    """Ensure all symbols have instrument configurations, creating defaults if needed."""
    if not instrument_configs:
        instrument_configs = {}
        for symbol in symbols:
            # Create a simple stock config with daily period for direct symbol downloads
            instrument_configs[symbol] = InstrumentConfig(
                asset_class='stock',
                name=symbol,
                code=symbol,
                periods='1d'
            )
    return instrument_configs


def _count_total_jobs(symbols: List[str], instrument_configs: dict) -> int:
    """Count the total number of download jobs to process."""
    total_jobs = 0
    for symbol in symbols:
        config = instrument_configs.get(symbol)
        if config and config.periods:
            total_jobs += len(config.periods)
        else:
            total_jobs += 1  # Default to one job (daily)
    return total_jobs


def _process_all_downloads(
    downloader, symbols: List[str], instrument_configs: dict,
    start_date: datetime, end_date: datetime, provider: str, total_jobs: int
) -> int:
    """Process all downloads with progress tracking."""
    success_count = 0
    job_count = 0
    
    with ux.progress(f"Downloading {total_jobs} symbol-period combinations") as progress:
        for symbol in symbols:
            config = instrument_configs.get(symbol)
            periods = _get_periods_for_symbol(config)
            instrument = _create_instrument_from_config(symbol, config)
            
            logger.info(f"Processing {symbol} with {len(periods)} period(s): {[p.value for p in periods]}", 
                       symbol=symbol, provider=provider)
            
            # Process each period for this symbol
            for period in periods:
                job_count += 1
                
                job_context = JobExecutionContext(
                    downloader=downloader,
                    instrument=instrument,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    symbol=symbol,
                    provider=provider,
                    job_count=job_count,
                    total_jobs=total_jobs,
                    progress=progress
                )
                
                result = _process_single_job(job_context)
                if result:
                    success_count += 1
    
    return success_count


def _get_periods_for_symbol(config) -> List:
    """Get the periods to download for a symbol."""
    if config and config.periods:
        return config.periods
    else:
        # Fallback to daily for direct symbol input
        return [Period.Daily]


class InstrumentFactory:
    """Factory for creating instrument objects from configuration using Strategy pattern."""
    
    _creators = {
        'stock': lambda symbol, config: StockInstrumentCreator.create(symbol, config),
        'forex': lambda symbol, config: ForexInstrumentCreator.create(symbol, config),
        'future': lambda symbol, config: FutureInstrumentCreator.create(symbol, config)
    }
    
    @classmethod
    def create_instrument(cls, symbol: str, config):
        """Create the appropriate instrument object from configuration."""
        if config and hasattr(config, 'asset_class'):
            creator = cls._creators.get(config.asset_class.value)
            if creator:
                return creator(symbol, config)
        
        # Default fallback to stock
        return StockInstrumentCreator.create_default(symbol)

class InstrumentCreator:
    """Base class for instrument creators."""
    
    @staticmethod
    def create(symbol: str, config):
        raise NotImplementedError
    
    @staticmethod
    def create_default(symbol: str):
        """Create default instrument when no config is available."""
        return Stock(id=symbol, symbol=symbol)

class StockInstrumentCreator(InstrumentCreator):
    """Creator for stock instruments."""
    
    @staticmethod
    def create(symbol: str, config):
        return Stock(id=symbol, symbol=config.code)

class ForexInstrumentCreator(InstrumentCreator):
    """Creator for forex instruments."""
    
    @staticmethod
    def create(symbol: str, config):
        from vortex.models.forex import Forex
        return Forex(id=symbol, symbol=config.code)

class FutureInstrumentCreator(InstrumentCreator):
    """Creator for future instruments."""
    
    @staticmethod
    def create(symbol: str, config):
        from vortex.models.future import Future
        
        parameters = FutureParameterExtractor.extract_parameters(config)
        
        return Future(
            id=symbol,
            futures_code=config.code,
            year=parameters['year'],
            month_code=parameters['month_code'],
            tick_date=parameters['tick_date'],
            days_count=parameters['days_count']
        )

class FutureParameterExtractor:
    """Extract and validate parameters for future instruments."""
    
    @staticmethod
    def extract_parameters(config) -> dict:
        """Extract all required parameters for future creation."""
        return {
            'year': FutureParameterExtractor._get_year(),
            'month_code': FutureParameterExtractor._get_month_code(config),
            'tick_date': FutureParameterExtractor._get_tick_date(config),
            'days_count': FutureParameterExtractor._get_days_count(config)
        }
    
    @staticmethod
    def _get_year() -> int:
        """Get current year for active contract."""
        return datetime.now().year
    
    @staticmethod
    def _get_month_code(config) -> str:
        """Get month code from cycle or default."""
        return config.cycle[0] if config.cycle else 'M'
    
    @staticmethod
    def _get_tick_date(config):
        """Get tick date from config or default to now."""
        return config.tick_date if config.tick_date else datetime.now()
    
    @staticmethod
    def _get_days_count(config) -> int:
        """Get days count from config or default."""
        return config.days_count if config.days_count else DEFAULT_CONTRACT_DURATION_IN_DAYS

def _create_instrument_from_config(symbol: str, config):
    """Create the appropriate instrument object from configuration."""
    return InstrumentFactory.create_instrument(symbol, config)


def _process_single_job(context: JobExecutionContext) -> bool:
    """Process a single download job and return success status."""
    context.progress.update(context.job_count - 1, context.total_jobs, 
                  f"Processing {context.symbol}|{context.period.value} ({context.job_count}/{context.total_jobs})")
    
    try:
        logger.info(f"Processing {str(context.instrument)}|{context.period.value}|{context.start_date.strftime('%Y-%m-%d')}|{context.end_date.strftime('%Y-%m-%d')}", 
                   symbol=context.symbol, period=context.period.value, provider=context.provider)
        
        # Ensure dates are timezone-aware (use UTC if naive) 
        safe_start_date = context.start_date.replace(tzinfo=timezone.utc) if context.start_date.tzinfo is None else context.start_date
        safe_end_date = context.end_date.replace(tzinfo=timezone.utc) if context.end_date.tzinfo is None else context.end_date
        
        job = DownloadJob(
            data_provider=context.downloader.data_provider,
            data_storage=context.downloader.data_storage,
            instrument=context.instrument,
            period=context.period,  # Use the actual period from config
            start_date=safe_start_date,
            end_date=safe_end_date
        )
        
        # Process the download job
        context.downloader._process_job(job)
        
        context.progress.update(context.job_count, context.total_jobs, 
                      f"✓ {context.symbol}|{context.period.value} completed ({context.job_count}/{context.total_jobs})")
        return True
        
    except Exception as e:
        context.progress.update(context.job_count, context.total_jobs, 
                      f"✗ {context.symbol}|{context.period.value} failed ({context.job_count}/{context.total_jobs})")
        logger.error(f"Failed to download {context.symbol}|{context.period.value}: {e}", 
                   symbol=context.symbol, period=context.period.value, error=str(e))
        return False

def get_download_config(
    config_manager: ConfigManager,
    output_dir: Path,
    backup: bool,
    force: bool
) -> dict:
    """Get configuration for the download."""
    
    # Load full configuration
    config = config_manager.load_config()
    
    return {
        'vortex_config': config,
        'output_dir': output_dir,
        'backup': backup,
        'force': force
    }

def create_downloader(provider: str, download_config: dict):
    """Create the appropriate downloader for the provider using plugin system."""
    
    vortex_config = download_config['vortex_config']
    output_dir = download_config['output_dir']
    backup = download_config['backup']
    force = download_config['force']
    
    # Create storage objects
    data_storage = CsvStorage(str(output_dir), False)  # dry_run handled at CLI level
    backup_data_storage = ParquetStorage(str(output_dir), False) if backup else None
    
    # Create data provider using plugin system
    try:
        registry = get_provider_registry()
        
        # Get provider-specific configuration dynamically
        provider_config = get_provider_config_from_vortex_config(provider, vortex_config)
        
        # Create data provider through plugin system
        data_provider = registry.create_provider(provider, provider_config)
        
        logger.info(f"Created data provider '{provider}' using plugin system")
        
    except Exception as e:
        logger.error(f"Failed to create provider '{provider}' via plugin system: {e}")
        raise DataProviderError(provider, f"Initialization failed: {e}")
    
    # Create and return the downloader
    return UpdatingDownloader(
        data_storage, 
        data_provider, 
        backup_data_storage,
        force_backup=force, 
        random_sleep_in_sec=vortex_config.general.random_sleep_max,
        dry_run=vortex_config.general.dry_run
    )