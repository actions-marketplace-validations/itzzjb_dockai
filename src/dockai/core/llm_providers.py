"""
DockAI LLM Providers Module.

This module provides a unified interface for creating LLM instances across
multiple providers (OpenAI, Azure OpenAI, Google Gemini, Anthropic). It enables users
to configure different models for each AI agent in the DockAI workflow.

Supported Providers:
- openai: OpenAI API (GPT-4, GPT-4o, GPT-4o-mini, etc.)
- azure: Azure OpenAI Service
- gemini: Google Gemini (Gemini Pro, Gemini 1.5 Pro, etc.)
- anthropic: Anthropic Claude (Claude 3.5 Sonnet, Claude 3 Opus, etc.)

Configuration is done via environment variables:
- DOCKAI_LLM_PROVIDER: Default provider (openai, azure, gemini, anthropic)
- DOCKAI_MODEL_<AGENT>: Model name for each agent
- Provider-specific credentials (OPENAI_API_KEY, AZURE_OPENAI_*, GOOGLE_API_KEY, ANTHROPIC_API_KEY)

Per-Agent Model Configuration:
- DOCKAI_MODEL_ANALYZER: Model for the analyzer agent
- DOCKAI_MODEL_PLANNER: Model for the planner agent
- DOCKAI_MODEL_GENERATOR: Model for the generator agent
- DOCKAI_MODEL_GENERATOR_ITERATIVE: Model for iterative generation
- DOCKAI_MODEL_REVIEWER: Model for the security reviewer
- DOCKAI_MODEL_REFLECTOR: Model for failure reflection
- DOCKAI_MODEL_HEALTH_DETECTOR: Model for health endpoint detection
- DOCKAI_MODEL_READINESS_DETECTOR: Model for readiness pattern detection
- DOCKAI_MODEL_ERROR_ANALYZER: Model for error classification
- DOCKAI_MODEL_ITERATIVE_IMPROVER: Model for iterative improvement
"""

import os
import logging
from typing import Optional, Any, Literal
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("dockai")


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: {
        "fast": "gpt-4o-mini",      # Fast, cost-effective model for analysis
        "powerful": "gpt-4o",        # Powerful model for generation/reflection
    },
    LLMProvider.AZURE: {
        "fast": "gpt-4o-mini",       # Azure deployment name for fast model
        "powerful": "gpt-4o",         # Azure deployment name for powerful model
    },
    LLMProvider.GEMINI: {
        "fast": "gemini-1.5-flash",  # Fast Gemini model
        "powerful": "gemini-1.5-pro", # Powerful Gemini model
    },
    LLMProvider.ANTHROPIC: {
        "fast": "claude-3-5-haiku-latest",   # Fast Claude model
        "powerful": "claude-sonnet-4-20250514", # Powerful Claude model
    },
}


# Agent to model type mapping (which agents need fast vs powerful models)
AGENT_MODEL_TYPE = {
    "analyzer": "fast",
    "planner": "fast",
    "generator": "powerful",
    "generator_iterative": "powerful",
    "reviewer": "fast",
    "reflector": "powerful",
    "health_detector": "fast",
    "readiness_detector": "fast",
    "error_analyzer": "fast",
    "iterative_improver": "powerful",
}


@dataclass
class LLMConfig:
    """
    Configuration for LLM provider and per-agent model settings.
    
    Attributes:
        provider: The LLM provider to use (openai, azure, gemini)
        models: Dictionary mapping agent names to model names
        temperature: Default temperature for LLM calls
        
    Azure-specific attributes:
        azure_endpoint: Azure OpenAI endpoint URL
        azure_api_version: Azure OpenAI API version
        azure_deployment_map: Mapping of model names to Azure deployment names
        
    Gemini-specific attributes:
        google_project: Google Cloud project ID (optional)
    """
    provider: LLMProvider = LLMProvider.OPENAI
    
    # Per-agent model configuration
    models: dict = field(default_factory=dict)
    
    # General settings
    temperature: float = 0.0
    
    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_api_version: str = "2024-02-15-preview"
    azure_deployment_map: dict = field(default_factory=dict)
    
    # Gemini-specific settings
    google_project: Optional[str] = None


# Global LLM configuration instance
_llm_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """
    Returns the global LLM configuration.
    
    If not initialized, creates a default configuration from environment variables.
    
    Returns:
        LLMConfig: The current LLM configuration.
    """
    global _llm_config
    if _llm_config is None:
        _llm_config = load_llm_config_from_env()
    return _llm_config


