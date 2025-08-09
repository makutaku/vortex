"""
Enhanced CLI User Experience utilities for Vortex.

This module provides interactive features, command builders, better error messages,
progress indicators, and user-friendly CLI enhancements.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta

import click

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.tree import Tree
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from vortex.core.logging_integration import get_module_logger
from vortex.exceptions import VortexError, CLIError, MissingArgumentError

logger = get_module_logger()


class CliUX:
    """Enhanced CLI user experience utilities."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.quiet = False
        self.force_yes = False
    
    def set_quiet(self, quiet: bool = True):
        """Set quiet mode (suppress non-essential output)."""
        self.quiet = quiet
    
    def set_force_yes(self, force_yes: bool = True):
        """Set force yes mode (auto-confirm all prompts)."""
        self.force_yes = force_yes
    
    def print(self, message: str, style: Optional[str] = None, **kwargs):
        """Print message with optional Rich styling."""
        if self.quiet:
            return
        
        if self.console and style:
            self.console.print(message, style=style, **kwargs)
        elif self.console:
            self.console.print(message, **kwargs)
        else:
            print(message)
    
    def print_success(self, message: str):
        """Print success message."""
        self.print(f"✓ {message}", style="green")
    
    def print_error(self, message: str):
        """Print error message.""" 
        self.print(f"✗ {message}", style="red bold")
    
    def print_warning(self, message: str):
        """Print warning message."""
        self.print(f"⚠ {message}", style="yellow")
    
    def print_info(self, message: str):
        """Print info message."""
        self.print(f"ℹ {message}", style="blue")
    
    def print_panel(self, content: str, title: str = "", style: str = ""):
        """Print content in a panel."""
        if self.quiet:
            return
        
        if self.console:
            panel = Panel(content, title=title, border_style=style)
            self.console.print(panel)
        else:
            print(f"\n=== {title} ===")
            print(content)
            print("=" * (len(title) + 8))
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """Get user confirmation."""
        if self.force_yes:
            return True
        
        if self.console:
            return Confirm.ask(message, default=default)
        else:
            suffix = " [Y/n]" if default else " [y/N]"
            while True:
                response = input(f"{message}{suffix}: ").lower().strip()
                if not response:
                    return default  
                if response in ('y', 'yes'):
                    return True
                elif response in ('n', 'no'):
                    return False
                print("Please enter 'y' or 'n'")
    
    def prompt(self, message: str, default: Optional[str] = None, password: bool = False) -> str:
        """Get user input."""
        if self.console:
            return Prompt.ask(message, default=default, password=password)
        else:
            import getpass
            if password:
                return getpass.getpass(f"{message}: ")
            else:
                prompt_text = f"{message}"
                if default:
                    prompt_text += f" [{default}]"
                prompt_text += ": "
                response = input(prompt_text).strip()
                return response or default or ""
    
    def choice(self, message: str, choices: List[str], default: Optional[str] = None) -> str:
        """Get user choice from a list."""
        if len(choices) == 1:
            return choices[0]
        
        if self.console:
            # Create a rich choice display
            choice_text = Text()
            for i, choice in enumerate(choices, 1):
                if choice == default:
                    choice_text.append(f"{i}. {choice} (default)\n", style="green")
                else:
                    choice_text.append(f"{i}. {choice}\n")
            
            self.console.print(choice_text)
            
            while True:
                try:
                    response = IntPrompt.ask(
                        f"{message} (1-{len(choices)})",
                        default=choices.index(default) + 1 if default in choices else 1
                    )
                    if 1 <= response <= len(choices):
                        return choices[response - 1]
                    else:
                        self.print_error(f"Please enter a number between 1 and {len(choices)}")
                except (ValueError, KeyboardInterrupt):
                    self.print_error("Invalid input. Please enter a number.")
        else:
            print(f"\n{message}")
            for i, choice in enumerate(choices, 1):
                marker = " (default)" if choice == default else ""
                print(f"{i}. {choice}{marker}")
            
            while True:
                try:
                    response = input(f"Enter choice (1-{len(choices)}): ").strip()
                    if not response and default:
                        return default
                    
                    idx = int(response) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                    else:
                        print(f"Please enter a number between 1 and {len(choices)}")
                except (ValueError, KeyboardInterrupt):
                    print("Invalid input. Please enter a number.")
    
    def progress(self, description: str = "Processing..."):
        """Create a progress context manager."""
        return ProgressContext(self, description)
    
    def table(self, title: str = "") -> 'TableBuilder':
        """Create a table builder."""
        return TableBuilder(self, title)
    
    def tree(self, title: str) -> 'TreeBuilder':
        """Create a tree builder."""
        return TreeBuilder(self, title)


