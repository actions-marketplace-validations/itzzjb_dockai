"""
DockAI Core Module.

This module contains the core components of the DockAI framework:
- LLM provider abstraction and configuration
- Pydantic schemas for structured data
- State management for the workflow
- Error classification and handling
- AgentContext for unified agent context
"""

from .agent_context import AgentContext
from .llm_providers import (
    LLMProvider,
    LLMConfig,
    create_llm,
    get_llm_config,
    set_llm_config,
    load_llm_config_from_env,
    get_model_for_agent,
    get_provider_info,
    log_provider_info,
)
from .schemas import (
    AnalysisResult,
    PlanningResult,
    DockerfileResult,
    IterativeDockerfileResult,
    SecurityReviewResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
)
from .state import DockAIState
from .errors import (
    ErrorType,
    ClassifiedError,
    classify_error,
    format_error_for_display,
)

__all__ = [
    # Agent Context
    "AgentContext",
    # LLM Providers
    "LLMProvider",
    "LLMConfig", 
    "create_llm",
    "get_llm_config",
    "set_llm_config",
    "load_llm_config_from_env",
    "get_model_for_agent",
    "get_provider_info",
    "log_provider_info",
    # Schemas
    "AnalysisResult",
    "PlanningResult",
    "DockerfileResult",
    "IterativeDockerfileResult",
    "SecurityReviewResult",
    "ReflectionResult",
    "HealthEndpointDetectionResult",
    "ReadinessPatternResult",
    # State
    "DockAIState",
    # Errors
    "ErrorType",
    "ClassifiedError",
    "classify_error",
    "format_error_for_display",
]
