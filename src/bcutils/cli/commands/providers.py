"""Provider management command."""

import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config_manager import ConfigManager

console = Console()
logger = logging.getLogger(__name__)

@click.command()
@click.option(
    "--list", "list_providers",
    is_flag=True,
    help="List all available providers"
)
@click.option(
    "--test",
    type=click.Choice(["barchart", "yahoo", "ibkr", "all"], case_sensitive=False),
    help="Test provider connectivity"
)
@click.option(
    "--info",
    type=click.Choice(["barchart", "yahoo", "ibkr"], case_sensitive=False),
    help="Show detailed provider information"
)
@click.pass_context
def providers(
    ctx: click.Context,
    list_providers: bool,
    test: Optional[str],
    info: Optional[str],
) -> None:
    """Manage data providers.
    
    Examples:
        bcutils providers --list
        bcutils providers --test barchart
        bcutils providers --test all
        bcutils providers --info barchart
        
    Quick Setup:
        # Install with uv (10x faster)
        uv pip install -e .
        
        # Configure provider
        bcutils config --provider barchart --set-credentials
    """
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    
    if list_providers or not any([test, info]):
        show_providers_list(config_manager)
        return
    
    if test:
        test_providers(config_manager, test)
        return
    
    if info:
        show_provider_info(config_manager, info)

def show_providers_list(config_manager: ConfigManager) -> None:
    """Display list of available providers."""
    table = Table(title="Available Data Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Data Types", style="blue")
    table.add_column("Authentication")
    table.add_column("Rate Limits")
    
    providers_info = {
        "barchart": {
            "status": "✓ Available",
            "data_types": "Futures, Stocks, Options",
            "auth": "Username/Password",
            "limits": "150/day"
        },
        "yahoo": {
            "status": "✓ Available",
            "data_types": "Stocks, ETFs, Indices",
            "auth": "None required",
            "limits": "Unlimited"
        },
        "ibkr": {
            "status": "✓ Available",
            "data_types": "All asset classes",
            "auth": "TWS/Gateway",
            "limits": "Real-time connection"
        }
    }
    
    config = config_manager.load_config()
    
    for provider, info in providers_info.items():
        provider_config = config.get("providers", {}).get(provider, {})
        
        # Check if configured
        if provider == "barchart":
            configured = bool(provider_config.get("username"))
        elif provider == "yahoo":
            configured = True  # No config needed
        elif provider == "ibkr":
            configured = bool(provider_config.get("host"))
        else:
            configured = False
        
        status = info["status"] if configured else "⚠ Not configured"
        
        table.add_row(
            provider.upper(),
            status,
            info["data_types"],
            info["auth"],
            info["limits"]
        )
    
    console.print(table)
    console.print("\n[dim]Use 'bcutils config --provider PROVIDER --set-credentials' to configure[/dim]")

def test_providers(config_manager: ConfigManager, provider: str) -> None:
    """Test provider connectivity."""
    providers_to_test = ["barchart", "yahoo", "ibkr"] if provider == "all" else [provider]
    
    console.print(f"[bold]Testing provider connectivity...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for prov in providers_to_test:
            task = progress.add_task(f"Testing {prov.upper()}...", total=None)
            
            try:
                result = test_single_provider(config_manager, prov)
                
                if result["success"]:
                    progress.update(task, description=f"✓ {prov.upper()} - {result['message']}")
                else:
                    progress.update(task, description=f"✗ {prov.upper()} - {result['message']}")
                    
            except Exception as e:
                progress.update(task, description=f"✗ {prov.upper()} - Error: {e}")

def test_single_provider(config_manager: ConfigManager, provider: str) -> dict:
    """Test connectivity to a single provider."""
    provider_config = config_manager.get_provider_config(provider)
    
    if provider == "barchart":
        if not provider_config.get("username") or not provider_config.get("password"):
            return {"success": False, "message": "No credentials configured"}
        
        # TODO: Implement actual Barchart connectivity test
        # For now, just check if credentials exist
        return {"success": True, "message": "Credentials configured"}
        
    elif provider == "yahoo":
        # Test Yahoo Finance connectivity by fetching a small amount of data
        try:
            from datetime import datetime, timedelta
            from ...data_providers.yf_data_provider import YahooDataProvider
            
            # Test with a reliable ticker (Apple) for the last 5 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            df = YahooDataProvider.fetch_historical_data_for_symbol(
                "AAPL", "1d", start_date, end_date
            )
            
            if df is not None and not df.empty:
                return {"success": True, "message": f"Service available - fetched {len(df)} data points"}
            else:
                return {"success": False, "message": "Service returned empty data"}
                
        except ImportError:
            return {"success": False, "message": "yfinance package not installed"}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)[:50]}..."}
        
    elif provider == "ibkr":
        host = provider_config.get("host", "localhost")
        port = provider_config.get("port", 7497)
        
        # TODO: Implement actual IBKR connectivity test
        # For now, just check if configuration exists
        if not host:
            return {"success": False, "message": "No host configured"}
        
        return {"success": True, "message": f"Configuration ready for {host}:{port}"}
    
    return {"success": False, "message": "Unknown provider"}

