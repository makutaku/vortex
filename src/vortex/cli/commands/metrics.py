"""CLI metrics command for Vortex monitoring and observability."""
import time
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from vortex.infrastructure.metrics import get_metrics
from vortex.core.config import get_config_manager

console = Console()

@click.group()
def metrics():
    """View and manage Vortex metrics and monitoring."""
    pass

@metrics.command("status")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format for metrics status"
)
def status(format: str):
    """Show current metrics collection status and health."""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config.general.metrics.enabled:
        console.print("[yellow]⚠️  Metrics collection is disabled in configuration[/yellow]")
        return
    
    metrics_instance = get_metrics()
    if not metrics_instance:
        console.print("[red]❌ Metrics system not available[/red]")
        return
    
    if format == "json":
        import json
        status_data = {
            "enabled": True,
            "port": config.general.metrics.port,
            "path": config.general.metrics.path,
            "instance_active": True
        }
        console.print(json.dumps(status_data, indent=2))
    else:
        # Rich table format
        table = Table(title="Vortex Metrics Status", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", "✅ Enabled")
        table.add_row("Port", str(config.general.metrics.port))
        table.add_row("Endpoint", f"http://localhost:{config.general.metrics.port}{config.general.metrics.path}")
        table.add_row("Instance", "✅ Active")
        
        console.print(table)

@metrics.command("endpoint")
def endpoint():
    """Show the metrics endpoint URL."""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config.general.metrics.enabled:
        console.print("[yellow]Metrics are disabled[/yellow]")
        return
    
    endpoint_url = f"http://localhost:{config.general.metrics.port}{config.general.metrics.path}"
    
    panel = Panel(
        f"[bold green]{endpoint_url}[/bold green]",
        title="Metrics Endpoint",
        border_style="blue"
    )
    console.print(panel)
    console.print(f"\n💡 Access this URL to view Prometheus metrics")
    console.print(f"🔗 Or integrate with monitoring tools like Grafana")

@metrics.command("test")
@click.option(
    "--samples",
    type=int,
    default=5,
    help="Number of test samples to generate"
)
def test(samples: int):
    """Generate test metrics to verify monitoring system."""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config.general.metrics.enabled:
        console.print("[yellow]⚠️  Metrics are disabled - enable in configuration first[/yellow]")
        return
    
    metrics_instance = get_metrics()
    if not metrics_instance:
        console.print("[red]❌ Metrics system not available[/red]")
        return
    
    console.print(f"[blue]🧪 Generating {samples} test metrics...[/blue]")
    
    # Generate test provider metrics
    providers = ["yahoo", "barchart", "ibkr"]
    operations = ["download", "authenticate", "fetch_data"]
    
    with console.status("[bold green]Generating test metrics...") as status:
        for i in range(samples):
            provider = providers[i % len(providers)]
            operation = operations[i % len(operations)]
            
            # Simulate request timing
            duration = 0.5 + (i * 0.1)  # Varying durations
            success = i % 4 != 0  # 75% success rate
            
            # Record test metrics
            metrics_instance.record_provider_request(
                provider=provider,
                operation=operation,
                duration=duration,
                success=success
            )
            
            if success:
                # Record download metrics for successful requests
                rows = 100 + (i * 50)
                metrics_instance.record_download_rows(provider, f"TEST{i}", rows)
                metrics_instance.record_download_success(provider, f"TEST{i}")
            else:
                metrics_instance.record_download_failure(provider, f"TEST{i}", "TestError")
            
            status.update(f"Generated test metric {i+1}/{samples}")
            time.sleep(0.1)  # Small delay for realism
    
    console.print("[green]✅ Test metrics generated successfully![/green]")
    console.print("\n📊 View metrics at:", style="bold")
    endpoint_url = f"http://localhost:{config.general.metrics.port}{config.general.metrics.path}"
    console.print(f"   {endpoint_url}")

@metrics.command("summary")
@click.option(
    "--provider",
    type=click.Choice(["yahoo", "barchart", "ibkr"]),
    help="Filter summary by provider"
)
def summary(provider: Optional[str]):
    """Show a summary of recent metrics activity."""
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config.general.metrics.enabled:
        console.print("[yellow]⚠️  Metrics collection is disabled[/yellow]")
        return
    
    metrics_instance = get_metrics()
    if not metrics_instance:
        console.print("[red]❌ Metrics system not available[/red]")
        return
    
    # This is a placeholder - in a real implementation, you'd query
    # the metrics store for recent activity
    console.print("[blue]📈 Metrics Summary[/blue]")
    
    if provider:
        console.print(f"[cyan]Filter: {provider.upper()} provider[/cyan]")
    
    console.print("\n[yellow]💡 For detailed metrics analysis:[/yellow]")
    console.print("   • Use Grafana dashboards for visualizations")
    console.print("   • Query Prometheus directly for raw metrics")
    console.print("   • Check monitoring stack with: docker compose -f docker/docker-compose.monitoring.yml up")
    
    endpoint_url = f"http://localhost:{config.general.metrics.port}{config.general.metrics.path}"
    console.print(f"\n🔗 Metrics endpoint: {endpoint_url}")

@metrics.command("dashboard")
def dashboard():
    """Show information about monitoring dashboards."""
    console.print("[blue]📊 Vortex Monitoring Dashboards[/blue]\n")
    
    # Grafana dashboard info
    dashboard_panel = Panel(
        "[bold green]Grafana Dashboard[/bold green]\n"
        "• URL: http://localhost:3000\n"
        "• Default login: admin/admin\n"
        "• Dashboard: Vortex Financial Data Automation\n"
        "• Features: Download success rates, provider performance,\n"
        "           circuit breaker status, error tracking",
        title="📈 Visual Monitoring",
        border_style="green"
    )
    console.print(dashboard_panel)
    
    # Prometheus info
    prometheus_panel = Panel(
        "[bold blue]Prometheus Metrics[/bold blue]\n"
        "• URL: http://localhost:9090\n"
        "• Raw metrics and queries\n"
        "• Alert rule management\n"
        "• Time series data exploration",
        title="🔍 Raw Metrics",
        border_style="blue"
    )
    console.print(prometheus_panel)
    
    # Setup instructions
    setup_panel = Panel(
        "[bold yellow]Quick Setup[/bold yellow]\n"
        "1. Start monitoring stack:\n"
        "   docker compose -f docker/docker-compose.monitoring.yml up -d\n"
        "\n"
        "2. Enable metrics in config:\n"
        "   vortex config --set metrics.enabled=true\n"
        "\n"
        "3. Access dashboards at URLs above",
        title="🚀 Getting Started",
        border_style="yellow"
    )
    console.print(setup_panel)

if __name__ == "__main__":
    metrics()