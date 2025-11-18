"""
Unit tests for Prometheus metrics collection.

Tests VortexMetrics class logic without actually registering Prometheus metrics.
"""

import threading
from unittest.mock import Mock, patch, MagicMock
import pytest


@pytest.mark.unit
class TestVortexMetrics:
    """Test cases for VortexMetrics functionality."""

    @pytest.fixture
    def metrics(self):
        """Create a VortexMetrics instance with mocked Prometheus objects."""
        with patch('vortex.infrastructure.metrics.prometheus_metrics.Counter') as mock_counter, \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Gauge') as mock_gauge, \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Histogram') as mock_histogram, \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Info') as mock_info:

            # Create mock return values
            mock_counter.return_value = Mock()
            mock_gauge.return_value = Mock()
            mock_histogram.return_value = Mock()
            mock_info.return_value = Mock()

            from vortex.infrastructure.metrics.prometheus_metrics import VortexMetrics
            metrics_instance = VortexMetrics()
            yield metrics_instance

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

    def test_set_system_info_success(self, metrics):
        """Test _set_system_info sets metrics correctly."""
        # Create mock plugins module since get_provider_registry is imported inside the function
        mock_plugins_module = MagicMock()
        mock_registry = Mock()
        mock_registry.list_plugins.return_value = ["yahoo", "barchart", "ibkr"]
        mock_plugins_module.get_provider_registry.return_value = mock_registry

        # Inject mock module into sys.modules so the import finds it
        import sys
        with patch.dict(sys.modules, {'vortex.plugins': mock_plugins_module}):
            with patch.object(metrics, '_get_vortex_version', return_value='1.0.0'):
                metrics._set_system_info()

        # system_info.info() should have been called
        metrics.system_info.info.assert_called_once()

    def test_set_system_info_error_fallback(self, metrics):
        """Test _set_system_info handles errors gracefully."""
        # Create mock plugins module that raises exception
        mock_plugins_module = MagicMock()
        mock_plugins_module.get_provider_registry.side_effect = Exception("Registry error")

        import sys
        with patch.dict(sys.modules, {'vortex.plugins': mock_plugins_module}):
            # Should not raise, should use fallback
            metrics._set_system_info()

        # Should still call info with fallback data
        metrics.system_info.info.assert_called_once()

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

        # Should not call any metric methods
        metrics.provider_requests_total.labels.assert_not_called()

    def test_record_provider_request_initialized(self, metrics):
        """Test record_provider_request when initialized."""
        metrics._initialized = True

        # Mock the labels chain
        mock_labels = Mock()
        metrics.provider_requests_total.labels.return_value = mock_labels
        metrics.provider_request_duration.labels.return_value = Mock()

        metrics.record_provider_request("yahoo", "fetch_data", 1.5, True)

        # Should call labels with correct parameters
        metrics.provider_requests_total.labels.assert_called_with(
            provider="yahoo", operation="fetch_data", status="success"
        )
        mock_labels.inc.assert_called_once()

    def test_record_download_initialized(self, metrics):
        """Test record_download when initialized."""
        metrics._initialized = True

        mock_downloads = Mock()
        mock_rows = Mock()
        metrics.downloads_total.labels.return_value = mock_downloads
        metrics.download_rows.labels.return_value = mock_rows

        metrics.record_download("yahoo", "AAPL", 1000, True)

        metrics.downloads_total.labels.assert_called_with(
            provider="yahoo", status="success", symbol="AAPL"
        )
        mock_downloads.inc.assert_called_once()
        mock_rows.observe.assert_called_once_with(1000)

    def test_record_download_zero_rows(self, metrics):
        """Test record_download with zero rows doesn't record histogram."""
        metrics._initialized = True

        mock_downloads = Mock()
        metrics.downloads_total.labels.return_value = mock_downloads

        metrics.record_download("yahoo", "AAPL", 0, True)

        # Should not observe rows for zero count
        metrics.download_rows.labels.assert_not_called()

    def test_record_circuit_breaker_state_initialized(self, metrics):
        """Test record_circuit_breaker_state when initialized."""
        metrics._initialized = True

        mock_gauge = Mock()
        metrics.circuit_breaker_state.labels.return_value = mock_gauge

        metrics.record_circuit_breaker_state("yahoo", "closed")
        mock_gauge.set.assert_called_with(0)

        metrics.record_circuit_breaker_state("barchart", "open")
        mock_gauge.set.assert_called_with(1)

        metrics.record_circuit_breaker_state("ibkr", "half_open")
        mock_gauge.set.assert_called_with(2)

    def test_record_circuit_breaker_failure_initialized(self, metrics):
        """Test record_circuit_breaker_failure when initialized."""
        metrics._initialized = True

        mock_counter = Mock()
        metrics.circuit_breaker_failures.labels.return_value = mock_counter

        metrics.record_circuit_breaker_failure("yahoo")

        metrics.circuit_breaker_failures.labels.assert_called_with(provider="yahoo")
        mock_counter.inc.assert_called_once()

    def test_record_error_initialized(self, metrics):
        """Test record_error when initialized."""
        metrics._initialized = True

        mock_counter = Mock()
        metrics.errors_total.labels.return_value = mock_counter

        metrics.record_error("NetworkError", "yahoo", "fetch_data")

        metrics.errors_total.labels.assert_called_with(
            error_type="NetworkError", provider="yahoo", operation="fetch_data"
        )
        mock_counter.inc.assert_called_once()

    def test_record_storage_operation_initialized(self, metrics):
        """Test record_storage_operation when initialized."""
        metrics._initialized = True

        mock_counter = Mock()
        mock_histogram = Mock()
        metrics.storage_operations_total.labels.return_value = mock_counter
        metrics.storage_operation_duration.labels.return_value = mock_histogram

        metrics.record_storage_operation("write", "csv", 0.5, True)

        metrics.storage_operations_total.labels.assert_called_with(
            operation="write", storage_type="csv", status="success"
        )
        mock_counter.inc.assert_called_once()
        mock_histogram.observe.assert_called_once_with(0.5)

    def test_record_config_load_initialized(self, metrics):
        """Test record_config_load when initialized."""
        metrics._initialized = True

        mock_counter = Mock()
        metrics.config_loads_total.labels.return_value = mock_counter

        metrics.record_config_load(True)

        metrics.config_loads_total.labels.assert_called_with(status="success")
        mock_counter.inc.assert_called_once()

    def test_update_active_correlations_initialized(self, metrics):
        """Test update_active_correlations when initialized."""
        metrics._initialized = True

        metrics.update_active_correlations(5)

        metrics.active_correlations.set.assert_called_once_with(5)

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

    def test_get_metrics_returns_instance(self):
        """Test get_metrics returns an instance."""
        with patch('vortex.infrastructure.metrics.prometheus_metrics.Counter'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Gauge'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Histogram'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Info'):

            from vortex.infrastructure.metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            assert metrics is not None

    @patch('vortex.infrastructure.metrics.prometheus_metrics.start_http_server')
    def test_initialize_metrics_enabled(self, mock_start):
        """Test initialize_metrics when enabled."""
        mock_start.return_value = "mock_server"

        with patch('vortex.infrastructure.metrics.prometheus_metrics.Counter'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Gauge'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Histogram'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Info'):

            from vortex.infrastructure.metrics.prometheus_metrics import initialize_metrics

            metrics = initialize_metrics(port=9090, enabled=True)

            assert metrics is not None

    def test_initialize_metrics_disabled(self):
        """Test initialize_metrics when disabled."""
        with patch('vortex.infrastructure.metrics.prometheus_metrics.Counter'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Gauge'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Histogram'), \
             patch('vortex.infrastructure.metrics.prometheus_metrics.Info'):

            from vortex.infrastructure.metrics.prometheus_metrics import initialize_metrics

            metrics = initialize_metrics(port=8000, enabled=False)

            assert metrics is None
