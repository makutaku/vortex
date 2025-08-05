"""
Auto-completion support for Vortex CLI.

This module provides tab completion for commands, options, and values
to improve the user experience and reduce typing errors.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click

from vortex.core.config import ConfigManager
from vortex.logging_integration import get_module_logger

logger = get_module_logger()


def complete_provider(ctx, param, incomplete):
    """Auto-complete provider names."""
    providers = ["barchart", "yahoo", "ibkr"]
    return [p for p in providers if p.startswith(incomplete.lower())]


def complete_symbol(ctx, param, incomplete):
    """Auto-complete symbol names from common symbols."""
    # Common symbols for quick completion
    common_symbols = [
        # Major stocks
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX",
        "BRKB", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL",
        
        # Major indices/ETFs
        "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "BND",
        
        # Futures (Barchart)
        "ES", "NQ", "YM", "RTY",  # Equity indices
        "GC", "SI", "HG", "PL",   # Metals
        "CL", "NG", "RB", "HO",   # Energy
        "ZC", "ZS", "ZW", "ZM",   # Agriculture
        "6E", "6B", "6J", "6A",   # Currencies
        
        # Forex pairs
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"
    ]
    
    incomplete_upper = incomplete.upper()
    matches = [s for s in common_symbols if s.startswith(incomplete_upper)]
    
    # Also try to load symbols from recent downloads
    try:
        data_dir = Path("./data")
        if data_dir.exists():
            csv_files = list(data_dir.glob("*.csv"))
            recent_symbols = [f.stem for f in csv_files[-20:]]  # Last 20 files
            for symbol in recent_symbols:
                if symbol.upper().startswith(incomplete_upper) and symbol not in matches:
                    matches.append(symbol.upper())
    except Exception:
        pass  # Ignore errors in completion
    
    return matches[:20]  # Limit to 20 suggestions


def complete_config_file(ctx, param, incomplete):
    """Auto-complete configuration file paths."""
    paths = []
    
    # Common config file locations
    config_locations = [
        Path.home() / ".config" / "vortex" / "config.toml",
        Path("./config.toml"),
        Path("./vortex.toml"),
        Path("./config") / "vortex.toml"
    ]
    
    for path in config_locations:
        if path.exists() and str(path).startswith(incomplete):
            paths.append(str(path))
    
    # Also complete paths in current directory
    try:
        current_dir = Path(".")
        for item in current_dir.iterdir():
            if item.name.startswith(incomplete):
                if item.is_file() and item.suffix in [".toml", ".yaml", ".yml", ".json"]:
                    paths.append(str(item))
                elif item.is_dir():
                    paths.append(str(item) + "/")
    except Exception:
        pass
    
    return paths


def complete_symbols_file(ctx, param, incomplete):
    """Auto-complete symbols file paths."""
    paths = []
    
    try:
        current_dir = Path(".")
        for item in current_dir.iterdir():
            if item.name.startswith(incomplete):
                if item.is_file() and item.suffix in [".txt", ".csv", ".json"]:
                    paths.append(str(item))
                elif item.is_dir():
                    paths.append(str(item) + "/")
    except Exception:
        pass
    
    return paths


def complete_assets_file(ctx, param, incomplete):
    """Auto-complete assets file paths."""
    paths = []
    
    # Check assets directory
    assets_dir = Path("assets")
    if assets_dir.exists():
        try:
            for item in assets_dir.iterdir():
                if item.name.startswith(incomplete) and item.suffix == ".json":
                    paths.append(str(item))
        except Exception:
            pass
    
    # Also check current directory
    try:
        current_dir = Path(".")
        for item in current_dir.iterdir():
            if item.name.startswith(incomplete):
                if item.is_file() and item.suffix == ".json":
                    paths.append(str(item))
                elif item.is_dir():
                    paths.append(str(item) + "/")
    except Exception:
        pass
    
    return paths


def complete_log_level(ctx, param, incomplete):
    """Auto-complete log levels."""
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    return [level for level in levels if level.lower().startswith(incomplete.lower())]


def complete_output_format(ctx, param, incomplete):
    """Auto-complete output formats."""
    formats = ["console", "json", "rich"]
    return [fmt for fmt in formats if fmt.startswith(incomplete.lower())]


def complete_date(ctx, param, incomplete):
    """Auto-complete common date formats."""
    from datetime import datetime, timedelta
    
    suggestions = []
    today = datetime.now()
    
    # Add common relative dates
    if not incomplete or "today".startswith(incomplete.lower()):
        suggestions.append(today.strftime("%Y-%m-%d"))
    
    if not incomplete or "yesterday".startswith(incomplete.lower()):
        yesterday = today - timedelta(days=1)
        suggestions.append(yesterday.strftime("%Y-%m-%d"))
    
    if not incomplete or "week".startswith(incomplete.lower()):
        week_ago = today - timedelta(weeks=1)
        suggestions.append(week_ago.strftime("%Y-%m-%d"))
    
    if not incomplete or "month".startswith(incomplete.lower()):
        month_ago = today - timedelta(days=30)
        suggestions.append(month_ago.strftime("%Y-%m-%d"))
    
    # Add year boundaries
    current_year = today.year
    suggestions.extend([
        f"{current_year}-01-01",
        f"{current_year-1}-01-01",
        f"{current_year-1}-12-31"
    ])
    
    # Filter by incomplete input
    if incomplete:
        suggestions = [s for s in suggestions if s.startswith(incomplete)]
    
    return suggestions[:10]


class CompletionInstaller:
    """Install shell completion for Vortex."""
    
    @staticmethod
    def get_completion_script(shell: str) -> str:
        """Get completion script for the specified shell."""
        if shell == "bash":
            return '''
# Vortex completion for Bash
_vortex_completion() {
    local IFS=$'\\n'
    local response
    
    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _VORTEX_COMPLETE=complete_bash $1)
    
    for completion in $response; do
        IFS=',' read type value <<< "$completion"
        
        if [[ $type == 'dir' ]]; then
            COMPREPLY+=("$value/")
        elif [[ $type == 'file' ]]; then
            COMPREPLY+=("$value")
        else
            COMPREPLY+=("$value")
        fi
    done
    
    return 0
}

complete -o default -F _vortex_completion vortex
'''
        
        elif shell == "zsh":
            return '''
# Vortex completion for Zsh
_vortex_completion() {
    local response
    local -a completions
    local -a completions_with_descriptions
    local -a response_lines
    
    response=$(env COMP_WORDS="$words" COMP_CWORD=$((CURRENT-1)) _VORTEX_COMPLETE=complete_zsh vortex)
    response_lines=(${(f)response})
    
    for line in $response_lines; do
        local type value
        type=${line%%,*}
        value=${line#*,}
        
        if [[ $type == 'dir' ]]; then
            _path_files -/
        elif [[ $type == 'file' ]]; then
            _path_files -f
        else
            completions+=$value
        fi
    done
    
    if [[ ${#completions[@]} -ne 0 ]]; then
        _describe 'values' completions
    fi
}

compdef _vortex_completion vortex
'''
        
        elif shell == "fish":
            return '''
# Vortex completion for Fish
complete -c vortex -f -a "(env _VORTEX_COMPLETE=complete_fish COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) vortex)"
'''
        
        else:
            raise ValueError(f"Unsupported shell: {shell}")
    
    @staticmethod
    def install_completion(shell: str = None) -> bool:
        """Install completion for the specified shell."""
        if not shell:
            shell = os.environ.get("SHELL", "").split("/")[-1]
            if not shell or shell not in ["bash", "zsh", "fish"]:
                return False
        
        try:
            script = CompletionInstaller.get_completion_script(shell)
            
            # Determine completion file location
            if shell == "bash":
                completion_dir = Path.home() / ".bash_completion.d"
                completion_dir.mkdir(exist_ok=True)
                completion_file = completion_dir / "vortex"
            
            elif shell == "zsh":
                # Try to find zsh completion directory
                zsh_dirs = [
                    Path.home() / ".zsh" / "completions",
                    Path("/usr/local/share/zsh/site-functions"),
                    Path("/usr/share/zsh/site-functions")
                ]
                
                completion_dir = None
                for zsh_dir in zsh_dirs:
                    if zsh_dir.exists() or zsh_dir.parent.exists():
                        completion_dir = zsh_dir
                        break
                
                if not completion_dir:
                    completion_dir = Path.home() / ".zsh" / "completions"
                
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "_vortex"
            
            elif shell == "fish":
                completion_dir = Path.home() / ".config" / "fish" / "completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "vortex.fish"
            
            # Write completion script
            completion_file.write_text(script)
            
            logger.info(f"Installed {shell} completion", shell=shell, file=str(completion_file))
            return True
            
        except Exception as e:
            logger.error(f"Failed to install {shell} completion: {e}")
            return False


@click.command()
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell to install completion for (auto-detected if not specified)"  
)
@click.option(
    "--show-script",
    is_flag=True,
    help="Show completion script instead of installing"
)
def install_completion(shell: Optional[str], show_script: bool):
    """Install shell completion for Vortex commands."""
    from vortex.cli.ux import get_ux
    
    ux = get_ux()
    
    if not shell:
        shell = os.environ.get("SHELL", "").split("/")[-1]
        if shell not in ["bash", "zsh", "fish"]:
            ux.print_error(f"Unsupported or unknown shell: {shell}")
            ux.print_info("Supported shells: bash, zsh, fish")
            ux.print_info("Use --shell option to specify explicitly")
            return
    
    installer = CompletionInstaller()
    
    if show_script:
        try:
            script = installer.get_completion_script(shell)
            ux.print_panel(
                script,
                title=f"{shell.capitalize()} Completion Script",
                style="green"
            )
        except ValueError as e:
            ux.print_error(str(e))
    else:
        ux.print(f"Installing {shell} completion...")
        
        if installer.install_completion(shell):
            ux.print_success(f"✓ {shell.capitalize()} completion installed!")
            
            if shell == "bash":
                ux.print_info("Add this to your ~/.bashrc:")
                ux.print("  source ~/.bash_completion.d/vortex", style="green")
            elif shell == "zsh":
                ux.print_info("Restart zsh or run:")
                ux.print("  autoload -U compinit && compinit", style="green")
            elif shell == "fish":
                ux.print_info("Restart fish shell to activate completion")
            
            ux.print("\nTest completion with:")
            ux.print("  vortex download --provider <TAB>", style="cyan")
            
        else:
            ux.print_error("Failed to install completion")
            ux.print_info("Try running with --show-script to see the completion code")