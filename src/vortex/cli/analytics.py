"""
Privacy-respecting CLI analytics for Vortex.

This module provides optional usage analytics to help improve the CLI experience.
All data is anonymized and users can opt-out at any time.
"""

import json
import os
import hashlib
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

from vortex.core.logging_integration import get_module_logger
from vortex.cli.ux import get_ux

logger = get_module_logger()


class CliAnalytics:
    """Privacy-respecting CLI usage analytics."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "vortex"
        self.analytics_file = self.config_dir / "analytics.json"
        self.session_id = str(uuid4())
        self.enabled = self._check_enabled()
        self.user_id = self._get_or_create_user_id()
    
    def _check_enabled(self) -> bool:
        """Check if analytics are enabled."""
        # Check environment variable first
        env_setting = os.environ.get("VORTEX_ANALYTICS", "").lower()
        if env_setting in ("false", "0", "no", "off", "disabled"):
            return False
        elif env_setting in ("true", "1", "yes", "on", "enabled"):
            return True
        
        # Check config file
        try:
            if self.analytics_file.exists():
                with open(self.analytics_file) as f:
                    config = json.load(f)
                    return config.get("enabled", True)  # Default to enabled
        except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError) as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to read analytics config: {e}")
        
        return True  # Default to enabled
    
    def _get_or_create_user_id(self) -> str:
        """Get or create anonymous user ID."""
        try:
            if self.analytics_file.exists():
                with open(self.analytics_file) as f:
                    config = json.load(f)
                    if "user_id" in config:
                        return config["user_id"]
        except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError) as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to read analytics user ID: {e}")
        
        # Create new anonymous user ID
        user_id = hashlib.sha256(str(uuid4()).encode()).hexdigest()[:12]
        self._save_config({"user_id": user_id, "enabled": True})
        return user_id
    
    def _save_config(self, config: Dict[str, Any]):
        """Save analytics configuration."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.analytics_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save analytics config: {e}")
    
    def track_command(self, command: str, provider: Optional[str] = None, 
                     success: bool = True, duration_ms: Optional[float] = None,
                     **kwargs):
        """Track command usage."""
        if not self.enabled:
            return
        
        try:
            event = {
                "event": "command_executed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": self.session_id,
                "user_id": self.user_id,
                "command": command,
                "success": success,
                "platform": platform.system(),
                "python_version": platform.python_version(),
            }
            
            if provider:
                event["provider"] = provider
            if duration_ms is not None:
                event["duration_ms"] = duration_ms
            
            # Add safe metadata (no sensitive data)
            safe_kwargs = {}
            for key, value in kwargs.items():
                if key not in ["password", "username", "credentials"]:
                    if isinstance(value, (str, int, float, bool)):
                        safe_kwargs[key] = value
                    elif isinstance(value, list) and len(value) < 100:  # Avoid huge lists
                        safe_kwargs[key] = len(value)  # Just track count
            
            event.update(safe_kwargs)
            
            self._send_event(event)
            
        except Exception as e:
            logger.debug(f"Analytics tracking failed: {e}")
    
    def track_error(self, command: str, error_type: str, error_message: str = ""):
        """Track command errors."""
        if not self.enabled:
            return
        
        try:
            event = {
                "event": "command_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": self.session_id,
                "user_id": self.user_id,
                "command": command,
                "error_type": error_type,
                "error_message": error_message[:200],  # Truncate long messages
                "platform": platform.system(),
                "python_version": platform.python_version(),
            }
            
            self._send_event(event)
            
        except Exception as e:
            logger.debug(f"Analytics error tracking failed: {e}")
    
    def _send_event(self, event: Dict[str, Any]):
        """Send analytics event (placeholder for future implementation)."""
        # For now, just log the event locally for debugging
        # In a real implementation, this would send to an analytics service
        logger.debug("Analytics event", **event)
        
        # Store locally for potential future upload
        self._store_event_locally(event)
    
    def _store_event_locally(self, event: Dict[str, Any]):
        """Store event locally for potential future upload."""
        try:
            events_file = self.config_dir / "events.jsonl"
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(events_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            # Keep only last 1000 events to prevent file bloat
            self._trim_events_file(events_file)
            
        except Exception as e:
            logger.debug(f"Failed to store analytics event: {e}")
    
    def _trim_events_file(self, events_file: Path, max_events: int = 1000):
        """Trim events file to keep only recent events."""
        try:
            if not events_file.exists():
                return
            
            with open(events_file) as f:
                lines = f.readlines()
            
            if len(lines) > max_events:
                with open(events_file, 'w') as f:
                    f.writelines(lines[-max_events:])
                    
        except Exception as e:
            logger.debug(f"Failed to trim events file: {e}")
    
    def disable(self):
        """Disable analytics."""
        self.enabled = False
        config = {"enabled": False, "user_id": self.user_id}
        self._save_config(config)
        
        # Clear stored events
        try:
            events_file = self.config_dir / "events.jsonl"
            if events_file.exists():
                events_file.unlink()
        except (OSError, PermissionError) as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to clear events file: {e}")
    
    def enable(self):
        """Enable analytics."""
        self.enabled = True
        config = {"enabled": True, "user_id": self.user_id}
        self._save_config(config)
    
    def get_status(self) -> Dict[str, Any]:
        """Get analytics status information."""
        return {
            "enabled": self.enabled,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "config_file": str(self.analytics_file),
            "events_stored": self._count_stored_events()
        }
    
    def _count_stored_events(self) -> int:
        """Count stored events."""
        try:
            events_file = self.config_dir / "events.jsonl"
            if events_file.exists():
                with open(events_file) as f:
                    return sum(1 for _ in f)
        except (FileNotFoundError, OSError, PermissionError) as e:
            import logging
            logging.getLogger(__name__).debug(f"Failed to count stored events: {e}")
        return 0


# Global analytics instance
analytics = CliAnalytics()


def track_command(command: str, **kwargs):
    """Track command usage."""
    analytics.track_command(command, **kwargs)


def track_error(command: str, error_type: str, error_message: str = ""):
    """Track command error."""
    analytics.track_error(command, error_type, error_message)


def analytics_decorator(command_name: str):
    """Decorator to automatically track command usage."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                track_error(command_name, error_type, str(e))
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                track_command(command_name, success=success, duration_ms=duration_ms)
        
        return wrapper
    return decorator


import click

@click.group()
def analytics_cmd():
    """Manage analytics settings."""
    pass


@analytics_cmd.command()
def status():
    """Show analytics status."""
    ux = get_ux()
    status = analytics.get_status()
    
    table = ux.table("Analytics Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Enabled", "✓ Yes" if status["enabled"] else "✗ No")
    table.add_row("User ID", status["user_id"])
    table.add_row("Session ID", status["session_id"])
    table.add_row("Events Stored", str(status["events_stored"]))
    table.add_row("Config File", status["config_file"])
    
    table.print()
    
    if status["enabled"]:
        ux.print_info("🔒 Analytics are anonymized and help improve Vortex")
        ux.print_info("💡 Disable with: vortex analytics disable")
    else:
        ux.print_info("📊 Enable analytics to help improve Vortex")
        ux.print_info("💡 Enable with: vortex analytics enable")


@analytics_cmd.command()
def enable():
    """Enable analytics."""
    ux = get_ux()
    analytics.enable()
    ux.print_success("✓ Analytics enabled")
    ux.print_info("🔒 All data is anonymized and helps improve Vortex")


@analytics_cmd.command() 
def disable():
    """Disable analytics."""
    ux = get_ux()
    analytics.disable()
    ux.print_success("✓ Analytics disabled")
    ux.print_info("📊 All stored analytics data has been cleared")