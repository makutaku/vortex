"""
CLI commands for resilience monitoring and management.

Provides commands to view circuit breaker status, error recovery statistics,
and system health information.
"""

import click
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from vortex.infrastructure.resilience.circuit_breaker import get_circuit_breaker_stats, reset_all_circuit_breakers
    from vortex.infrastructure.resilience.recovery import ErrorRecoveryManager
    from vortex.core.correlation import get_request_tracker
    RESILIENCE_AVAILABLE = True
except ImportError as e:
    # Graceful fallback if resilience system is not available
    RESILIENCE_AVAILABLE = False
    _import_error = e

from ..ux import get_ux


def _check_resilience_available():
    """Check if resilience system is available."""
    if not RESILIENCE_AVAILABLE:
        ux = get_ux()
        ux.print(f"❌ Resilience system not available: {_import_error}")
        ux.print("This may be due to missing dependencies or import issues.")
        return False
    return True


@click.group()
def resilience():
    """Monitor and manage system resilience features."""
    pass


@resilience.command()
@click.option(
    "--format", "-f",
    type=click.Choice(["table", "json", "summary"]),
    default="table",
    help="Output format"
)
@click.option(
    "--provider", "-p",
    help="Show stats for specific provider only"
)
def status(format: str, provider: Optional[str]):
    """Show circuit breaker and resilience status."""
    if not _check_resilience_available():
        return
        
    ux = get_ux()
    
    # Get circuit breaker stats
    cb_stats = get_circuit_breaker_stats()
    
    if provider:
        cb_stats = {k: v for k, v in cb_stats.items() if provider.lower() in k.lower()}
    
    if not cb_stats:
        if provider:
            ux.print(f"No circuit breakers found for provider: {provider}")
        else:
            ux.print("No circuit breakers are currently active")
        return
    
    if format == "json":
        ux.print_json(cb_stats)
        
    elif format == "summary":
        _show_summary(ux, cb_stats)
        
    else:  # table format
        _show_table(ux, cb_stats)


def _show_summary(ux, stats: Dict[str, Dict[str, Any]]):
    """Show summary view of circuit breaker status."""
    total_breakers = len(stats)
    healthy = sum(1 for s in stats.values() if s['state'] == 'closed')
    failing = sum(1 for s in stats.values() if s['state'] == 'open')
    testing = sum(1 for s in stats.values() if s['state'] == 'half_open')
    
    ux.print_panel(
        f"🔧 **Circuit Breaker Summary**\n\n"
        f"• Total Breakers: {total_breakers}\n"
        f"• Healthy (Closed): {healthy} ✅\n"
        f"• Failing (Open): {failing} ❌\n"
        f"• Testing (Half-Open): {testing} ⚠️\n\n"
        f"**Health Score:** {(healthy/total_breakers)*100:.1f}%" if total_breakers > 0 else "No breakers active",
        title="System Resilience Status",
        style="green" if failing == 0 else "yellow" if failing < total_breakers/2 else "red"
    )
    
    if failing > 0:
        failing_breakers = [name for name, s in stats.items() if s['state'] == 'open']
        ux.print(f"\n⚠️  **Failing Components:** {', '.join(failing_breakers)}")


def _show_table(ux, stats: Dict[str, Dict[str, Any]]):
    """Show detailed table view of circuit breaker status."""
    headers = ["Component", "State", "Failure Rate", "Total Calls", "Circuit Opens", "Last Failure"]
    rows = []
    
    for name, s in stats.items():
        state_emoji = {
            'closed': '✅',
            'open': '❌', 
            'half_open': '⚠️'
        }.get(s['state'], '❓')
        
        failure_rate = f"{s['failure_rate']*100:.1f}%" if s['failure_rate'] is not None else "N/A"
        last_failure = s['last_failure_time']
        if last_failure:
            try:
                dt = datetime.fromisoformat(last_failure.replace('Z', '+00:00'))
                last_failure = dt.strftime('%H:%M:%S')
            except:
                last_failure = last_failure[:19] if len(last_failure) > 19 else last_failure
        else:
            last_failure = "Never"
        
        rows.append([
            name[:20],  # Truncate long names
            f"{state_emoji} {s['state'].replace('_', '-').title()}",
            failure_rate,
            str(s['total_calls']),
            str(s['circuit_opened_count']),
            last_failure
        ])
    
    ux.print_table(rows, headers=headers, title="🔧 Circuit Breaker Status")


