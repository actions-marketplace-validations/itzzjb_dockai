"""
DockAI Utils Module.

This module contains utility functions and helpers:
- Project scanner for file discovery
- Function registry for validation
- Dockerfile validator
- Prompt templates
- Rate limiting for API calls
- Token usage callbacks
- OpenTelemetry tracing
"""

from .scanner import get_file_tree
from .registry import get_docker_tags
from .validator import validate_docker_build_and_run, check_container_readiness, lint_dockerfile_with_hadolint
from .prompts import (
    get_prompt,
    get_prompt_config,
    set_prompt_config,
    load_prompts,
    PromptConfig,
)
from .rate_limiter import (
    RateLimitHandler,
    with_rate_limit_handling,
    handle_registry_rate_limit,
    RateLimitExceededError,
)
from .callbacks import TokenUsageCallback
from .tracing import (
    init_tracing,
    shutdown_tracing,
    create_span,
    trace_node,
    trace_llm_call,
    record_workflow_start,
    record_workflow_end,
    is_tracing_enabled,
)

__all__ = [
    "get_file_tree",
    "get_docker_tags",
    "validate_docker_build_and_run",
    "check_container_readiness",
    "lint_dockerfile_with_hadolint",
    "get_prompt",
    "get_prompt_config",
    "set_prompt_config",
    "load_prompts",
    "PromptConfig",
    "RateLimitHandler",
    "with_rate_limit_handling",
    "handle_registry_rate_limit",
    "RateLimitExceededError",
    "TokenUsageCallback",
    "init_tracing",
    "shutdown_tracing",
    "create_span",
    "trace_node",
    "trace_llm_call",
    "record_workflow_start",
    "record_workflow_end",
    "is_tracing_enabled",
]
