"""
Interactive setup wizard functionality.

Provides guided setup for new users with interactive prompts.
"""

from datetime import datetime
from pathlib import Path

import click

from .ux import CommandWizard, get_ux


def _convert_wizard_config_to_params(config: dict) -> dict:
    """Convert wizard config to CLI parameters."""
    params = {
        "provider": config.get("provider"),
        "symbol": config.get("symbols", []),
        "symbols_file": (
            Path(config["symbols_file"]) if config.get("symbols_file") else None
        ),
        "assets": None,
        "start_date": (
            datetime.fromisoformat(config["start_date"])
            if config.get("start_date")
            else None
        ),
        "end_date": (
            datetime.fromisoformat(config["end_date"])
            if config.get("end_date")
            else None
        ),
        "output_dir": None,
        "backup": config.get("backup", False),
        "force": config.get("force", False),
        "chunk_size": 30,
        "yes": True,  # Skip confirmation in wizard mode
    }
    return {k: v for k, v in params.items() if v is not None}


def wizard_command(ctx: click.Context):
    """Interactive setup and command wizard."""
    ux = get_ux()
    command_wizard = CommandWizard(ux)

    ux.print_panel(
        "🧙 **Vortex Wizard**\n\n" "Choose what you'd like to do:",
        title="Interactive Setup",
        style="magenta",
    )

    action = ux.choice(
        "What would you like to set up?",
        ["Download data", "Configure providers", "View help", "Exit"],
        "Download data",
    )

    if action == "Download data":
        config = command_wizard.run_download_wizard()
        if config.get("execute"):
            # Execute the download command
            from .commands.download import download

            ctx.invoke(download, **_convert_wizard_config_to_params(config))

    elif action == "Configure providers":
        config = command_wizard.run_config_wizard()
        if config.get("provider"):
            # Execute the config command
            from .commands.config import config as config_cmd

            ctx.invoke(config_cmd, provider=config["provider"], set_credentials=True)

    elif action == "View help":
        from .help import get_help_system

        help_system = get_help_system()
        help_system.show_quick_start()

    else:
        ux.print("👋 Goodbye!")
