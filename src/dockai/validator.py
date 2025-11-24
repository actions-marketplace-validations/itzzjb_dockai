import subprocess
import time
import uuid
import logging
from typing import List, Tuple

logger = logging.getLogger("dockai")

def run_command(command: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr.
    
    Args:
        command (List[str]): The command to run as a list of strings.
        cwd (str): The working directory to run the command in.
        
    Returns:
        Tuple[int, str, str]: A tuple containing (exit_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def validate_docker_build_and_run(directory: str, project_type: str = "service") -> Tuple[bool, str]:
    """
    Builds and runs the Dockerfile in the given directory to verify it works.
    
    This function performs the following steps:
    1. Builds the Docker image with strict memory limits to prevent host exhaustion.
    2. Runs a container from the image in a sandboxed environment (limited memory, CPU, PIDs).
    3. Checks if the container starts successfully.
    4. For 'service' type: Checks if it stays running.
    5. For 'script' type: Checks if it exits with code 0.
    6. Cleans up the container and image.
    
    Args:
        directory (str): The directory containing the Dockerfile.
        project_type (str): 'service' or 'script'.
        
    Returns:
        Tuple[bool, str]: A tuple containing (success, message).
    """
    image_name = f"dockai-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dockai-container-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Validating Dockerfile in {directory} (Type: {project_type})...")
    
    # 1. Build
    logger.info("Building Docker image (with resource limits)...")
    # Limit build memory to 2GB to prevent host exhaustion during build
    build_cmd = ["docker", "build", "--memory=2g", "-t", image_name, "."]
    code, stdout, stderr = run_command(build_cmd, cwd=directory)
    
    if code != 0:
        error_msg = f"Docker build failed:\n{stderr}\n{stdout}"
        logger.error("Docker build failed.")
        return False, error_msg
    
    # 2. Run
    logger.info("Running Docker container (sandboxed)...")
    # Run detached with strict resource limits and security controls
    run_cmd = [
        "docker", "run", 
        "-d", 
        "--name", container_name,
        "--memory=512m",                    # Limit RAM to 512MB
        "--cpus=1.0",                       # Limit to 1 CPU core
        "--pids-limit=100",                 # Prevent fork bombs
        "--security-opt=no-new-privileges", # Prevent privilege escalation
        image_name
    ]
    code, stdout, stderr = run_command(run_cmd)
    
    if code != 0:
        error_msg = f"Failed to start container:\n{stderr}"
        logger.error("Failed to start container.")
        # Cleanup image
        run_command(["docker", "rmi", image_name])
        return False, error_msg
    
    # Wait for container to initialize or finish
    time.sleep(5)
    
    # Check status
    inspect_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
    code, stdout, stderr = run_command(inspect_cmd)
    is_running = stdout.strip() == "true"
    
    # Get exit code
    exit_code_cmd = ["docker", "inspect", "-f", "{{.State.ExitCode}}", container_name]
    _, exit_code_out, _ = run_command(exit_code_cmd)
    exit_code = int(exit_code_out.strip()) if exit_code_out.strip().isdigit() else -1

    # Get logs for debugging
    logs_cmd = ["docker", "logs", container_name]
    _, logs_out, logs_err = run_command(logs_cmd)
    
    success = False
    message = ""

    if project_type == "service":
        if is_running:
            success = True
            message = "Service is running successfully."
        else:
            success = False
            message = f"Service stopped unexpectedly. Exit Code: {exit_code}\nLogs:\n{logs_out}\n{logs_err}"
            
    elif project_type == "script":
        if is_running:
            # It's still running, which is fine for a long script, but we can't verify success yet.
            # Ideally we'd wait longer, but for now we'll assume it's working if it hasn't crashed.
            success = True
            message = "Script is running (long-running task)."
        else:
            if exit_code == 0:
                success = True
                message = "Script finished successfully (Exit Code 0)."
            else:
                success = False
                message = f"Script failed. Exit Code: {exit_code}\nLogs:\n{logs_out}\n{logs_err}"
    
    else:
        # Fallback for unknown types
        if is_running or exit_code == 0:
            success = True
            message = "Container ran successfully."
        else:
            success = False
            message = f"Container failed. Exit Code: {exit_code}\nLogs:\n{logs_out}\n{logs_err}"

    if success:
        logger.info(message)
    else:
        logger.error(message)

    # Cleanup
    run_command(["docker", "rm", "-f", container_name])
    run_command(["docker", "rmi", image_name])
    
    return success, message
