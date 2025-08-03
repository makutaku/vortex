"""
Enhanced help system for Vortex CLI.

This module provides contextual help, examples, tutorials, and interactive guidance
to improve the user experience and reduce learning curve.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.tree import Tree
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .ux import get_ux


class HelpSystem:
    """Enhanced help system with contextual guidance."""
    
    def __init__(self):
        self.ux = get_ux()
        self.examples = self._load_examples()
        self.tutorials = self._load_tutorials()
        self.tips = self._load_tips()
    
    def _load_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """Load command examples."""
        return {
            "download": [
                {
                    "title": "Download Apple stock data for last 30 days",
                    "command": "vortex download --provider yahoo --symbol AAPL",
                    "description": "Downloads daily price data for Apple stock using Yahoo Finance"
                },
                {
                    "title": "Download multiple symbols with date range",
                    "command": "vortex download -p yahoo -s AAPL -s GOOGL -s MSFT --start-date 2024-01-01",
                    "description": "Downloads data for multiple stocks from a specific start date"
                },
                {
                    "title": "Download from Barchart with backup",
                    "command": "vortex download -p barchart -s GCM25 --backup --start-date 2024-01-01",
                    "description": "Downloads futures data with Parquet backup files"
                },
                {
                    "title": "Download from symbols file",
                    "command": "vortex download -p yahoo --symbols-file my-symbols.txt --yes",
                    "description": "Downloads symbols listed in a text file (one per line)"
                },
                {
                    "title": "Use custom assets configuration",
                    "command": "vortex download -p barchart --assets ./my-assets.json",
                    "description": "Downloads using custom instrument definitions"
                }
            ],
            "config": [
                {
                    "title": "Set up Barchart credentials",
                    "command": "vortex config --provider barchart --set-credentials",
                    "description": "Interactive setup for Barchart.com username and password"
                },
                {
                    "title": "View current configuration",
                    "command": "vortex config --show",
                    "description": "Display all current configuration settings and provider status"
                },
                {
                    "title": "Export configuration to file",
                    "command": "vortex config --export config-backup.toml",
                    "description": "Save current configuration to a TOML file"
                },
                {
                    "title": "Import configuration from file",
                    "command": "vortex config --import config-backup.toml",
                    "description": "Load configuration from a previously exported file"
                },
                {
                    "title": "Reset to defaults",
                    "command": "vortex config --reset",
                    "description": "Reset all configuration to default values"
                }
            ],
            "providers": [
                {
                    "title": "List available providers",
                    "command": "vortex providers --list",
                    "description": "Show all supported data providers and their status"
                },
                {
                    "title": "Test provider connection",
                    "command": "vortex providers --test barchart",
                    "description": "Test connection and credentials for Barchart provider"
                },
                {
                    "title": "Get provider information",
                    "command": "vortex providers --info yahoo",
                    "description": "Display detailed information about Yahoo Finance provider"
                }
            ],
            "validate": [
                {
                    "title": "Validate downloaded data",
                    "command": "vortex validate --path ./data",
                    "description": "Check integrity and completeness of data files"
                },
                {
                    "title": "Validate specific file",
                    "command": "vortex validate --path ./data/AAPL.csv --provider yahoo",
                    "description": "Validate a specific data file against provider schema"
                }
            ]
        }
    
    def _load_tutorials(self) -> Dict[str, str]:
        """Load tutorial content."""
        return {
            "getting_started": """
# Getting Started with Vortex

## 1. Installation

### Using uv (Recommended - Fast!)
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Vortex
uv pip install -e .
```

### Using pip (Traditional)
```bash
pip install -e .
```

## 2. Quick Setup

### For Yahoo Finance (Free, No Setup Required)
```bash
# Yahoo Finance works immediately, no configuration needed
vortex download --provider yahoo --symbol AAPL
```

### For Barchart (Professional Data)
```bash
# Set up your Barchart.com credentials
vortex config --provider barchart --set-credentials

# Test the connection
vortex providers --test barchart

