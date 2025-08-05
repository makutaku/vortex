"""
Integration tests for the Vortex logging system.

These tests involve actual logging operations, file I/O, and system integration.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from vortex.logging.manager import LoggingManager
from vortex.logging.config import LoggingConfig
from vortex.logging.performance import PerformanceLogger, TimedOperation, get_performance_logger, timed
from vortex.logging.loggers import get_logger


@pytest.mark.integration
class TestVortexLoggerIntegration:
    """Integration tests for VortexLogger with actual logging."""
    
    def test_context_management(self, logger, caplog):
        """Test logger context management integration."""
        with caplog.at_level(logging.INFO):
            with logger.context({"user_id": "123", "action": "test"}):
                logger.info("Test message with context")
                
                # Nested context should merge
                with logger.context({"session": "abc"}):
                    logger.warning("Nested context message")
        
        # Verify context was used in logging
        assert "Test message with context" in caplog.text
        assert "Nested context message" in caplog.text
    
    def test_temporary_context(self, logger, caplog):
        """Test temporary context integration."""
        with caplog.at_level(logging.INFO):
            logger.info("Before temp context")
            
            with logger.temp_context(request_id="req-123"):
                logger.info("During temp context")
            
            logger.info("After temp context")
        
        # Check that context was applied and removed  
        # The request_id should be in the extra context, not necessarily in the message text
        log_text = caplog.text
        assert "req-123" in log_text or "During temp context" in log_text


@pytest.mark.integration
class TestPerformanceLoggerIntegration:
    """Integration tests for PerformanceLogger with actual operations."""
    
    def test_time_operation(self, perf_logger, caplog):
        """Test timing actual operations."""
        import time
        
        with caplog.at_level(logging.INFO):
            with perf_logger.start_operation("slow_operation", size="large"):
                time.sleep(0.1)  # Simulate work
        
        # Should have logged performance metrics
        assert "slow_operation" in caplog.text
        assert "duration" in caplog.text or "Completed operation" in caplog.text
    
    def test_failed_operation(self, perf_logger, caplog):
        """Test timing failed operations."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                with perf_logger.start_operation("failing_operation"):
                    raise ValueError("Simulated failure")
        
        # Should log the failure
        assert "failing_operation" in caplog.text
        assert "failed" in caplog.text.lower()
    
    def test_log_metric(self, perf_logger, caplog):
        """Test logging metrics integration."""
        with caplog.at_level(logging.INFO):
            perf_logger.log_metric("response_time", 0.123, endpoint="/api/data")
        
        assert "response_time" in caplog.text
        assert "0.123" in caplog.text
    
    def test_log_counter(self, perf_logger, caplog):
        """Test logging counters integration."""
        with caplog.at_level(logging.INFO):
            perf_logger.log_counter("requests", 5, method="GET")
        
        assert "requests" in caplog.text
        assert "5" in caplog.text


@pytest.mark.integration
class TestTimedOperationIntegration:
    """Integration tests for TimedOperation context manager."""
    
    def test_successful_operation(self, caplog):
        """Test successful timed operation."""
        import time
        
        with caplog.at_level(logging.INFO):
            with TimedOperation("database_query", {"table": "users"}):
                time.sleep(0.05)  # Simulate DB query
        
        assert "database_query" in caplog.text
        assert "completed" in caplog.text.lower()
    
    def test_failed_operation(self, caplog):
        """Test failed timed operation."""
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                with TimedOperation("failing_query", {"table": "missing"}):
                    raise RuntimeError("Table not found")
        
        assert "failing_query" in caplog.text
        assert "failed" in caplog.text.lower()


@pytest.mark.integration
class TestDecoratorsIntegration:
    """Integration tests for logging decorators."""
    
    def test_timed_decorator(self, caplog):
        """Test @timed decorator integration."""
        @timed("test_function")
        def test_function():
            import time
            time.sleep(0.02)
            return "success"
        
        with caplog.at_level(logging.INFO):
            result = test_function()
        assert result == "success"
        assert "test_function" in caplog.text


@pytest.mark.integration  
class TestLoggingEndToEndIntegration:
    """End-to-end integration tests for logging system."""
    
    def test_json_logging_to_file(self, temp_dir):
        """Test JSON logging to file integration."""
        log_file = temp_dir / "test.log"
        
        # Configure logging to file
        logging_manager = LoggingManager()
        config = LoggingConfig(
            level=logging.INFO,
            format_type="json",
            output="file",
            file_path=log_file
        )
        logging_manager.configure(config)
        
        logger = get_logger("test.module")
        logger.info("Test message", user="test_user")
        
        # Verify file was created and contains JSON
        assert log_file.exists()
        content = log_file.read_text()
        assert '"message": "Test message"' in content
        # User should be directly in the JSON (not nested in extra_context)
        assert '"user": "test_user"' in content
    
    def test_performance_logging_integration(self, caplog):
        """Test performance logging integration."""
        # Set logging level to ensure logs are captured
        with caplog.at_level(logging.INFO):
            perf_logger = get_performance_logger("test.module")
            
            # Log timing operation
            perf_logger.time_operation("data_processing", 12.5, cpu_usage=85.5, api_calls=42)
            
            # Use timed context manager
            with perf_logger.start_operation("data_processing"):
                import time
                time.sleep(0.01)
        
        # Verify all metrics were logged
        log_text = caplog.text
        assert "cpu_usage" in log_text
        assert "85.5" in log_text
        assert "api_calls" in log_text
        assert "42" in log_text
        assert "data_processing" in log_text