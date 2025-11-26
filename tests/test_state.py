"""Tests for the state module."""
import pytest
from dockai.state import DockAIState


class TestDockAIState:
    """Test DockAIState TypedDict."""
    
    def test_create_state(self):
        """Test creating a state dictionary."""
        state: DockAIState = {
            "path": "/project",
            "file_tree": None,
            "analysis_result": None,
            "file_contents": None,
            "planning_result": None,
            "health_detection_result": None,
            "readiness_detection_result": None,
            "dockerfile_content": None,
            "project_type": None,
            "review_result": None,
            "validation_result": None,
            "reflection_result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "retry_history": [],
            "config": {},
            "usage_stats": []
        }
        
        assert state["path"] == "/project"
        assert state["max_retries"] == 3
        assert state["retry_count"] == 0
    
    def test_state_mutation(self):
        """Test that state can be mutated."""
        state: DockAIState = {
            "path": "/project",
            "file_tree": None,
            "analysis_result": None,
            "file_contents": None,
            "planning_result": None,
            "health_detection_result": None,
            "readiness_detection_result": None,
            "dockerfile_content": None,
            "project_type": None,
            "review_result": None,
            "validation_result": None,
            "reflection_result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "retry_history": [],
            "config": {},
            "usage_stats": []
        }
        
        # Simulate workflow updates
        state["file_tree"] = ["app.py", "requirements.txt"]
        state["analysis_result"] = {"stack": "Python"}
        state["dockerfile_content"] = "FROM python:3.11"
        state["retry_count"] = 1
        
        assert state["file_tree"] == ["app.py", "requirements.txt"]
        assert state["analysis_result"]["stack"] == "Python"
        assert state["dockerfile_content"] == "FROM python:3.11"
        assert state["retry_count"] == 1
    
    def test_state_with_error(self):
        """Test state with error."""
        state: DockAIState = {
            "path": "/project",
            "file_tree": None,
            "analysis_result": None,
            "file_contents": None,
            "planning_result": None,
            "health_detection_result": None,
            "readiness_detection_result": None,
            "dockerfile_content": None,
            "project_type": None,
            "review_result": None,
            "validation_result": None,
            "reflection_result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "retry_history": [],
            "config": {},
            "usage_stats": []
        }
        
        state["error"] = "Build failed: missing dependency"
        state["validation_result"] = {"success": False, "message": "Build failed"}
        
        assert state["error"] == "Build failed: missing dependency"
        assert state["validation_result"]["success"] is False
    
    def test_state_usage_stats(self):
        """Test state usage statistics tracking."""
        state: DockAIState = {
            "path": "/project",
            "file_tree": None,
            "analysis_result": None,
            "file_contents": None,
            "planning_result": None,
            "health_detection_result": None,
            "readiness_detection_result": None,
            "dockerfile_content": None,
            "project_type": None,
            "review_result": None,
            "validation_result": None,
            "reflection_result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "retry_history": [],
            "config": {},
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


class TestStateConfig:
    """Test state configuration."""
    
    def test_config_with_instructions(self):
        """Test config with custom instructions."""
        state: DockAIState = {
            "path": "/project",
            "file_tree": None,
            "analysis_result": None,
            "file_contents": None,
            "planning_result": None,
            "health_detection_result": None,
            "readiness_detection_result": None,
            "dockerfile_content": None,
            "project_type": None,
            "review_result": None,
            "validation_result": None,
            "reflection_result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "retry_history": [],
            "config": {
                "analyzer_instructions": "Use Python 3.11",
                "generator_instructions": "Use Alpine base",
                "reviewer_instructions": "Check for CVEs"
            },
            "usage_stats": []
        }
        
        assert state["config"]["analyzer_instructions"] == "Use Python 3.11"
        assert state["config"]["generator_instructions"] == "Use Alpine base"
        assert state["config"]["reviewer_instructions"] == "Check for CVEs"
