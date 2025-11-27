"""Tests for generic rate limiting logic."""
import pytest
import time
from unittest.mock import patch, MagicMock
from dockai.utils.rate_limiter import (
    with_rate_limit_handling,
    RateLimitExceededError
)

class GenericRateLimitError(Exception):
    """A generic rate limit exception for testing."""
    pass

class TestGenericRateLimitHandling:
    """Test generic rate limit handling without provider dependencies."""
    
    def test_retries_on_generic_rate_limit_string(self):
        """Test retries when exception message contains 'rate limit'."""
        call_count = 0
        
        @with_rate_limit_handling(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("API rate limit exceeded")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert call_count == 2

    def test_retries_on_429_string(self):
        """Test retries when exception message contains '429'."""
        call_count = 0
        
        @with_rate_limit_handling(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Error 429: Too Many Requests")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert call_count == 2

    def test_fails_on_other_errors(self):
        """Test that other errors are raised immediately."""
        @with_rate_limit_handling(max_retries=3)
        def failing_func():
            raise ValueError("Some other error")
            
        with pytest.raises(ValueError):
            failing_func()

    def test_max_retries_exceeded(self):
        """Test that RateLimitExceededError is raised after max retries."""
        @with_rate_limit_handling(max_retries=2, base_delay=0.01)
        def always_fails():
            raise Exception("Rate limit exceeded")
            
        with pytest.raises(RateLimitExceededError):
            always_fails()
