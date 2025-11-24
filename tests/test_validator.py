from unittest.mock import patch, MagicMock
from dockai.validator import validate_docker_build_and_run

@patch("dockai.validator.run_command")
@patch("dockai.validator.time.sleep") # Skip sleep
def test_validate_success(mock_sleep, mock_run_command):
    """Test successful validation"""
    # Mock sequence of calls:
    # 1. build -> (0, "success", "")
    # 2. run -> (0, "container_id", "")
    # 3. inspect running -> (0, "true", "")
    # 4. rm -> (0, "", "")
    # 5. rmi -> (0, "", "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""), # build
        (0, "container_id", ""),  # run
        (0, "true", ""),          # inspect running
        (0, "", ""),              # rm
        (0, "", "")               # rmi
    ]
    
    success, msg = validate_docker_build_and_run(".")
    
    assert success is True
    assert "Build and Run successful" in msg

@patch("dockai.validator.run_command")
def test_validate_build_failure(mock_run_command):
    """Test build failure"""
    # 1. build -> (1, "", "Build failed")
    
    mock_run_command.side_effect = [
        (1, "", "Build failed error message"), # build
    ]
    
    success, msg = validate_docker_build_and_run(".")
    
    assert success is False
    assert "Docker build failed" in msg
    assert "Build failed error message" in msg

@patch("dockai.validator.run_command")
@patch("dockai.validator.time.sleep")
def test_validate_run_failure_immediate(mock_sleep, mock_run_command):
    """Test container fails to start immediately (docker run returns non-zero)"""
    # 1. build -> (0, "", "")
    # 2. run -> (1, "", "Cannot start container")
    # 3. rmi -> (0, "", "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""),      # build
        (1, "", "Cannot start container"), # run
        (0, "", "")                    # rmi
    ]
    
    success, msg = validate_docker_build_and_run(".")
    
    assert success is False
    assert "Failed to start container" in msg

@patch("dockai.validator.run_command")
@patch("dockai.validator.time.sleep")
def test_validate_run_failure_crash(mock_sleep, mock_run_command):
    """Test container starts but crashes (inspect returns false)"""
    # 1. build -> (0, "", "")
    # 2. run -> (0, "id", "")
    # 3. inspect running -> (0, "false", "")
    # 4. inspect exit code -> (0, "1", "")
    # 5. logs -> (0, "Error: crash", "")
    # 6. rm -> (0, "", "")
    # 7. rmi -> (0, "", "")
    
    mock_run_command.side_effect = [
        (0, "Build success", ""), # build
        (0, "id", ""),            # run
        (0, "false", ""),         # inspect running
        (0, "1", ""),             # inspect exit code
        (0, "Error: crash", ""),  # logs
        (0, "", ""),              # rm
        (0, "", "")               # rmi
    ]
    
    success, msg = validate_docker_build_and_run(".")
    
    assert success is False
    assert "Container stopped unexpectedly" in msg
    assert "Error: crash" in msg
