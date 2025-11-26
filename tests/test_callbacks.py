"""Tests for the callbacks module."""
import pytest
from unittest.mock import MagicMock
from dockai.utils.callbacks import TokenUsageCallback


class TestTokenUsageCallback:
    """Test TokenUsageCallback class."""
    
    def test_callback_initial_state(self):
        """Test callback initializes with zero values."""
        callback = TokenUsageCallback()
        
        usage = callback.get_usage()
        assert usage["total_tokens"] == 0
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
    
    def test_callback_tracks_tokens(self):
        """Test that callback tracks token usage."""
        callback = TokenUsageCallback()
        
        # Simulate LLM response
        response = MagicMock()
        response.llm_output = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        callback.on_llm_end(response)
        
        usage = callback.get_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150
    
    def test_callback_accumulates_tokens(self):
        """Test that callback accumulates multiple calls."""
        callback = TokenUsageCallback()
        
        # First call
        response1 = MagicMock()
        response1.llm_output = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        callback.on_llm_end(response1)
        
        # Second call
        response2 = MagicMock()
        response2.llm_output = {
            "token_usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            }
        }
        callback.on_llm_end(response2)
        
        usage = callback.get_usage()
        assert usage["total_tokens"] == 450  # 150 + 300
        assert usage["prompt_tokens"] == 300
        assert usage["completion_tokens"] == 150
    
    def test_callback_handles_missing_usage(self):
        """Test callback handles missing token usage gracefully."""
        callback = TokenUsageCallback()
        
        response = MagicMock()
        response.llm_output = {}  # No token_usage
        
        callback.on_llm_end(response)
        
        usage = callback.get_usage()
        assert usage["total_tokens"] == 0
    
    def test_callback_handles_none_output(self):
        """Test callback handles None llm_output gracefully."""
        callback = TokenUsageCallback()
        
        response = MagicMock()
        response.llm_output = None
        
        callback.on_llm_end(response)
        
        usage = callback.get_usage()
        assert usage["total_tokens"] == 0
