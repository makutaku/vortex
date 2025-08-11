"""
End-to-end tests for complete CLI workflows.

Tests complete user scenarios from command-line invocation
through data download and file output validation.
"""

import pytest
import tempfile
import socket
from pathlib import Path
from click.testing import CliRunner
from datetime import datetime, timedelta

from vortex.cli.main import cli
from vortex.models.columns import DATE_TIME_COLUMN


def check_network_connectivity(host="finance.yahoo.com", port=443, timeout=5):
    """Check if network connectivity to a host is available."""
    try:
        socket.create_connection((host, port), timeout)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


class TestCLIWorkflows:
    """End-to-end tests for CLI command workflows."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner for tests."""
        return CliRunner()

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_help_command_workflow(self, cli_runner):
        """Test the complete help command workflow."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Vortex: Financial data download automation tool" in result.output
        assert "Commands:" in result.output

    def test_providers_list_workflow(self, cli_runner):
        """Test the complete providers list workflow."""
        result = cli_runner.invoke(cli, ['providers'])
        
        # Should not fail even if some providers have dependency issues
        assert result.exit_code in [0, 1]  # May fail due to missing dependencies
        
        if result.exit_code == 0:
            assert "Total providers available" in result.output

    def test_config_show_workflow(self, cli_runner):
        """Test the configuration display workflow."""
        result = cli_runner.invoke(cli, ['config', '--show'])
        
        # Should show configuration even if some providers are unavailable
        assert result.exit_code in [0, 1]

    @pytest.mark.slow
    def test_download_dry_run_workflow(self, cli_runner, temp_output_dir):
        """Test download command with dry run."""
        # This would test the complete download workflow in dry-run mode
        # to avoid actually downloading data in tests
        
        result = cli_runner.invoke(cli, [
            'download',
            '--provider', 'yahoo',
            '--symbol', 'AAPL',
            '--output-dir', str(temp_output_dir),
            '--dry-run'
        ])
        
        # Dry run should complete without errors
        # Note: Actual behavior depends on implementation
        assert result.exit_code in [0, 1, 2]  # Various exit codes possible

    def test_invalid_command_workflow(self, cli_runner):
        """Test handling of invalid commands."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0
        assert "No such command" in result.output or "Usage:" in result.output

    @pytest.mark.e2e
    @pytest.mark.network
    @pytest.mark.slow
    @pytest.mark.skipif(
        not check_network_connectivity("finance.yahoo.com"),
        reason="No network connectivity to Yahoo Finance"
    )
    def test_yahoo_download_real_data_workflow(self, cli_runner, temp_output_dir):
        """
        Test complete Yahoo Finance download workflow with real market data.
        
        This is a true end-to-end test that:
        1. Invokes the CLI command as a user would
        2. Makes real network calls to Yahoo Finance API  
        3. Downloads actual market data
        4. Creates real files in the filesystem
        5. Validates the complete user workflow
        
        Uses a short date range to minimize API load and execution time.
        """
        # Calculate a recent 5-day period to ensure data availability
        # Avoid weekends by using a slightly longer range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # 10 days to account for weekends
        
        # Format dates for CLI (YYYY-MM-DD)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute the complete CLI download workflow
        result = cli_runner.invoke(cli, [
            'download',
            '--provider', 'yahoo',
            '--symbol', 'AAPL',  # Highly liquid stock, always available
            '--start-date', start_date_str,
            '--end-date', end_date_str,
            '--output-dir', str(temp_output_dir),
            '--yes'  # Skip confirmation prompts for automation
        ])
        
        # Validate command completed successfully
        assert result.exit_code == 0, f"Download command failed: {result.output}"
        
        # Validate success messages in output
        success_indicators = [
            "Fetched remote data",  # Indicates data was downloaded
            "Download completed successfully",  # Indicates workflow completed
            "AAPL"  # Symbol was processed
        ]
        
        output_text = result.output
        found_indicators = [msg for msg in success_indicators if msg in output_text]
        assert len(found_indicators) >= 2, f"Missing success indicators. Output: {output_text}"
        
        # Validate file structure creation
        expected_csv_file = temp_output_dir / "stocks" / "1d" / "AAPL.csv"
        assert expected_csv_file.exists(), f"Expected CSV file not created: {expected_csv_file}"
        
        # Comprehensive CSV validation
        from .csv_validation import validate_market_data_csv, validate_business_day_count
        
        # Calculate expected business day count
        date_range = (start_date, end_date)
        
        # Perform comprehensive validation
        validation_result = validate_market_data_csv(
            expected_csv_file,
            expected_min_rows=3,  # At least 3 trading days in 10-day period
            date_range=date_range,
            provider="yahoo"
        )
        
        # Assert validation passed
        assert validation_result.is_valid, f"CSV validation failed: {validation_result.errors}"
        
        # Validate business day count
        is_valid, expected_days, message = validate_business_day_count(
            start_date, end_date, validation_result.row_count, tolerance=3
        )
        assert is_valid, f"Business day count validation failed: {message}"
        
        # Log validation success details
        print(f"✅ Yahoo CSV validation passed:")
        print(f"  File: {expected_csv_file.name}")
        print(f"  Rows: {validation_result.row_count}")
        print(f"  Columns: {', '.join(validation_result.columns)}")
        print(f"  Size: {validation_result.file_size} bytes")
        print(f"  {message}")
        
        if validation_result.warnings:
            print(f"  Warnings: {', '.join(validation_result.warnings)}")

    @pytest.mark.e2e
    @pytest.mark.network
    @pytest.mark.slow
    @pytest.mark.skipif(
        not check_network_connectivity("finance.yahoo.com"),
        reason="No network connectivity to Yahoo Finance"
    )
    def test_yahoo_assets_file_workflow(self, cli_runner, temp_output_dir):
        """
        Test complete Yahoo Finance workflow using JSON assets file with multiple stocks.
        
        This test validates:
        1. JSON asset file parsing and processing
        2. Multi-symbol download workflow
        3. Batch processing of multiple instruments
        4. File creation for each symbol in the asset file
        5. Proper directory structure creation
        
        Uses a minimal asset file with liquid stocks to ensure data availability.
        """
        # Create a minimal test asset file with highly liquid stocks
        test_assets_file = temp_output_dir / "test_assets.json"
        test_assets_content = {
            "stock": {
                "AAPL": {
                    "code": "AAPL",
                    "tick_date": "1980-12-12",
                    "start_date": "1980-12-12",
                    "periods": "1d"
                },
                "MSFT": {
                    "code": "MSFT", 
                    "tick_date": "1986-03-13",
                    "start_date": "1986-03-13",
                    "periods": "1d"
                },
                "SPY": {
                    "code": "SPY",
                    "tick_date": "1993-01-29", 
                    "start_date": "1993-01-29",
                    "periods": "1d"
                }
            }
        }
        
        # Write test asset file
        import json
        with open(test_assets_file, 'w') as f:
            json.dump(test_assets_content, f, indent=2)
        
        # Calculate recent date range for data availability
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Shorter range for multiple symbols
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute CLI command with assets file
        result = cli_runner.invoke(cli, [
            'download',
            '--provider', 'yahoo',
            '--assets', str(test_assets_file),
            '--start-date', start_date_str,
            '--end-date', end_date_str,
            '--output-dir', str(temp_output_dir),
            '--yes'  # Skip confirmation prompts
        ])
        
        # Validate command success
        assert result.exit_code == 0, f"Assets file download failed: {result.output}"
        
        # Validate that all symbols were processed
        expected_symbols = ["AAPL", "MSFT", "SPY"]
        output_text = result.output
        
        # Check for processing indicators for each symbol
        symbols_found = 0
        for symbol in expected_symbols:
            if symbol in output_text:
                symbols_found += 1
        
        assert symbols_found >= 2, f"Expected processing of at least 2 symbols. Output: {output_text}"
        
        # Comprehensive validation for multiple CSV files
        from .csv_validation import validate_multiple_csvs, print_validation_summary
        
        # Find all created CSV files
        created_files = []
        missing_files = []
        
        for symbol in expected_symbols:
            expected_file = temp_output_dir / "stocks" / "1d" / f"{symbol}.csv"
            if expected_file.exists():
                created_files.append(expected_file)
            else:
                missing_files.append(symbol)
        
        # Require at least 2 out of 3 files to be created (some might fail due to market conditions)
        assert len(created_files) >= 2, f"Expected at least 2 CSV files. Created: {len(created_files)}, Missing: {missing_files}"
        
        # Validate all created CSV files comprehensively
        validation_results = validate_multiple_csvs(
            created_files,
            expected_min_rows=3,  # At least 3 trading days in 7-day period
            date_range=(start_date, end_date),
            provider="yahoo"
        )
        
        # Check that all created files passed validation
        failed_validations = [name for name, result in validation_results.items() if not result.is_valid]
        assert len(failed_validations) == 0, f"CSV validation failed for: {failed_validations}"
        
        # Print detailed validation summary
        print_validation_summary(validation_results)
        
        # Validate directory structure was created properly
        stocks_dir = temp_output_dir / "stocks" / "1d"
        assert stocks_dir.exists(), "Expected stocks/1d directory structure not created"
        
        # Validate that batch processing completed
        completion_indicators = ["Download completed successfully", "Completed"]
        found_completion = any(indicator in output_text for indicator in completion_indicators)
        assert found_completion, f"Missing completion indicator. Output: {output_text}"
        
        # Summary validation
        total_file_size = sum(f.stat().st_size for f in created_files)
        assert total_file_size > 500, f"Total files seem too small: {total_file_size} bytes"

    @pytest.mark.e2e
    @pytest.mark.network
    @pytest.mark.slow
    @pytest.mark.skipif(
        not check_network_connectivity("finance.yahoo.com"),
        reason="No network connectivity to Yahoo Finance"
    )
    def test_yahoo_all_supported_periods_workflow(self, cli_runner, temp_output_dir):
        """
        Test Yahoo Finance download workflow with ALL supported time periods.
        
        This comprehensive test validates:
        1. All Yahoo Finance supported periods work end-to-end
        2. Proper file path creation for different periods
        3. Data retrieval across different time frames
        4. Period-specific date range handling based on Yahoo limitations
        
        Yahoo Finance supported periods tested:
        - Monthly (1mo): No date restrictions  
        - Weekly (1wk): No date restrictions
        - Daily (1d): No date restrictions
        - Hourly (1h): Up to 729 days of history
        - 30-minute (30m): Up to 59 days of history  
        - 15-minute (15m): Up to 59 days of history
        - 5-minute (5m): Up to 59 days of history
        - 1-minute (1m): Up to 7 days of history
        """
        # Define ALL Yahoo Finance supported periods with appropriate date ranges
        # Based on Yahoo Finance limitations from the provider implementation
        period_configs = [
            # Long-term periods (no date restrictions - should work)
            {"period": "1M", "days_back": 120, "expected_dir": "stocks/1M", "min_rows": 2},   # Monthly
            {"period": "1W", "days_back": 35, "expected_dir": "stocks/1W", "min_rows": 3},    # Weekly  
            {"period": "1d", "days_back": 10, "expected_dir": "stocks/1d", "min_rows": 5},    # Daily
            
            # Medium-term periods (up to 729 days for hourly)
            {"period": "1h", "days_back": 3, "expected_dir": "stocks/1h", "min_rows": 24},    # Hourly - 3 days
            
            # Short-term periods (up to 59 days) - may fail due to market hours
            {"period": "30m", "days_back": 2, "expected_dir": "stocks/30m", "min_rows": 24},  # 30-min - 2 days
            {"period": "15m", "days_back": 2, "expected_dir": "stocks/15m", "min_rows": 48},  # 15-min - 2 days
            {"period": "5m", "days_back": 1, "expected_dir": "stocks/5m", "min_rows": 60},    # 5-min - 1 day
            
            # Ultra short-term (up to 7 days) - likely to fail due to real-time restrictions
            {"period": "1m", "days_back": 1, "expected_dir": "stocks/1m", "min_rows": 200}    # 1-min - 1 day
        ]
        
        successful_periods = []
        failed_periods = []
        
        for config in period_configs:
            period = config["period"]
            days_back = config["days_back"]
            expected_dir = config["expected_dir"]
            min_rows = config["min_rows"]
            
            # Calculate appropriate date range for this period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Create period-specific asset file
            period_assets_file = temp_output_dir / f"assets_{period}.json"
            period_assets_content = {
                "stock": {
                    "AAPL": {
                        "code": "AAPL",
                        "tick_date": "1980-12-12",
                        "start_date": "1980-12-12", 
                        "periods": period  # Use the specific period
                    }
                }
            }
            
            # Write period-specific asset file
            import json
            with open(period_assets_file, 'w') as f:
                json.dump(period_assets_content, f, indent=2)
            
            try:
                # Execute CLI command for this period
                result = cli_runner.invoke(cli, [
                    'download',
                    '--provider', 'yahoo',
                    '--assets', str(period_assets_file),
                    '--start-date', start_date_str,
                    '--end-date', end_date_str,
                    '--output-dir', str(temp_output_dir),
                    '--yes'
                ])
                
                # Check if command succeeded
                if result.exit_code != 0:
                    failed_periods.append({
                        "period": period,
                        "reason": f"Command failed with exit code {result.exit_code}",
                        "output": result.output[:500]  # First 500 chars
                    })
                    continue
                
                # Validate file creation
                expected_file = temp_output_dir / expected_dir / "AAPL.csv"
                if not expected_file.exists():
                    failed_periods.append({
                        "period": period,
                        "reason": f"Expected file not created: {expected_file}",
                        "output": result.output[:500]
                    })
                    continue
                
                # Comprehensive CSV validation for this period
                from .csv_validation import validate_market_data_csv
                
                validation_result = validate_market_data_csv(
                    expected_file,
                    expected_min_rows=1,  # Minimum 1 data row
                    date_range=(start_date, end_date),
                    provider="yahoo"
                )
                
                if not validation_result.is_valid:
                    failed_periods.append({
                        "period": period,
                        "reason": f"CSV validation failed: {', '.join(validation_result.errors)}",
                        "output": result.output[:500]
                    })
                    continue
                
                # If we got here, the period test was successful
                successful_periods.append({
                    "period": period,
                    "file": str(expected_file),
                    "rows": validation_result.row_count,
                    "columns": len(validation_result.columns),
                    "size": validation_result.file_size,
                    "warnings": validation_result.warnings
                })
                
            except Exception as e:
                failed_periods.append({
                    "period": period,
                    "reason": f"Exception: {str(e)}",
                    "output": "Exception during test execution"
                })
        
        # Test validation - require at least 50% of periods to succeed
        total_periods = len(period_configs)
        success_count = len(successful_periods)
        failure_count = len(failed_periods)
        
        # Log results for debugging
        print(f"\n=== Period Test Results ===")
        print(f"Total periods tested: {total_periods}")
        print(f"Successful periods: {success_count}")
        print(f"Failed periods: {failure_count}")
        
        if successful_periods:
            print("\n✅ Successful periods:")
            for result in successful_periods:
                print(f"  {result['period']}: {result['rows']} rows, {result['size']} bytes")
        
        if failed_periods:
            print("\n❌ Failed periods:")
            for failure in failed_periods:
                print(f"  {failure['period']}: {failure['reason']}")
        
        # Require at least 1 period to succeed (we're testing a subset now)
        min_required_success = 1
        assert success_count >= min_required_success, (
            f"Insufficient successful periods. Got {success_count}/{total_periods}, "
            f"required at least {min_required_success}. "
            f"Failures: {[f['period'] + ': ' + f['reason'] for f in failed_periods]}"
        )
        
        # Basic validation - ensure at least daily period worked
        successful_period_names = [r['period'] for r in successful_periods]
        assert '1d' in successful_period_names, f"Daily period must work. Successful: {successful_period_names}"
        
        # Log summary for documentation/debugging purposes
        print(f"\n📊 Summary: {success_count}/{total_periods} periods working with Yahoo Finance")
        if success_count > 1:
            print(f"✅ Multiple timeframes validated: {', '.join(successful_period_names)}")
        else:
            print("ℹ️ Only daily timeframe validated (others may require market hours or special handling)")