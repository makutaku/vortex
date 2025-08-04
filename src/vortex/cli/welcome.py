"""
Welcome screen and initial user interaction.

Provides the welcome message and helpful tips for new users.
"""

from . import __version__


def show_welcome(ux):
    """Show enhanced welcome message."""
    ux.print_panel(
        f"🚀 **Vortex v{__version__}**\n\n"
        "Financial data download automation tool\n\n"
        "**Get Started Instantly (No Setup Required!):**\n"
        "• `vortex download --symbol AAPL` - Download Apple stock data\n"
        "• `vortex download -s TSLA MSFT` - Download multiple stocks\n"
        "• `vortex download -s GOOGL --start-date 2024-01-01` - Historical data\n\n"
        "**Other Commands:**\n"
        "• `vortex wizard` - Interactive setup wizard\n"
        "• `vortex providers --list` - Show all data providers\n"
        "• `vortex help quickstart` - Quick start guide",
        title="Welcome to Vortex - Free Data Ready!",
        style="green"
    )
    
    # Show helpful tips
    from .help import get_help_system
    help_system = get_help_system()
    help_system.show_tips(2)