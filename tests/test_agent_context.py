"""Tests for the AgentContext class."""
import pytest
from dockai.core.agent_context import AgentContext


class TestAgentContextDefaults:
    """Tests for AgentContext default values."""
    
    def test_empty_context_creation(self):
        """Should create context with all defaults."""
        context = AgentContext()
        
        assert context.file_tree == []
        assert context.file_contents == ""
        assert context.analysis_result == {}
        assert context.current_plan is None
        assert context.retry_history == []
        assert context.dockerfile_content is None
        assert context.reflection is None
        assert context.error_message is None
        assert context.error_details is None
        assert context.container_logs == ""
        assert context.retry_count == 0
        assert context.custom_instructions == ""
        assert context.verified_tags == ""
    
    def test_partial_context_creation(self):
        """Should allow partial initialization with defaults for the rest."""
        context = AgentContext(
            file_tree=["app.py"],
            file_contents="print('hello')"
        )
        
        assert context.file_tree == ["app.py"]
        assert context.file_contents == "print('hello')"
        assert context.analysis_result == {}  # Default
        assert context.custom_instructions == ""  # Default


class TestAgentContextWithValues:
    """Tests for AgentContext with provided values."""
    
    def test_full_context_creation(self):
        """Should create context with all values provided."""
        context = AgentContext(
            file_tree=["app.py", "requirements.txt"],
            file_contents="flask==2.0.0",
            analysis_result={"stack": "Python with Flask", "project_type": "service"},
            current_plan={"strategy": "multi-stage"},
            retry_history=[{"attempt": 1, "error": "build failed"}],
            dockerfile_content="FROM python:3.11",
            reflection={"root_cause": "missing dependencies"},
            error_message="Build failed",
            error_details={"error_type": "dockerfile_error"},
            container_logs="Container started...",
            retry_count=2,
            custom_instructions="Use Alpine base",
            verified_tags="3.11-slim, 3.11-alpine"
        )
        
        assert context.file_tree == ["app.py", "requirements.txt"]
        assert context.file_contents == "flask==2.0.0"
        assert context.analysis_result == {"stack": "Python with Flask", "project_type": "service"}
        assert context.current_plan == {"strategy": "multi-stage"}
        assert len(context.retry_history) == 1
        assert context.dockerfile_content == "FROM python:3.11"
        assert context.reflection == {"root_cause": "missing dependencies"}
        assert context.error_message == "Build failed"
        assert context.error_details == {"error_type": "dockerfile_error"}
        assert context.container_logs == "Container started..."
        assert context.retry_count == 2
        assert context.custom_instructions == "Use Alpine base"
        assert context.verified_tags == "3.11-slim, 3.11-alpine"


class TestAgentContextFromState:
    """Tests for AgentContext.from_state() class method."""
    
    def test_from_empty_state(self):
        """Should create context from empty state dict."""
        state = {}
        context = AgentContext.from_state(state)
        
        assert context.file_tree == []
        assert context.file_contents == ""
        assert context.retry_count == 0
    
    def test_from_state_with_values(self):
        """Should correctly map state values to context."""
        state = {
            "file_tree": ["main.py", "config.yaml"],
            "file_contents": "import flask",
            "analysis_result": {"stack": "Python"},
            "current_plan": {"build_strategy": "single-stage"},
            "retry_history": [{"attempt": 1}],
            "dockerfile_content": "FROM python:3.11",
            "reflection": {"needs_fix": True},
            "error": "Test error",
            "error_details": {"type": "docker"},
            "retry_count": 3,
            "config": {
                "analyzer_instructions": "Focus on Flask"
            }
        }
        
        context = AgentContext.from_state(state, agent_name="analyzer")
        
        assert context.file_tree == ["main.py", "config.yaml"]
        assert context.file_contents == "import flask"
        assert context.analysis_result == {"stack": "Python"}
        assert context.current_plan == {"build_strategy": "single-stage"}
        assert context.retry_history == [{"attempt": 1}]
        assert context.dockerfile_content == "FROM python:3.11"
        assert context.reflection == {"needs_fix": True}
        assert context.error_message == "Test error"
        assert context.error_details == {"type": "docker"}
        assert context.retry_count == 3
        assert context.custom_instructions == "Focus on Flask"
    
    def test_from_state_uses_previous_dockerfile_fallback(self):
        """Should use previous_dockerfile if dockerfile_content is not available."""
        state = {
            "previous_dockerfile": "FROM node:18"
        }
        
        context = AgentContext.from_state(state)
        
        assert context.dockerfile_content == "FROM node:18"
    
    def test_from_state_with_different_agent_names(self):
        """Should fetch correct instructions based on agent name."""
        state = {
            "config": {
                "generator_instructions": "Use multi-stage builds",
                "reviewer_instructions": "Check for security issues"
            }
        }
        
        generator_context = AgentContext.from_state(state, agent_name="generator")
        reviewer_context = AgentContext.from_state(state, agent_name="reviewer")
        
        assert generator_context.custom_instructions == "Use multi-stage builds"
        assert reviewer_context.custom_instructions == "Check for security issues"
    
    def test_from_state_with_no_agent_name(self):
        """Should use custom_instructions key when no agent name provided."""
        state = {
            "config": {
                "custom_instructions": "General instructions"
            }
        }
        
        context = AgentContext.from_state(state, agent_name="")
        
        assert context.custom_instructions == "General instructions"


class TestAgentContextDataclassBehavior:
    """Tests for standard dataclass behavior."""
    
    def test_context_is_mutable(self):
        """Context fields should be mutable."""
        context = AgentContext()
        
        context.file_tree = ["new_file.py"]
        context.retry_count = 5
        
        assert context.file_tree == ["new_file.py"]
        assert context.retry_count == 5
    
    def test_context_equality(self):
        """Two contexts with same values should be equal."""
        context1 = AgentContext(file_tree=["a.py"], file_contents="test")
        context2 = AgentContext(file_tree=["a.py"], file_contents="test")
        
        assert context1 == context2
    
    def test_context_inequality(self):
        """Two contexts with different values should not be equal."""
        context1 = AgentContext(file_tree=["a.py"])
        context2 = AgentContext(file_tree=["b.py"])
        
        assert context1 != context2
    
    def test_list_fields_are_independent(self):
        """List fields should not be shared between instances."""
        context1 = AgentContext()
        context2 = AgentContext()
        
        context1.file_tree.append("test.py")
        
        assert "test.py" not in context2.file_tree
    
    def test_dict_fields_are_independent(self):
        """Dict fields should not be shared between instances."""
        context1 = AgentContext()
        context2 = AgentContext()
        
        context1.analysis_result["key"] = "value"
        
        assert "key" not in context2.analysis_result
