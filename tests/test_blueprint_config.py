"""Tests for Blueprint agent configuration."""
import os
import tempfile
import pytest
from unittest.mock import patch
from dockai.utils.prompts import (
    PromptConfig,
    load_prompts_from_env,
    load_prompts_from_file,
    load_prompts,
    get_prompt,
    get_instructions,
    set_prompt_config
)

class TestBlueprintConfig:
    """Test configuration specifically for the Blueprint agent."""
    
    def teardown_method(self):
        """Reset global config after each test."""
        set_prompt_config(PromptConfig())

    def test_blueprint_env_vars(self):
        """Test loading blueprint config from environment variables."""
        with patch.dict(os.environ, {
            "DOCKAI_PROMPT_BLUEPRINT": "Custom blueprint prompt",
            "DOCKAI_BLUEPRINT_INSTRUCTIONS": "Custom blueprint instructions"
        }, clear=False):
            config = load_prompts_from_env()
            
            assert config.blueprint == "Custom blueprint prompt"
            assert config.blueprint_instructions == "Custom blueprint instructions"

    def test_blueprint_file_config(self):
        """Test loading blueprint config from .dockai file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[prompt_blueprint]
File blueprint prompt

[instructions_blueprint]
File blueprint instructions
""")
            
            prompts = load_prompts_from_file(tmpdir)
            
            assert prompts["blueprint"] == "File blueprint prompt"
            assert prompts["blueprint_instructions"] == "File blueprint instructions"

    def test_blueprint_precedence(self):
        """Test that env vars override file config for blueprint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[prompt_blueprint]
File prompt
""")
            
            with patch.dict(os.environ, {
                "DOCKAI_PROMPT_BLUEPRINT": "Env prompt"
            }, clear=False):
                config = load_prompts(tmpdir)
                assert config.blueprint == "Env prompt"

    def test_get_blueprint_prompt_with_instructions(self):
        """Test get_prompt for blueprint with instructions."""
        config = PromptConfig(blueprint_instructions="Extra instructions")
        set_prompt_config(config)
        
        prompt = get_prompt("blueprint", "Default prompt")
        
        assert "Default prompt" in prompt
        assert "Extra instructions" in prompt
        assert "ADDITIONAL INSTRUCTIONS" in prompt

    def test_get_blueprint_custom_prompt_ignores_instructions(self):
        """Test that custom blueprint prompt ignores instructions."""
        config = PromptConfig(
            blueprint="Custom prompt",
            blueprint_instructions="Should be ignored"
        )
        set_prompt_config(config)
        
        prompt = get_prompt("blueprint", "Default prompt")
        
        assert prompt == "Custom prompt"
        assert "Should be ignored" not in prompt
