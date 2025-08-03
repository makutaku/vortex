"""Configuration management command."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...exceptions import ConfigurationError, InvalidConfigurationError, MissingArgumentError
from ...config import ConfigManager, Provider
from ...logging_integration import get_module_logger

console = Console()
logger = get_module_logger()

@click.command()
@click.option(
    "--show",
    is_flag=True,
    help="Show current configuration"
)
@click.option(
    "--provider",
    type=str,
    help="Provider to configure (dynamic based on available plugins)"
)
@click.option(
    "--set-credentials",
    is_flag=True,
    help="Set credentials for specified provider"
)
@click.option(
    "--export",
    type=click.Path(path_type=Path),
    help="Export configuration to file"
)
@click.option(
    "--import",
    "import_file",
    type=click.Path(exists=True, path_type=Path),
    help="Import configuration from file"
)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset configuration to defaults"
)
@click.pass_context
def config(
    ctx: click.Context,
    show: bool,
    provider: Optional[str],
    set_credentials: bool,
    export: Optional[Path],
    import_file: Optional[Path],
    reset: bool,
) -> None:
    """Manage configuration and credentials.
    
    \b
    Examples:
        vortex config --show
        vortex config --provider barchart --set-credentials
        vortex config --export config.toml
        vortex config --import config.toml
        
    \b
    Installation:
        # Fast installation with uv (recommended)
        uv pip install -e .
        
        # Traditional installation
        pip install -e .
    """
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    
    # Handle reset first
    if reset:
        if Confirm.ask("Are you sure you want to reset all configuration?"):
            config_manager.reset_config()
            console.print("[green]✓ Configuration reset to defaults[/green]")
        return
    
    # Handle import
    if import_file:
        try:
            config_manager.import_config(import_file)
            console.print(f"[green]✓ Configuration imported from {import_file}[/green]")
        except (FileNotFoundError, PermissionError) as e:
            raise ConfigurationError(
                f"Cannot import configuration: {e}",
                f"Check that {import_file} exists and is readable"
            )
        except ValueError as e:
            raise InvalidConfigurationError("import_file", import_file, "valid TOML format")
        return
    
    # Handle export
    if export:
        try:
            config_manager.export_config(export)
            console.print(f"[green]✓ Configuration exported to {export}[/green]")
        except (PermissionError, OSError) as e:
            raise ConfigurationError(
                f"Cannot export configuration: {e}",
                f"Check that you have write permissions for {export}"
            )
        return
    
    # Handle set credentials
    if set_credentials:
        if not provider:
            raise MissingArgumentError("--provider", "config --set-credentials")
        
        set_provider_credentials(config_manager, provider)
        return
    
    # Handle show or default behavior
    if show or not any([provider, set_credentials, export, import_file, reset]):
        show_configuration(config_manager)
        return
    
    # If provider specified without action, show provider config
    if provider:
        show_provider_configuration(config_manager, provider)

def show_configuration(config_manager: ConfigManager) -> None:
    """Display current configuration."""
    config = config_manager.load_config()
    
    # General settings table
    table = Table(title="Vortex Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Config File", str(config_manager.config_file))
    table.add_row("Default Output Directory", str(config.general.output_directory))
    table.add_row("Default Backup", str(config.general.backup_enabled))
    table.add_row("Log Level", config.general.log_level.value)
    
    # Show default date range for download command when not specified
    from datetime import datetime, timedelta
    default_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    default_end = datetime.now().strftime("%Y-%m-%d")
    table.add_row("Default Download Date Range", f"{default_start} to {default_end} (last 30 days)")
    
    # Check for default assets files
    from pathlib import Path
    default_assets = []
    for provider in ["barchart", "yahoo", "ibkr"]:
        assets_file = Path(f"assets/{provider}.json")
        if assets_file.exists():
            default_assets.append(f"{provider}: {assets_file}")
    if not default_assets:
        assets_file = Path("assets/default.json")
        if assets_file.exists():
            default_assets.append(f"all providers: {assets_file}")
    
    if default_assets:
        table.add_row("Default Assets Files", "\n".join(default_assets))
    
    console.print(table)
    
    # Provider status table
    providers_table = Table(title="Provider Status")
    providers_table.add_column("Provider", style="cyan")
    providers_table.add_column("Status", style="green")
    providers_table.add_column("Notes")
    
    for provider in ["barchart", "yahoo", "ibkr"]:
        if provider == "barchart":
            has_creds = config_manager.validate_provider_credentials(provider)
            status = "✓ Configured" if has_creds else "✗ No credentials"
            notes = f"Daily limit: {config.providers.barchart.daily_limit}" if has_creds else "Use --set-credentials"
        elif provider == "yahoo":
            status = "✓ Ready"
            notes = "No credentials required"
        elif provider == "ibkr":
            status = "✓ Configured"  # IBKR always has default config
            notes = f"Host: {config.providers.ibkr.host}:{config.providers.ibkr.port}"
        
        providers_table.add_row(provider.upper(), status, notes)
    
    console.print(providers_table)

def show_provider_configuration(config_manager: ConfigManager, provider: str) -> None:
    """Display configuration for a specific provider."""
    provider_config = config_manager.get_provider_config(provider)
    
    table = Table(title=f"{provider.upper()} Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    if provider == "barchart":
        table.add_row("Username", provider_config.get("username") or "[red]Not set[/red]")
        table.add_row("Password", "••••••••" if provider_config.get("password") else "[red]Not set[/red]")
        table.add_row("Daily Limit", str(provider_config.get("daily_limit", 150)))
    elif provider == "yahoo":
        table.add_row("Status", "No configuration required")
        table.add_row("Enabled", str(provider_config.get("enabled", True)))
    elif provider == "ibkr":
        table.add_row("Host", provider_config.get("host", "localhost"))
        table.add_row("Port", str(provider_config.get("port", 7497)))
        table.add_row("Client ID", str(provider_config.get("client_id", 1)))
        table.add_row("Timeout", f"{provider_config.get('timeout', 30)}s")
    
    # Show default assets file for this provider
    from pathlib import Path
    assets_file = Path(f"assets/{provider}.json")
    if assets_file.exists():
        table.add_row("Default Assets File", str(assets_file))
    else:
        assets_file = Path("assets/default.json")
        if assets_file.exists():
            table.add_row("Default Assets File", f"{assets_file} (fallback)")
    
    console.print(table)

def set_provider_credentials(config_manager: ConfigManager, provider: str) -> None:
    """Interactively set credentials for a provider."""
    console.print(f"[bold]Setting up {provider.upper()} credentials[/bold]")
    
    if provider == "barchart":
        console.print("Enter your Barchart.com credentials:")
        username = Prompt.ask("Username (email)")
        password = Prompt.ask("Password", password=True)
        daily_limit = Prompt.ask("Daily download limit", default="150")
        
        config_manager.set_provider_config(provider, {
            "username": username,
            "password": password,
            "daily_limit": int(daily_limit)
        })
        
    elif provider == "yahoo":
        console.print("[yellow]Yahoo Finance doesn't require credentials[/yellow]")
        console.print("Configuration is automatically set up.")
        
        # Ensure Yahoo provider is enabled
        config_manager.set_provider_config(provider, {
            "enabled": True
        })
        
    elif provider == "ibkr":
        console.print("Enter your Interactive Brokers TWS/Gateway settings:")
        host = Prompt.ask("Host", default="localhost")
        port = Prompt.ask("Port", default="7497")
        client_id = Prompt.ask("Client ID", default="1")
        timeout = Prompt.ask("Timeout (seconds)", default="30")
        
        config_manager.set_provider_config(provider, {
            "host": host,
            "port": int(port),
            "client_id": int(client_id),
            "timeout": int(timeout)
        })
    
    console.print(f"[green]✓ {provider.upper()} credentials saved[/green]")
    console.print("\n[dim]Ready to download data! Try:[/dim]")
    console.print(f"[dim]  vortex download --provider {provider} --symbol SYMBOL[/dim]")
    
    if provider == "barchart":
        console.print("[dim]  vortex download --provider barchart --symbol GC --start-date 2024-01-01[/dim]")
    elif provider == "ibkr":
        console.print("[dim]  Make sure TWS/Gateway is running and API is enabled[/dim]")