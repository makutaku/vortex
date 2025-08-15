"""Display functionality for validation results."""

import json
import csv
import io
from typing import List
from rich.console import Console
from rich.table import Table

from vortex.constants import BYTES_PER_KB, BYTES_PER_MB

console = Console()


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
    # Convert Path objects to strings for JSON serialization
    json_results = []
    for result in results:
        json_result = result.copy()
        json_result["file"] = str(result["file"])
        json_results.append(json_result)
    
    console.print(json.dumps(json_results, indent=2))


def display_csv_results(results: List[dict]) -> None:
    """Display results in CSV format."""
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