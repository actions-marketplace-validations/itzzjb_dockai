"""Tests for the agent module."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dockai.agents.agent_functions import (
    reflect_on_failure,
    generate_iterative_dockerfile,
    safe_invoke_chain,
)
from dockai.core.agent_context import AgentContext
from dockai.core.schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult,
    HealthEndpoint,
)


class TestReflectOnFailure:
    """Test reflect_on_failure function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_reflect_returns_reflection_result(self, mock_create_llm, mock_invoke):
        """Test reflection returns proper result structure."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = ReflectionResult(
            thought_process="Analyzing failure",
            root_cause_analysis="Missing build dependency gcc",
            was_error_predictable=False,
            what_was_tried="Standard Python slim Dockerfile",
            why_it_failed="gcc not found when compiling C extension",
            lesson_learned="Install build dependencies for packages with C extensions",
            should_change_base_image=False,
            should_change_build_strategy=True,
            new_build_strategy="Add build-essential package",
            specific_fixes=["RUN apt-get update && apt-get install -y gcc"],
            needs_reanalysis=False,
            confidence_in_fix="high"
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            dockerfile_content="FROM python:3.11-slim\nRUN pip install numpy",
            error_message="gcc: command not found",
            error_details={"stage": "build", "exit_code": 1},
            analysis_result={"stack": "Python", "project_type": "service"}
        )
        
        result, usage = reflect_on_failure(context=context)
        
        assert isinstance(result, ReflectionResult)
        assert result.confidence_in_fix == "high"
        assert len(result.specific_fixes) > 0


class TestGenerateIterativeDockerfile:
    """Test generate_iterative_dockerfile function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_generate_iterative_dockerfile(self, mock_create_llm, mock_invoke):
        """Test iterative Dockerfile generation."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = IterativeDockerfileResult(
            thought_process="Fixed build error by adding gcc",
            previous_issues_addressed=["Missing gcc compiler"],
            dockerfile="FROM python:3.11-slim\nRUN apt-get update && apt-get install -y gcc\nRUN pip install numpy",
            changes_summary=["Added gcc installation"],
            confidence_in_fix="high",
            fallback_strategy="Use full Python image",
            project_type="service"
        )
        
        mock_invoke.return_value = mock_result
        
        reflection = {
            "root_cause_analysis": "Missing gcc",
            "specific_fixes": ["Install gcc"]
        }
        
        context = AgentContext(
            dockerfile_content="FROM python:3.11-slim\nRUN pip install numpy",
            reflection=reflection,
            analysis_result={"stack": "Python", "project_type": "service"},
            file_contents="# numpy app",
            current_plan={"use_multi_stage": False}
        )
        
        result, usage = generate_iterative_dockerfile(context=context)
        
        assert isinstance(result, IterativeDockerfileResult)
        assert "gcc" in result.dockerfile


class TestSafeInvokeChain:
    """Test safe_invoke_chain function."""
    
    def test_safe_invoke_chain_returns_result(self):
        """Test that safe_invoke_chain returns chain result."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "test_result"
        
        result = safe_invoke_chain(mock_chain, {"key": "value"}, [])
        
        assert result == "test_result"
        mock_chain.invoke.assert_called_once()
