"""Tests for the workflow graph module."""
from unittest.mock import patch, MagicMock
from dockai.workflow.graph import should_retry, check_security
from dockai.workflow.nodes import increment_retry, scan_node, analyze_node, read_files_node, generate_node

def test_increment_retry():
    """Test retry counter increment"""
    state = {"retry_count": 0}
    result = increment_retry(state)
    assert result["retry_count"] == 1
    
    state = {"retry_count": 2}
    result = increment_retry(state)
    assert result["retry_count"] == 3

def test_should_retry_on_validation_failure():
    """Test retry logic when validation fails"""
    state = {
        "retry_count": 0,
        "max_retries": 3,
        "validation_result": {"success": False, "message": "Failed"}
    }
    
    result = should_retry(state)
    assert result == "reflect" # Updated expectation: goes to reflect first

def test_should_retry_max_retries_reached():
    """Test that retry stops at max_retries"""
    state = {
        "retry_count": 3,
        "max_retries": 3,
        "validation_result": {"success": False, "message": "Failed"}
    }
    
    result = should_retry(state)
    assert result == "end"

def test_should_retry_on_success():
    """Test that retry ends on success"""
    state = {
        "retry_count": 1,
        "max_retries": 3,
        "validation_result": {"success": True, "message": "Success"}
    }
    
    result = should_retry(state)
    assert result == "end"

def test_should_retry_on_security_error():
    """Test retry on security check failure"""
    state = {
        "retry_count": 0,
        "max_retries": 3,
        "error": "Security check failed",
        "validation_result": None
    }
    
    result = should_retry(state)
    assert result == "reflect" # Updated expectation: goes to reflect first

def test_check_security_passes():
    """Test security check when no errors"""
    state = {"error": None}
    
    result = check_security(state)
    assert result == "validate"

def test_check_security_fails_with_retries():
    """Test security check failure with retries available"""
    state = {
        "error": "Security issue found",
        "retry_count": 0,
        "max_retries": 3
    }
    
    result = check_security(state)
    assert result == "reflect"

def test_check_security_fails_max_retries():
    """Test security check failure at max retries"""
    state = {
        "error": "Security issue found",
        "retry_count": 3,
        "max_retries": 3
    }
    
    result = check_security(state)
    assert result == "end"

@patch("dockai.workflow.nodes.get_file_tree")
def test_scan_node(mock_get_file_tree):
    """Test scan node"""
    mock_get_file_tree.return_value = ["app.py", "requirements.txt"]
    
    state = {"path": "/test/path"}
    result = scan_node(state)
    
    assert result["file_tree"] == ["app.py", "requirements.txt"]
    mock_get_file_tree.assert_called_once_with("/test/path")

@patch("dockai.workflow.nodes.analyze_repo_needs")
def test_analyze_node(mock_analyze):
    """Test analyze node"""
    from dockai.core.schemas import AnalysisResult
    
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
    
    mock_analyze.return_value = (mock_result, {"total_tokens": 500})
    
    state = {
        "file_tree": ["app.py"],
        "config": {"analyzer_instructions": ""},
        "usage_stats": []
    }
    
    result = analyze_node(state)
    
    assert result["analysis_result"]["stack"] == "Python"
    assert len(result["usage_stats"]) == 1
    assert result["usage_stats"][0]["total_tokens"] == 500
    assert result["usage_stats"][0]["model"] == "gpt-4o-mini"  # default

def test_read_files_node():
    """Test read_files node"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write("print('hello')")
        
        state = {
            "path": tmpdir,
            "analysis_result": {"files_to_read": ["test.py"]}
        }
        
        result = read_files_node(state)
        
        assert "test.py" in result["file_contents"]
        assert "print('hello')" in result["file_contents"]

def test_read_files_node_truncation():
    """Test that large files are truncated when truncation is enabled"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create large file
        test_file = os.path.join(tmpdir, "large.py")
        with open(test_file, "w") as f:
            # Write more than 5000 lines (new default limit)
            for i in range(6000):
                f.write(f"line {i}\n")
        
        state = {
            "path": tmpdir,
            "analysis_result": {"files_to_read": ["large.py"]},
            "config": {"truncation_enabled": True}  # Enable truncation for this test
        }
        
        result = read_files_node(state)
        
        assert "TRUNCATED" in result["file_contents"]


