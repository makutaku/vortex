"""
Unit tests for Prometheus metrics collection.

Tests VortexMetrics class, global metrics instance,
and all metric recording functions.
"""

import threading
from unittest.mock import Mock, patch, MagicMock
import pytest

from vortex.infrastructure.metrics.prometheus_metrics import (
    VortexMetrics,
    get_metrics,
    initialize_metrics,
)


@pytest.mark.unit
class TestVortexMetrics:
    """Test cases for VortexMetrics functionality."""

    @pytest.fixture
    def metrics(self):
        """Create a VortexMetrics instance."""
        return VortexMetrics()

    def test_metrics_initialization(self, metrics):
        """Test metrics instance is properly initialized."""
        assert metrics.provider_requests_total is not None
        assert metrics.provider_request_duration is not None
        assert metrics.downloads_total is not None
        assert metrics.download_rows is not None
        assert metrics.circuit_breaker_state is not None
        assert metrics.circuit_breaker_failures is not None
        assert metrics.active_correlations is not None
        assert metrics.system_info is not None
        assert metrics.errors_total is not None
        assert metrics.storage_operations_total is not None
        assert metrics.storage_operation_duration is not None
        assert metrics.config_loads_total is not None
        assert metrics._initialized is False
        assert metrics._http_server is None

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_start_metrics_server_already_running(self, mock_start, metrics):
        """Test starting metrics server when already running."""
        metrics._http_server = "mock_server"

        # Should log warning and return early
        metrics.start_metrics_server(8000)

        # Should not call start_http_server again
        mock_start.assert_not_called()

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_start_metrics_server_non_threaded(self, mock_start, metrics):
        """Test starting metrics server in non-threaded mode."""
        mock_start.return_value = "mock_server"

        metrics.start_metrics_server(8000, threaded=False)

        assert metrics._initialized is True
        assert metrics._metrics_port == 8000
        mock_start.assert_called_once_with(8000)

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    @patch('vortex.infrastructure.metrics.prometheus_metrics.threading.Thread')
    def test_start_metrics_server_threaded(self, mock_thread, mock_start, metrics):
        """Test starting metrics server in threaded mode."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        metrics.start_metrics_server(9090, threaded=True)

        assert metrics._initialized is True
        assert metrics._metrics_port == 9090
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_start_server_thread_success(self, mock_start, metrics):
        """Test _start_server_thread succeeds."""
        mock_start.return_value = "mock_server"

        metrics._start_server_thread(8000)

        assert metrics._http_server == "mock_server"
        mock_start.assert_called_once_with(8000)

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_start_server_thread_failure(self, mock_start, metrics):
        """Test _start_server_thread handles errors."""
        mock_start.side_effect = Exception("Port in use")

        with pytest.raises(Exception, match="Port in use"):
            metrics._start_server_thread(8000)

    @patch('vortex.infrastructure.metrics.prometheus_metrics.get_provider_registry')
    def test_set_system_info_success(self, mock_registry, metrics):
        """Test _set_system_info sets metrics correctly."""
        # Mock provider registry
        mock_reg = Mock()
        mock_reg.list_plugins.return_value = ["yahoo", "barchart", "ibkr"]
        mock_registry.return_value = mock_reg

        # Mock _get_vortex_version
        with patch.object(metrics, '_get_vortex_version', return_value='1.0.0'):
            metrics._set_system_info()

        # system_info.info() should have been called
        # We can't easily verify the exact call, but can verify it didn't raise

    @patch('vortex.infrastructure.metrics.prometheus_metrics.get_provider_registry')
    def test_set_system_info_error_fallback(self, mock_registry, metrics):
        """Test _set_system_info handles errors gracefully."""
        mock_registry.side_effect = Exception("Registry error")

        # Should not raise, should use fallback
        metrics._set_system_info()

    def test_get_vortex_version_success(self, metrics):
        """Test _get_vortex_version returns version."""
        with patch('pkg_resources.get_distribution') as mock_dist:
            mock_dist.return_value.version = '1.2.3'

            version = metrics._get_vortex_version()

            assert version == '1.2.3'

    def test_get_vortex_version_fallback(self, metrics):
        """Test _get_vortex_version returns 'development' on error."""
        with patch('pkg_resources.get_distribution', side_effect=Exception("Not found")):
            version = metrics._get_vortex_version()

            assert version == 'development'

    def test_record_provider_request_not_initialized(self, metrics):
        """Test record_provider_request when not initialized."""
        # Should return early without error
        metrics.record_provider_request("yahoo", "fetch_data", 1.5, True)

    def test_record_provider_request_initialized(self, metrics):
        """Test record_provider_request when initialized."""
        metrics._initialized = True

        # Should not raise
        metrics.record_provider_request("yahoo", "fetch_data", 1.5, True)
        metrics.record_provider_request("barchart", "login", 0.5, False)

    def test_record_download_not_initialized(self, metrics):
        """Test record_download when not initialized."""
        metrics.record_download("yahoo", "AAPL", 1000, True)

    def test_record_download_initialized(self, metrics):
        """Test record_download when initialized."""
        metrics._initialized = True

        metrics.record_download("yahoo", "AAPL", 1000, True)
        metrics.record_download("barchart", "GC", 500, False)
        metrics.record_download("ibkr", "EURUSD", 0, True)  # Zero rows

    def test_record_circuit_breaker_state_not_initialized(self, metrics):
        """Test record_circuit_breaker_state when not initialized."""
        metrics.record_circuit_breaker_state("yahoo", "open")

    def test_record_circuit_breaker_state_initialized(self, metrics):
        """Test record_circuit_breaker_state when initialized."""
        metrics._initialized = True

        metrics.record_circuit_breaker_state("yahoo", "closed")
        metrics.record_circuit_breaker_state("barchart", "open")
        metrics.record_circuit_breaker_state("ibkr", "half_open")
        metrics.record_circuit_breaker_state("test", "unknown")  # Unknown state defaults to 0

    def test_record_circuit_breaker_failure_not_initialized(self, metrics):
        """Test record_circuit_breaker_failure when not initialized."""
        metrics.record_circuit_breaker_failure("yahoo")

    def test_record_circuit_breaker_failure_initialized(self, metrics):
        """Test record_circuit_breaker_failure when initialized."""
        metrics._initialized = True

        metrics.record_circuit_breaker_failure("yahoo")
        metrics.record_circuit_breaker_failure("barchart")

    def test_record_error_not_initialized(self, metrics):
        """Test record_error when not initialized."""
        metrics.record_error("NetworkError", "yahoo", "fetch_data")

    def test_record_error_initialized(self, metrics):
        """Test record_error when initialized."""
        metrics._initialized = True

        metrics.record_error("NetworkError", "yahoo", "fetch_data")
        metrics.record_error("AuthError", "barchart", "login")
        metrics.record_error("ValidationError", "", "")  # Empty provider/operation

    def test_record_storage_operation_not_initialized(self, metrics):
        """Test record_storage_operation when not initialized."""
        metrics.record_storage_operation("write", "csv", 0.5, True)

    def test_record_storage_operation_initialized(self, metrics):
        """Test record_storage_operation when initialized."""
        metrics._initialized = True

        metrics.record_storage_operation("write", "csv", 0.5, True)
        metrics.record_storage_operation("read", "parquet", 0.3, False)

    def test_record_config_load_not_initialized(self, metrics):
        """Test record_config_load when not initialized."""
        metrics.record_config_load(True)

    def test_record_config_load_initialized(self, metrics):
        """Test record_config_load when initialized."""
        metrics._initialized = True

        metrics.record_config_load(True)
        metrics.record_config_load(False)

    def test_update_active_correlations_not_initialized(self, metrics):
        """Test update_active_correlations when not initialized."""
        metrics.update_active_correlations(5)

    def test_update_active_correlations_initialized(self, metrics):
        """Test update_active_correlations when initialized."""
        metrics._initialized = True

        metrics.update_active_correlations(5)
        metrics.update_active_correlations(0)

    def test_is_server_running(self, metrics):
        """Test is_server_running."""
        assert metrics.is_server_running() is False

        metrics._http_server = "mock_server"
        assert metrics.is_server_running() is True

    def test_stop_metrics_server(self, metrics):
        """Test stop_metrics_server."""
        metrics._http_server = "mock_server"

        metrics.stop_metrics_server()

        assert metrics._http_server is None


@pytest.mark.unit
class TestGlobalMetrics:
    """Test global metrics singleton."""

    def test_get_metrics_singleton(self):
        """Test get_metrics returns singleton instance."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_get_metrics_thread_safe(self):
        """Test get_metrics is thread-safe."""
        instances = []

        def get_instance():
            instances.append(get_metrics())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_initialize_metrics_enabled(self, mock_start):
        """Test initialize_metrics when enabled."""
        mock_start.return_value = "mock_server"

        metrics = initialize_metrics(port=9090, enabled=True)

        assert metrics is not None
        assert metrics._initialized is True

    def test_initialize_metrics_disabled(self):
        """Test initialize_metrics when disabled."""
        metrics = initialize_metrics(port=8000, enabled=False)

        assert metrics is None

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_initialize_metrics_error_handling(self, mock_start):
        """Test initialize_metrics handles errors."""
        mock_start.side_effect = Exception("Port in use")

        metrics = initialize_metrics(port=8000, enabled=True)

        # Should return None on error, not raise
        assert metrics is None
