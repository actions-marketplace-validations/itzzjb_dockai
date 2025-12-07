"""Tests for the prompts module."""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from dockai.utils.prompts import (
    PromptConfig,
    get_prompt_config,
    set_prompt_config,
    load_prompts_from_env,
    load_prompts_from_file,
    load_prompts,
    get_prompt,
    get_instructions,
)


class TestPromptConfig:
    """Test PromptConfig dataclass."""
    
    def test_default_config(self):
        """Test default config has all None values."""
        config = PromptConfig()
        assert config.analyzer is None
        assert config.blueprint is None
        assert config.generator is None
        assert config.reviewer is None
        assert config.analyzer_instructions is None
        assert config.generator_instructions is None
    
    def test_custom_config(self):
        """Test config with custom values."""
        config = PromptConfig(
            analyzer="custom analyzer",
            generator_instructions="custom instructions"
        )
        assert config.analyzer == "custom analyzer"
        assert config.generator_instructions == "custom instructions"
        assert config.blueprint is None


class TestPromptConfigGlobal:
    """Test global prompt config management."""
    
    def teardown_method(self):
        """Reset global config after each test."""
        set_prompt_config(PromptConfig())
    
    def test_get_prompt_config_default(self):
        """Test get_prompt_config returns default if not set."""
        set_prompt_config(PromptConfig())
        config = get_prompt_config()
        assert isinstance(config, PromptConfig)
    
    def test_set_prompt_config(self):
        """Test setting global config."""
        custom_config = PromptConfig(analyzer="test")
        set_prompt_config(custom_config)
        
        config = get_prompt_config()
        assert config.analyzer == "test"


class TestLoadPromptsFromEnv:
    """Test loading prompts from environment variables."""
    
    @patch.dict(os.environ, {
        "DOCKAI_PROMPT_ANALYZER": "env analyzer prompt",
        "DOCKAI_ANALYZER_INSTRUCTIONS": "env analyzer instructions"
    }, clear=False)
    def test_load_from_env(self):
        """Test loading prompts from env vars."""
        config = load_prompts_from_env()
        
        assert config.analyzer == "env analyzer prompt"
        assert config.analyzer_instructions == "env analyzer instructions"
        assert config.blueprint is None
    
    @patch.dict(os.environ, {
        "DOCKAI_PROMPT_GENERATOR": "gen prompt",
        "DOCKAI_GENERATOR_INSTRUCTIONS": "gen instructions",
        "DOCKAI_REVIEWER_INSTRUCTIONS": "review instructions"
    }, clear=False)
    def test_load_multiple_from_env(self):
        """Test loading multiple prompts from env."""
        config = load_prompts_from_env()
        
        assert config.generator == "gen prompt"
        assert config.generator_instructions == "gen instructions"
        assert config.reviewer_instructions == "review instructions"


class TestLoadPromptsFromFile:
    """Test loading prompts from .dockai file."""
    
    def test_load_instructions_section(self):
        """Test loading [instructions_*] sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[instructions_analyzer]
Use Python 3.11
Check for FastAPI

[instructions_generator]
Use Alpine base image
Run as non-root
""")
            
            prompts = load_prompts_from_file(tmpdir)
            
            assert "analyzer_instructions" in prompts
            assert "Python 3.11" in prompts["analyzer_instructions"]
            assert "generator_instructions" in prompts
            assert "Alpine" in prompts["generator_instructions"]
    
    def test_load_prompt_section(self):
        """Test loading [prompt_*] sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[prompt_analyzer]
You are a custom analyzer.
Analyze the project.

[prompt_blueprint]
You are a custom blueprint agent.
""")
            
            prompts = load_prompts_from_file(tmpdir)
            
            assert "analyzer" in prompts
            assert "custom analyzer" in prompts["analyzer"]
            assert "blueprint" in prompts
            assert "custom blueprint agent" in prompts["blueprint"]
    
    def test_load_legacy_sections(self):
        """Test loading legacy [analyzer] and [generator] sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[analyzer]
Legacy analyzer instructions

[generator]
Legacy generator instructions
""")
            
            prompts = load_prompts_from_file(tmpdir)
            
            # Legacy sections map to instructions
            assert "analyzer_instructions" in prompts
            assert "Legacy analyzer" in prompts["analyzer_instructions"]
            assert "generator_instructions" in prompts
            assert "Legacy generator" in prompts["generator_instructions"]
    
    def test_file_not_exists(self):
        """Test handling when .dockai file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts = load_prompts_from_file(tmpdir)
            assert prompts == {}
    
    def test_comments_ignored(self):
        """Test that comment lines are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[instructions_analyzer]
