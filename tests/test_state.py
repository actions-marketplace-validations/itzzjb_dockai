"""Tests for the state module."""
import pytest
from dockai.core.state import DockAIState, RetryAttempt


class TestRetryAttempt:
    """Test RetryAttempt TypedDict."""
    
    def test_create_retry_attempt(self):
        """Test creating a retry attempt record."""
        attempt: RetryAttempt = {
            "attempt_number": 1,
            "dockerfile_content": "FROM python:3.11\nCMD python app.py",
            "error_message": "pip install failed",
            "error_type": "DEPENDENCY_ERROR",
            "what_was_tried": "Used slim base image",
            "why_it_failed": "Missing gcc for native extensions",
            "lesson_learned": "Need build tools for numpy"
        }
        
        assert attempt["attempt_number"] == 1
        assert attempt["error_type"] == "DEPENDENCY_ERROR"
        assert "gcc" in attempt["why_it_failed"]


class TestDockAIState:
    """Test DockAIState TypedDict."""
    
    def test_create_state(self):
        """Test creating a state dictionary."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        assert state["path"] == "/project"
        assert state["max_retries"] == 3
        assert state["retry_count"] == 0
        assert state["needs_reanalysis"] is False
    
    def test_state_mutation(self):
        """Test that state can be mutated during workflow."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        # Simulate workflow updates
        state["file_tree"] = ["app.py", "requirements.txt"]
        state["analysis_result"] = {"stack": "Python", "project_type": "service"}
        state["dockerfile_content"] = "FROM python:3.11\nCOPY . .\nCMD python app.py"
        state["retry_count"] = 1
        
        assert state["file_tree"] == ["app.py", "requirements.txt"]
        assert state["analysis_result"]["stack"] == "Python"
        assert "FROM python:3.11" in state["dockerfile_content"]
        assert state["retry_count"] == 1
    
    def test_state_with_error(self):
        """Test state with error after validation failure."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": ["app.py"],
            "file_contents": "print('hello')",
            "analysis_result": {"stack": "Python"},
            "current_plan": None,
            "dockerfile_content": "FROM python:3.11\nCMD python app.py",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        # Simulate validation failure
        state["error"] = "Build failed: missing dependency"
        state["error_details"] = {
            "error_type": "DEPENDENCY_ERROR",
            "root_cause": "Missing gcc",
            "suggestions": ["Use full base image"]
        }
        state["validation_result"] = {"success": False, "message": "Build failed"}
        state["logs"] = ["Step 1/4: FROM python:3.11", "Error: pip install failed"]
        
        assert state["error"] == "Build failed: missing dependency"
        assert state["error_details"]["error_type"] == "DEPENDENCY_ERROR"
        assert state["validation_result"]["success"] is False
        assert len(state["logs"]) == 2
    
    def test_state_usage_stats(self):
        """Test state usage statistics tracking."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        # Add usage stats as workflow progresses
        state["usage_stats"].append({
            "stage": "analyze",
            "model": "gpt-4o-mini",
            "total_tokens": 500
        })
        state["usage_stats"].append({
            "stage": "generate",
            "model": "gpt-4o",
            "total_tokens": 1000
        })
        
        assert len(state["usage_stats"]) == 2
        assert state["usage_stats"][0]["stage"] == "analyze"
        assert state["usage_stats"][1]["total_tokens"] == 1000
    
    def test_state_retry_history(self):
        """Test state retry history tracking."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        # Add retry attempts
        attempt1: RetryAttempt = {
            "attempt_number": 1,
            "dockerfile_content": "FROM python:3.11-slim",
            "error_message": "gcc not found",
            "error_type": "BUILD_ERROR",
            "what_was_tried": "Slim image",
            "why_it_failed": "Missing build tools",
            "lesson_learned": "Need gcc for native extensions"
        }
        
        state["retry_history"].append(attempt1)
        state["retry_count"] = 1
        
        assert len(state["retry_history"]) == 1
        assert state["retry_history"][0]["lesson_learned"] == "Need gcc for native extensions"
    
    def test_state_health_detection(self):
        """Test state with detected health endpoint."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        # Set health detection results
        state["detected_health_endpoint"] = {
            "path": "/health",
            "port": 8080,
            "confidence": 0.95
        }
        state["readiness_patterns"] = [r"Uvicorn running on", r"Application startup complete"]
        state["failure_patterns"] = [r"Error:", r"Failed to start"]
        
        assert state["detected_health_endpoint"]["path"] == "/health"
        assert state["detected_health_endpoint"]["port"] == 8080
        assert len(state["readiness_patterns"]) == 2


class TestStateConfig:
    """Test state configuration."""
    
    def test_config_with_instructions(self):
        """Test config with custom instructions."""
        state: DockAIState = {
            "path": "/project",
            "config": {
                "analyzer_instructions": "Use Python 3.11",
                "generator_instructions": "Use Alpine base",
                "reviewer_instructions": "Check for CVEs"
            },
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {},
            "current_plan": None,
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        assert state["config"]["analyzer_instructions"] == "Use Python 3.11"
        assert state["config"]["generator_instructions"] == "Use Alpine base"
        assert state["config"]["reviewer_instructions"] == "Check for CVEs"
    
    def test_state_with_plan(self):
        """Test state with current plan."""
        state: DockAIState = {
            "path": "/project",
            "config": {},
            "max_retries": 3,
            "file_tree": [],
            "file_contents": "",
            "analysis_result": {"stack": "Python"},
            "current_plan": {
                "base_image_strategy": "Use python:3.11-slim",
                "build_strategy": "Multi-stage build",
                "use_multi_stage": True,
                "optimization_priorities": ["security", "size"]
            },
            "dockerfile_content": "",
            "previous_dockerfile": None,
            "validation_result": {},
            "retry_count": 0,
            "error": None,
            "error_details": None,
            "logs": [],
            "retry_history": [],
            "reflection": None,
            "detected_health_endpoint": None,
            "readiness_patterns": [],
            "failure_patterns": [],
            "needs_reanalysis": False,
            "usage_stats": []
        }
        
        assert state["current_plan"]["use_multi_stage"] is True
        assert "security" in state["current_plan"]["optimization_priorities"]