# Download data
vortex download --provider barchart --symbol GC
```

### For Interactive Brokers
```bash
# Configure TWS/Gateway connection
vortex config --provider ibkr --set-credentials

# Make sure TWS or IB Gateway is running
# Download data
vortex download --provider ibkr --symbol AAPL
```

## 3. Your First Download

```bash
# Download Apple stock data for the last 30 days
vortex download --provider yahoo --symbol AAPL

# Check the results
ls -la data/
```

## 4. Next Steps

- Use `vortex config --show` to see your current setup
- Try `vortex download --help` for more options
- Use `vortex providers --list` to see all available providers
""",
            
            "advanced_usage": """
# Advanced Vortex Usage

## Bulk Downloads

### Using Symbols Files
Create a file with one symbol per line:
```
# symbols.txt
AAPL
GOOGL
MSFT
TSLA
```

Then download:
```bash
vortex download --provider yahoo --symbols-file symbols.txt
```

### Using Custom Assets
Create a custom assets configuration:
```json
{
  "stocks": {
    "AAPL": {
      "code": "AAPL",
      "asset_class": "stock",
      "start_date": "2020-01-01"
    }
  }
}
```

Use it:
```bash
vortex download --provider yahoo --assets my-assets.json
```

## Date Ranges and Scheduling

### Specific Date Ranges
```bash
# Download specific date range
vortex download -p yahoo -s AAPL --start-date 2024-01-01 --end-date 2024-12-31

# Download year-to-date
vortex download -p yahoo -s AAPL --start-date 2024-01-01
```

### Automation with Cron
```bash
# Daily download at 6 PM (add to crontab)
0 18 * * * /path/to/vortex download -p yahoo -s AAPL --yes
```

## Data Management

### Backup and Recovery
```bash
# Enable Parquet backups
vortex download -p yahoo -s AAPL --backup

# Force re-download
vortex download -p yahoo -s AAPL --force
```

### Validation
```bash
# Validate all data
vortex validate --path ./data

# Validate specific provider data
vortex validate --path ./data --provider yahoo
```

## Configuration Management

### Multiple Environments
```bash
# Development config
vortex --config dev-config.toml download -p yahoo -s AAPL

# Production config
vortex --config prod-config.toml download -p barchart -s GC
```

### Environment Variables
```bash
export VORTEX_BARCHART_USERNAME="your-email@example.com"
export VORTEX_BARCHART_PASSWORD="your-password"
export VORTEX_OUTPUT_DIR="/data/financial"

vortex download -p barchart -s GC
```
""",
            
            "troubleshooting": """
# Troubleshooting Guide

## Common Issues

### 1. Authentication Errors

**Barchart Authentication Failed**
```
Error: Authentication failed for Barchart provider
```

**Solutions:**
- Check your username and password: `vortex config --provider barchart --set-credentials`
- Verify your account has API access
- Check for account lockout or suspension

**Interactive Brokers Connection Failed**
```
Error: Cannot connect to TWS/Gateway
```

**Solutions:**
- Ensure TWS or IB Gateway is running
- Check the host and port: `vortex config --provider ibkr --set-credentials`
- Verify API is enabled in TWS settings
- Check firewall settings

### 2. Data Issues

**No Data Retrieved**
```
Warning: No data found for symbol AAPL
```

**Solutions:**
- Verify the symbol is correct and exists
- Check the date range (weekends/holidays have no data)
- Try a different provider
- Use `vortex providers --test [provider]` to test connection

**File Permission Errors**
```
Error: Cannot write to output directory
```

**Solutions:**
- Check directory permissions: `ls -la data/`
- Create the directory: `mkdir -p data`
- Use a different output directory: `--output-dir /tmp/vortex-data`

### 3. Configuration Issues

**Configuration File Not Found**
```
Error: Configuration file not found
```

**Solutions:**
- Use `vortex config --show` to see current config location
- Create default config: `vortex config --provider yahoo --set-credentials`
- Use custom config: `vortex --config my-config.toml`

### 4. Performance Issues

**Slow Downloads**
```
Download taking very long...
```

**Solutions:**
- Reduce date range or number of symbols
- Use `--chunk-size` to adjust batch size
- Check network connection
- Try different provider

## Getting Help

### Verbose Output
```bash
# Enable debug logging
vortex -vv download -p yahoo -s AAPL