def test_read_files_node_no_truncation_by_default():
    """Test that large files are NOT truncated by default when under token limit"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create large file (but under default token limit of 100K tokens)
        test_file = os.path.join(tmpdir, "large.py")
        with open(test_file, "w") as f:
            # Write more than 5000 lines but within token limits
            for i in range(6000):
                f.write(f"line {i}\n")
        
        state = {
            "path": tmpdir,
            "analysis_result": {"files_to_read": ["large.py"]}
            # No config - truncation should be disabled by default
        }
        
        result = read_files_node(state)
        
        # Should NOT be truncated (file is under token limit)
        assert "TRUNCATED" not in result["file_contents"]
        # Should contain all lines
        assert "line 5999" in result["file_contents"]


def test_read_files_node_auto_truncation_on_token_limit():
    """Test that truncation auto-enables when token limit is exceeded"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a very large file that will exceed token limit
        test_file = os.path.join(tmpdir, "huge.py")
        with open(test_file, "w") as f:
            # Write ~500K chars which is > 100K tokens (at ~4 chars/token)
            for i in range(50000):
                f.write(f"# This is line number {i} with some padding text to make it longer\n")
        
        # Set a low token limit for testing
        os.environ["DOCKAI_TOKEN_LIMIT"] = "1000"  # Very low limit
        
        try:
            state = {
                "path": tmpdir,
                "analysis_result": {"files_to_read": ["huge.py"]}
                # No truncation_enabled - should auto-enable due to token limit
            }
            
            result = read_files_node(state)
            
            # Should be auto-truncated due to exceeding token limit
            assert "TRUNCATED" in result["file_contents"]
        finally:
            # Clean up env var
            del os.environ["DOCKAI_TOKEN_LIMIT"]


def test_read_files_node_truncation_via_env_var():
    """Test that truncation can be enabled via environment variable"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create large file
        test_file = os.path.join(tmpdir, "large.py")
        with open(test_file, "w") as f:
            for i in range(6000):
                f.write(f"line {i}\n")
        
        # Enable truncation via env var
        os.environ["DOCKAI_TRUNCATION_ENABLED"] = "true"
        
        try:
            state = {
                "path": tmpdir,
                "analysis_result": {"files_to_read": ["large.py"]}
                # No config - should use env var
            }
            
            result = read_files_node(state)
            
            # Should be truncated due to env var
            assert "TRUNCATED" in result["file_contents"]
        finally:
            # Clean up env var
            del os.environ["DOCKAI_TRUNCATION_ENABLED"]

@patch("dockai.workflow.nodes.generate_dockerfile")
@patch("dockai.workflow.nodes.get_docker_tags")
def test_generate_node_first_attempt(mock_get_tags, mock_generate):
    """Test generate node on first attempt (uses cheaper model)"""
    
    mock_get_tags.return_value = ["python:3.11-alpine", "python:3.11-slim"]
    mock_generate.return_value = (
        "FROM python:3.11-alpine",
        "service",
        "Using alpine for size",
        {"total_tokens": 800}
    )
    
    state = {
        "analysis_result": {
            "stack": "Python",
            "suggested_base_image": "python",
            "build_command": "pip install",
            "start_command": "python app.py"
        },
        "file_contents": "...",
        "config": {"generator_instructions": ""},
        "error": None,
        "retry_count": 0,
        "usage_stats": []
    }
    
    result = generate_node(state)
    
    assert result["dockerfile_content"] == "FROM python:3.11-alpine"
    assert result["error"] is None
    assert len(result["usage_stats"]) == 1
    # Should use MODEL_ANALYZER on first attempt
    assert result["usage_stats"][0]["model"] == "gpt-4o-mini"

@patch("dockai.workflow.nodes.generate_dockerfile")
@patch("dockai.workflow.nodes.get_docker_tags")
@patch("dockai.workflow.nodes.os.getenv")
def test_generate_node_retry(mock_getenv, mock_get_tags, mock_generate):
    """Test generate node on retry (uses more powerful model)"""
    
    mock_getenv.side_effect = lambda key, default=None: {
        "MODEL_ANALYZER": "gpt-4o-mini",
        "MODEL_GENERATOR": "gpt-4o"
    }.get(key, default)
    
    mock_get_tags.return_value = ["python:3.11-alpine"]
    mock_generate.return_value = (
        "FROM python:3.11-alpine",
        "service",
        "Fixed the issue",
        {"total_tokens": 1200}
    )
    
    state = {
        "analysis_result": {
            "stack": "Python",
            "suggested_base_image": "python",
            "build_command": None,
            "start_command": None
        },
        "file_contents": "...",
        "config": {"generator_instructions": ""},
        "error": "Previous error",
        "retry_count": 1,  # This is a retry
        "usage_stats": []
    }
    
    result = generate_node(state)
    
    # Should use MODEL_GENERATOR on retry
    assert result["usage_stats"][0]["model"] == "gpt-4o"