def show_provider_info(config_manager: ConfigManager, provider: str) -> None:
    """Show detailed information about a provider."""
    console.print(f"[bold]{provider.upper()} Provider Information[/bold]")
    
    if provider == "barchart":
        show_barchart_info()
    elif provider == "yahoo":
        show_yahoo_info()
    elif provider == "ibkr":
        show_ibkr_info()

def show_barchart_info() -> None:
    """Show Barchart provider information."""
    info = Table()
    info.add_column("Attribute", style="cyan")
    info.add_column("Details", style="green")
    
    info.add_row("Description", "Professional futures and options data")
    info.add_row("Website", "https://www.barchart.com")
    info.add_row("Data Coverage", "Futures, stocks, options, forex")
    info.add_row("Historical Data", "Up to 20+ years depending on contract")
    info.add_row("Rate Limits", "150 downloads per day")
    info.add_row("Authentication", "Username and password required")
    info.add_row("Cost", "Subscription required")
    info.add_row("Data Format", "CSV")
    info.add_row("Update Frequency", "End-of-day")
    
    console.print(info)
    
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Create account at barchart.com")
    console.print("2. Subscribe to data package")
    console.print("3. Run: bcutils config --provider barchart --set-credentials")

def show_yahoo_info() -> None:
    """Show Yahoo Finance provider information."""
    info = Table()
    info.add_column("Attribute", style="cyan")
    info.add_column("Details", style="green")
    
    info.add_row("Description", "Free financial data service")
    info.add_row("Website", "https://finance.yahoo.com")
    info.add_row("Data Coverage", "Stocks, ETFs, indices, mutual funds")
    info.add_row("Historical Data", "Several decades for major securities")
    info.add_row("Rate Limits", "Reasonable use policy")
    info.add_row("Authentication", "None required")
    info.add_row("Cost", "Free")
    info.add_row("Data Format", "JSON/CSV")
    info.add_row("Update Frequency", "Real-time (delayed)")
    
    console.print(info)
    
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("No setup required - ready to use!")

def show_ibkr_info() -> None:
    """Show Interactive Brokers provider information."""
    info = Table()
    info.add_column("Attribute", style="cyan")
    info.add_column("Details", style="green")
    
    info.add_row("Description", "Professional trading platform data")
    info.add_row("Website", "https://www.interactivebrokers.com")
    info.add_row("Data Coverage", "All major asset classes worldwide")
    info.add_row("Historical Data", "Extensive coverage, varies by exchange")
    info.add_row("Rate Limits", "Based on connection type")
    info.add_row("Authentication", "TWS/Gateway connection")
    info.add_row("Cost", "Account required, data fees may apply")
    info.add_row("Data Format", "Real-time API")
    info.add_row("Update Frequency", "Real-time")
    
    console.print(info)
    
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Open Interactive Brokers account")
    console.print("2. Install and configure TWS or Gateway")
    console.print("3. Enable API connections in TWS")
    console.print("4. Run: bcutils config --provider ibkr --set-credentials")