class ProgressContext:
    """Context manager for progress indicators."""
    
    def __init__(self, ux: CliUX, description: str):
        self.ux = ux
        self.description = description
        self.start_time = None
        self.progress = None
        self.task = None
    
    def __enter__(self):
        self.start_time = time.time()
        
        if self.ux.console and not self.ux.quiet:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.ux.console
            )
            self.progress.start()
            self.task = self.progress.add_task(self.description, total=100)
        elif not self.ux.quiet:
            print(f"{self.description}...")
        
        return self
    
    def update(self, completed: int, total: int = 100, description: str = None):
        """Update progress."""
        if self.progress and self.task:
            percentage = (completed / total) * 100 if total > 0 else 0
            self.progress.update(self.task, completed=percentage, description=description or self.description)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
        
        if exc_type is None:
            elapsed = time.time() - self.start_time
            if not self.ux.quiet:
                self.ux.print_success(f"Completed in {elapsed:.2f}s")
        else:
            if not self.ux.quiet:
                self.ux.print_error(f"Failed: {exc_val}")


class TableBuilder:
    """Builder for Rich tables."""
    
    def __init__(self, ux: CliUX, title: str):
        self.ux = ux
        self.title = title
        self.columns = []
        self.rows = []
    
    def add_column(self, name: str, style: str = "", justify: str = "left"):
        """Add a column to the table."""
        self.columns.append({"name": name, "style": style, "justify": justify})
        return self
    
    def add_row(self, *values):
        """Add a row to the table."""
        self.rows.append(values)
        return self
    
    def print(self):
        """Print the table."""
        if self.ux.quiet:
            return
        
        if self.ux.console:
            table = Table(title=self.title)
            for col in self.columns:
                table.add_column(col["name"], style=col["style"], justify=col["justify"])
            for row in self.rows:
                table.add_row(*[str(v) for v in row])
            self.ux.console.print(table)
        else:
            # Fallback text table
            if self.title:
                print(f"\n{self.title}")
                print("=" * len(self.title))
            
            if self.columns and self.rows:
                # Calculate column widths
                col_widths = []
                for i, col in enumerate(self.columns):
                    width = len(col["name"])
                    for row in self.rows:
                        if i < len(row):
                            width = max(width, len(str(row[i])))
                    col_widths.append(width)
                
                # Print header
                header_parts = []
                for i, col in enumerate(self.columns):
                    header_parts.append(col["name"].ljust(col_widths[i]))
                print(" | ".join(header_parts))
                print("-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))
                
                # Print rows
                for row in self.rows:
                    row_parts = []
                    for i, value in enumerate(row):
                        if i < len(col_widths):
                            row_parts.append(str(value).ljust(col_widths[i]))
                    print(" | ".join(row_parts))


class TreeBuilder:
    """Builder for Rich trees."""
    
    def __init__(self, ux: CliUX, title: str):
        self.ux = ux
        self.title = title
        self.items = []
    
    def add_item(self, text: str, children: List[str] = None):
        """Add an item to the tree."""
        self.items.append({"text": text, "children": children or []})
        return self
    
    def print(self):
        """Print the tree."""
        if self.ux.quiet:
            return
        
        if self.ux.console:
            tree = Tree(self.title)
            for item in self.items:
                node = tree.add(item["text"])
                for child in item["children"]:
                    node.add(child)
            self.ux.console.print(tree)
        else:
            # Fallback text tree
            print(f"\n{self.title}")
            for i, item in enumerate(self.items):
                is_last = i == len(self.items) - 1
                prefix = "└── " if is_last else "├── "
                print(f"{prefix}{item['text']}")
                
                for j, child in enumerate(item["children"]):
                    child_is_last = j == len(item["children"]) - 1
                    child_prefix = "    " if is_last else "│   "
                    child_prefix += "└── " if child_is_last else "├── "
                    print(f"{child_prefix}{child}")


class CommandWizard:
    """Interactive command builder wizard."""
    
    def __init__(self, ux: CliUX):
        self.ux = ux
        self.config = {}
    
    def run_download_wizard(self) -> Dict[str, Any]:
        """Interactive download command builder."""
        self.ux.print_panel(
            "📥 **Download Wizard**\n\n"
            "This wizard will help you build a download command step by step.\n"
            "You can exit at any time with Ctrl+C.",
            title="Vortex Download Wizard",
            style="blue"
        )
        
        config = {}
        
        # Provider selection
        providers = ["barchart", "yahoo", "ibkr"]
        provider_descriptions = {
            "barchart": "Professional futures and forex data (requires credentials)",
            "yahoo": "Free stock and ETF data (no credentials required)",
            "ibkr": "Interactive Brokers data (requires TWS/Gateway)"
        }
        
        self.ux.print("\n🔌 **Choose Data Provider**")
        for provider in providers:
            self.ux.print(f"  • {provider}: {provider_descriptions[provider]}")
        
        config["provider"] = self.ux.choice("Select provider", providers, "yahoo")
        
        # Symbols selection
        self.ux.print(f"\n📊 **Choose Symbols for {config['provider'].upper()}**")
        
        symbol_method = self.ux.choice(
            "How do you want to specify symbols?",
            ["Enter symbols manually", "Use symbols file", "Use default assets"],
            "Enter symbols manually"
        )
        
        if symbol_method == "Enter symbols manually":
            symbols_input = self.ux.prompt("Enter symbols (comma-separated)", "AAPL,GOOGL,MSFT")
            config["symbols"] = [s.strip() for s in symbols_input.split(",")]
        
        elif symbol_method == "Use symbols file":
            symbols_file = self.ux.prompt("Enter path to symbols file", "symbols.txt")
            config["symbols_file"] = symbols_file
        
        else:  # Use default assets
            self.ux.print("✓ Will use default assets for the provider")
            config["use_defaults"] = True
        
        # Date range
        self.ux.print("\n📅 **Choose Date Range**")
        date_method = self.ux.choice(
            "Date range selection",
            ["Last 30 days (default)", "Last 90 days", "This year", "Custom range"],
            "Last 30 days (default)"
        )
        
        if date_method == "Last 90 days":
            config["start_date"] = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        elif date_method == "This year":
            config["start_date"] = f"{datetime.now().year}-01-01"
        elif date_method == "Custom range":
            config["start_date"] = self.ux.prompt("Start date (YYYY-MM-DD)", "2024-01-01")
            config["end_date"] = self.ux.prompt("End date (YYYY-MM-DD)", "2024-12-31")
        
        # Output options
        self.ux.print("\n💾 **Output Options**")
        config["backup"] = self.ux.confirm("Create Parquet backup files?", False)
        config["force"] = self.ux.confirm("Force re-download existing data?", False)
        
        # Show summary
        self.ux.print("\n📋 **Command Summary**")
        command_parts = ["vortex download"]
        command_parts.append(f"--provider {config['provider']}")
        
        if "symbols" in config:
            for symbol in config["symbols"]:
                command_parts.append(f"--symbol {symbol}")
        elif "symbols_file" in config:
            command_parts.append(f"--symbols-file {config['symbols_file']}")
        
        if "start_date" in config:
            command_parts.append(f"--start-date {config['start_date']}")
        if "end_date" in config:
            command_parts.append(f"--end-date {config['end_date']}")
        
        if config.get("backup"):
            command_parts.append("--backup")
        if config.get("force"):
            command_parts.append("--force")
        
        command = " ".join(command_parts)
        
        if self.ux.console:
            syntax = Syntax(command, "bash", theme="github-dark", line_numbers=False)
            self.ux.console.print(Panel(syntax, title="Generated Command"))
        else:
            self.ux.print(f"\nGenerated command:\n{command}")
        
        if self.ux.confirm("\nExecute this command now?", True):
            config["execute"] = True
        
        return config
    
    def run_config_wizard(self) -> Dict[str, Any]:
        """Interactive configuration wizard."""
        self.ux.print_panel(
            "⚙️ **Configuration Wizard**\n\n"
            "This wizard will help you set up Vortex configuration.\n"
            "You can configure providers, output settings, and more.",
            title="Vortex Configuration Wizard",
            style="green"
        )
        
        config = {}
        
        # Provider configuration
        self.ux.print("\n🔧 **Provider Configuration**")
        provider = self.ux.choice(
            "Which provider would you like to configure?",
            ["barchart", "yahoo", "ibkr", "skip"],
            "barchart"
        )
        
        if provider != "skip":
            config["provider"] = provider
            
            if provider == "barchart":
                self.ux.print("\n📊 **Barchart Configuration**")
                self.ux.print("You'll need a Barchart.com account with API access.")
                config["username"] = self.ux.prompt("Barchart username (email)")
                config["password"] = self.ux.prompt("Barchart password", password=True)
                config["daily_limit"] = self.ux.prompt("Daily download limit", "150")
            
            elif provider == "ibkr":
                self.ux.print("\n🏦 **Interactive Brokers Configuration**")
                self.ux.print("Make sure TWS or IB Gateway is running with API enabled.")
                config["host"] = self.ux.prompt("Host", "localhost")
                config["port"] = self.ux.prompt("Port", "7497")
                config["client_id"] = self.ux.prompt("Client ID", "1")
            
            else:  # yahoo
                self.ux.print("✓ Yahoo Finance requires no configuration!")
        
        # General settings
        self.ux.print("\n🎛️ **General Settings**")
        if self.ux.confirm("Configure general settings?", False):
            config["output_dir"] = self.ux.prompt("Output directory", "./data")
            config["log_level"] = self.ux.choice(
                "Log level",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                "INFO"
            )
            config["backup_enabled"] = self.ux.confirm("Enable automatic Parquet backups?", False)
        
        return config


# Global UX instance
ux = CliUX()


def get_ux() -> CliUX:
    """Get the global UX instance."""
    return ux


def enhanced_error_handler(func: Callable) -> Callable:
    """Decorator for enhanced error handling in CLI commands."""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VortexError as e:
            ux.print_error(f"{type(e).__name__}: {e}")
            if hasattr(e, 'help_text') and e.help_text:
                ux.print_info(f"💡 {e.help_text}")
            logger.error(f"CLI command failed: {e}", command=func.__name__)
            raise click.Abort()
        except KeyboardInterrupt:
            ux.print_warning("\n⚠️ Operation cancelled by user")
            raise click.Abort()
        except Exception as e:
            ux.print_error(f"Unexpected error: {e}")
            ux.print_info("💡 This might be a bug. Please report it at: https://github.com/makutaku/vortex/issues")
            logger.error(f"Unexpected CLI error: {e}", command=func.__name__, exc_info=True)
            raise click.Abort()
    
    return wrapper


def validate_symbols(symbols: List[str]) -> List[str]:
    """Validate and clean symbol list."""
    cleaned = []
    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        
        # Basic symbol validation
        if not symbol.replace("-", "").replace(".", "").replace("=", "").isalnum():
            ux.print_warning(f"⚠️ Symbol '{symbol}' may not be valid")
        
        cleaned.append(symbol)
    
    return cleaned


def suggest_command_fixes(command: str, available_commands: List[str]) -> List[str]:
    """Suggest similar commands for typos."""
    suggestions = []
    command_lower = command.lower()
    
    for cmd in available_commands:
        # Simple similarity check
        if command_lower in cmd.lower() or cmd.lower() in command_lower:
            suggestions.append(cmd)
        elif len(command) > 2:
            # Check for single character differences
            if abs(len(command) - len(cmd)) <= 2:
                diff_count = sum(1 for a, b in zip(command_lower, cmd.lower()) if a != b)
                if diff_count <= 2:
                    suggestions.append(cmd)
    
    return suggestions[:3]  # Return top 3 suggestions