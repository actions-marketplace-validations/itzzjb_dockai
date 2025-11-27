"""Tests for the agent module."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dockai.agents.agent_functions import (
    create_plan,
    reflect_on_failure,
    detect_health_endpoints,
    detect_readiness_patterns,
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


class TestCreatePlan:
    """Test create_plan function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_create_plan_returns_planning_result(self, mock_create_llm, mock_invoke):
        """Test creating a Dockerfile plan returns proper result."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = PlanningResult(
            thought_process="Planning multi-stage build",
            base_image_strategy="Use python:3.11-slim for runtime",
            build_strategy="Multi-stage for smaller image",
            optimization_priorities=["security", "size"],
            potential_challenges=["Large dependencies"],
            mitigation_strategies=["Use multi-stage build"],
            use_multi_stage=True,
            use_minimal_runtime=True,
            use_static_linking=False,
            estimated_image_size="100-200MB"
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            analysis_result={"stack": "Python", "project_type": "service", "suggested_base_image": "python:3.11"},
            file_contents="# app code"
        )
        
        plan, usage = create_plan(context=context)
        
        assert isinstance(plan, PlanningResult)
        assert plan.use_multi_stage is True
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_create_plan_with_retry_history(self, mock_create_llm, mock_invoke):
        """Test create_plan uses retry history."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = PlanningResult(
            thought_process="Learning from previous failure",
            base_image_strategy="Switch to full image",
            build_strategy="Single stage with all deps",
            optimization_priorities=["compatibility"],
            potential_challenges=["Previous gcc error"],
            mitigation_strategies=["Install build-essential"],
            lessons_applied=["Install gcc before pip install"],
            use_multi_stage=False,
            use_minimal_runtime=False,
            use_static_linking=False,
            estimated_image_size="500MB"
        )
        
        mock_invoke.return_value = mock_result
        
        retry_history = [
            {"what_was_tried": "slim image", "why_it_failed": "missing gcc", "lesson_learned": "need build tools"}
        ]
        
        context = AgentContext(
            analysis_result={"stack": "Python", "project_type": "service"},
            file_contents="# numpy requires compilation",
            retry_history=retry_history
        )
        
        plan, usage = create_plan(context=context)
        
        assert len(plan.lessons_applied) > 0


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


class TestDetectHealthEndpoints:
    """Test detect_health_endpoints function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_detect_health_found(self, mock_create_llm, mock_invoke):
        """Test detecting an existing health endpoint."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        health_endpoint = HealthEndpoint(path="/health", port=8080)
        mock_result = HealthEndpointDetectionResult(
            thought_process="Found /health endpoint in routes",
            health_endpoints_found=[health_endpoint],
            primary_health_endpoint=health_endpoint,
            confidence="high",
            evidence=["Found @app.get('/health') in main.py"]
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            file_contents="@app.get('/health')\ndef health(): return {'status': 'ok'}",
            analysis_result={"stack": "Python", "project_type": "service"}
        )
        
        result, usage = detect_health_endpoints(context=context)
        
        assert isinstance(result, HealthEndpointDetectionResult)
        assert result.confidence == "high"
        assert result.primary_health_endpoint.path == "/health"
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_detect_health_not_found(self, mock_create_llm, mock_invoke):
        """Test when no health endpoint exists."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = HealthEndpointDetectionResult(
            thought_process="No explicit health endpoint found",
            health_endpoints_found=[],
            confidence="none",
            evidence=[],
            suggested_health_path="/health"
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            file_contents="# No health endpoint defined",
            analysis_result={"stack": "Python", "project_type": "service"}
        )
        
        result, usage = detect_health_endpoints(context=context)
        
        assert result.confidence == "none"
        assert len(result.health_endpoints_found) == 0


class TestDetectReadinessPatterns:
    """Test detect_readiness_patterns function."""
    
    @patch("dockai.agents.agent_functions.safe_invoke_chain")
    @patch("dockai.agents.agent_functions.create_llm")
    def test_detect_readiness_patterns(self, mock_create_llm, mock_invoke):
        """Test detecting readiness patterns."""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_result = ReadinessPatternResult(
            thought_process="Found startup patterns for FastAPI app",
            startup_success_patterns=["Uvicorn running on", "Application startup complete"],
            startup_failure_patterns=["Error:", "Failed to bind"],
            estimated_startup_time=5,
            max_wait_time=30,
            technology_detected="FastAPI",
            technology_specific_patterns=["Uvicorn running"]
        )
        
        mock_invoke.return_value = mock_result
        
        context = AgentContext(
            file_contents="from fastapi import FastAPI\napp = FastAPI()",
            analysis_result={"stack": "Python FastAPI", "project_type": "service"}
        )
        
        result, usage = detect_readiness_patterns(context=context)
        
        assert isinstance(result, ReadinessPatternResult)
        assert result.technology_detected == "FastAPI"
        assert len(result.startup_success_patterns) > 0


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
