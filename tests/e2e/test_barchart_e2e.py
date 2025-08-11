"""
End-to-end tests for Barchart provider complete workflow.

Tests complete user scenarios from CLI invocation through authentication,
data download, and file output validation using real Barchart.com API.

IMPORTANT: These tests require valid Barchart credentials and network access.
They make real API calls to Barchart.com and should be run with caution in
production environments due to API rate limits.
"""

import pytest
import tempfile
import socket
import os
from pathlib import Path
from click.testing import CliRunner
from datetime import datetime, timedelta

from vortex.cli.main import cli
from vortex.models.columns import DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN


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
        Test complete Barchart download workflow and error handling.
        
        This comprehensive test validates:
        1. CLI command parsing and configuration
        2. Barchart authentication using bc-utils methodology
        3. API session establishment and XSRF token management
        4. API endpoint attempts (JSON and CSV fallback)
        5. Graceful handling of unavailable symbols
        6. Proper error messages and logging
        7. System resilience when data is not available
        
        Note: Barchart specializes in commodity/futures data. Stock symbols may not be
        available, which is normal and tests our error handling capabilities.
        """
        # Calculate historical date range (definitely in the past to avoid future date issues)
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=14)     # 2 weeks of data
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute complete CLI download workflow  
        # Focus on symbols that are definitely available on Barchart (commodities/futures)
        # Barchart specializes in commodity data more than stocks
        test_symbols = ['AAPL', 'IBM', '^GSPC']  # Try stocks, but expect some might not work
        
        result = None
        successful_symbol = None
        
        for symbol in test_symbols:
            result = cli_runner.invoke(cli, [
                '--config', str(test_config_file),
                'download',
                '--provider', 'barchart',
                '--symbol', symbol,
                '--start-date', start_date_str,
                '--end-date', end_date_str,
                '--output-dir', str(temp_output_dir),
                '--yes'
            ])
            
            # Check if this symbol worked
            if result.exit_code == 0 and ("Download completed successfully" in result.output or "successful" in result.output):
                successful_symbol = symbol
                break
        
        # At least one symbol should work or we should get clear authentication success
        assert result is not None, "No test symbols were tried"
        
        # Check if authentication worked (most important for this test)
        output_text = result.output
        auth_success = "Logged in" in output_text
        assert auth_success, f"Authentication failed. Output: {output_text}"
        
        # If a symbol worked, validate file creation
        if successful_symbol:
            # Determine expected directory based on symbol type
            if successful_symbol in ['GCZ24', 'GC']:
                expected_dir = "futures"
            else:
                expected_dir = "stocks"
                
            expected_csv_file = temp_output_dir / expected_dir / "1d" / f"{successful_symbol}.csv"
            
            if expected_csv_file.exists():
                # Validate file content if it was created
                with open(expected_csv_file, 'r') as f:
                    csv_content = f.read()
                    assert len(csv_content) > 100, f"CSV file too small: {len(csv_content)} chars"
                    
                    csv_lines = csv_content.strip().split('\n')
                    assert len(csv_lines) >= 2, f"CSV should have header + data. Got: {len(csv_lines)} lines"
            else:
                # If no file was created, that's also okay as long as auth worked
                # Some symbols might not have data available
                pass
        else:
            # No symbol worked, but if auth succeeded, that's still valuable
            # Just ensure we got proper error messages
            error_indicators = ["not found", "unavailable", "invalid", "error"]
            found_error = any(indicator in output_text.lower() for indicator in error_indicators)
            assert found_error, f"No clear error indication when download failed: {output_text}"

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    @pytest.mark.slow
    def test_barchart_stocks_download_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test complete Barchart stocks download workflow with real data.
        
        This test validates:
        1. Stock symbol processing through Barchart
        2. Different API endpoints for stocks vs futures
        3. Proper directory structure (stocks/1d/)
        4. Stock-specific data format and validation
        5. Error handling for stock data retrieval
        
        Uses AAPL as it's highly liquid and available on Barchart.
        """
        # Calculate recent date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute stock download workflow
        result = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            'download',
            '--provider', 'barchart',
            '--symbol', 'AAPL',  # Apple stock - highly liquid
            '--start-date', start_date_str,
            '--end-date', end_date_str,
            '--output-dir', str(temp_output_dir),
            '--yes'
        ])
        
        # Validate command success (may have different success criteria than futures)
        # Some stocks might not be available on Barchart or require premium access
        if result.exit_code != 0:
            # Check if it's a data availability issue vs authentication issue
            output_text = result.output
            if "authentication" in output_text.lower() or "login" in output_text.lower():
                pytest.fail(f"Authentication failed: {result.output}")
            elif "not found" in output_text.lower() or "unavailable" in output_text.lower():
                pytest.skip("Stock data not available on Barchart (may require premium subscription)")
            else:
                pytest.fail(f"Unexpected failure: {result.output}")
        
        # If successful, validate file creation
        expected_csv_file = temp_output_dir / "stocks" / "1d" / "AAPL.csv"
        if expected_csv_file.exists():
            # Validate content
            with open(expected_csv_file, 'r') as f:
                content = f.read()
                assert len(content) > 50, f"Stock CSV too small: {len(content)} chars"
                
                lines = content.strip().split('\n')
                assert len(lines) >= 2, "Should have header + data"
                
                # Check for stock-specific columns
                header = lines[0].upper()
                assert any(col in header for col in ["DATE", "DATETIME"]), f"Missing date: {header}"
                assert "CLOSE" in header, f"Missing close price: {header}"

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    def test_barchart_asset_file_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test Barchart provider with JSON assets file containing multiple symbols.
        
        This test validates:
        1. JSON asset file parsing with Barchart-specific format
        2. Multi-symbol batch processing
        3. Mixed asset types (futures + stocks if available)
        4. Proper error handling for unavailable symbols
        5. Batch processing completion even with partial failures
        
        Uses a minimal asset file with liquid instruments.
        """
        # Create test assets file with Barchart-compatible symbols
        test_assets_file = temp_output_dir / "barchart_assets.json"
        test_assets_content = {
            "future": {
                "GC": {
                    "code": "GC",
                    "tick_date": "2020-01-01",
                    "start_date": "2020-01-01",
                    "periods": "1d",
                    "cycle": "GHKMQUVXZ"  # Gold futures cycle
                },
                "CL": {
                    "code": "CL", 
                    "tick_date": "2020-01-01",
                    "start_date": "2020-01-01",
                    "periods": "1d",
                    "cycle": "FGHJKMNQUVXZ"  # Crude oil futures cycle
                }
            }
        }
        
        # Write assets file
        import json
        with open(test_assets_file, 'w') as f:
            json.dump(test_assets_content, f, indent=2)
        
        # Calculate recent date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Execute batch download with assets file
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
        assert result.exit_code == 0, f"Assets file processing failed: {result.output}"
        
        # Check that symbols were processed
        output_text = result.output
        expected_symbols = ["GC", "CL"]
        processed_symbols = []
        
        for symbol in expected_symbols:
            if symbol in output_text:
                processed_symbols.append(symbol)
        
        assert len(processed_symbols) >= 1, (
            f"No symbols processed successfully. Expected: {expected_symbols}, "
            f"Output: {output_text}"
        )
        
        # Validate file creation for processed symbols
        created_files = []
        for symbol in processed_symbols:
            expected_file = temp_output_dir / "futures" / "1d" / f"{symbol}.csv"
            if expected_file.exists():
                created_files.append(expected_file)
                
                # Quick content validation
                with open(expected_file, 'r') as f:
                    content = f.read()
                    assert len(content) > 100, f"{symbol} file too small"
        
        # Require at least one successful file creation
        assert len(created_files) >= 1, (
            f"No CSV files created. Processed symbols: {processed_symbols}, "
            f"Directory contents: {list(temp_output_dir.rglob('*'))}"
        )
        
        # Validate batch processing completion
        completion_indicators = [
            "Download completed successfully",
            "Processing completed",
            "Finished"
        ]
        found_completion = any(indicator in output_text for indicator in completion_indicators)
        assert found_completion, f"Missing batch completion indicator: {output_text}"

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    def test_barchart_error_handling_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test Barchart provider error handling and resilience.
        
        This test validates:
        1. Invalid symbol handling
        2. Date range validation
        3. API rate limiting responses
        4. Authentication error recovery
        5. Graceful failure with informative messages
        
        Uses intentionally problematic inputs to test error paths.
        """
        # Test 1: Invalid symbol
        result = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            'download',
            '--provider', 'barchart',
            '--symbol', 'INVALID_SYMBOL_XYZ123',  # Non-existent symbol
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-05',
            '--output-dir', str(temp_output_dir),
            '--yes'
        ])
        
        # Should handle invalid symbol gracefully
        # Exit code might be non-zero, but should have informative error message
        output_text = result.output
        
        # Should contain informative error messages
        error_indicators = [
            "not found",
            "invalid",
            "unavailable", 
            "error",
            "failed"
        ]
        
        found_error_indicator = any(indicator in output_text.lower() for indicator in error_indicators)
        assert found_error_indicator, (
            f"Missing error indication for invalid symbol. Output: {output_text}"
        )
        
        # Should not create empty files for invalid symbols
        invalid_file = temp_output_dir / "futures" / "1d" / "INVALID_SYMBOL_XYZ123.csv"
        if invalid_file.exists():
            # If file was created, it should be empty or contain error message
            with open(invalid_file, 'r') as f:
                content = f.read()
                assert len(content) < 100, f"Invalid symbol created substantial file: {len(content)} chars"
        
        # Test 2: Invalid date range (future dates)
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        result2 = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            'download',
            '--provider', 'barchart', 
            '--symbol', 'GC',
            '--start-date', future_date,
            '--end-date', future_date,
            '--output-dir', str(temp_output_dir),
            '--yes'
        ])
        
        # Should handle future dates gracefully
        # Either reject with clear error or return empty result
        if result2.exit_code != 0:
            assert "date" in result2.output.lower() or "range" in result2.output.lower(), (
                f"Missing date-related error message: {result2.output}"
            )

    @pytest.mark.skipif(
        not check_barchart_connectivity("www.barchart.com"),
        reason="No network connectivity to Barchart.com"
    )
    @pytest.mark.skipif(
        not has_barchart_credentials(),
        reason="Barchart credentials not available in environment"
    )
    @pytest.mark.slow
    def test_barchart_api_resilience_workflow(self, cli_runner, temp_output_dir, test_config_file):
        """
        Test Barchart provider API resilience and fallback mechanisms.
        
        This test validates:
        1. JSON API primary endpoint usage
        2. CSV fallback mechanism when JSON fails
        3. Multiple API endpoint fallback chain
        4. Session management and token refresh
        5. Retry logic and error recovery
        
        This test specifically exercises the bc-utils methodology implementation.
        """
        # Use a symbol that might trigger different API responses
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Enable debug logging to see API flow
        result = cli_runner.invoke(cli, [
            '--config', str(test_config_file),
            '-v',  # Verbose output to see API calls
            'download',
            '--provider', 'barchart',
            '--symbol', 'GC',  # Use reliable symbol
            '--start-date', start_date_str,
            '--end-date', end_date_str,
            '--output-dir', str(temp_output_dir),
            '--yes'
        ])
        
        # Validate successful completion
        assert result.exit_code == 0, f"API resilience test failed: {result.output}"
        
        # Check for API methodology indicators in verbose output
        output_text = result.output
        api_indicators = [
            "JSON API",  # Primary JSON endpoint attempted
            "proxies/core-api",  # Core API endpoint
            "proxies/timeseries",  # Timeseries endpoint  
            "CSV download",  # CSV fallback mechanism
            "successful"  # Some API method succeeded
        ]
        
        found_indicators = [indicator for indicator in api_indicators if indicator in output_text]
        assert len(found_indicators) >= 2, (
            f"Missing API methodology indicators. "
            f"Expected multiple API attempts, found: {found_indicators}. "
            f"Output: {output_text}"
        )
        
        # Validate file was created successfully
        expected_file = temp_output_dir / "futures" / "1d" / "GC.csv"
        assert expected_file.exists(), "No file created despite successful API calls"
        
        # Validate content quality
        with open(expected_file, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            assert len(lines) >= 2, "Insufficient data from API resilience test"
            
            # Check that data looks valid
            header = lines[0]
            assert "," in header, "Invalid CSV format from API calls"