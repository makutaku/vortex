"""Data validation command."""

import logging
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from vortex.infrastructure.providers.barchart.column_mapping import (
    BarchartColumnMapping,
)
from vortex.infrastructure.providers.ibkr.column_mapping import IbkrColumnMapping

# Import provider-specific constants from their respective providers
from vortex.infrastructure.providers.yahoo.column_mapping import YahooColumnMapping
from vortex.models.columns import (
    CLOSE_COLUMN,
    DATETIME_COLUMN_NAME,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    VOLUME_COLUMN,
)

from .validation_display import display_results, show_validation_summary
from .validation_fixes import attempt_fixes
from .validation_formats import ProviderFormatValidator

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
    "--path",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory or file to validate",
)
@click.option(
    "--provider",
    type=str,
    help="Expected data provider format (dynamic based on available plugins)",
)
@click.option("--fix", is_flag=True, help="Attempt to fix validation issues")
@click.option("--detailed", is_flag=True, help="Show detailed validation results")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format for results",
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
        if path.suffix.lower() in [".csv", ".parquet"]:
            files.append(path)
    else:
        # Search directory for data files
        for pattern in ["*.csv", "*.parquet"]:
            files.extend(path.rglob(pattern))

    return sorted(files)


def run_validation(files: List[Path], provider: Optional[str], fix: bool) -> List[dict]:
    """Run validation on all files."""
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating files...", total=len(files))

        for file_path in files:
            result = validate_single_file(file_path, provider, fix)
            results.append(result)

            status = "✓" if result["valid"] else "✗"
            progress.update(task, advance=1, description=f"{status} {file_path.name}")

    return results


def validate_single_file(path: Path, provider: Optional[str], fix: bool) -> dict:
    """Validate a single data file."""
    result = {
        "file": path,
        "valid": True,
        "errors": [],
        "warnings": [],
        "metrics": {},
        "fixed": False,
    }

    try:
        # Perform comprehensive file validation

        # Basic file checks
        if path.stat().st_size == 0:
            result["errors"].append("File is empty")
            result["valid"] = False

        # Format-specific validation
        if path.suffix.lower() == ".csv":
            csv_result = validate_csv_file(path, provider)
            result["errors"].extend(csv_result.get("errors", []))
            result["warnings"].extend(csv_result.get("warnings", []))
            result["metrics"].update(csv_result.get("metrics", {}))
            if csv_result.get("errors"):
                result["valid"] = False
        elif path.suffix.lower() == ".parquet":
            parquet_result = validate_parquet_file(path, provider)
            result["errors"].extend(parquet_result.get("errors", []))
            result["warnings"].extend(parquet_result.get("warnings", []))
            result["metrics"].update(parquet_result.get("metrics", {}))
            if parquet_result.get("errors"):
                result["valid"] = False

        # Provider-specific validation
        if provider:
            validator = ProviderFormatValidator()
            provider_result = validator.validate(path, provider)
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
        expected_columns_constants = [
            DATETIME_COLUMN_NAME,
            OPEN_COLUMN,
            HIGH_COLUMN,
            LOW_COLUMN,
            CLOSE_COLUMN,
        ]
        expected_columns = [col.lower() for col in expected_columns_constants]
        df_columns_lower = [col.lower() for col in df.columns]

        missing_columns = []
        for col in expected_columns:
            if col not in df_columns_lower and col.capitalize() not in df.columns:
                missing_columns.append(col.upper())

        if missing_columns:
            result["warnings"].append(
                f"Missing common columns: {', '.join(missing_columns)}"
            )

        # Check for empty rows
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            result["warnings"].append(f"Found {empty_rows} completely empty rows")

        # Validate OHLC relationships if columns exist
        ohlc_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        ohlc_lower = [col.lower() for col in ohlc_constants]
        if all(
            col in df_columns_lower or col.capitalize() in df.columns
            for col in ohlc_lower
        ):
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
                        o = float(row[ohlc_cols["open"]])
                        h = float(row[ohlc_cols["high"]])
                        line = float(row[ohlc_cols["low"]])
                        c = float(row[ohlc_cols["close"]])
                        if not (line <= o <= h and line <= c <= h):
                            invalid_ohlc += 1
                    except (ValueError, TypeError):
                        # Skip non-numeric values
                        continue

                if invalid_ohlc > 0:
                    result["errors"].append(
                        f"Found {invalid_ohlc} rows with invalid OHLC relationships"
                    )

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
        expected_columns_constants = [
            DATETIME_COLUMN_NAME,
            OPEN_COLUMN,
            HIGH_COLUMN,
            LOW_COLUMN,
            CLOSE_COLUMN,
        ]
        expected_columns = [col.lower() for col in expected_columns_constants]
        df_columns_lower = [col.lower() for col in df.columns]

        missing_columns = []
        for col in expected_columns:
            if col not in df_columns_lower and col.capitalize() not in df.columns:
                missing_columns.append(col.upper())

        if missing_columns:
            result["warnings"].append(
                f"Missing common columns: {', '.join(missing_columns)}"
            )

        # Check data types (using constants for consistency)
        numeric_columns_constants = [
            OPEN_COLUMN,
            HIGH_COLUMN,
            LOW_COLUMN,
            CLOSE_COLUMN,
            VOLUME_COLUMN,
        ]
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
