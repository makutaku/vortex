"""Provider management command."""

import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config_manager import ConfigManager
from vortex.plugins import get_provider_registry
from ..utils.provider_utils import get_available_providers, check_provider_configuration

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
    type=str,
    help="Test provider connectivity (use 'all' to test all providers)"
)
@click.option(
    "--info",
    type=str,
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
    
    \b
    Examples:
        vortex providers --list
        vortex providers --test barchart
        vortex providers --test all
        vortex providers --info barchart
        
    \b
    Quick Setup:
        # Install with uv (10x faster)
        uv pip install -e .
        
        # Configure provider
        vortex config --provider barchart --set-credentials
    """
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    
    if list_providers or not any([test, info]):
        show_providers_list(config_manager)
        return
    
    if test:
        # Validate test parameter
        if test != "all" and test not in get_available_providers():
            available_providers = get_available_providers()
            console.print(f"[red]Unknown provider '{test}'[/red]")
            console.print(f"Available providers: {', '.join(available_providers)}")
            console.print("Use 'all' to test all providers")
            return
        test_providers(config_manager, test)
        return
    
    if info:
        # Validate info parameter
        if info not in get_available_providers():
            available_providers = get_available_providers()
            console.print(f"[red]Unknown provider '{info}'[/red]")
            console.print(f"Available providers: {', '.join(available_providers)}")
            return
        show_provider_info(config_manager, info)

def show_providers_list(config_manager: ConfigManager) -> None:
    """Display list of available providers using plugin registry."""
    table = Table(title="Available Data Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Data Types", style="blue")
    table.add_column("Authentication")
    table.add_column("Rate Limits")
    
    try:
        registry = get_provider_registry()
        config = config_manager.load_config()
        
        # Get all available providers from plugin registry
        for provider_name in registry.list_plugins():
            try:
                plugin_info = registry.get_plugin_info(provider_name)
                provider_config = config.get("providers", {}).get(provider_name, {})
                
                # Check if configured using dynamic plugin-based validation
                config_status = check_provider_configuration(provider_name, provider_config)
                configured = config_status["configured"]
                
                status = "✓ Available" if configured else "⚠ Not configured"
                
                # Format supported assets
                assets_str = ", ".join(plugin_info["supported_assets"][:3])
                if len(plugin_info["supported_assets"]) > 3:
                    assets_str += f", +{len(plugin_info['supported_assets']) - 3} more"
                
                # Format authentication info dynamically
                auth_info = "None required" if not plugin_info["requires_auth"] else "Required"
                
                # Get more specific auth info from plugin if available
                try:
                    registry_plugin = registry.get_plugin(provider_name)
                    auth_details = getattr(registry_plugin.metadata, 'auth_method', None)
                    if auth_details:
                        auth_info = auth_details
                    elif plugin_info["requires_auth"]:
                        # Try to infer from plugin description or name
                        if "username" in str(plugin_info.get("config_schema", {})).lower():
                            auth_info = "Username/Password"
                        elif "gateway" in plugin_info["description"].lower() or "tws" in plugin_info["description"].lower():
                            auth_info = "TWS/Gateway"
                        else:
                            auth_info = "Authentication required"
                except Exception:
                    pass  # Use default auth_info
                
                # Format rate limits
                rate_limits = plugin_info.get("rate_limits", "Not specified")
                
                # Highlight default provider
                provider_display = provider_name.upper()
                if provider_name == "yahoo":
                    provider_display = f"{provider_name.upper()} [DEFAULT]"
                    if status == "✓ Available":
                        status = "✓ Ready (Free)"
                
                table.add_row(
                    provider_display,
                    status,
                    assets_str.title(),
                    auth_info,
                    rate_limits
                )
                
            except Exception as e:
                logger.warning(f"Error getting info for provider '{provider_name}': {e}")
                # Add minimal row for problematic providers
                table.add_row(
                    provider_name.upper(),
                    "✗ Error",
                    "Unknown",
                    "Unknown",
                    "Unknown"
                )
        
        console.print(table)
        console.print("\n[green]💡 Yahoo Finance is the default provider - no setup required![/green]")
        console.print("[dim]Use 'vortex config --provider PROVIDER --set-credentials' to configure premium providers[/dim]")
        
        # Show available providers count
        provider_count = len(registry.list_plugins())
        console.print(f"\n[dim]Total providers available: {provider_count}[/dim]")
        
    except Exception as e:
        logger.error(f"Failed to load provider registry: {e}")
        console.print(f"[red]Error loading providers: {e}[/red]")
        console.print("[yellow]Falling back to built-in provider list...[/yellow]")
        
        # Fallback to hardcoded list if plugin system fails
        _show_fallback_providers_list(config_manager)


def _show_fallback_providers_list(config_manager: ConfigManager) -> None:
    """Fallback provider list when plugin system fails."""
    table = Table(title="Available Data Providers (Fallback)")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Data Types", style="blue")
    table.add_column("Authentication")
    table.add_column("Rate Limits")
    
    # Get available providers dynamically, but with fallback info
    available_providers = get_available_providers()
    config = config_manager.load_config()
    
    # Default info for common providers if registry fails
    fallback_info = {
        "barchart": {
            "data_types": "Futures, Stocks, Options",
            "auth": "Username/Password",
            "limits": "150/day",
            "requires_auth": True,
            "auth_fields": ["username"]
        },
        "yahoo": {
            "data_types": "Stocks, ETFs, Indices",
            "auth": "None required",
            "limits": "Unlimited",
            "requires_auth": False,
            "auth_fields": []
        },
        "ibkr": {
            "data_types": "All asset classes",
            "auth": "TWS/Gateway",
            "limits": "Real-time connection",
            "requires_auth": True,
            "auth_fields": ["host"]
        }
    }
    
    for provider in available_providers:
        provider_config = config.get("providers", {}).get(provider, {})
        info = fallback_info.get(provider, {
            "data_types": "Unknown",
            "auth": "Unknown",
            "limits": "Unknown",
            "requires_auth": True,
            "auth_fields": []
        })
        
        # Check if configured dynamically
        if not info["requires_auth"]:
            configured = True
        elif info["auth_fields"]:
            configured = any(provider_config.get(field) for field in info["auth_fields"])
        else:
            configured = len(provider_config) > 0
        
        status = "✓ Available" if configured else "⚠ Not configured"
        
        # Highlight default provider
        provider_display = provider.upper()
        if provider == "yahoo":
            provider_display = f"{provider.upper()} [DEFAULT]"
            if status == "✓ Available":
                status = "✓ Ready (Free)"
        
        table.add_row(
            provider_display,
            status,
            info["data_types"],
            info["auth"],
            info["limits"]
        )
    
    console.print(table)
    console.print("\n[dim]Use 'vortex config --provider PROVIDER --set-credentials' to configure[/dim]")


def test_providers(config_manager: ConfigManager, provider: str) -> None:
    """Test provider connectivity using plugin registry."""
    try:
        registry = get_provider_registry()
        
        if provider == "all":
            providers_to_test = registry.list_plugins()
        else:
            providers_to_test = [provider]
        
        console.print(f"[bold]Testing provider connectivity...[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for prov in providers_to_test:
                task = progress.add_task(f"Testing {prov.upper()}...", total=None)
                
                try:
                    result = test_single_provider_via_plugin(config_manager, prov, registry)
                    
                    if result["success"]:
                        progress.update(task, description=f"✓ {prov.upper()} - {result['message']}")
                    else:
                        progress.update(task, description=f"✗ {prov.upper()} - {result['message']}")
                        
                except Exception as e:
                    progress.update(task, description=f"✗ {prov.upper()} - Error: {e}")
                    
    except Exception as e:
        logger.error(f"Failed to load plugin registry for testing: {e}")
        console.print(f"[red]Error loading plugin registry: {e}[/red]")
        console.print("[yellow]Falling back to legacy testing...[/yellow]")
        _test_providers_fallback(config_manager, provider)


def test_single_provider_via_plugin(config_manager: ConfigManager, provider: str, registry) -> dict:
    """Test connectivity to a single provider via plugin system."""
    try:
        # Get provider configuration
        config = config_manager.load_config()
        provider_config = config.get("providers", {}).get(provider, {})
        
        # Get plugin info to check requirements
        plugin_info = registry.get_plugin_info(provider)
        
        # Check if provider requires configuration using dynamic validation
        config_status = check_provider_configuration(provider, provider_config)
        if not config_status["configured"]:
            return {
                "success": False,
                "message": config_status["message"]
            }
        
        # Test connection via plugin
        test_result = registry.test_provider(provider, provider_config)
        
        if test_result:
            return {
                "success": True,
                "message": "Connection successful"
            }
        else:
            return {
                "success": False,
                "message": "Connection failed"
            }
            
    except Exception as e:
        logger.error(f"Plugin test failed for {provider}: {e}")
        return {
            "success": False,
            "message": f"Test error: {str(e)[:50]}..."
        }


def _test_providers_fallback(config_manager: ConfigManager, provider: str) -> None:
    """Fallback testing when plugins fail."""
    providers_to_test = get_available_providers() if provider == "all" else [provider]
    
    console.print(f"[bold]Testing provider connectivity (fallback)...[/bold]")
    
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
        
        # Test Barchart connectivity by attempting login and checking allowance
        try:
            from vortex.infrastructure.providers.bc_data_provider import BarchartDataProvider
            
            username = provider_config.get("username")
            password = provider_config.get("password")
            
            # Create provider instance which will attempt login
            bc_provider = BarchartDataProvider(username, password, daily_download_limit=1)
            
            # Check allowance to verify full connectivity
            url = "https://www.barchart.com/my/download"
            session = bc_provider.session
            resp = session.get(url)
            
            if resp.status_code == 200:
                # Extract XSRF token and check allowance
                xsf_token = BarchartDataProvider.extract_xsrf_token(resp)
                allowance, _ = bc_provider._fetch_allowance(url, xsf_token)
                
                if allowance.get('success'):
                    current_allowance = int(allowance.get('count', '0'))
                    return {"success": True, "message": f"Connected - {current_allowance} downloads used today"}
                else:
                    return {"success": False, "message": "Allowance check failed"}
            else:
                return {"success": False, "message": f"Connection failed - HTTP {resp.status_code}"}
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid Barchart credentials" in error_msg:
                return {"success": False, "message": "Invalid credentials"}
            elif "requests" in error_msg.lower() or "connection" in error_msg.lower():
                return {"success": False, "message": "Network connection failed"}
            else:
                return {"success": False, "message": f"Connection failed: {error_msg[:50]}..."}
        
    elif provider == "yahoo":
        # Test Yahoo Finance connectivity by fetching a small amount of data
        try:
            from datetime import datetime, timedelta
            from vortex.infrastructure.providers.yf_data_provider import YahooDataProvider
            
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
    console.print("3. Run: vortex config --provider barchart --set-credentials")

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
    console.print("4. Run: vortex config --provider ibkr --set-credentials")