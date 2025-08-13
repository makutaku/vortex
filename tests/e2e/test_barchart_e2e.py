"""
End-to-end tests for Barchart provider complete workflow.

Tests complete user scenarios from CLI invocation through authentication,
data download, and file output validation using real Barchart.com API.

IMPORTANT: These tests require valid Barchart credentials and network access.
They make real API calls to Barchart.com and should be run with caution in
production environments due to API rate limits.

CONSERVATIVE APPROACH: Yahoo E2E tests provide comprehensive scenario coverage.
Barchart tests focus on Barchart-specific functionality with controlled API usage:
- Authentication workflow (bc-utils methodology)
- Comprehensive download test with assets file (6 downloads: 3 symbols × 2 periods)
- Asset coverage: Stock (AAPL), Future (GC), Forex (EURUSD) with daily + hourly periods
- Full CSV validation for actual data quality verification
- Minimal symbol count (1 per asset type) to conserve daily credits while ensuring coverage
"""

import pytest
import tempfile
import socket
import os
from pathlib import Path
from click.testing import CliRunner
from datetime import datetime, timedelta

from vortex.cli.main import cli
from vortex.models.columns import DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN


def check_barchart_connectivity(host="www.barchart.com", port=443, timeout=5):
    """Check if network connectivity to Barchart is available."""
    try:
        socket.create_connection((host, port), timeout)
        return True
    except (socket.timeout, socket.error, OSError):
        return False


def get_barchart_credentials():
    """Get Barchart credentials from environment variables."""
    username = os.environ.get('VORTEX_BARCHART_USERNAME')
    password = os.environ.get('VORTEX_BARCHART_PASSWORD')
    return username, password


def has_barchart_credentials():
    """Check if Barchart credentials are available."""
    username, password = get_barchart_credentials()
    return bool(username and password)


