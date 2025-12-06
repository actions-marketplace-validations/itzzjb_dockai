import os
import sys
import types

import pytest

from dockai.core import llm_providers
from dockai.core.llm_providers import LLMProvider, get_model_for_agent, load_llm_config_from_env, create_llm


@pytest.fixture(autouse=True)
def reset_llm_config():
    original = llm_providers._llm_config
    llm_providers._llm_config = None
    yield
    llm_providers._llm_config = original


def test_unknown_provider_defaults_to_openai(monkeypatch):
    monkeypatch.setenv("DOCKAI_LLM_PROVIDER", "not-a-provider")
    config = load_llm_config_from_env()
    assert config.default_provider == LLMProvider.OPENAI


def test_agent_specific_model_override(monkeypatch):
    monkeypatch.setenv("DOCKAI_MODEL_ANALYZER", "custom-model")
    config = load_llm_config_from_env()
    assert get_model_for_agent("analyzer", config) == "custom-model"


def test_azure_deployment_map_parsing(monkeypatch):
    monkeypatch.setenv("DOCKAI_LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_GPT_4O_MINI", "deploy-4o")
    config = load_llm_config_from_env()
    assert config.azure_deployment_map["gpt-4o-mini"] == "deploy-4o"
    assert config.azure_api_version == "2024-02-15-preview"


def test_caching_flag_disable(monkeypatch):
    monkeypatch.setenv("DOCKAI_LLM_CACHING", "false")
    config = load_llm_config_from_env()
    assert config.enable_caching is False


def test_create_llm_routes_with_provider_prefix(monkeypatch):
    # Force provider prefix to switch to Gemini even though default is OpenAI
    monkeypatch.setenv("DOCKAI_LLM_PROVIDER", "openai")
    monkeypatch.setenv("DOCKAI_MODEL_ANALYZER", "gemini/gemini-1.5-pro")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("DOCKAI_LLM_CACHING", "false")  # avoid cache init path

    dummy_return = object()

    class DummyChatGemini:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def __repr__(self):
            return "DummyChatGemini"

    fake_module = types.ModuleType("langchain_google_genai")
    fake_module.ChatGoogleGenerativeAI = lambda **kwargs: DummyChatGemini(**kwargs)
    monkeypatch.setitem(sys.modules, "langchain_google_genai", fake_module)

    config = load_llm_config_from_env()
    result = create_llm("analyzer", config=config)

    assert isinstance(result, DummyChatGemini)
    assert result.kwargs["model"] == "gemini-1.5-pro"
    assert result.kwargs["temperature"] == 0.0