@resilience.command()
@click.option(
    "--confirm", "-y",
    is_flag=True,
    help="Skip confirmation prompt"
)
def reset(confirm: bool):
    """Reset all circuit breakers to closed state."""
    ux = get_ux()
    
    if not confirm:
        if not ux.confirm("Reset all circuit breakers to closed state?"):
            ux.print("Operation cancelled")
            return
    
    reset_all_circuit_breakers()
    ux.print("✅ All circuit breakers have been reset to closed state")


@resilience.command()
@click.option(
    "--format", "-f",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
def recovery(format: str):
    """Show error recovery statistics."""
    ux = get_ux()
    
    # Note: This would need to be integrated with a global recovery manager
    # For now, show placeholder information
    ux.print("📊 Error Recovery Statistics")
    ux.print("\nThis feature requires integration with active recovery managers.")
    ux.print("Recovery stats will be available when operations are running.")


@resilience.command()
@click.option(
    "--format", "-f", 
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
def requests(format: str):
    """Show active request tracking information."""
    ux = get_ux()
    
    tracker = get_request_tracker()
    active_requests = tracker.get_active_requests()
    
    if not active_requests:
        ux.print("No active requests are currently being tracked")
        return
    
    if format == "json":
        ux.print_json(active_requests)
    else:
        headers = ["Correlation ID", "Operation", "Provider", "Duration", "Started"]
        rows = []
        
        for corr_id, req in active_requests.items():
            duration = (datetime.now() - req['start_time']).total_seconds()
            started = req['start_time'].strftime('%H:%M:%S')
            provider = req.get('metadata', {}).get('provider', 'N/A')
            
            rows.append([
                corr_id[:8],
                req['operation'][:20],
                provider,
                f"{duration:.1f}s",
                started
            ])
        
        ux.print_table(rows, headers=headers, title="📡 Active Requests")


@resilience.command()
def health():
    """Show overall system health status."""
    ux = get_ux()
    
    # Get circuit breaker stats
    cb_stats = get_circuit_breaker_stats()
    
    # Calculate health metrics
    total_breakers = len(cb_stats)
    if total_breakers == 0:
        ux.print_panel(
            "🏥 **System Health: UNKNOWN**\n\n"
            "No circuit breakers are active.\n"
            "Health monitoring will be available when components are in use.",
            title="System Health Check",
            style="blue"
        )
        return
    
    healthy = sum(1 for s in cb_stats.values() if s['state'] == 'closed')
    failing = sum(1 for s in cb_stats.values() if s['state'] == 'open')
    testing = sum(1 for s in cb_stats.values() if s['state'] == 'half_open')
    
    health_score = (healthy / total_breakers) * 100
    
    # Determine overall health status
    if health_score >= 90:
        status = "HEALTHY"
        style = "green"
        emoji = "✅"
    elif health_score >= 70:
        status = "DEGRADED"
        style = "yellow" 
        emoji = "⚠️"
    else:
        status = "UNHEALTHY"
        style = "red"
        emoji = "❌"
    
    # Show health summary
    ux.print_panel(
        f"🏥 **System Health: {status}** {emoji}\n\n"
        f"**Overall Health Score:** {health_score:.1f}%\n\n"
        f"**Component Status:**\n"
        f"• Healthy Components: {healthy}/{total_breakers}\n"
        f"• Failing Components: {failing}/{total_breakers}\n"
        f"• Components Under Test: {testing}/{total_breakers}\n\n"
        f"**Recommendations:**\n" +
        _get_health_recommendations(health_score, failing, testing),
        title="System Health Check",
        style=style
    )


def _get_health_recommendations(health_score: float, failing: int, testing: int) -> str:
    """Get health recommendations based on current status."""
    recommendations = []
    
    if health_score >= 90:
        recommendations.append("• System is operating normally")
        recommendations.append("• Continue monitoring for any changes")
    elif health_score >= 70:
        recommendations.append("• Some components experiencing issues")
        recommendations.append("• Monitor failing components closely")
        if testing > 0:
            recommendations.append("• Allow time for recovery testing")
    else:
        recommendations.append("• System health is compromised")
        recommendations.append("• Check provider connectivity and credentials")
        recommendations.append("• Consider manual intervention for critical components")
        
    if failing > 0:
        recommendations.append(f"• Review logs for {failing} failing component(s)")
        
    return "\n".join(recommendations)


# Add the command group
@click.command()
@click.pass_context
def resilience_status(ctx):
    """Quick access to resilience status."""
    ctx.invoke(status, format="summary", provider=None)