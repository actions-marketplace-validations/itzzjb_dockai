import os
import pytest
from unittest.mock import patch, MagicMock
from dockai.core.llm_providers import (
    LLMProvider,
    LLMConfig,
    load_llm_config_from_env,
    create_llm,
    get_provider_info,
    _llm_config
)

@pytest.fixture
def clean_env():
    """Clean environment variables before and after tests."""
    # Save original env
    original_env = dict(os.environ)
    
    # Clear relevant env vars
    keys_to_clear = [
        "DOCKAI_LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "DOCKAI_MODEL_ANALYZER",
        "DOCKAI_MODEL_GENERATOR",
        "MODEL_ANALYZER",
        "MODEL_GENERATOR"
    ]
    for key in keys_to_clear:
        if key in os.environ:
            del os.environ[key]
            
    yield
    
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)

def test_load_ollama_config(clean_env):
    """Test loading Ollama configuration from environment."""
    os.environ["DOCKAI_LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_BASE_URL"] = "http://custom-ollama:11434"
    
    config = load_llm_config_from_env()
    
    assert config.default_provider == LLMProvider.OLLAMA
    assert config.ollama_base_url == "http://custom-ollama:11434"

def test_load_ollama_config_default(clean_env):
    """Test loading Ollama configuration with defaults."""
    os.environ["DOCKAI_LLM_PROVIDER"] = "ollama"
    
    config = load_llm_config_from_env()
    
    assert config.default_provider == LLMProvider.OLLAMA
    assert config.ollama_base_url == "http://localhost:11434"

@patch("dockai.utils.ollama_docker.is_ollama_available", return_value=True)
@patch("langchain_ollama.ChatOllama")
def test_create_ollama_llm(mock_chat_ollama, mock_is_available, clean_env):
    """Test creating an Ollama LLM instance."""
    os.environ["DOCKAI_LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_BASE_URL"] = "http://test-url:11434"
    
    # Reset global config to force reload
    import dockai.core.llm_providers
    dockai.core.llm_providers._llm_config = None
    
    llm = create_llm("analyzer", temperature=0.5)
    
    mock_chat_ollama.assert_called_once()
    call_kwargs = mock_chat_ollama.call_args.kwargs
    
    assert call_kwargs["base_url"] == "http://test-url:11434"
    assert call_kwargs["temperature"] == 0.5
    # Default model for analyzer is "llama3"
    assert call_kwargs["model"] == "llama3"

def test_get_provider_info_ollama(clean_env):
    """Test provider info for Ollama."""
    os.environ["DOCKAI_LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_BASE_URL"] = "http://info-test:11434"
    
    # Reset global config
    import dockai.core.llm_providers
    dockai.core.llm_providers._llm_config = None
    
    info = get_provider_info()
    
    assert info["default_provider"] == "ollama"
    assert info["credentials_configured"]["ollama"] is True
    assert info["ollama_base_url"] == "http://info-test:11434"

@patch("dockai.utils.ollama_docker.is_ollama_available", return_value=True)
@patch("langchain_openai.ChatOpenAI")
@patch("langchain_ollama.ChatOllama")
def test_mixed_provider_creation(mock_chat_ollama, mock_chat_openai, mock_is_available, clean_env):
    """Test creating LLMs with mixed providers."""
    os.environ["DOCKAI_LLM_PROVIDER"] = "ollama"
    os.environ["DOCKAI_MODEL_ANALYZER"] = "openai/gpt-4o-mini"
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    
    # Reset global config
    import dockai.core.llm_providers
    dockai.core.llm_providers._llm_config = None
    
    # Create analyzer LLM (should be OpenAI)
    llm_analyzer = create_llm("analyzer")
    mock_chat_openai.assert_called_once()
    assert mock_chat_openai.call_args.kwargs["model"] == "gpt-4o-mini"
    
    # Create generator LLM (should be Ollama default)
    llm_generator = create_llm("generator")
    mock_chat_ollama.assert_called_once()
    assert mock_chat_ollama.call_args.kwargs["model"] == "llama3"
