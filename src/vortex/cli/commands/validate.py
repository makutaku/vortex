"""Data validation command."""

import logging
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from vortex.models.columns import (
    DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)
from vortex.constants import BYTES_PER_KB, BYTES_PER_MB

# Import provider-specific constants from their respective providers
from vortex.infrastructure.providers.yahoo.column_mapping import YahooColumnMapping
from vortex.infrastructure.providers.barchart.column_mapping import BarchartColumnMapping  
from vortex.infrastructure.providers.ibkr.column_mapping import IbkrColumnMapping

# Create instances to access provider-specific constants
_yahoo_mapping = YahooColumnMapping()
_barchart_mapping = BarchartColumnMapping()
_ibkr_mapping = IbkrColumnMapping()

# Extract constants for use in validation
ADJ_CLOSE_COLUMN = _yahoo_mapping.ADJ_CLOSE_COLUMN
DIVIDENDS_COLUMN = _yahoo_mapping.DIVIDENDS_COLUMN
STOCK_SPLITS_COLUMN = _yahoo_mapping.STOCK_SPLITS_COLUMN
OPEN_INTEREST_COLUMN = _barchart_mapping.OPEN_INTEREST_COLUMN
WAP_COLUMN = _ibkr_mapping.WAP_COLUMN
COUNT_COLUMN = _ibkr_mapping.COUNT_COLUMN

# Create provider-specific column sets for validation
YAHOO_SPECIFIC_COLUMNS = _yahoo_mapping.get_provider_specific_columns()
BARCHART_SPECIFIC_COLUMNS = _barchart_mapping.get_provider_specific_columns()
IBKR_SPECIFIC_COLUMNS = _ibkr_mapping.get_provider_specific_columns()

console = Console()
logger = logging.getLogger(__name__)

@click.command()
@click.option(
    "--path", "-p",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory or file to validate"
)
@click.option(
    "--provider",
    type=str,
    help="Expected data provider format (dynamic based on available plugins)"
)
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix validation issues"
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed validation results"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format for results"
)
@click.pass_context
def validate(
    ctx: click.Context,
    path: Path,
    provider: Optional[str],
    fix: bool,
    detailed: bool,
    output_format: str,
) -> None:
    """Validate downloaded data integrity and format.
    
    \b
    Examples:
        vortex validate --path ./data
        vortex validate --path ./data/GC.csv --provider barchart
        vortex validate --path ./data --fix --detailed
    """
    
    console.print(f"[bold]Validating data in: {path}[/bold]")
    
    # Determine files to validate
    files_to_validate = get_files_to_validate(path)
    
    if not files_to_validate:
        console.print("[yellow]No data files found to validate[/yellow]")
        return
    
    console.print(f"Found {len(files_to_validate)} files to validate")
    
    # Run validation
    results = run_validation(files_to_validate, provider, fix)
    
    # Display results
    display_results(results, detailed, output_format)
    
    # Summary
    show_validation_summary(results)

def get_files_to_validate(path: Path) -> List[Path]:
    """Get list of data files to validate."""
    files = []
    
    if path.is_file():
        if path.suffix.lower() in ['.csv', '.parquet']:
            files.append(path)
    else:
        # Search directory for data files
        for pattern in ['*.csv', '*.parquet']:
            files.extend(path.rglob(pattern))
    
    return sorted(files)

def run_validation(
    files: List[Path],
    provider: Optional[str],
    fix: bool
) -> List[dict]:
    """Run validation on all files."""
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("Validating files...", total=len(files))
        
        for file_path in files:
            result = validate_single_file(file_path, provider, fix)
            results.append(result)
            
            status = "✓" if result["valid"] else "✗"
            progress.update(
                task,
                advance=1,
                description=f"{status} {file_path.name}"
            )
    
    return results

def validate_single_file(path: Path, provider: Optional[str], fix: bool) -> dict:
    """Validate a single data file."""
    result = {
        "file": path,
        "valid": True,
        "errors": [],
        "warnings": [],
        "metrics": {},
        "fixed": False
    }
    
    try:
        # TODO: Implement actual validation logic
        # For now, we'll simulate validation
        
        # Basic file checks
        if path.stat().st_size == 0:
            result["errors"].append("File is empty")
            result["valid"] = False
        
        # Format-specific validation
        if path.suffix.lower() == '.csv':
            csv_result = validate_csv_file(path, provider)
            result["errors"].extend(csv_result.get("errors", []))
            result["warnings"].extend(csv_result.get("warnings", []))
            result["metrics"].update(csv_result.get("metrics", {}))
            if csv_result.get("errors"):
                result["valid"] = False
        elif path.suffix.lower() == '.parquet':
            parquet_result = validate_parquet_file(path, provider)
            result["errors"].extend(parquet_result.get("errors", []))
            result["warnings"].extend(parquet_result.get("warnings", []))
            result["metrics"].update(parquet_result.get("metrics", {}))
            if parquet_result.get("errors"):
                result["valid"] = False
        
        # Provider-specific validation
        if provider:
            provider_result = validate_provider_format(path, provider)
            result["errors"].extend(provider_result.get("errors", []))
            result["warnings"].extend(provider_result.get("warnings", []))
            if provider_result.get("errors"):
                result["valid"] = False
        
        # Attempt fixes if requested
        if fix and result["errors"] and not result["valid"]:
            result["fixed"] = attempt_fixes(path, result["errors"])
            if result["fixed"]:
                result["valid"] = True
                result["errors"] = []
        
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Validation error: {e}")
        logger.exception(f"Error validating {path}")
    
    return result

