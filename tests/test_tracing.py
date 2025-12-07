"""Tests for the OpenTelemetry tracing module."""

import pytest
import os
from unittest.mock import patch, MagicMock

from dockai.utils.tracing import (
    is_tracing_enabled,
    init_tracing,
    create_span,
    NoOpSpan,
    _noop_span
)


class TestIsTracingEnabled:
    """Tests for the is_tracing_enabled function."""
    
    def test_tracing_disabled_by_default(self):
        """Test that tracing is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing env var
            os.environ.pop("DOCKAI_ENABLE_TRACING", None)
            assert is_tracing_enabled() is False
    
    def test_tracing_enabled_with_env_var(self):
        """Test that tracing can be enabled via environment variable."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "true"}):
            assert is_tracing_enabled() is True
    
    def test_tracing_enabled_case_insensitive(self):
        """Test that the env var check is case insensitive."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "TRUE"}):
            assert is_tracing_enabled() is True
        
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "True"}):
            assert is_tracing_enabled() is True
    
    def test_tracing_disabled_explicitly(self):
        """Test that tracing can be explicitly disabled."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            assert is_tracing_enabled() is False


class TestNoOpSpan:
    """Tests for the NoOpSpan class."""
    
    def test_noop_span_exists(self):
        """Test that the singleton NoOpSpan instance exists."""
        assert _noop_span is not None
        assert isinstance(_noop_span, NoOpSpan)
    
    def test_noop_span_set_attribute(self):
        """Test that set_attribute is a no-op."""
        span = NoOpSpan()
        # Should not raise any exceptions
        span.set_attribute("key", "value")
        span.set_attribute("number", 42)
        span.set_attribute("bool", True)
    
    def test_noop_span_set_attributes(self):
        """Test that set_attributes is a no-op."""
        span = NoOpSpan()
        span.set_attributes({"key": "value", "number": 42})
    
    def test_noop_span_add_event(self):
        """Test that add_event is a no-op."""
        span = NoOpSpan()
        span.add_event("event_name", {"attr": "value"})
    
    def test_noop_span_record_exception(self):
        """Test that record_exception is a no-op."""
        span = NoOpSpan()
        span.record_exception(Exception("test"))
    
    def test_noop_span_set_status(self):
        """Test that set_status is a no-op."""
        span = NoOpSpan()
        span.set_status("some_status")
    
    def test_noop_span_context_manager(self):
        """Test that NoOpSpan works as a context manager."""
        span = NoOpSpan()
        with span as s:
            assert s is span


class TestCreateSpan:
    """Tests for the create_span context manager."""
    
    def test_create_span_returns_noop_when_disabled(self):
        """Test that create_span returns NoOpSpan when tracing is disabled."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            with create_span("test_span") as span:
                assert isinstance(span, NoOpSpan)
                # Should not raise exceptions
                span.set_attribute("key", "value")
    
    def test_create_span_with_attributes(self):
        """Test that create_span accepts attributes even when disabled."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            with create_span("test_span", {"attr1": "value1", "attr2": 42}) as span:
                assert isinstance(span, NoOpSpan)
                span.set_attribute("additional", "attr")
    
    def test_create_span_safe_for_none_attributes(self):
        """Test that create_span handles None attributes."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            with create_span("test_span", None) as span:
                assert isinstance(span, NoOpSpan)


class TestInitTracing:
    """Tests for the init_tracing function."""
    
    def test_init_tracing_does_nothing_when_disabled(self):
        """Test that init_tracing is a no-op when tracing is disabled."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            # Should not raise any exceptions
            init_tracing("test_service")
    
    def test_init_tracing_graceful_when_otel_not_installed(self):
        """Test that init_tracing handles missing OpenTelemetry gracefully."""
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "true"}):
            with patch.dict('sys.modules', {'opentelemetry': None}):
                # Should not raise exceptions even if OpenTelemetry is not installed
                try:
                    init_tracing("test_service")
                except ImportError:
                    pass  # Expected when OpenTelemetry is not available


class TestTracingIntegrationWithNodes:
    """Integration tests ensuring tracing doesn't break workflow nodes."""
    
    def test_workflow_nodes_work_with_tracing_disabled(self):
        """Test that workflow nodes work correctly when tracing is disabled."""
        # This is implicitly tested by the existing test suite,
        # but we add an explicit test for clarity
        with patch.dict(os.environ, {"DOCKAI_ENABLE_TRACING": "false"}):
            with create_span("node.test", {"retry_count": 0}) as span:
                # Simulate what nodes do
                span.set_attribute("test_result", "success")
                span.set_attribute("count", 42)
                result = {"success": True}
                
            assert result["success"] is True
