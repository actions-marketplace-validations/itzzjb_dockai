"""
DockAI OpenTelemetry Tracing Module.

This module provides distributed tracing capabilities for the DockAI workflow.
It enables visibility into each step of the Dockerfile generation process,
helping with debugging, performance optimization, and observability in CI/CD.

Features:
- Automatic span creation for workflow nodes
- LLM call instrumentation with token usage attributes
- Console and OTLP export support
- Configurable via environment variables

Environment Variables:
- DOCKAI_ENABLE_TRACING: Enable/disable tracing (default: false)
- DOCKAI_TRACING_EXPORTER: Exporter type - 'console' or 'otlp' (default: console)
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL (for otlp exporter)
- OTEL_SERVICE_NAME: Service name for traces (default: dockai)
"""

import os
import logging
import functools
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger("dockai")

# Global tracer instance
_tracer = None
_tracing_enabled = False


class NoOpSpan:
    """
    A no-op span that safely ignores all attribute operations.
    
    This is used when tracing is disabled to avoid null checks
    throughout the codebase.
    """
    
    def set_attribute(self, key: str, value: Any) -> None:
        """No-op set_attribute."""
        pass
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """No-op set_attributes."""
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """No-op add_event."""
        pass
    
    def record_exception(self, exception: Exception) -> None:
        """No-op record_exception."""
        pass
    
    def set_status(self, status: Any) -> None:
        """No-op set_status."""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


# Singleton no-op span instance
_noop_span = NoOpSpan()


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled via environment variable."""
    return os.getenv("DOCKAI_ENABLE_TRACING", "false").lower() == "true"


def init_tracing(service_name: str = "dockai") -> None:
    """
    Initialize OpenTelemetry tracing.
    
    This should be called once at application startup. It configures
    the tracer provider and exporter based on environment variables.
    
    Args:
        service_name: Name of the service for trace identification.
    """
    global _tracer, _tracing_enabled
    
    if not is_tracing_enabled():
        logger.debug("Tracing is disabled (set DOCKAI_ENABLE_TRACING=true to enable)")
        _tracing_enabled = False
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        
        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: service_name})
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure exporter based on environment
        exporter_type = os.getenv("DOCKAI_TRACING_EXPORTER", "console").lower()
        
        if exporter_type == "otlp":
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
                exporter = OTLPSpanExporter(endpoint=endpoint)
                logger.info(f"OpenTelemetry OTLP exporter configured: {endpoint}")
            except ImportError:
                logger.warning("OTLP exporter not available, falling back to console")
                exporter = ConsoleSpanExporter()
        else:
            exporter = ConsoleSpanExporter()
            logger.info("OpenTelemetry console exporter configured")
        
        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer instance
        _tracer = trace.get_tracer("dockai", "1.0.0")
        _tracing_enabled = True
        
        logger.info("OpenTelemetry tracing initialized successfully")
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed, tracing disabled: {e}")
        _tracing_enabled = False
    except Exception as e:
        logger.warning(f"Failed to initialize tracing: {e}")
        _tracing_enabled = False


def get_tracer():
    """Get the global tracer instance."""
    return _tracer


@contextmanager
def create_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager to create a tracing span.
    
    If tracing is disabled, this returns a no-op span that safely ignores
    all attribute operations.
    
    Args:
        name: Name of the span (e.g., "analyze_node", "llm_call").
        attributes: Optional dictionary of span attributes.
        
    Yields:
        The span object if tracing is enabled, a NoOpSpan otherwise.
        
    Example:
        with create_span("analyze_node", {"project_path": "/my/project"}) as span:
            # Do work - no need to check if span is None
            span.set_attribute("files_found", 42)
    """
    if not _tracing_enabled or _tracer is None:
        yield _noop_span
        return
    
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    
    with _tracer.start_as_current_span(name) as span:
        try:
            # Set initial attributes
            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        # Convert to supported types
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(key, value)
                        elif isinstance(value, (list, tuple)):
                            span.set_attribute(key, str(value)[:500])
                        else:
                            span.set_attribute(key, str(value)[:500])
            
            yield span
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_node(node_name: str):
    """
    Decorator to trace a LangGraph workflow node.
    
    Automatically creates a span for the node execution and records
    relevant state information.
    
    Args:
        node_name: Name of the node for the span.
        
    Example:
        @trace_node("analyze")
        def analyze_node(state: DockAIState) -> DockAIState:
            # Node logic
            return updated_state
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            attributes = {
                "node.name": node_name,
                "workflow.retry_count": state.get("retry_count", 0),
                "workflow.path": state.get("path", ""),
            }
            
            with create_span(f"node.{node_name}", attributes) as span:
                result = func(state)
                
                # Record output attributes if span exists
                if span and isinstance(result, dict):
                    if "error" in result and result["error"]:
                        span.set_attribute("node.error", str(result["error"])[:500])
                    if "usage_stats" in result:
                        # Record token usage from this node
                        stats = result.get("usage_stats", [])
                        if stats and isinstance(stats, list) and len(stats) > 0:
                            latest = stats[-1] if isinstance(stats[-1], dict) else {}
                            span.set_attribute("llm.total_tokens", latest.get("total_tokens", 0))
                            span.set_attribute("llm.model", latest.get("model", ""))
                
                return result
        
        return wrapper
    return decorator


def trace_llm_call(agent_name: str):
    """
    Decorator to trace an LLM call.
    
    Records model, token usage, and timing information.
    
    Args:
        agent_name: Name of the agent making the call.
        
    Example:
        @trace_llm_call("analyzer")
        def analyze_repo_needs(context: AgentContext) -> Tuple[AnalysisResult, Dict]:
            # LLM call logic
            return result, usage
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attributes = {
                "llm.agent": agent_name,
            }
            
            with create_span(f"llm.{agent_name}", attributes) as span:
                result = func(*args, **kwargs)
                
                # Record token usage if available
                if span and isinstance(result, tuple) and len(result) >= 2:
                    usage = result[1]
                    if isinstance(usage, dict):
                        span.set_attribute("llm.prompt_tokens", usage.get("prompt_tokens", 0))
                        span.set_attribute("llm.completion_tokens", usage.get("completion_tokens", 0))
                        span.set_attribute("llm.total_tokens", usage.get("total_tokens", 0))
                
                return result
        
        return wrapper
    return decorator


def record_workflow_start(path: str, config: Dict[str, Any]) -> None:
    """Record the start of a DockAI workflow execution."""
    if not _tracing_enabled:
        return
    
    with create_span("workflow.start", {
        "workflow.path": path,
        "workflow.max_retries": config.get("max_retries", 3),
    }):
        pass


def record_workflow_end(success: bool, retry_count: int, total_tokens: int) -> None:
    """Record the end of a DockAI workflow execution."""
    if not _tracing_enabled:
        return
    
    with create_span("workflow.end", {
        "workflow.success": success,
        "workflow.retry_count": retry_count,
        "workflow.total_tokens": total_tokens,
    }):
        pass


def shutdown_tracing() -> None:
    """Shutdown the tracing provider gracefully."""
    global _tracing_enabled
    
    if not _tracing_enabled:
        return
    
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, 'shutdown'):
            provider.shutdown()
        logger.debug("OpenTelemetry tracing shutdown complete")
    except Exception as e:
        logger.warning(f"Error shutting down tracing: {e}")
    
    _tracing_enabled = False