def validate_csv_file(path: Path, provider: Optional[str]) -> dict:
    """Validate CSV file format."""
    result = {"errors": [], "warnings": [], "metrics": {}}
    
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(path)
        result["metrics"]["rows"] = len(df)
        result["metrics"]["columns"] = len(df.columns)
        
        # Basic validation checks
        if df.empty:
            result["errors"].append("CSV file contains no data")
            return result
        
        # Check for common financial data columns (using constants for consistency)
        expected_columns_constants = [DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        expected_columns = [col.lower() for col in expected_columns_constants]
        df_columns_lower = [col.lower() for col in df.columns]
        
        missing_columns = []
        for col in expected_columns:
            if col not in df_columns_lower and col.capitalize() not in df.columns:
                missing_columns.append(col.upper())
        
        if missing_columns:
            result["warnings"].append(f"Missing common columns: {', '.join(missing_columns)}")
        
        # Check for empty rows
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            result["warnings"].append(f"Found {empty_rows} completely empty rows")
        
        # Validate OHLC relationships if columns exist
        ohlc_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        ohlc_lower = [col.lower() for col in ohlc_constants]
        if all(col in df_columns_lower or col.capitalize() in df.columns for col in ohlc_lower):
            # Find actual column names (case insensitive)
            ohlc_cols = {}
            for target_lower, target_const in zip(ohlc_lower, ohlc_constants):
                for actual_col in df.columns:
                    if actual_col.lower() == target_lower:
                        ohlc_cols[target_lower] = actual_col
                        break
            
            if len(ohlc_cols) == 4:
                # Validate OHLC relationships
                invalid_ohlc = 0
                for idx, row in df.iterrows():
                    try:
                        o = float(row[ohlc_cols['open']])
                        h = float(row[ohlc_cols['high']]) 
                        l = float(row[ohlc_cols['low']])
                        c = float(row[ohlc_cols['close']])
                        if not (l <= o <= h and l <= c <= h):
                            invalid_ohlc += 1
                    except (ValueError, TypeError):
                        # Skip non-numeric values
                        continue
                
                if invalid_ohlc > 0:
                    result["errors"].append(f"Found {invalid_ohlc} rows with invalid OHLC relationships")
        
    except FileNotFoundError:
        result["errors"].append("File not found")
    except pd.errors.EmptyDataError:
        result["errors"].append("CSV file is empty or invalid")
    except Exception as e:
        result["errors"].append(f"CSV validation error: {e}")
    
    return result

def validate_parquet_file(path: Path, provider: Optional[str]) -> dict:
    """Validate Parquet file format."""
    result = {"errors": [], "warnings": [], "metrics": {}}
    
    try:
        import pandas as pd
        
        # Read Parquet file
        df = pd.read_parquet(path)
        result["metrics"]["rows"] = len(df)
        result["metrics"]["columns"] = len(df.columns)
        
        # Basic validation checks
        if df.empty:
            result["errors"].append("Parquet file contains no data")
            return result
        
        # Check for common financial data columns (using constants for consistency)
        expected_columns_constants = [DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        expected_columns = [col.lower() for col in expected_columns_constants]
        df_columns_lower = [col.lower() for col in df.columns]
        
        missing_columns = []
        for col in expected_columns:
            if col not in df_columns_lower and col.capitalize() not in df.columns:
                missing_columns.append(col.upper())
        
        if missing_columns:
            result["warnings"].append(f"Missing common columns: {', '.join(missing_columns)}")
        
        # Check data types (using constants for consistency)
        numeric_columns_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        numeric_columns = [col.lower() for col in numeric_columns_constants]
        for col in df.columns:
            if col.lower() in numeric_columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    result["warnings"].append(f"Column {col} should be numeric")
        
    except FileNotFoundError:
        result["errors"].append("File not found")
    except Exception as e:
        result["errors"].append(f"Parquet validation error: {e}")
    
    return result

class ProviderFormatValidator:
    """Strategy pattern for provider-specific format validation."""
    
    def __init__(self):
        self.validators = {
            "barchart": BarchartFormatValidator(),
            "yahoo": YahooFormatValidator(),
            "ibkr": IbkrFormatValidator()
        }
    
    def validate(self, path: Path, provider: str) -> dict:
        """Validate provider-specific format requirements."""
        result = {"errors": [], "warnings": []}
        
        try:
            df = self._load_dataframe(path, result)
            if df is None:
                return result
            
            validator = self.validators.get(provider)
            if validator:
                validator.validate_format(df, result)
            else:
                result["warnings"].append(f"Unknown provider '{provider}' - skipping provider-specific validation")
                
        except Exception as e:
            result["errors"].append(f"Provider format validation error: {e}")
        
        return result
    
    def _load_dataframe(self, path: Path, result: dict):
        """Load DataFrame from file."""
        import pandas as pd
        
        if path.suffix.lower() == '.csv':
            return pd.read_csv(path)
        elif path.suffix.lower() == '.parquet':
            return pd.read_parquet(path)
        else:
            result["errors"].append(f"Unsupported file format for provider validation: {path.suffix}")
            return None

class BaseFormatValidator:
    """Base class for provider format validators."""
    
    def validate_format(self, df, result: dict):
        """Validate format for specific provider."""
        raise NotImplementedError
    
    def _normalize_columns(self, df, replacement: str = '') -> list:
        """Normalize column names for comparison."""
        return [col.lower().replace(' ', replacement) for col in df.columns]
    
    def _check_required_columns(self, df_columns: list, required_columns: list, 
                              column_constants: list, provider_name: str, result: dict):
        """Check for required columns and add warnings for missing ones."""
        for col_const, col_lower in zip(column_constants, required_columns):
            if col_lower not in df_columns:
                result["warnings"].append(f"{provider_name} format missing '{col_const}' column")
    
    def _check_date_columns(self, df_columns: list, date_variants: list, 
                          provider_name: str, result: dict):
        """Check for date/time columns."""
        has_date = any(col in df_columns for col in date_variants)
        if not has_date:
            result["warnings"].append(f"{provider_name} format missing date/time column")

class BarchartFormatValidator(BaseFormatValidator):
    """Validator for Barchart format."""
    
    def validate_format(self, df, result: dict):
        """Validate Barchart-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '')
        
        # Check date/time columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'time', 'datetime'], 
            "Barchart", 
            result
        )
        
        # Check OHLCV columns
        self._check_ohlcv_columns(df_columns_lower, result)
        
        # Check close/last column (Barchart uses 'Last')
        self._check_close_column(df_columns_lower, result)
    
    def _check_ohlcv_columns(self, df_columns: list, result: dict):
        """Check OHLCV columns for Barchart."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, "Barchart", result)
    
    def _check_close_column(self, df_columns: list, result: dict):
        """Check for close/last price column."""
        has_close = any(col in df_columns for col in [CLOSE_COLUMN.lower(), 'last'])
        if not has_close:
            result["warnings"].append("Barchart format missing close/last price column")

class YahooFormatValidator(BaseFormatValidator):
    """Validator for Yahoo Finance format."""
    
    def validate_format(self, df, result: dict):
        """Validate Yahoo Finance-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '_')
        
        # Check date columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'datetime'], 
            "Yahoo", 
            result
        )
        
        # Check OHLCV columns
        self._check_standard_ohlcv_columns(df_columns_lower, result, "Yahoo")
        
        # Check Yahoo-specific columns
        self._check_adj_close_column(df_columns_lower, result)
    
    def _check_standard_ohlcv_columns(self, df_columns: list, result: dict, provider: str):
        """Check standard OHLCV columns."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, provider, result)
    
    def _check_adj_close_column(self, df_columns: list, result: dict):
        """Check for Yahoo's Adj Close column."""
        has_adj_close = any(col in df_columns for col in ['adj_close', 'adjclose'])
        if not has_adj_close:
            result["warnings"].append(f"Yahoo format typically includes '{ADJ_CLOSE_COLUMN}' column")

class IbkrFormatValidator(BaseFormatValidator):
    """Validator for IBKR format."""
    
    def validate_format(self, df, result: dict):
        """Validate IBKR-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '')
        
        # Check date columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'datetime'], 
            "IBKR", 
            result
        )
        
        # Check OHLCV columns
        self._check_standard_ohlcv_columns(df_columns_lower, result, "IBKR")
        
        # Check IBKR-specific columns
        self._check_ibkr_specific_columns(df_columns_lower, result)
    
    def _check_standard_ohlcv_columns(self, df_columns: list, result: dict, provider: str):
        """Check standard OHLCV columns."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, provider, result)
    
    def _check_ibkr_specific_columns(self, df_columns: list, result: dict):
        """Check IBKR-specific columns."""
        if WAP_COLUMN.lower() not in df_columns:
            result["warnings"].append(f"IBKR format typically includes '{WAP_COLUMN}' (Weighted Average Price) column")
        if COUNT_COLUMN.lower() not in df_columns:
            result["warnings"].append(f"IBKR format typically includes '{COUNT_COLUMN}' (trade count) column")

def validate_provider_format(path: Path, provider: str) -> dict:
    """Validate provider-specific format requirements."""
    validator = ProviderFormatValidator()
    return validator.validate(path, provider)

def attempt_fixes(path: Path, errors: List[str]) -> bool:
    """Attempt to fix common validation issues."""
    fixed = False
    
    try:
        # Simple fix attempts for common issues
        for error in errors:
            if "File is empty" in error:
                # Cannot fix empty files
                continue
            elif "invalid OHLC relationships" in error:
                # Could attempt to fix OHLC data, but complex
                logger.info(f"Cannot auto-fix OHLC relationships in {path}")
                continue
            else:
                # For now, we don't implement automatic fixes
                # This is a placeholder for future enhancement
                logger.info(f"No automatic fix available for: {error}")
        
        # Return False as no actual fixes are implemented yet
        # In a real implementation, this would attempt actual file modifications
        
    except Exception as e:
        logger.exception(f"Error attempting fixes for {path}: {e}")
    
    return fixed

def display_results(results: List[dict], detailed: bool, output_format: str) -> None:
    """Display validation results."""
    
    if output_format == "table":
        display_table_results(results, detailed)
    elif output_format == "json":
        display_json_results(results)
    elif output_format == "csv":
        display_csv_results(results)

def display_table_results(results: List[dict], detailed: bool) -> None:
    """Display results in table format."""
    table = Table(title="Validation Results")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Size")
    table.add_column("Rows")
    table.add_column("Issues")
    
    for result in results:
        file_path = result["file"]
        status = "✓ Valid" if result["valid"] else "✗ Invalid"
        
        if result["fixed"]:
            status += " (Fixed)"
        
        size = format_file_size(file_path.stat().st_size)
        rows = str(result["metrics"].get("rows", "Unknown"))
        
        issues = len(result["errors"]) + len(result["warnings"])
        issues_str = str(issues) if issues > 0 else "-"
        
        table.add_row(
            file_path.name,
            status,
            size,
            rows,
            issues_str
        )
    
    console.print(table)
    
    # Show detailed issues if requested
    if detailed:
        show_detailed_issues(results)

def show_detailed_issues(results: List[dict]) -> None:
    """Show detailed validation issues."""
    for result in results:
        if result["errors"] or result["warnings"]:
            console.print(f"\n[bold]{result['file'].name}[/bold]")
            
            for error in result["errors"]:
                console.print(f"  [red]✗ Error: {error}[/red]")
            
            for warning in result["warnings"]:
                console.print(f"  [yellow]⚠ Warning: {warning}[/yellow]")

def display_json_results(results: List[dict]) -> None:
    """Display results in JSON format."""
    import json
    
    # Convert Path objects to strings for JSON serialization
    json_results = []
    for result in results:
        json_result = result.copy()
        json_result["file"] = str(result["file"])
        json_results.append(json_result)
    
    console.print(json.dumps(json_results, indent=2))

def display_csv_results(results: List[dict]) -> None:
    """Display results in CSV format."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["File", "Valid", "Errors", "Warnings", "Rows", "Columns"])
    
    # Data
    for result in results:
        writer.writerow([
            str(result["file"]),
            result["valid"],
            len(result["errors"]),
            len(result["warnings"]),
            result["metrics"].get("rows", ""),
            result["metrics"].get("columns", "")
        ])
    
    console.print(output.getvalue())

def show_validation_summary(results: List[dict]) -> None:
    """Show validation summary."""
    total_files = len(results)
    valid_files = sum(1 for r in results if r["valid"])
    fixed_files = sum(1 for r in results if r["fixed"])
    total_errors = sum(len(r["errors"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)
    
    console.print(f"\n[bold]Validation Summary[/bold]")
    console.print(f"Total files: {total_files}")
    console.print(f"Valid files: [green]{valid_files}[/green]")
    console.print(f"Invalid files: [red]{total_files - valid_files}[/red]")
    
    if fixed_files > 0:
        console.print(f"Fixed files: [blue]{fixed_files}[/blue]")
    
    if total_errors > 0:
        console.print(f"Total errors: [red]{total_errors}[/red]")
    
    if total_warnings > 0:
        console.print(f"Total warnings: [yellow]{total_warnings}[/yellow]")

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.1f} KB"
    else:
        return f"{size_bytes / BYTES_PER_MB:.1f} MB"