# This is a comment
Use Python
# Another comment
Check dependencies
""")
            
            prompts = load_prompts_from_file(tmpdir)
            
            assert "# This is a comment" not in prompts["analyzer_instructions"]
            assert "Use Python" in prompts["analyzer_instructions"]
            assert "Check dependencies" in prompts["analyzer_instructions"]


class TestLoadPrompts:
    """Test the main load_prompts function."""
    
    def test_env_takes_precedence(self):
        """Test that env vars take precedence over file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[instructions_analyzer]
File instructions
""")
            
            with patch.dict(os.environ, {
                "DOCKAI_ANALYZER_INSTRUCTIONS": "Env instructions"
            }, clear=False):
                config = load_prompts(tmpdir)
                
                # Env should win
                assert config.analyzer_instructions == "Env instructions"
    
    def test_file_fills_gaps(self):
        """Test that file prompts fill in when env not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockai_file = os.path.join(tmpdir, ".dockai")
            with open(dockai_file, "w") as f:
                f.write("""
[instructions_analyzer]
File analyzer

[instructions_generator]
File generator
""")
            
            with patch.dict(os.environ, {
                "DOCKAI_ANALYZER_INSTRUCTIONS": "Env analyzer"
            }, clear=False):
                # Clear generator env var if it exists
                os.environ.pop("DOCKAI_GENERATOR_INSTRUCTIONS", None)
                
                config = load_prompts(tmpdir)
                
                assert config.analyzer_instructions == "Env analyzer"
                assert config.generator_instructions == "File generator"


class TestGetPrompt:
    """Test get_prompt function."""
    
    def teardown_method(self):
        """Reset global config after each test."""
        set_prompt_config(PromptConfig())
    
    def test_returns_default_when_no_custom(self):
        """Test returns default prompt when no custom set."""
        set_prompt_config(PromptConfig())
        
        result = get_prompt("analyzer", "Default prompt")
        assert result == "Default prompt"
    
    def test_returns_custom_prompt(self):
        """Test returns custom prompt when set."""
        config = PromptConfig(analyzer="Custom prompt")
        set_prompt_config(config)
        
        result = get_prompt("analyzer", "Default prompt")
        assert result == "Custom prompt"
    
    def test_appends_instructions_to_default(self):
        """Test instructions are appended to default prompt."""
        config = PromptConfig(analyzer_instructions="Extra instructions")
        set_prompt_config(config)
        
        result = get_prompt("analyzer", "Default prompt")
        
        assert "Default prompt" in result
        assert "ADDITIONAL INSTRUCTIONS" in result
        assert "Extra instructions" in result
    
    def test_instructions_not_appended_to_custom(self):
        """Test instructions NOT appended when custom prompt set."""
        config = PromptConfig(
            analyzer="Custom prompt",
            analyzer_instructions="Should not appear"
        )
        set_prompt_config(config)
        
        result = get_prompt("analyzer", "Default prompt")
        
        assert result == "Custom prompt"
        assert "Should not appear" not in result


class TestGetInstructions:
    """Test get_instructions function."""
    
    def teardown_method(self):
        """Reset global config after each test."""
        set_prompt_config(PromptConfig())
    
    def test_returns_none_when_not_set(self):
        """Test returns None when no instructions set."""
        set_prompt_config(PromptConfig())
        
        result = get_instructions("analyzer")
        assert result is None
    
    def test_returns_instructions_when_set(self):
        """Test returns instructions when set."""
        config = PromptConfig(generator_instructions="Gen instructions")
        set_prompt_config(config)
        
        result = get_instructions("generator")
        assert result == "Gen instructions"
