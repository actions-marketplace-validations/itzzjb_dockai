"""Tests for the validator module."""
import os
from unittest.mock import patch, MagicMock
from dockai.utils.validator import validate_docker_build_and_run, check_health_endpoint, lint_dockerfile_with_hadolint
from dockai.core.errors import ClassifiedError, ErrorType


@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_success_service(mock_getenv, mock_sleep, mock_run_command, mock_hadolint):
    """Test successful service validation"""
    # Mock env vars
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_VALIDATION_MEMORY": "512m",
        "DOCKAI_VALIDATION_CPUS": "1.0",
        "DOCKAI_VALIDATION_PIDS": "100",
        "DOCKAI_SKIP_SECURITY_SCAN": "true",  # Skip Trivy for test
        "DOCKAI_SKIP_HADOLINT": "true",  # Skip Hadolint for test
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    # Mock sequence: build, run, inspect running, inspect exit code, logs, inspect size, rm, rmi
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "true", ""),           # inspect running
        (0, "0", ""),              # inspect exit code
        (0, "Service started", ""),# logs
        (0, "104857600", ""),      # inspect size (100MB)
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    success, msg, size, _ = validate_docker_build_and_run(".", project_type="service")
    
    assert success is True
    assert "running successfully" in msg.lower()
    assert size == 104857600

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_success_script(mock_getenv, mock_sleep, mock_run_command, mock_hadolint):
    """Test successful script validation (exits with code 0)"""
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_SKIP_SECURITY_SCAN": "true",
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    # Script runs and exits successfully
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "false", ""),          # inspect running (not running - script finished)
        (0, "0", ""),              # inspect exit code (0 = success)
        (0, "Script output", ""),  # logs
        (0, "52428800", ""),       # inspect size (50MB)
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    success, msg, size, _ = validate_docker_build_and_run(".", project_type="script")
    
    assert success is True
    assert "finished successfully" in msg.lower()

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.classify_error")
@patch("dockai.utils.validator.run_command")
def test_validate_build_failure(mock_run_command, mock_classify, mock_hadolint):
    """Test build failure"""
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    mock_run_command.side_effect = [
        (1, "", "Build failed error message"),  # build fails
    ]
    
    # Mock classify_error return
    mock_classify.return_value = ClassifiedError(
        error_type=ErrorType.DOCKERFILE_ERROR,
        message="Build failed error message",
        suggestion="Fix it",
        original_error="Build failed error message",
        should_retry=True
    )
    
    success, msg, size, _ = validate_docker_build_and_run(".")
    
    assert success is False
    assert "Docker build failed" in msg
    assert "Build failed error message" in msg
    assert size == 0

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_with_health_check_success(mock_getenv, mock_sleep, mock_run_command, mock_hadolint):
    """Test service with health check that passes"""
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_SKIP_SECURITY_SCAN": "true",
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    # Mock sequence including health check
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "true", ""),           # inspect running
        (0, "0", ""),              # inspect exit code
        (0, "Service started", ""),# logs
        (0, "8080", ""),           # inspect host port (NEW)
        (0, "200", ""),            # health check (HTTP 200)
        (0, "104857600", ""),      # inspect size
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    success, msg, size, _ = validate_docker_build_and_run(
        ".", 
        project_type="service",
        health_endpoint=("/health", 8080)
    )
    
    assert success is True
    assert "health check passed" in msg.lower()

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_with_health_check_failure_but_running(mock_getenv, mock_sleep, mock_run_command, mock_hadolint):
    """Test service with health check that fails but service keeps running (should pass with warning)"""
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_SKIP_SECURITY_SCAN": "true",
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    # Health check returns non-200 multiple times
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "true", ""),           # inspect running
        (0, "0", ""),              # inspect exit code
        (0, "Service started", ""),# logs
        (0, "8080", ""),           # inspect host port (NEW)
        (0, "500", ""),            # health check attempt 1 (HTTP 500)
        (0, "500", ""),            # health check attempt 2
        (0, "500", ""),            # health check attempt 3
        (0, "500", ""),            # health check attempt 4
        (0, "500", ""),            # health check attempt 5
        (0, "500", ""),            # health check attempt 6 (final)
        (0, "104857600", ""),      # inspect size
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    success, msg, size, _ = validate_docker_build_and_run(
        ".", 
        project_type="service",
        health_endpoint=("/health", 8080)
    )
    
    # Updated expectation: Success is True, but message indicates health check issue
    assert success is True
    assert "health check" in msg.lower()
    assert "did not respond" in msg.lower() or "failed" in msg.lower()


from dockai.utils.validator import suggest_health_endpoint

