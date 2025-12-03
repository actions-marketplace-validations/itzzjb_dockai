"""Tests for LangSmith integration."""

import os
import logging
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from dockai.cli.main import app

runner = CliRunner()

def test_langsmith_enabled_log():
    """Test that LangSmith enabled log message appears when env var is set."""
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "test"}):
        with patch("dockai.cli.main.create_graph") as mock_create_graph:
            # Mock the graph and workflow
            mock_workflow = MagicMock()
            mock_create_graph.return_value = mock_workflow
            
            # Mock the invoke result
            mock_workflow.invoke.return_value = {
                "validation_result": {"success": True},
                "retry_count": 0,
                "usage_stats": []
            }
            
            # Mock os.path.exists to pass validation
            with patch("os.path.exists", return_value=True):
                # Mock loading prompts
                with patch("dockai.cli.main.load_instructions") as mock_load_instructions:
                    mock_load_instructions.return_value = MagicMock(
                        analyzer_instructions="", 
                        generator_instructions=""
                    )
                    
                    # Mock LLM config loading to avoid API key errors
                    with patch("dockai.core.llm_providers.load_llm_config_from_env") as mock_load_config:
                        mock_config = MagicMock()
                        mock_config.default_provider = "openai" # Use string or enum if needed, but mocking check
                        mock_load_config.return_value = mock_config
                        
                        # Mock the API key check
                        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
                            # Run the command with verbose to ensure logs are captured if needed, 
                            # though INFO logs should show up.
                            # We need to capture logs. Typer runner captures stdout/stderr.
                            # The logger is configured in main.py.
                            
                            # We can patch the logger in main.py
                            with patch("dockai.cli.main.logger") as mock_logger:
                                result = runner.invoke(app, ["build", "/tmp/test"])
                                
                                # Verify the log call
                                mock_logger.info.assert_any_call("LangSmith tracing enabled")

def test_langsmith_metadata_passed():
    """Test that metadata is passed to workflow.invoke for LangSmith."""
    with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "test", "OPENAI_API_KEY": "test"}):
        with patch("dockai.cli.main.create_graph") as mock_create_graph:
            mock_workflow = MagicMock()
            mock_create_graph.return_value = mock_workflow
            
            mock_workflow.invoke.return_value = {
                "validation_result": {"success": True},
                "retry_count": 0,
                "usage_stats": []
            }
            
            with patch("os.path.exists", return_value=True):
                with patch("dockai.cli.main.load_instructions") as mock_load_instructions:
                    mock_load_instructions.return_value = MagicMock(
                        analyzer_instructions="", 
                        generator_instructions=""
                    )
                    
                    with patch("dockai.core.llm_providers.load_llm_config_from_env") as mock_load_config:
                        mock_config = MagicMock()
                        mock_config.default_provider = "openai"
                        mock_load_config.return_value = mock_config
                        
                        runner.invoke(app, ["build", "/tmp/test", "--verbose"])
                        
                        # Verify invoke was called with config containing metadata
                        args, kwargs = mock_workflow.invoke.call_args
                        config = kwargs.get("config", {})
                        assert "metadata" in config
                        assert config["metadata"]["project_path"] == "/tmp/test"
                        assert config["metadata"]["verbose"] is True
