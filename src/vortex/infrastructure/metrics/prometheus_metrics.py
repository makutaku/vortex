"""
Prometheus metrics collection for Vortex financial data automation.

This module provides comprehensive metrics collection for monitoring
provider performance, download success rates, circuit breaker status,
and system health.
"""

import sys
import time
import threading
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
from vortex.core.correlation import get_correlation_manager
import logging

logger = logging.getLogger(__name__)


class VortexMetrics:
    """Prometheus metrics collection for Vortex"""
    
    def __init__(self):
        # Provider metrics
        self.provider_requests_total = Counter(
            'vortex_provider_requests_total',
            'Total provider API requests',
            ['provider', 'operation', 'status']
        )
        
        self.provider_request_duration = Histogram(
            'vortex_provider_request_duration_seconds',
            'Provider request duration in seconds',
            ['provider', 'operation'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        # Download metrics
        self.downloads_total = Counter(
            'vortex_downloads_total',
            'Total downloads processed',
            ['provider', 'status', 'symbol']
        )
        
        self.download_rows = Histogram(
            'vortex_download_rows',
            'Number of rows downloaded per request',
            ['provider', 'symbol'],
            buckets=[1, 10, 100, 1000, 5000, 10000, 50000, 100000]
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'vortex_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['provider']
        )
        
        self.circuit_breaker_failures = Counter(
            'vortex_circuit_breaker_failures_total',
            'Circuit breaker failures',
            ['provider']
        )
        
        # System metrics
        self.active_correlations = Gauge(
            'vortex_active_correlations',
            'Number of active correlation contexts'
        )
        
        self.system_info = Info(
            'vortex_system_info',
            'Vortex system information'
        )
        
        # Error metrics
        self.errors_total = Counter(
            'vortex_errors_total',
            'Total errors by type',
            ['error_type', 'provider', 'operation']
        )
        
        # Storage metrics
        self.storage_operations_total = Counter(
            'vortex_storage_operations_total',
            'Total storage operations',
            ['operation', 'storage_type', 'status']
        )
        
        self.storage_operation_duration = Histogram(
            'vortex_storage_operation_duration_seconds',
            'Storage operation duration',
            ['operation', 'storage_type'],
            buckets=[0.01, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # Configuration metrics
        self.config_loads_total = Counter(
            'vortex_config_loads_total',
            'Total configuration loads',
            ['status']
        )
        
        self._http_server = None
        self._metrics_port = 8000
        self._server_thread = None
        self._initialized = False

    def start_metrics_server(self, port: int = 8000, threaded: bool = True):
        """Start Prometheus metrics HTTP server"""
        if self._http_server is not None:
            logger.warning("Metrics server already running")
            return
            
        self._metrics_port = port
        
        if threaded:
            self._server_thread = threading.Thread(
                target=self._start_server_thread,
                args=(port,),
                daemon=True
            )
            self._server_thread.start()
        else:
            self._start_server_thread(port)
        
        self._initialized = True
        logger.info(f"Prometheus metrics server started on port {port}")
        
        # Set system info
        self._set_system_info()

    def _start_server_thread(self, port: int):
        """Start the metrics server in a thread"""
        try:
            self._http_server = start_http_server(port)
        except Exception as e:
            logger.error(f"Failed to start metrics server on port {port}: {e}")
            raise

    def _set_system_info(self):
        """Set system information metrics"""
        try:
            # Import here to avoid circular imports
            from vortex.plugins import get_provider_registry
            
            registry = get_provider_registry()
            providers = registry.list_plugins()
            
            self.system_info.info({
                'version': self._get_vortex_version(),
                'python_version': sys.version.split()[0],
                'providers': ','.join(providers),
                'provider_count': str(len(providers))
            })
        except Exception as e:
            logger.warning(f"Could not set system info: {e}")
            self.system_info.info({
                'version': 'unknown',
                'python_version': sys.version.split()[0]
            })

    def _get_vortex_version(self) -> str:
        """Get Vortex version"""
        try:
            import pkg_resources
            return pkg_resources.get_distribution('vortex').version
        except:
            return 'development'

    def record_provider_request(self, provider: str, operation: str, 
                              duration: float, success: bool):
        """Record provider request metrics"""
        if not self._initialized:
            return
            
        status = 'success' if success else 'error'
        
        self.provider_requests_total.labels(
            provider=provider.lower(),
            operation=operation,
            status=status
        ).inc()
        
        self.provider_request_duration.labels(
            provider=provider.lower(),
            operation=operation
        ).observe(duration)

    def record_download(self, provider: str, symbol: str, 
                       row_count: int, success: bool):
        """Record download metrics"""
        if not self._initialized:
            return
            
        status = 'success' if success else 'error'
        
        self.downloads_total.labels(
            provider=provider.lower(),
            status=status,
            symbol=symbol
        ).inc()
        
        if success and row_count > 0:
            self.download_rows.labels(
                provider=provider.lower(),
                symbol=symbol
            ).observe(row_count)

    def record_circuit_breaker_state(self, provider: str, state: str):
        """Record circuit breaker state"""
        if not self._initialized:
            return
            
        state_value = {'closed': 0, 'open': 1, 'half_open': 2}.get(state.lower(), 0)
        self.circuit_breaker_state.labels(provider=provider.lower()).set(state_value)

    def record_circuit_breaker_failure(self, provider: str):
        """Record circuit breaker failure"""
        if not self._initialized:
            return
            
        self.circuit_breaker_failures.labels(provider=provider.lower()).inc()

    def record_error(self, error_type: str, provider: str = '', operation: str = ''):
        """Record error occurrence"""
        if not self._initialized:
            return
            
        self.errors_total.labels(
            error_type=error_type,
            provider=provider.lower() if provider else '',
            operation=operation
        ).inc()

    def record_storage_operation(self, operation: str, storage_type: str,
                                duration: float, success: bool):
        """Record storage operation metrics"""
        if not self._initialized:
            return
            
        status = 'success' if success else 'error'
        
        self.storage_operations_total.labels(
            operation=operation,
            storage_type=storage_type,
            status=status
        ).inc()
        
        self.storage_operation_duration.labels(
            operation=operation,
            storage_type=storage_type
        ).observe(duration)

    def record_config_load(self, success: bool):
        """Record configuration load"""
        if not self._initialized:
            return
            
        status = 'success' if success else 'error'
        self.config_loads_total.labels(status=status).inc()

    def update_active_correlations(self, count: int):
        """Update active correlation count"""
        if not self._initialized:
            return
            
        self.active_correlations.set(count)

    def is_server_running(self) -> bool:
        """Check if metrics server is running"""
        return self._http_server is not None

    def stop_metrics_server(self):
        """Stop metrics server"""
        if self._http_server is not None:
            # Note: prometheus_client doesn't provide a clean way to stop the server
            # This is mainly for testing purposes
            self._http_server = None
            logger.info("Metrics server stopped")


# Global metrics instance
_metrics: Optional[VortexMetrics] = None
_metrics_lock = threading.Lock()


def get_metrics() -> VortexMetrics:
    """Get global metrics instance (thread-safe singleton)"""
    global _metrics
    
    if _metrics is None:
        with _metrics_lock:
            if _metrics is None:
                _metrics = VortexMetrics()
    
    return _metrics


def initialize_metrics(port: int = 8000, enabled: bool = True) -> Optional[VortexMetrics]:
    """Initialize metrics with configuration"""
    if not enabled:
        return None
        
    metrics = get_metrics()
    
    try:
        metrics.start_metrics_server(port)
        return metrics
    except Exception as e:
        logger.error(f"Failed to initialize metrics: {e}")
        return None