def set_llm_config(config: LLMConfig) -> None:
    """
    Sets the global LLM configuration.
    
    Args:
        config (LLMConfig): The LLM configuration to set.
    """
    global _llm_config
    _llm_config = config


def load_llm_config_from_env() -> LLMConfig:
    """
    Loads LLM configuration from environment variables.
    
    Environment Variables:
        DOCKAI_LLM_PROVIDER: Provider name (openai, azure, gemini)
        DOCKAI_MODEL_<AGENT>: Model for specific agent
        MODEL_ANALYZER / MODEL_GENERATOR: Legacy model env vars
        
        Azure-specific:
        AZURE_OPENAI_ENDPOINT: Azure endpoint URL
        AZURE_OPENAI_API_VERSION: API version
        AZURE_OPENAI_DEPLOYMENT_<MODEL>: Deployment name mapping
        
        Gemini-specific:
        GOOGLE_CLOUD_PROJECT: Google Cloud project ID
    
    Returns:
        LLMConfig: Configuration loaded from environment.
    """
    # Determine provider
    provider_str = os.getenv("DOCKAI_LLM_PROVIDER", "openai").lower()
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        logger.warning(f"Unknown provider '{provider_str}', defaulting to OpenAI")
        provider = LLMProvider.OPENAI
    
    # Load per-agent model configuration
    models = {}
    
    # Map of agent names to their environment variable names
    agent_env_map = {
        "analyzer": "DOCKAI_MODEL_ANALYZER",
        "planner": "DOCKAI_MODEL_PLANNER", 
        "generator": "DOCKAI_MODEL_GENERATOR",
        "generator_iterative": "DOCKAI_MODEL_GENERATOR_ITERATIVE",
        "reviewer": "DOCKAI_MODEL_REVIEWER",
        "reflector": "DOCKAI_MODEL_REFLECTOR",
        "health_detector": "DOCKAI_MODEL_HEALTH_DETECTOR",
        "readiness_detector": "DOCKAI_MODEL_READINESS_DETECTOR",
        "error_analyzer": "DOCKAI_MODEL_ERROR_ANALYZER",
        "iterative_improver": "DOCKAI_MODEL_ITERATIVE_IMPROVER",
    }
    
    # Load models from environment
    for agent, env_var in agent_env_map.items():
        model = os.getenv(env_var)
        if model:
            models[agent] = model
    
    # Support legacy MODEL_ANALYZER and MODEL_GENERATOR env vars
    legacy_analyzer = os.getenv("MODEL_ANALYZER")
    legacy_generator = os.getenv("MODEL_GENERATOR")
    
    if legacy_analyzer and "analyzer" not in models:
        models["analyzer"] = legacy_analyzer
        # Also use for other "fast" agents if not specified
        for agent, model_type in AGENT_MODEL_TYPE.items():
            if model_type == "fast" and agent not in models:
                models[agent] = legacy_analyzer
                
    if legacy_generator and "generator" not in models:
        models["generator"] = legacy_generator
        # Also use for other "powerful" agents if not specified
        for agent, model_type in AGENT_MODEL_TYPE.items():
            if model_type == "powerful" and agent not in models:
                models[agent] = legacy_generator
    
    # Load Azure-specific settings
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    # Load Azure deployment mappings
    azure_deployment_map = {}
    for key, value in os.environ.items():
        if key.startswith("AZURE_OPENAI_DEPLOYMENT_"):
            model_name = key.replace("AZURE_OPENAI_DEPLOYMENT_", "").lower().replace("_", "-")
            azure_deployment_map[model_name] = value
    
    # Load Gemini-specific settings
    google_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    return LLMConfig(
        provider=provider,
        models=models,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
        azure_deployment_map=azure_deployment_map,
        google_project=google_project,
    )


def get_model_for_agent(agent_name: str, config: Optional[LLMConfig] = None) -> str:
    """
    Gets the configured model name for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., 'analyzer', 'generator')
        config: Optional LLM config, uses global if not provided
        
    Returns:
        str: The model name to use for this agent
    """
    if config is None:
        config = get_llm_config()
    
    # Check if agent has a specific model configured
    if agent_name in config.models:
        return config.models[agent_name]
    
    # Fall back to default model for this agent's type
    model_type = AGENT_MODEL_TYPE.get(agent_name, "fast")
    return DEFAULT_MODELS[config.provider][model_type]


