"""Tests for the rate_limiter module."""
import pytest
import time
from unittest.mock import patch, MagicMock
from dockai.utils.rate_limiter import (
    RateLimitHandler,
    with_rate_limit_handling,
)


class TestRateLimitHandler:
    """Test RateLimitHandler class."""
    
    def test_handler_creation(self):
        """Test creating a rate limit handler."""
        handler = RateLimitHandler(
            base_delay=1.0,
            max_delay=60.0,
            max_retries=5
        )
        
        assert handler.base_delay == 1.0
        assert handler.max_delay == 60.0
        assert handler.max_retries == 5
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        handler = RateLimitHandler(base_delay=1.0, backoff_factor=2.0)
        
        # Delays should increase exponentially
        delay0 = handler.calculate_delay(0)
        delay1 = handler.calculate_delay(1)
        delay2 = handler.calculate_delay(2)
        
        # With base=1 and factor=2: delays are ~1, ~2, ~4 (plus jitter)
        assert delay0 >= 0.9 and delay0 <= 1.2  # ~1 + jitter
        assert delay1 >= 1.8 and delay1 <= 2.4  # ~2 + jitter
        assert delay2 >= 3.6 and delay2 <= 4.8  # ~4 + jitter
    
    def test_calculate_delay_respects_max(self):
        """Test that delay respects max_delay limit."""
        handler = RateLimitHandler(base_delay=1.0, max_delay=5.0, backoff_factor=2.0)
        
        # High attempt number should cap at max_delay
        delay = handler.calculate_delay(10)  # Would be 2^10 = 1024
        
        assert delay <= 5.5  # max_delay + jitter
    
    def test_calculate_delay_with_retry_after(self):
        """Test that retry_after header is respected."""
        handler = RateLimitHandler(base_delay=1.0, max_delay=60.0)
        
        delay = handler.calculate_delay(0, retry_after=30)
        
        assert delay == 30
    
    def test_reset(self):
        """Test handler reset."""
        handler = RateLimitHandler()
        handler.retry_count = 5
        
        handler.reset()
        
        assert handler.retry_count == 0


class TestWithRateLimitHandling:
    """Test with_rate_limit_handling decorator."""
    
    def test_successful_call(self):
        """Test decorator with successful function call."""
        @with_rate_limit_handling(max_retries=3)
        def success_func():
            return "success"
        
        result = success_func()
        
        assert result == "success"
    
    def test_retries_on_rate_limit(self):
        """Test decorator retries on rate limit error."""
        call_count = 0
        
        @with_rate_limit_handling(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Simulate rate limit error
                import openai
                raise openai.RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(),
                    body=None
                )
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_gives_up_after_max_retries(self):
        """Test decorator gives up after max retries."""
        @with_rate_limit_handling(max_retries=2, base_delay=0.01)
        def always_fails():
            import openai
            raise openai.RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(),
                body=None
            )
        
        with pytest.raises(Exception):
            always_fails()
