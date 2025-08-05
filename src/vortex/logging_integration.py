"""
Integration between Vortex configuration system and logging.

This module provides functions to configure the logging system based on
Vortex configuration and provides easy access to loggers throughout the application.
"""

from pathlib import Path
from typing import Optional

from .core.config import VortexConfig, ConfigManager
from .logging import (
    LoggingConfig as LogConfig, 
    LoggingManager, 
    VortexLogger, 
    PerformanceLogger,
    configure_logging,
    get_logger as _get_logger,
    get_performance_logger as _get_performance_logger
)

# Global state
_logging_configured = False
_current_config: Optional[VortexConfig] = None


def configure_logging_from_config(config: VortexConfig, service_name: str = "vortex", version: str = "unknown"):
    """Configure logging system from Vortex configuration."""
    global _logging_configured, _current_config
    
    logging_config = config.general.logging
    
    # Convert Vortex logging config to internal logging config
    log_config = LogConfig(
        level=logging_config.level.value,
        format_type=logging_config.format,
        output=logging_config.output,
        file_path=logging_config.file_path,
        max_file_size=logging_config.max_file_size,
        backup_count=logging_config.backup_count,
        service_name=service_name,
        version=version
    )
    
    configure_logging(log_config)
    _logging_configured = True
    _current_config = config


def configure_logging_from_manager(config_manager: ConfigManager, service_name: str = "vortex", version: str = "unknown"):
    """Configure logging system from ConfigManager."""
    config = config_manager.load_config()
    configure_logging_from_config(config, service_name, version)


def ensure_logging_configured():
    """Ensure logging is configured with defaults if not already done."""
    global _logging_configured
    
    if not _logging_configured:
        # Use default configuration
        default_config = LogConfig(
            level="INFO",
            format_type="console",
            output=["console"],
            service_name="vortex",
            version="unknown"
        )
        configure_logging(default_config)
        _logging_configured = True


def get_logger(name: str, correlation_id: Optional[str] = None) -> VortexLogger:
    """Get a Vortex logger instance, ensuring logging is configured."""
    ensure_logging_configured()
    return _get_logger(name, correlation_id)


def get_performance_logger(name: str, correlation_id: Optional[str] = None) -> PerformanceLogger:
    """Get a performance logger instance, ensuring logging is configured."""
    ensure_logging_configured()
    return _get_performance_logger(name, correlation_id)


def get_module_logger(module_name: str = None) -> VortexLogger:
    """Get a logger for the calling module."""
    if module_name is None:
        import inspect
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals.get('__name__', 'unknown')
    
    return get_logger(module_name)


def get_module_performance_logger(module_name: str = None) -> PerformanceLogger:
    """Get a performance logger for the calling module."""
    if module_name is None:
        import inspect
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals.get('__name__', 'unknown')
    
    return get_performance_logger(module_name)


def reconfigure_if_changed(config: VortexConfig):
    """Reconfigure logging if the configuration has changed."""
    global _current_config
    
    if not _logging_configured or _current_config is None:
        configure_logging_from_config(config)
        return
    
    # Check if logging configuration has changed
    current_logging = _current_config.general.logging
    new_logging = config.general.logging
    
    if (current_logging.level != new_logging.level or
        current_logging.format != new_logging.format or
        current_logging.output != new_logging.output or
        current_logging.file_path != new_logging.file_path):
        configure_logging_from_config(config)


# Health check and monitoring support
class HealthChecker:
    """Simple health check functionality."""
    
    def __init__(self):
        self.logger = get_logger("vortex.health")
        self.checks = {}
    
    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func
        self.logger.debug(f"Registered health check: {name}")
    
    def run_checks(self) -> dict:
        """Run all health checks and return results."""
        results = {
            "status": "healthy",
            "timestamp": None,
            "checks": {}
        }
        
        from datetime import datetime, timezone
        results["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = datetime.now()
                check_result = check_func()
                end_time = datetime.now()
                
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                if isinstance(check_result, bool):
                    check_result = {"healthy": check_result}
                elif not isinstance(check_result, dict):
                    check_result = {"healthy": bool(check_result), "details": str(check_result)}
                
                check_result["duration_ms"] = round(duration_ms, 2)
                results["checks"][name] = check_result
                
                if not check_result.get("healthy", False):
                    overall_healthy = False
                    self.logger.warning(f"Health check failed: {name}", check_name=name, result=check_result)
                else:
                    self.logger.debug(f"Health check passed: {name}", check_name=name, duration_ms=duration_ms)
                    
            except Exception as e:
                overall_healthy = False
                error_result = {
                    "healthy": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                results["checks"][name] = error_result
                self.logger.error(f"Health check error: {name}: {e}", check_name=name, exc_info=True)
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        
        self.logger.info(
            f"Health check completed: {results['status']}",
            overall_status=results["status"],
            checks_count=len(self.checks),
            healthy_count=sum(1 for c in results["checks"].values() if c.get("healthy", False))
        )
        
        return results


# Global health checker instance
health_checker = HealthChecker()


def register_health_check(name: str, check_func):
    """Register a health check function."""
    health_checker.register_check(name, check_func)


def run_health_checks() -> dict:
    """Run all registered health checks."""
    return health_checker.run_checks()


# Built-in health checks
def _check_logging_system():
    """Check that logging system is working."""
    return {
        "healthy": _logging_configured,
        "details": "Logging system configured" if _logging_configured else "Logging not configured"
    }


def _check_config_system():
    """Check that configuration system is accessible."""
    try:
        from .core.config import ConfigManager
        manager = ConfigManager()
        config = manager.load_config()
        return {
            "healthy": True,
            "details": f"Configuration loaded successfully, log level: {config.general.logging.level.value}"
        }
    except Exception as e:
        return {
            "healthy": False,
            "details": f"Configuration system error: {e}"
        }


# Register built-in health checks
register_health_check("logging_system", _check_logging_system)
register_health_check("config_system", _check_config_system)