"""
Download execution engine for download commands.

Extracted from download.py to implement single responsibility principle.
Handles download execution, progress tracking, and result reporting.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any

# Note: Simple console output instead of complex UX functions
from vortex.services.updating_downloader import UpdatingDownloader
from vortex.services.backfill_downloader import BackfillDownloader
from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration
from vortex.infrastructure.providers.base import HistoricalDataResult

from .job_creator import create_jobs_using_downloader_logic, get_periods_for_symbol


class JobExecutionContext:
    """Context for executing individual download jobs."""
    
    def __init__(self, job, job_number: int, total_jobs: int, symbol: str):
        self.job = job
        self.job_number = job_number
        self.total_jobs = total_jobs
        self.symbol = symbol


class DownloadExecutor:
    """Executes download operations with progress tracking and error handling."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def execute_downloads(self, symbols: List[str], instrument_configs: Dict[str, Any]) -> int:
        """Execute downloads for all symbols and return success count."""
        # Ensure all symbols have configurations
        instrument_configs = self._ensure_instrument_configs(instrument_configs, symbols)
        
        # Count total jobs for progress tracking
        total_jobs = self._count_total_jobs(symbols, instrument_configs)
        
        if total_jobs == 0:
            self.logger.warning("No download jobs to execute")
            return 0
        
        self.logger.info(f"Starting download execution: {len(symbols)} symbols, {total_jobs} total jobs")
        
        # Process all downloads
        success_count = self._process_all_downloads(symbols, instrument_configs, total_jobs)
        
        self.logger.info(f"Download execution completed: {success_count}/{total_jobs} jobs successful")
        return success_count
    
    def _ensure_instrument_configs(self, instrument_configs: dict, symbols: List[str]) -> dict:
        """Ensure all symbols have instrument configurations."""
        updated_configs = instrument_configs.copy()
        
        for symbol in symbols:
            if symbol not in updated_configs:
                # Create minimal default config
                updated_configs[symbol] = {
                    'asset_class': 'stock',  # Default to stock
                    'periods': ['1d']        # Default to daily
                }
                self.logger.debug(f"Created default config for symbol: {symbol}")
        
        return updated_configs
    
    def _count_total_jobs(self, symbols: List[str], instrument_configs: dict) -> int:
        """Count total number of download jobs."""
        total_jobs = 0
        
        for symbol in symbols:
            config = instrument_configs.get(symbol, {})
            periods = get_periods_for_symbol(config)
            total_jobs += len(periods)
        
        return total_jobs
    
    def _process_all_downloads(self, symbols: List[str], instrument_configs: dict, total_jobs: int) -> int:
        """Process all downloads with threading and progress tracking."""
        start_time = time.time()
        completed_jobs = 0
        successful_jobs = 0
        
        # Create downloader
        downloader = self._create_downloader()
        
        # Process downloads (could be threaded in the future)
        for symbol in symbols:
            config = instrument_configs.get(symbol, {})
            periods = get_periods_for_symbol(config)
            
            # Create jobs for this symbol
            try:
                jobs = create_jobs_using_downloader_logic(
                    downloader, symbol, config, periods, 
                    self.config.start_date, self.config.end_date
                )
                
                # Execute jobs for this symbol
                for job in jobs:
                    completed_jobs += 1
                    context = JobExecutionContext(job, completed_jobs, total_jobs, symbol)
                    
                    if self._process_single_job(context):
                        successful_jobs += 1
                    
                    # Show progress
                    progress = (completed_jobs / total_jobs) * 100
                    elapsed = time.time() - start_time
                    self.logger.info(f"Progress: {completed_jobs}/{total_jobs} ({progress:.1f}%) - "
                                   f"Elapsed: {elapsed:.1f}s")
                
            except Exception as e:
                self.logger.error(f"Failed to create jobs for symbol {symbol}: {e}")
                continue
        
        return successful_jobs
    
    def _process_single_job(self, context: JobExecutionContext) -> bool:
        """Process a single download job."""
        config = LoggingConfiguration(
            entry_msg=f"Processing job {context.job_number}/{context.total_jobs}: {context.symbol}",
            entry_level=logging.INFO,
            success_msg=f"Completed job {context.job_number}/{context.total_jobs}: {context.symbol}",
            success_level=logging.DEBUG
        )
        
        with LoggingContext(config):
            try:
                downloader = self._create_downloader()
                result = downloader._process_job(context.job)
                
                if result == HistoricalDataResult.OK:
                    self.logger.debug(f"Job {context.job_number} completed successfully")
                    return True
                elif result == HistoricalDataResult.EXISTS:
                    self.logger.debug(f"Job {context.job_number} - data already exists")
                    return True
                else:
                    self.logger.warning(f"Job {context.job_number} - no data available")
                    return False
                    
            except KeyboardInterrupt:
                self.logger.info("Download interrupted by user")
                raise
            except Exception as e:
                self.logger.error(f"Job {context.job_number} failed: {e}")
                return False
    
    def _create_downloader(self):
        """Create appropriate downloader instance."""
        from vortex.infrastructure.providers.factory import ProviderFactory
        from vortex.infrastructure.storage.csv_storage import CsvStorage
        from vortex.infrastructure.storage.parquet_storage import ParquetStorage
        
        # Create provider
        factory = ProviderFactory()
        provider = factory.create_provider(self.config.provider, self.config.download_config)
        
        # Create storage
        csv_storage = CsvStorage(str(self.config.output_dir), self.config.dry_run)
        parquet_storage = ParquetStorage(str(self.config.output_dir)) if self.config.backup_enabled else None
        
        # Create downloader
        if self.config.mode == 'updating':
            return UpdatingDownloader(
                data_storage=csv_storage,
                data_provider=provider,
                backup_data_storage=parquet_storage,
                force_backup=self.config.force_backup,
                random_sleep_in_sec=self.config.random_sleep,
                dry_run=self.config.dry_run
            )
        else:
            return BackfillDownloader(
                data_storage=csv_storage,
                data_provider=provider,
                backup_data_storage=parquet_storage,
                force_backup=self.config.force_backup,
                random_sleep_in_sec=self.config.random_sleep,
                dry_run=self.config.dry_run
            )


def show_download_summary(start_time: float, end_time: float, total_jobs: int, 
                         successful_jobs: int, failed_jobs: int) -> None:
    """Display download execution summary."""
    duration = end_time - start_time
    success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
    
    print(f"\n📊 Download Summary:")
    print(f"  Total Jobs: {total_jobs}")
    print(f"  Successful: {successful_jobs}")
    print(f"  Failed: {failed_jobs}")
    print(f"  Success Rate: {success_rate:.1f}%")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Jobs/second: {total_jobs/duration:.2f}" if duration > 0 else "  Jobs/second: N/A")
    print()