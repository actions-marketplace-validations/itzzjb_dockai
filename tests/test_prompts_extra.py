import os
import tempfile

from dockai.utils import prompts
from dockai.utils.prompts import PromptConfig


def test_load_prompts_merges_file_and_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(prompts, "load_prompts_from_env", lambda: PromptConfig())
        monkeypatch.setattr(prompts, "load_prompts_from_file", lambda path: {"analyzer": "file-analyzer"})

        result = prompts.load_prompts(tmpdir)

        assert result.analyzer == "file-analyzer"


def test_get_prompt_appends_instructions_when_default(monkeypatch):
    cfg = PromptConfig(generator_instructions="follow instructions")
    prompts.set_prompt_config(cfg)

    combined = prompts.get_prompt("generator", "BASE")

    assert combined.startswith("BASE")
    assert "ADDITIONAL INSTRUCTIONS" in combined
    assert "follow instructions" in combined


def test_get_prompt_uses_custom_without_instructions(monkeypatch):
    cfg = PromptConfig(generator="custom", generator_instructions="ignore me")
    prompts.set_prompt_config(cfg)

    combined = prompts.get_prompt("generator", "BASE")

    assert combined == "custom"
    assert "ignore me" not in combined


def test_load_prompts_prefers_env_over_file(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("DOCKAI_PROMPT_ANALYZER", "env-override")
        monkeypatch.setattr(prompts, "load_prompts_from_file", lambda path: {"analyzer": "file-value"})

        result = prompts.load_prompts(tmpdir)

        assert result.analyzer == "env-override"


def test_load_prompts_fills_instruction_gap(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.delenv("DOCKAI_GENERATOR_INSTRUCTIONS", raising=False)
        monkeypatch.setattr(
            prompts,
            "load_prompts_from_file",
            lambda path: {"generator_instructions": "file-gen"},
        )
        monkeypatch.setattr(prompts, "load_prompts_from_env", lambda: PromptConfig())

        result = prompts.load_prompts(tmpdir)

        assert result.generator_instructions == "file-gen"
