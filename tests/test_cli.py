import contextlib
import os
import sys
from pathlib import Path

import pytest
import typer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dockai.cli import main
from dockai.core import llm_providers
from dockai.core.llm_providers import LLMConfig, LLMProvider
from dockai.utils.prompts import PromptConfig


class DummyWorkflow:
    """Minimal workflow stub used to capture invocations."""

    def __init__(self, result):
        self.result = result
        self.invocations = []

    def invoke(self, initial_state, config):
        self.invocations.append((initial_state, config))
        return self.result


def test_load_instructions_sets_prompt_config(monkeypatch):
    prompt_config = PromptConfig(analyzer="custom")
    set_calls = []

    monkeypatch.setattr(main, "load_prompts", lambda path: prompt_config)
    monkeypatch.setattr(main, "set_prompt_config", lambda config: set_calls.append(config))

    result = main.load_instructions("/tmp/project")

    assert result is prompt_config
    assert set_calls == [prompt_config]


def test_build_exits_on_missing_path(monkeypatch, tmp_path):
    errors = []
    monkeypatch.setattr(main, "init_tracing", lambda service_name="dockai": None)
    monkeypatch.setattr(main.ui, "print_error", lambda title, msg, details=None: errors.append((title, msg, details)))

    with pytest.raises(typer.Exit) as exc:
        main.build(str(tmp_path / "missing"))

    assert exc.value.exit_code == 1
    assert errors and "does not exist" in errors[0][1]


def test_build_requires_api_key_when_openai(monkeypatch, tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(main, "init_tracing", lambda service_name="dockai": None)
    monkeypatch.setattr(llm_providers, "load_llm_config_from_env", lambda: LLMConfig(default_provider=LLMProvider.OPENAI, models={}))
    monkeypatch.setattr(llm_providers, "set_llm_config", lambda config: None)
    monkeypatch.setattr(llm_providers, "log_provider_info", lambda: None)

    errors = []
    monkeypatch.setattr(main.ui, "print_error", lambda title, msg, details=None: errors.append((title, msg, details)))

    with pytest.raises(typer.Exit) as exc:
        main.build(str(project_dir))

    assert exc.value.exit_code == 1
    assert errors and "OPENAI_API_KEY" in errors[0][1]


def test_build_runs_workflow_and_shows_summary(monkeypatch, tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    prompt_config = PromptConfig(analyzer_instructions="a")

    start_calls = []
    end_calls = []
    shutdown_calls = []
    display_calls = []

    monkeypatch.setattr(main, "init_tracing", lambda service_name="dockai": start_calls.append(service_name))
    monkeypatch.setattr(main, "record_workflow_start", lambda path, meta: start_calls.append((path, meta)))
    monkeypatch.setattr(main, "record_workflow_end", lambda success, retries, tokens: end_calls.append((success, retries, tokens)))
    monkeypatch.setattr(main, "shutdown_tracing", lambda: shutdown_calls.append(True))
    monkeypatch.setattr(llm_providers, "load_llm_config_from_env", lambda: LLMConfig(default_provider=LLMProvider.OPENAI, models={}))
    monkeypatch.setattr(llm_providers, "set_llm_config", lambda config: None)
    monkeypatch.setattr(llm_providers, "log_provider_info", lambda: None)
    monkeypatch.setattr(main, "load_instructions", lambda path: prompt_config)
    monkeypatch.setattr(main.ui, "get_status_spinner", lambda message: contextlib.nullcontext())
    monkeypatch.setattr(main.ui, "display_summary", lambda state, output: display_calls.append((state, output)))

    final_state = {
        "validation_result": {"success": True, "message": "ok"},
        "retry_history": [{"lesson_learned": "stub"}],
        "usage_stats": [{"total_tokens": 5, "stage": "analyze"}],
        "retry_count": 1,
        "current_plan": {
            "base_image_strategy": "use-slim-base",
            "use_multi_stage": True,
        },
    }
    workflow = DummyWorkflow(final_state)
    monkeypatch.setattr(main, "create_graph", lambda: workflow)

    main.build(str(project_dir))

    assert workflow.invocations, "workflow.invoke should be called"
    assert display_calls and display_calls[0][0] is final_state
    assert end_calls and end_calls[0][0] is True
    assert shutdown_calls == [True]


def test_build_failure_displays_failure_and_exits(monkeypatch, tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    prompt_config = PromptConfig()

    end_calls = []
    shutdown_calls = []
    failure_calls = []

    monkeypatch.setattr(main, "init_tracing", lambda service_name="dockai": None)
    monkeypatch.setattr(main, "record_workflow_start", lambda path, meta: None)
    monkeypatch.setattr(main, "record_workflow_end", lambda success, retries, tokens: end_calls.append((success, retries, tokens)))
    monkeypatch.setattr(main, "shutdown_tracing", lambda: shutdown_calls.append(True))
    monkeypatch.setattr(llm_providers, "load_llm_config_from_env", lambda: LLMConfig(default_provider=LLMProvider.OPENAI, models={}))
    monkeypatch.setattr(llm_providers, "set_llm_config", lambda config: None)
    monkeypatch.setattr(llm_providers, "log_provider_info", lambda: None)
    monkeypatch.setattr(main, "load_instructions", lambda path: prompt_config)
    monkeypatch.setattr(main.ui, "get_status_spinner", lambda message: contextlib.nullcontext())
    monkeypatch.setattr(main.ui, "display_failure", lambda state: failure_calls.append(state))

    final_state = {
        "validation_result": {"success": False, "message": "invalid"},
        "retry_count": 2,
        "max_retries": 3,
        "retry_history": [],
        "usage_stats": [{"total_tokens": 3, "stage": "generate"}],
    }
    workflow = DummyWorkflow(final_state)
    monkeypatch.setattr(main, "create_graph", lambda: workflow)

    with pytest.raises(typer.Exit) as exc:
        main.build(str(project_dir))

    assert exc.value.exit_code == 1
    assert failure_calls and failure_calls[0] is final_state
    assert end_calls and end_calls[0][0] is False
    assert shutdown_calls == [True]
