"""Tests for runtime configuration detection."""
import pytest
from unittest.mock import patch, MagicMock
from dockai.agents.agent_functions import detect_runtime_config
from dockai.core.agent_context import AgentContext
from dockai.core.schemas import RuntimeConfigResult, HealthEndpoint

class TestDetectRuntimeConfig:
    """Test detect_runtime_config function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_detect_runtime_config_success(self, mock_create_llm, mock_invoke):
        """Test detecting both health and readiness."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        health_endpoint = HealthEndpoint(path="/health", port=8080)
        mock_result = RuntimeConfigResult(
            thought_process="Found /health and startup logs",
            health_endpoints_found=[health_endpoint],
            primary_health_endpoint=health_endpoint,
            health_confidence="high",
            startup_success_patterns=["Server started"],
            startup_failure_patterns=["Error starting"],
            estimated_startup_time=5,
            max_wait_time=30
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            file_contents="@app.get('/health')\nprint('Server started')",
            analysis_result={"stack": "Python", "project_type": "service"}
        )
        
        result, usage = detect_runtime_config(context=context)
        
        assert isinstance(result, RuntimeConfigResult)
        assert result.health_confidence == "high"
        assert result.primary_health_endpoint.path == "/health"
        assert "Server started" in result.startup_success_patterns