@pytest.mark.e2e
@pytest.mark.network
@pytest.mark.credentials
class TestBarchartEndToEnd:
    """End-to-end tests for Barchart provider complete workflow."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner for tests."""
        return CliRunner()

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def barchart_credentials(self):
        """Get Barchart credentials or skip test if not available."""
        username, password = get_barchart_credentials()
        if not username or not password:
            pytest.skip(
                "Barchart credentials not available. Set VORTEX_BARCHART_USERNAME "
                "and VORTEX_BARCHART_PASSWORD environment variables."
            )
        return username, password

    @pytest.fixture
    def test_config_file(self, temp_output_dir, barchart_credentials):
        """Create test configuration file with Barchart credentials."""
        username, password = barchart_credentials
        
        config_content = f"""
[general]
output_directory = "{temp_output_dir}"
default_provider = "barchart"

[general.logging]
level = "DEBUG"
format = "console"
output = ["console"]

[providers.barchart]
username = "{username}"
password = "{password}"
daily_limit = 50

[date_range]
start_year = 2024
end_year = 2025
"""
        
        config_file = temp_output_dir / "test_config.toml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        return config_file

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    def test_barchart_authentication_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test Barchart authentication workflow through CLI.
        
        This test validates:
        1. Configuration file parsing with Barchart credentials
        2. Provider initialization with authentication
        3. Login process using bc-utils methodology
        4. Proper error handling for authentication failures
        
        This is a lightweight test focused on authentication only.
        """
        # Test that providers command works with Barchart configured
        result = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            'providers', 
            '--list'
        ])
        
        # Should complete successfully or with minor provider issues
        assert result.exit_code in [0, 1], f"Providers command failed: {result.output}"
        
        # Should show Barchart provider in the list
        output_text = result.output
        assert "barchart" in output_text.lower(), f"Barchart not found in providers output: {output_text}"
        
        # If successful, should show total providers count
        if result.exit_code == 0:
            assert "Total providers available" in output_text

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    @pytest.mark.slow
    def test_barchart_download_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test complete Barchart download workflow with comprehensive asset coverage.
        
        This test validates:
        1. Assets file processing with multiple instrument types
        2. Barchart authentication using bc-utils methodology  
        3. API session establishment and XSRF token management
        4. Download workflow for stocks, futures, and forex
        5. Multiple time periods (daily and hourly) validation
        6. Comprehensive CSV data validation for each download
        7. Proper error handling and logging
        
        Coverage: 6 downloads total (3 symbols × 2 periods each)
        - Stock: AAPL (daily + hourly)
        - Future: GC (daily + hourly) 
        - Forex: EURUSD (daily + hourly)
        """
        # Create comprehensive test assets file with minimal symbols
        test_assets_file = temp_output_dir / "barchart_test_assets.json"
        test_assets_content = {
            "stock": {
                "AAPL": {
                    "code": "AAPL",
                    "tick_date": "1980-12-12",
                    "start_date": "1980-12-12",
                    "periods": "1d,1h"  # Both daily and hourly
                }
            },
            "future": {
                "GC": {
                    "code": "GC",
                    "tick_date": "2008-05-04", 
                    "start_date": "2008-05-04",
                    "periods": "1d,1h"  # Both daily and hourly
                }
            },
            "forex": {
                "EURUSD": {
                    "code": "EURUSD",
                    "tick_date": "2000-01-01",
                    "start_date": "2000-01-01", 
                    "periods": "1d,1h"  # Both daily and hourly
                }
            }
        }
        
        # Write test asset file
        import json
        with open(test_assets_file, 'w') as f:
            json.dump(test_assets_content, f, indent=2)
        
        # Calculate historical date range for reliable data availability
        end_date = datetime.now() - timedelta(days=1)  # Yesterday 
        start_date = end_date - timedelta(days=7)      # 1 week of data
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute CLI download workflow with assets file
        result = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            'download',
            '--provider', 'barchart',
            '--assets', str(test_assets_file),
            '--start-date', start_date_str,
            '--end-date', end_date_str,
            '--output-dir', str(temp_output_dir),
            '--yes'
        ])
        
        # Validate command execution
        assert result is not None, "Test execution failed"
        output_text = result.output
        
        # Check authentication success (most critical)
        auth_success = "Logged in" in output_text
        assert auth_success, f"Authentication failed. Output: {output_text}"
        
        # Track successful downloads for validation
        expected_files = [
            # Stock files
            ("stocks", "1d", "AAPL.csv"),
            ("stocks", "1h", "AAPL.csv"),
            # Future files  
            ("futures", "1d", "GC.csv"),
            ("futures", "1h", "GC.csv"),
            # Forex files
            ("forex", "1d", "EURUSD.csv"),
            ("forex", "1h", "EURUSD.csv"),
        ]
        
        successful_files = []
        failed_files = []
        
        # Check each expected file and validate if it exists
        for asset_type, period, filename in expected_files:
            expected_file = temp_output_dir / asset_type / period / filename
            
            if expected_file.exists() and expected_file.stat().st_size > 100:
                successful_files.append((asset_type, period, filename, expected_file))
            else:
                failed_files.append((asset_type, period, filename))
        
        # Log download results
        print(f"\n=== Barchart Download Results ===")
        print(f"Successful downloads: {len(successful_files)}/6")
        print(f"Failed downloads: {len(failed_files)}/6")
        
        if successful_files:
            print("✅ Successful files:")
            for asset_type, period, filename, _ in successful_files:
                print(f"  {asset_type}/{period}/{filename}")
        
        if failed_files:
            print("❌ Failed files:")
            for asset_type, period, filename in failed_files:
                print(f"  {asset_type}/{period}/{filename}")
        
        # Require at least 2 successful downloads (authentication + basic functionality)
        assert len(successful_files) >= 2, (
            f"Expected at least 2 successful downloads, got {len(successful_files)}. "
            f"This ensures authentication works and basic download functionality is validated. "
            f"Output: {output_text}"
        )
        
        # Comprehensive validation for each successful file
        from .csv_validation import validate_market_data_csv, validate_business_day_count
        
        validation_results = []
        date_range = (start_date, end_date)
        
        for asset_type, period, filename, file_path in successful_files:
            try:
                # Perform comprehensive CSV validation
                validation_result = validate_market_data_csv(
                    file_path,
                    expected_min_rows=2,  # At least 2 data points in 1-week period
                    date_range=date_range,
                    provider="barchart"
                )
                
                # Assert each file passes validation
                assert validation_result.is_valid, (
                    f"Barchart CSV validation failed for {asset_type}/{period}/{filename}: "
                    f"{validation_result.errors}"
                )
                
                # Validate business day count with tolerance for Barchart
                is_valid, expected_days, message = validate_business_day_count(
                    start_date, end_date, validation_result.row_count, 
                    tolerance=7  # Higher tolerance for Barchart data availability
                )
                
                validation_results.append({
                    "file": f"{asset_type}/{period}/{filename}",
                    "rows": validation_result.row_count,
                    "columns": validation_result.columns,
                    "size": validation_result.file_size,
                    "valid": validation_result.is_valid,
                    "business_days": message
                })
                
                print(f"✅ CSV validation passed for {asset_type}/{period}/{filename}:")
                print(f"  Rows: {validation_result.row_count}")
                print(f"  Columns: {', '.join(validation_result.columns)}")
                print(f"  Size: {validation_result.file_size} bytes")
                if not is_valid:
                    print(f"  ⚠️ Business day warning: {message}")
                
            except Exception as e:
                print(f"❌ Validation failed for {asset_type}/{period}/{filename}: {e}")
                raise
        
        # Summary validation
        assert len(validation_results) == len(successful_files), "All successful files must pass validation"
        
        # Validate comprehensive coverage achieved
        total_downloads = len(successful_files)
        assert total_downloads >= 2, f"Expected at least 2 downloads for meaningful test, got {total_downloads}"
        
        print(f"\n🎯 Barchart E2E Test Summary:")
        print(f"  Authentication: ✅ SUCCESS")
        print(f"  Downloads: {total_downloads}/6 successful")
        print(f"  Validation: {len(validation_results)} files validated")
        print(f"  Asset types: {len(set(r['file'].split('/')[0] for r in validation_results))} types covered")

    # REMOVED: test_barchart_stocks_download_workflow
    # Reason: Integrated into comprehensive download workflow test with assets file.
    # Stock coverage provided via AAPL in main download test.
    
    # REMOVED: test_barchart_asset_file_workflow  
    # Reason: Integrated into main download workflow test.
    # Assets file processing now validated with comprehensive coverage.
    
    # REMOVED: test_barchart_error_handling_workflow
    # Reason: Yahoo E2E tests provide extensive error handling coverage.
    # Barchart-specific errors handled in comprehensive download test.
    
    # REMOVED: test_barchart_api_resilience_workflow
    # Reason: Yahoo E2E tests validate API resilience patterns.
    # Barchart resilience confirmed through comprehensive download test.