class TestSuggestHealthEndpoint:
    """Tests for the suggest_health_endpoint function."""
    
    def test_suggest_basic_fastapi(self):
        analysis = {
            "frameworks": ["FastAPI"],
            "all_ports": [8000]
        }
        path, port = suggest_health_endpoint(analysis)
        assert path == "/docs"
        assert port == 8000
    
    def test_suggest_flask(self):
        analysis = {
            "framework_hints": ["Flask"],
            "exposed_ports": [5000]
        }
        path, port = suggest_health_endpoint(analysis)
        assert path == "/health"
        assert port == 5000
    
    def test_suggest_unknown_framework(self):
        analysis = {
            "frameworks": ["Custom"],
            "all_ports": [8080]
        }
        # Should return None if framework not matched? 
        # Actually logic is just default "/", let's check code
        # Code: path = "/"; ... if ... path = ...
        path, port = suggest_health_endpoint(analysis)
        assert path == "/"
        assert port == 8080
    
    def test_no_ports(self):
        analysis = {
            "frameworks": ["FastAPI"],
            "all_ports": []
        }
        assert suggest_health_endpoint(analysis) is None

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.classify_error")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_service_crash(mock_getenv, mock_sleep, mock_run_command, mock_classify, mock_hadolint):
    """Test service that crashes after starting"""
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_SKIP_SECURITY_SCAN": "true",
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "false", ""),          # inspect running (crashed)
        (0, "1", ""),              # inspect exit code (non-zero)
        (0, "Error: crash", ""),   # logs
        (0, "104857600", ""),      # inspect size
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    mock_classify.return_value = ClassifiedError(
        error_type=ErrorType.DOCKERFILE_ERROR,
        message="Service crashed",
        suggestion="Fix crash",
        original_error="Error: crash",
        should_retry=True
    )
    
    success, msg, size, _ = validate_docker_build_and_run(".", project_type="service")
    
    assert success is False
    assert "stopped unexpectedly" in msg.lower()
    assert "Service crashed" in msg

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.classify_error")
@patch("dockai.utils.validator.run_command")
@patch("dockai.utils.validator.time.sleep")
@patch("dockai.utils.validator.os.getenv")
def test_validate_script_failure(mock_getenv, mock_sleep, mock_run_command, mock_classify, mock_hadolint):
    """Test script that exits with non-zero code"""
    mock_getenv.side_effect = lambda key, default=None: {
        "DOCKAI_SKIP_SECURITY_SCAN": "true",
    }.get(key, default)
    
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""),  # build
        (0, "container_id", ""),   # run
        (0, "false", ""),          # inspect running (finished)
        (0, "1", ""),              # inspect exit code (failed)
        (0, "Error occurred", ""), # logs
        (0, "52428800", ""),       # inspect size
        (0, "", ""),               # rm
        (0, "", "")                # rmi
    ]
    
    mock_classify.return_value = ClassifiedError(
        error_type=ErrorType.PROJECT_ERROR,
        message="Script failed",
        suggestion="Fix script",
        original_error="Error occurred",
        should_retry=False
    )
    
    success, msg, size, _ = validate_docker_build_and_run(".", project_type="script")
    
    assert success is False
    assert "failed" in msg.lower()
    assert "Exit Code: 1" in msg
    assert "Script failed" in msg

@patch("dockai.utils.validator.lint_dockerfile_with_hadolint")
@patch("dockai.utils.validator.classify_error")
@patch("dockai.utils.validator.run_command")
def test_validate_container_start_failure(mock_run_command, mock_classify, mock_hadolint):
    """Test container fails to start"""
    # Mock hadolint to pass
    mock_hadolint.return_value = (True, [], "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""),      # build
        (1, "", "Cannot start container"), # run fails
        (0, "", "")                    # rmi
    ]
    
    mock_classify.return_value = ClassifiedError(
        error_type=ErrorType.ENVIRONMENT_ERROR,
        message="Cannot start container",
        suggestion="Check docker",
        original_error="Cannot start container",
        should_retry=False
    )
    
    success, msg, size, _ = validate_docker_build_and_run(".")
    
    assert success is False
    assert "Container start failed" in msg
    assert "Cannot start container" in msg
    assert size == 0

def test_configurable_resource_limits():
    """Test that resource limits are configurable"""
    with patch("dockai.utils.validator.lint_dockerfile_with_hadolint") as mock_hadolint:
        with patch("dockai.utils.validator.run_command") as mock_run:
            with patch("dockai.utils.validator.time.sleep"):
                with patch("dockai.utils.validator.os.getenv") as mock_getenv:
                    # Mock hadolint to pass
                    mock_hadolint.return_value = (True, [], "")
                    
                    # Set custom resource limits
                    mock_getenv.side_effect = lambda key, default=None: {
                        "DOCKAI_VALIDATION_MEMORY": "2g",
                        "DOCKAI_VALIDATION_CPUS": "2.0",
                        "DOCKAI_VALIDATION_PIDS": "200",
                        "DOCKAI_SKIP_SECURITY_SCAN": "true",
                    }.get(key, default)
                    
                    mock_run.side_effect = [
                        (0, "Build success", ""),
                        (0, "container_id", ""),
                        (0, "true", ""),
                        (0, "0", ""),
                        (0, "logs", ""),
                        (0, "104857600", ""),
                        (0, "", ""),
                        (0, "", "")
                    ]
                    
                    validate_docker_build_and_run(".")
                    
                    # Check that docker run was called with custom limits
                    run_call = mock_run.call_args_list[1]
                    run_command = run_call[0][0]
                    
                    assert "--memory=2g" in run_command
                    assert "--cpus=2.0" in run_command
                    assert "--pids-limit=200" in run_command


def test_hadolint_lint_skip():
    """Test that Hadolint can be skipped via environment variable"""
    with patch("dockai.utils.validator.os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "DOCKAI_SKIP_HADOLINT": "true",
        }.get(key, default)
        
        passed, issues, output = lint_dockerfile_with_hadolint("/path/to/Dockerfile")
        
        assert passed is True
        assert issues == []
        assert output == "Skipped"