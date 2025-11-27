"""
DockAI Callbacks Module.

This module defines custom callback handlers for LangChain integration.
It is primarily used for monitoring and tracking the execution of LLM chains,
specifically focusing on token usage for cost estimation and optimization.
"""

from typing import Dict, Any, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

class TokenUsageCallback(BaseCallbackHandler):
    """
    A custom callback handler to track LLM API token usage.

    This class hooks into the LangChain execution lifecycle to capture token
    usage statistics returned by the LLM provider. This allows
    DockAI to report the cost of each operation to the user.

    Attributes:
        total_tokens (int): The cumulative total of tokens used.
        prompt_tokens (int): The cumulative number of tokens in the prompts.
        completion_tokens (int): The cumulative number of tokens in the completions.
    """

    def __init__(self):
        """Initializes the token counters to zero."""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when an LLM run ends.

        Extracts token usage information from the LLM output metadata and updates
        the internal counters.

        Args:
            response (LLMResult): The result object from the LLM execution.
            **kwargs: Additional keyword arguments provided by LangChain.
        """
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.total_tokens += usage.get("total_tokens", 0)
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            
    def get_usage(self) -> Dict[str, int]:
        """
        Retrieves the current token usage statistics.

        Returns:
            Dict[str, int]: A dictionary containing 'total_tokens', 'prompt_tokens',
            and 'completion_tokens'.
        """
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens
        }
