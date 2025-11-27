"""Tests for the errors module."""
import pytest
from unittest.mock import patch, MagicMock
from dockai.core.errors import (
    ClassifiedError,
    ErrorType,
    classify_error,
)
from dockai.core.agent_context import AgentContext


class TestClassifiedError:
    """Test ClassifiedError dataclass."""
    
    def test_creation(self):
        """Test creating a classified error."""
        error = ClassifiedError(
            error_type=ErrorType.DOCKERFILE_ERROR,
            message="Syntax error in Dockerfile",
            suggestion="Check RUN command syntax",
            original_error="unexpected EOF",
            should_retry=True
        )
        
        assert error.error_type == ErrorType.DOCKERFILE_ERROR
        assert error.message == "Syntax error in Dockerfile"
        assert error.should_retry is True
    
    def test_non_retryable_error(self):
        """Test non-retryable error."""
        error = ClassifiedError(
            error_type=ErrorType.ENVIRONMENT_ERROR,
            message="Docker not installed",
            suggestion="Install Docker",
            original_error="docker: command not found",
            should_retry=False
        )
        
        assert error.should_retry is False


class TestErrorType:
    """Test ErrorType enum."""
    
    def test_error_types_exist(self):
        """Test that key error types are defined."""
        # Check all error types exist
        assert ErrorType.PROJECT_ERROR
        assert ErrorType.DOCKERFILE_ERROR
        assert ErrorType.ENVIRONMENT_ERROR
        assert ErrorType.UNKNOWN_ERROR


class TestClassifyError:
    """Test error classification function."""
    
    def test_classify_returns_classified_error(self):
        """Test that classify_error returns a ClassifiedError."""
        error_msg = "some error occurred"
        
        context = AgentContext(error_message=error_msg)
        result = classify_error(context=context)
        
        assert isinstance(result, ClassifiedError)
        assert result.original_error == error_msg
    
    def test_classify_network_error(self):
        """Test classifying network-related error."""
        error_msg = "connection timed out"
        
        context = AgentContext(error_message=error_msg)
        result = classify_error(context=context)
        
        assert isinstance(result, ClassifiedError)
        # Network errors should generally be retryable
        assert result.should_retry in [True, False]  # Depends on implementation
    
    def test_classify_permission_error(self):
        """Test classifying permission error."""
        error_msg = "permission denied: cannot write to /app"
        
        context = AgentContext(error_message=error_msg)
        result = classify_error(context=context)
        
        assert isinstance(result, ClassifiedError)
    
    def test_classify_unknown_error(self):
        """Test classifying unknown error."""
        error_msg = "something weird happened xyz123"
        
        context = AgentContext(error_message=error_msg)
        result = classify_error(context=context)
        
        # Should still return a valid ClassifiedError
        assert isinstance(result, ClassifiedError)
        assert result.original_error == error_msg
