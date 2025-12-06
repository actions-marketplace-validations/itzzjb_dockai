"""
Rate Limit Handler for DockAI.

Provides exponential backoff with jitter for generic rate limits and
registry-specific retries for Docker Hub/GCR/Quay.
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps


logger = logging.getLogger("dockai")


class RateLimitHandler:
    """
    Handles rate limiting with exponential backoff and jitter.
    
    Attributes:
        base_delay (float): Initial delay in seconds (default: 1)
        max_delay (float): Maximum delay in seconds (default: 60)
        max_retries (int): Maximum number of retry attempts (default: 5)
        backoff_factor (float): Multiplier for exponential backoff (default: 2)
    """
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        max_retries: int = 5,
        backoff_factor: float = 2.0
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_count = 0
    
    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """
        Calculate delay with exponential backoff and optional jitter.
        
        Args:
            attempt (int): Current retry attempt number
            retry_after (Optional[int]): Retry-After header value in seconds
            
        Returns:
            float: Delay duration in seconds
        """
        if retry_after:
            return min(retry_after, self.max_delay)
        delay = min(
            self.base_delay * (self.backoff_factor ** attempt),
            self.max_delay
        )
        import random
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        return delay + jitter
    
    def reset(self):
        """Reset retry counter."""
        self.retry_count = 0


def with_rate_limit_handling(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """
    Decorator to add rate limit handling to any function.
    
    Catches rate limit errors and retries with exponential backoff.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            handler = RateLimitHandler(
                base_delay=base_delay,
                max_delay=max_delay,
                max_retries=max_retries
            )
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Reset retry count on success
                    if attempt > 0:
                        logger.info(f"Retry succeeded after {attempt} attempts")
                    
                    return result
                
                except Exception as e:
                    # Check for rate limit errors in a generic way
                    error_str = str(e).lower()
                    is_rate_limit = (
                        'rate limit' in error_str or 
                        '429' in error_str or 
                        'too many requests' in error_str or
                        'quota exceeded' in error_str
                    )
                    
                    # Also check for specific OpenAI RateLimitError if the library is available/used
                    # This handles cases where the exception type is specific but message might vary
                    if not is_rate_limit:
                        try:
                            import openai
                            if isinstance(e, openai.RateLimitError):
                                is_rate_limit = True
                        except ImportError:
                            pass

                    if is_rate_limit:
                        last_exception = e
                        
                        if attempt >= max_retries:
                            logger.error(f"Max retries ({max_retries}) exceeded for rate limit")
                            raise RateLimitExceededError(
                                f"Rate limit exceeded after {max_retries} retries. "
                                f"Please wait a few minutes and try again, or upgrade your API tier."
                            ) from e
                    
                        # Extract retry-after from headers if available (generic approach)
                        retry_after = None
                        if hasattr(e, 'response') and e.response:
                            retry_after = e.response.headers.get('Retry-After')
                            if retry_after:
                                try:
                                    retry_after = int(retry_after)
                                except (ValueError, TypeError):
                                    retry_after = None
                        
                        # Calculate delay
                        delay = handler.calculate_delay(attempt, retry_after)
                        
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {delay:.1f}s before retry..."
                        )
                        
                        time.sleep(delay)
                        continue
                    
                    # Don't retry on other exceptions
                    raise
            
            # If we get here, we've exhausted all retries
            raise last_exception
        
        return wrapper
    return decorator


class RateLimitExceededError(Exception):
    """
    Raised when rate limits are exceeded after all retry attempts.
    
    This is a custom exception that provides clear messaging to users
    about rate limit issues and suggests actionable solutions.
    """
    pass





def handle_registry_rate_limit(func: Callable) -> Callable:
    """
    Decorator specifically for Container Registry API calls (Docker Hub, GCR, Quay).
    
    Registries often have strict rate limits for unauthenticated requests.
    
    Args:
        func: Function making Registry API calls
        
    Returns:
        Wrapped function with Registry rate limit handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_delay = 5.0
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if this is a rate limit error
                if 'rate limit' in error_str or '429' in error_str or 'too many requests' in error_str:
                    
                    if attempt >= max_retries:
                        logger.warning(
                            "Registry rate limit exceeded. "
                            "This won't prevent Dockerfile generation, but image tag verification may be skipped."
                        )
                        # Return None (or empty list depending on usage) to indicate failure without crashing
                        # The original function returns list, so we should probably return empty list if it expects list
                        # But the decorator returns None in the original code. 
                        # Let's check usage in registry.py. get_docker_tags returns List[str].
                        # So returning [] is safer.
                        return []
                    
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Registry API rate limit (attempt {attempt + 1}/{max_retries}). "
                        f"Waiting {delay:.0f}s..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Not a rate limit error, don't retry
                    raise
        
        return []
    
    return wrapper

