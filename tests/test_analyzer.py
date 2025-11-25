import json
import os
from unittest.mock import patch, MagicMock, call
from dockai.analyzer import analyze_repo_needs
from dockai.schemas import AnalysisResult

@patch("dockai.analyzer.ChatOpenAI")
@patch("dockai.analyzer.TokenUsageCallback")
def test_analyze_repo_needs_basic(mock_callback_class, mock_chat_openai):
    """Test basic repository analysis"""
    # Setup mock result
    mock_result = AnalysisResult(
        thought_process="This is a Python Flask application",
        stack="Python 3.11 with Flask framework",
        project_type="service",
        files_to_read=["requirements.txt", "app.py", "config.py"],
        build_command="pip install -r requirements.txt",
        start_command="python app.py",
        suggested_base_image="python",
        health_endpoint={"path": "/health", "port": 5000},
        recommended_wait_time=5
    )
    
    # Setup mock chain
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    # Simulate the | operator creating a chain
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    # Setup mock callback
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {
        "total_tokens": 500,
        "prompt_tokens": 300,
        "completion_tokens": 200
    }
    mock_callback_class.return_value = mock_callback
    
    # Run function
    result, usage = analyze_repo_needs([
        "requirements.txt",
        "app.py",
        "config.py",
        "README.md"
    ])
    
    # Assertions
    assert result.stack == "Python 3.11 with Flask framework"
    assert result.project_type == "service"
    assert "requirements.txt" in result.files_to_read
    assert result.suggested_base_image == "python"
    assert result.health_endpoint["path"] == "/health"
    assert usage["total_tokens"] == 500

@patch("dockai.analyzer.ChatOpenAI")
@patch("dockai.analyzer.TokenUsageCallback")
def test_analyze_repo_needs_with_custom_instructions(mock_callback_class, mock_chat_openai):
    """Test analysis with custom instructions"""
    mock_result = AnalysisResult(
        thought_process="Node.js application with Express",
        stack="Node.js 20 with Express",
        project_type="service",
        files_to_read=["package.json", "package-lock.json", "server.js"],
        build_command="npm ci",
        start_command="npm start",
        suggested_base_image="node",
        health_endpoint=None,
        recommended_wait_time=3
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 400}
    mock_callback_class.return_value = mock_callback
    
    # Run with custom instructions
    custom_instructions = "Always include package-lock.json"
    result, usage = analyze_repo_needs(
        ["package.json", "server.js"],
        custom_instructions=custom_instructions
    )
    
    # Verify result
    assert result.stack == "Node.js 20 with Express"
    # Verify invoke was called (custom instructions passed via chain)
    assert mock_chain.invoke.called

@patch("dockai.analyzer.ChatOpenAI")
@patch("dockai.analyzer.TokenUsageCallback")
def test_analyze_repo_needs_script_type(mock_callback_class, mock_chat_openai):
    """Test analysis of a script (not a service)"""
    mock_result = AnalysisResult(
        thought_process="This is a Python CLI script",
        stack="Python 3.11",
        project_type="script",
        files_to_read=["requirements.txt", "cli.py"],
        build_command="pip install -r requirements.txt",
        start_command="python cli.py",
        suggested_base_image="python",
        health_endpoint=None,
        recommended_wait_time=3
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 300}
    mock_callback_class.return_value = mock_callback
    
    result, usage = analyze_repo_needs(["cli.py", "requirements.txt"])
    
    assert result.project_type == "script"
    assert result.health_endpoint is None

@patch("dockai.analyzer.ChatOpenAI")
@patch("dockai.analyzer.TokenUsageCallback")
@patch("dockai.analyzer.os.getenv")
def test_analyze_uses_correct_model(mock_getenv, mock_callback_class, mock_chat_openai):
    """Test that analyzer uses MODEL_ANALYZER from env"""
    mock_getenv.side_effect = lambda key, default=None: {
        "MODEL_ANALYZER": "gpt-4o-mini",
        "OPENAI_API_KEY": "test-key"
    }.get(key, default)
    
    mock_result = AnalysisResult(
        thought_process="Test",
        stack="Python",
        project_type="service",
        files_to_read=["app.py"],
        build_command=None,
        start_command=None,
        suggested_base_image="python",
        health_endpoint=None,
        recommended_wait_time=5
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 100}
    mock_callback_class.return_value = mock_callback
    
    analyze_repo_needs(["app.py"])
    
    # Verify ChatOpenAI was initialized with correct model
    mock_chat_openai.assert_called_once()
    call_kwargs = mock_chat_openai.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["api_key"] == "test-key"
    assert call_kwargs["temperature"] == 0