# Check configuration
vortex config --show
```

### Log Files
```bash
# Check log files (if file logging enabled)
tail -f logs/vortex.log
```

### Health Checks
```bash
# Test system health
vortex providers --test-all
```

### Report Issues
If you encounter bugs:
1. Enable verbose logging: `vortex -vv [command]`
2. Check the logs for error details
3. Report at: https://github.com/makutaku/vortex/issues
"""
        }
    
    def _load_tips(self) -> List[Dict[str, str]]:
        """Load helpful tips."""
        return [
            {
                "title": "Speed up installations",
                "tip": "Use `uv` instead of `pip` for 10-100x faster package installation!"
            },
            {
                "title": "Backup your data", 
                "tip": "Use `--backup` flag to create Parquet backups of your CSV data"
            },
            {
                "title": "Test before bulk downloads",
                "tip": "Always test with a single symbol before downloading hundreds of symbols"
            },
            {
                "title": "Use configuration files",
                "tip": "Export your working config with `vortex config --export` for easy sharing"
            },
            {
                "title": "Automate with cron",
                "tip": "Use `--yes` flag in scripts to skip confirmation prompts"
            },
            {
                "title": "Validate your data",
                "tip": "Run `vortex validate` regularly to check data integrity"
            },
            {
                "title": "Monitor provider limits",
                "tip": "Barchart has daily download limits - check with `vortex config --show`"
            },
            {
                "title": "Use dry run for testing",
                "tip": "Use `--dry-run` to test commands without making changes"
            }
        ]
    
    def show_examples(self, command: Optional[str] = None):
        """Show examples for a command or all commands."""
        if command and command in self.examples:
            self._show_command_examples(command)
        else:
            self._show_all_examples()
    
    def _show_command_examples(self, command: str):
        """Show examples for a specific command."""
        examples = self.examples.get(command, [])
        if not examples:
            self.ux.print_warning(f"No examples available for '{command}'")
            return
        
        title = f"Examples for 'vortex {command}'"
        self.ux.print_panel("", title=title, style="blue")
        
        for i, example in enumerate(examples, 1):
            self.ux.print(f"\n**{i}. {example['title']}**", style="bold cyan")
            self.ux.print(f"   `{example['command']}`", style="green")
            self.ux.print(f"   {example['description']}", style="dim")
    
    def _show_all_examples(self):
        """Show examples for all commands."""
        self.ux.print_panel(
            "💡 **Command Examples**\n\n"
            "Here are some common usage examples to get you started:",
            title="Vortex Examples",
            style="blue"
        )
        
        for command, examples in self.examples.items():
            self.ux.print(f"\n## {command.upper()}", style="bold magenta")
            
            for example in examples[:2]:  # Show first 2 examples for each command
                self.ux.print(f"  • {example['title']}")
                self.ux.print(f"    `{example['command']}`", style="green")
        
        self.ux.print(f"\nUse 'vortex help examples COMMAND' for more examples of a specific command.")
    
    def show_tutorial(self, topic: str):
        """Show tutorial content."""
        if topic not in self.tutorials:
            available = ", ".join(self.tutorials.keys())
            self.ux.print_error(f"Tutorial '{topic}' not found. Available: {available}")
            return
        
        content = self.tutorials[topic]
        
        if self.ux.console:
            markdown = Markdown(content)
            self.ux.console.print(markdown)
        else:
            # Fallback: strip markdown and print plain text
            import re
            plain_text = re.sub(r'[*_`#]', '', content)
            plain_text = re.sub(r'```[a-z]*\n', '', plain_text)
            plain_text = re.sub(r'```', '', plain_text)
            print(plain_text)
    
    def show_tips(self, count: int = 3):
        """Show helpful tips."""
        import random
        
        selected_tips = random.sample(self.tips, min(count, len(self.tips)))
        
        self.ux.print_panel(
            "💡 **Helpful Tips**\n\n"
            "Here are some tips to help you use Vortex more effectively:",
            title="Vortex Tips",
            style="yellow"
        )
        
        for i, tip in enumerate(selected_tips, 1):
            self.ux.print(f"\n**{i}. {tip['title']}**", style="bold cyan")
            self.ux.print(f"   {tip['tip']}", style="dim")
    
    def show_command_tree(self):
        """Show command structure as a tree."""
        tree_builder = self.ux.tree("Vortex Commands")
        
        tree_builder.add_item(
            "📥 download - Download financial data",
            [
                "--provider (barchart|yahoo|ibkr) - Data provider",
                "--symbol SYMBOL - Symbol to download",
                "--symbols-file FILE - File with symbols", 
                "--start-date DATE - Start date (YYYY-MM-DD)",
                "--end-date DATE - End date (YYYY-MM-DD)",
                "--backup - Create Parquet backups",
                "--force - Force re-download"
            ]
        )
        
        tree_builder.add_item(
            "⚙️ config - Manage configuration",
            [
                "--show - Show current configuration",
                "--provider PROVIDER - Select provider to configure", 
                "--set-credentials - Set provider credentials",
                "--export FILE - Export config to file",
                "--import FILE - Import config from file",
                "--reset - Reset to defaults"
            ]
        )
        
        tree_builder.add_item(
            "🔌 providers - Manage data providers",
            [
                "--list - List all providers",
                "--test PROVIDER - Test provider connection",
                "--info PROVIDER - Show provider information"
            ]
        )
        
        tree_builder.add_item(
            "✅ validate - Validate data files",
            [
                "--path PATH - Path to validate",
                "--provider PROVIDER - Validate against provider schema"
            ]
        )
        
        tree_builder.print()
    
    def show_quick_start(self):
        """Show quick start guide."""
        self.ux.print_panel(
            "🚀 **Quick Start Guide**\n\n"
            "Get up and running with Vortex in 3 easy steps:",
            title="Vortex Quick Start",
            style="green"
        )
        
        steps = [
            {
                "title": "1. Install Vortex",
                "commands": [
                    "curl -LsSf https://astral.sh/uv/install.sh | sh",
                    "uv pip install -e ."
                ],
                "description": "Install using uv for best performance"
            },
            {
                "title": "2. Test with Yahoo Finance (No Setup Required)",
                "commands": [
                    "vortex download --provider yahoo --symbol AAPL"
                ],
                "description": "Download Apple stock data to test the installation"
            },
            {
                "title": "3. Configure Your Preferred Provider",
                "commands": [
                    "vortex config --provider barchart --set-credentials",
                    "vortex providers --test barchart"
                ],
                "description": "Set up Barchart for professional data (optional)"
            }
        ]
        
        for step in steps:
            self.ux.print(f"\n**{step['title']}**", style="bold blue")
            self.ux.print(f"{step['description']}", style="dim")
            for cmd in step['commands']:
                self.ux.print(f"  $ {cmd}", style="green")
        
        self.ux.print(f"\n🎉 **You're ready to go!**", style="bold green")
        self.ux.print("Use 'vortex --help' to see all available commands.")


# Global help system instance
help_system = HelpSystem()


def get_help_system() -> HelpSystem:
    """Get the global help system instance."""
    return help_system


@click.group()
def help():
    """Enhanced help and guidance system."""
    pass


@help.command()
@click.argument("command", required=False)
def examples(command: Optional[str]):
    """Show usage examples for commands."""
    help_system.show_examples(command)


@help.command()
@click.argument("topic", type=click.Choice(["getting_started", "advanced_usage", "troubleshooting"]))
def tutorial(topic: str):
    """Show detailed tutorials."""
    help_system.show_tutorial(topic)


@help.command()
@click.option("--count", "-n", default=3, help="Number of tips to show")
def tips(count: int):
    """Show helpful tips and best practices."""
    help_system.show_tips(count)


@help.command()
def commands():
    """Show command structure and options."""
    help_system.show_command_tree()


@help.command()
def quickstart():
    """Show quick start guide."""
    help_system.show_quick_start()