
import pytest
from unittest.mock import patch, MagicMock
import os
from dockai.core.mcp_server import analyze_project, generate_dockerfile_content, validate_dockerfile, run_full_workflow

@pytest.fixture
def mock_file_tree():
    return ["app.py", "requirements.txt"]

@pytest.fixture
def mock_analysis_result():
    mock = MagicMock()
    mock.stack = "Python"
    mock.project_type = "service"
    mock.build_command = "pip install"
    mock.start_command = "python app.py"
    mock.suggested_base_image = "python:3.11"
    mock.files_to_read = ["app.py"]
    return mock

@patch("dockai.core.mcp_server.os.path.exists")
@patch("dockai.core.mcp_server.get_file_tree")
@patch("dockai.core.mcp_server.analyze_repo_needs")
def test_analyze_project(mock_analyze, mock_get_tree, mock_exists, mock_file_tree, mock_analysis_result):
    """Test analyze_project tool"""
    mock_exists.return_value = True
    mock_get_tree.return_value = mock_file_tree
    mock_analyze.return_value = (mock_analysis_result, {})
    
    result = analyze_project("/test/path")
    
    assert "Stack: Python" in result
    assert "Project Type: service" in result
    assert "Build Command: pip install" in result
    
    mock_get_tree.assert_called_once_with("/test/path")
    mock_analyze.assert_called_once()

@patch("dockai.core.mcp_server.os.path.exists")
def test_analyze_project_invalid_path(mock_exists):
    """Test analyze_project with invalid path"""
    mock_exists.return_value = False
    result = analyze_project("/invalid/path")
    assert "Error: Path" in result

@patch("dockai.core.mcp_server.os.path.exists")
@patch("dockai.core.mcp_server.get_file_tree")
@patch("dockai.core.mcp_server.analyze_repo_needs")
@patch("dockai.core.mcp_server.read_critical_files")
@patch("dockai.core.mcp_server.generate_dockerfile")
def test_generate_dockerfile_content(mock_gen, mock_read, mock_analyze, mock_get_tree, mock_exists, mock_analysis_result):
    """Test generate_dockerfile_content tool"""
    mock_exists.return_value = True
    mock_analyze.return_value = (mock_analysis_result, {})
    mock_read.return_value = "content"
    mock_gen.return_value = ("FROM python:3.11", "service", "thought process", {})
    
    result = generate_dockerfile_content("/test/path", instructions="Use Alpine")
    
    assert result == "FROM python:3.11"
    
    mock_analyze.assert_called_once()
    # Verify instructions were passed via AgentContext
    args, kwargs = mock_analyze.call_args
    context = kwargs.get("context")
    assert context is not None
    assert context.custom_instructions == "Use Alpine"

@patch("dockai.core.mcp_server.os.path.exists")
@patch("dockai.core.mcp_server.validate_docker_build_and_run")
@patch("builtins.open", new_callable=MagicMock)
@patch("os.rename")
def test_validate_dockerfile(mock_rename, mock_open, mock_validate, mock_exists):
    """Test validate_dockerfile tool"""
    mock_exists.return_value = True
    mock_validate.return_value = (True, "Success", 100, None)
    
    # Mock file operations context manager
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    
    result = validate_dockerfile("/test/path", "FROM python:3.11")
    
    assert "Validation Success" in result
    mock_validate.assert_called_once()
    
    # Verify it tried to write the file
    mock_open.assert_called()

@patch("dockai.core.mcp_server.os.path.exists")
@patch("dockai.workflow.graph.create_graph")
def test_run_full_workflow(mock_create_graph, mock_exists):
    """Test run_full_workflow tool"""
    mock_exists.return_value = True
    
    # Mock graph app
    mock_app = MagicMock()
    mock_create_graph.return_value = mock_app
    
    # Mock final state
    mock_app.invoke.return_value = {
        "dockerfile_content": "FROM python:3.11",
        "validation_result": {"success": True, "message": "All good"},
        "retry_count": 1
    }
    
    result = run_full_workflow("/test/path", instructions="Optimize")
    
    assert "Workflow Completed" in result
    assert "Status: SUCCESS" in result
    assert "FROM python:3.11" in result
    
    # Verify graph was invoked with correct initial state
    mock_app.invoke.assert_called_once()
    call_args = mock_app.invoke.call_args[0][0]
    assert call_args["path"] == "/test/path"
    assert call_args["config"]["generator_instructions"] == "Optimize"