def create_llm(
    agent_name: str,
    temperature: float = 0.0,
    config: Optional[LLMConfig] = None,
    **kwargs
) -> Any:
    """
    Creates an LLM instance for the specified agent.
    
    This is the main factory function that creates the appropriate LLM
    based on the provider configuration.
    
    Args:
        agent_name: Name of the agent (e.g., 'analyzer', 'generator', 'reviewer')
        temperature: Temperature for generation (0.0 = deterministic)
        config: Optional LLM config, uses global if not provided
        **kwargs: Additional arguments passed to the LLM constructor
        
    Returns:
        A LangChain chat model instance (ChatOpenAI, AzureChatOpenAI, or ChatGoogleGenerativeAI)
        
    Raises:
        ValueError: If the provider is not supported or credentials are missing
    """
    if config is None:
        config = get_llm_config()
    
    model_name = get_model_for_agent(agent_name, config)
    
    logger.debug(f"Creating LLM for agent '{agent_name}': provider={config.provider.value}, model={model_name}")
    
    if config.provider == LLMProvider.OPENAI:
        return _create_openai_llm(model_name, temperature, **kwargs)
    elif config.provider == LLMProvider.AZURE:
        return _create_azure_llm(model_name, temperature, config, **kwargs)
    elif config.provider == LLMProvider.GEMINI:
        return _create_gemini_llm(model_name, temperature, config, **kwargs)
    elif config.provider == LLMProvider.ANTHROPIC:
        return _create_anthropic_llm(model_name, temperature, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")


def _create_openai_llm(model_name: str, temperature: float, **kwargs) -> Any:
    """Creates an OpenAI LLM instance."""
    from langchain_openai import ChatOpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs
    )


def _create_azure_llm(model_name: str, temperature: float, config: LLMConfig, **kwargs) -> Any:
    """Creates an Azure OpenAI LLM instance."""
    from langchain_openai import AzureChatOpenAI
    
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required for Azure provider")
    
    if not config.azure_endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required for Azure provider")
    
    # Get deployment name from mapping or use model name
    deployment_name = config.azure_deployment_map.get(model_name, model_name)
    
    return AzureChatOpenAI(
        azure_deployment=deployment_name,
        azure_endpoint=config.azure_endpoint,
        api_version=config.azure_api_version,
        api_key=api_key,
        temperature=temperature,
        **kwargs
    )


def _create_gemini_llm(model_name: str, temperature: float, config: LLMConfig, **kwargs) -> Any:
    """Creates a Google Gemini LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini provider")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        **kwargs
    )


def _create_anthropic_llm(model_name: str, temperature: float, **kwargs) -> Any:
    """Creates an Anthropic Claude LLM instance."""
    from langchain_anthropic import ChatAnthropic
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic provider")
    
    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        **kwargs
    )


def get_provider_info() -> dict:
    """
    Returns information about the current LLM provider configuration.
    
    Useful for logging and debugging.
    
    Returns:
        dict: Provider information including name, models, and configuration status
    """
    config = get_llm_config()
    
    info = {
        "provider": config.provider.value,
        "models": {},
        "credentials_configured": False,
    }
    
    # Check credentials
    if config.provider == LLMProvider.OPENAI:
        info["credentials_configured"] = bool(os.getenv("OPENAI_API_KEY"))
    elif config.provider == LLMProvider.AZURE:
        info["credentials_configured"] = bool(
            os.getenv("AZURE_OPENAI_API_KEY") and config.azure_endpoint
        )
        info["azure_endpoint"] = config.azure_endpoint
        info["azure_api_version"] = config.azure_api_version
    elif config.provider == LLMProvider.GEMINI:
        info["credentials_configured"] = bool(os.getenv("GOOGLE_API_KEY"))
    elif config.provider == LLMProvider.ANTHROPIC:
        info["credentials_configured"] = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    # Get model for each agent
    for agent in AGENT_MODEL_TYPE.keys():
        info["models"][agent] = get_model_for_agent(agent, config)
    
    return info


def log_provider_info() -> None:
    """Logs the current LLM provider configuration."""
    info = get_provider_info()
    
    logger.info(f"LLM Provider: {info['provider'].upper()}")
    
    if not info["credentials_configured"]:
        logger.warning(f"Credentials not configured for {info['provider']} provider!")
    
    # Group models by unique value for cleaner output
    model_groups = {}
    for agent, model in info["models"].items():
        if model not in model_groups:
            model_groups[model] = []
        model_groups[model].append(agent)
    
    logger.info("Model Configuration:")
    for model, agents in model_groups.items():
        logger.info(f"  {model}: {', '.join(agents)}")
