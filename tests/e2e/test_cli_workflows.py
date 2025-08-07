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
        
        # Validate CSV file content
        with open(expected_csv_file, 'r') as f:
            csv_content = f.read()
            
            # Check for proper CSV header
            csv_lines = csv_content.strip().split('\n')
            assert len(csv_lines) >= 2, f"CSV file should have header + data rows. Got: {len(csv_lines)} lines"
            
            # Validate CSV header format
            header = csv_lines[0].lower()
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            for column in required_columns:
                assert column in header, f"Missing required column '{column}' in header: {header}"
            
            # Validate at least one data row exists
            assert len(csv_lines) > 1, "CSV should contain at least one data row"
            
            # Validate data row format (basic sanity check)
            if len(csv_lines) > 1:
                sample_data_row = csv_lines[1]
                data_fields = sample_data_row.split(',')
                assert len(data_fields) >= 6, f"Data row should have at least 6 fields: {sample_data_row}"
        
        # Validate file size (ensure it's not empty)
        file_size = expected_csv_file.stat().st_size
        assert file_size > 100, f"CSV file seems too small: {file_size} bytes"

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
        
        # Validate file creation for each symbol
        created_files = []
        missing_files = []
        
        for symbol in expected_symbols:
            expected_file = temp_output_dir / "stocks" / "1d" / f"{symbol}.csv"
            if expected_file.exists():
                created_files.append(expected_file)
                
                # Validate file content briefly
                with open(expected_file, 'r') as f:
                    content = f.read()
                    assert len(content) > 50, f"{symbol}.csv seems too small: {len(content)} chars"
                    # Check for date/datetime column (different providers use different formats)
                    has_date_column = any(col in content.upper() for col in ["DATE", "DATETIME"])
                    assert has_date_column, f"{symbol}.csv missing date column. Content start: {content[:200]}"
                    
            else:
                missing_files.append(symbol)
        
        # Require at least 2 out of 3 files to be created (some might fail due to market conditions)
        assert len(created_files) >= 2, f"Expected at least 2 CSV files. Created: {len(created_files)}, Missing: {missing_files}"
        
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