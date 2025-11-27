"""Tests for the reviewer module."""
import pytest
from unittest.mock import patch, MagicMock
from dockai.agents.reviewer import review_dockerfile
from dockai.core.schemas import SecurityReviewResult, SecurityIssue
from dockai.core.agent_context import AgentContext


class TestReviewDockerfile:
    """Test review_dockerfile function."""
    
    @patch("dockai.agents.reviewer.TokenUsageCallback")
    @patch("dockai.agents.reviewer.ChatPromptTemplate")
    @patch("dockai.agents.reviewer.create_llm")
    def test_review_secure_dockerfile(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test reviewing a secure Dockerfile."""
        # Set up mock callback
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        # Set up mock prompt
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        # Set up mock LLM
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        # Create mock chain
        mock_chain = MagicMock()
        mock_result = SecurityReviewResult(
            thought_process="Reviewed Dockerfile for security issues - all good",
            is_secure=True,
            issues=[]
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        dockerfile = """FROM python:3.11-slim
USER app
WORKDIR /app
COPY --chown=app:app . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "app.py"]
"""
        
        context = AgentContext(dockerfile_content=dockerfile)
        result, usage = review_dockerfile(context=context)
        
        assert isinstance(result, SecurityReviewResult)
        assert result.is_secure is True
        assert len(result.issues) == 0
    
    @patch("dockai.agents.reviewer.TokenUsageCallback")
    @patch("dockai.agents.reviewer.ChatPromptTemplate")
    @patch("dockai.agents.reviewer.create_llm")
    def test_review_insecure_dockerfile(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test reviewing a Dockerfile with security issues."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        issue = SecurityIssue(
            severity="high",
            description="Running as root user",
            line_number=1,
            suggestion="Add USER instruction to run as non-root"
        )
        
        mock_chain = MagicMock()
        mock_result = SecurityReviewResult(
            thought_process="Found security issues in Dockerfile",
            is_secure=False,
            issues=[issue],
            dockerfile_fixes=["Add USER instruction"],
            fixed_dockerfile="FROM python:3.11-slim\nUSER app"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
"""
        
        context = AgentContext(dockerfile_content=dockerfile)
        result, usage = review_dockerfile(context=context)
        
        assert result.is_secure is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == "high"
    
    @patch("dockai.agents.reviewer.TokenUsageCallback")
    @patch("dockai.agents.reviewer.ChatPromptTemplate")
    @patch("dockai.agents.reviewer.create_llm")
    def test_review_with_critical_issue(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test reviewing a Dockerfile with critical security issue."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        issue = SecurityIssue(
            severity="critical",
            description="Hardcoded secret in Dockerfile",
            line_number=3,
            suggestion="Use Docker secrets or environment variables"
        )
        
        mock_chain = MagicMock()
        mock_result = SecurityReviewResult(
            thought_process="Critical security issue found - hardcoded secret",
            is_secure=False,
            issues=[issue],
            dockerfile_fixes=["Remove hardcoded secret", "Use ARG or ENV"],
            fixed_dockerfile="FROM python:3.11\nARG SECRET"
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        dockerfile = """FROM python:3.11
ENV SECRET=mysecretkey
"""
        
        context = AgentContext(dockerfile_content=dockerfile)
        result, usage = review_dockerfile(context=context)
        
        assert result.is_secure is False
        assert result.issues[0].severity == "critical"
    
    @patch("dockai.agents.reviewer.TokenUsageCallback")
    @patch("dockai.agents.reviewer.ChatPromptTemplate")
    @patch("dockai.agents.reviewer.create_llm")
    def test_review_returns_usage_dict(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test that review returns usage dictionary."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        mock_chain = MagicMock()
        mock_result = SecurityReviewResult(
            thought_process="Quick review",
            is_secure=True,
            issues=[]
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        context = AgentContext(dockerfile_content="FROM python:3.11")
        result, usage = review_dockerfile(context=context)
        
        assert isinstance(usage, dict)
        assert "total_tokens" in usage
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
    
    @patch("dockai.agents.reviewer.TokenUsageCallback")
    @patch("dockai.agents.reviewer.ChatPromptTemplate")
    @patch("dockai.agents.reviewer.create_llm")
    def test_review_with_multiple_issues(self, mock_create_llm, mock_prompt_class, mock_callback_class):
        """Test reviewing a Dockerfile with multiple security issues."""
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {"total_tokens": 100, "prompt_tokens": 80, "completion_tokens": 20}
        mock_callback_class.return_value = mock_callback
        
        mock_prompt = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt
        
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm
        
        issues = [
            SecurityIssue(
                severity="high",
                description="Using latest tag",
                line_number=1,
                suggestion="Pin to specific version"
            ),
            SecurityIssue(
                severity="medium",
                description="No HEALTHCHECK instruction",
                line_number=None,
                suggestion="Add HEALTHCHECK instruction"
            )
        ]
        
        mock_chain = MagicMock()
        mock_result = SecurityReviewResult(
            thought_process="Found multiple issues",
            is_secure=False,
            issues=issues,
            dockerfile_fixes=["Pin version", "Add HEALTHCHECK"]
        )
        mock_chain.invoke.return_value = mock_result
        mock_prompt.__or__.return_value = mock_chain
        
        dockerfile = "FROM python:latest\nCMD python app.py"
        
        context = AgentContext(dockerfile_content=dockerfile)
        result, usage = review_dockerfile(context=context)
        
        assert len(result.issues) == 2
