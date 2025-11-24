import subprocess
import time
import uuid
import logging
from typing import List, Tuple

logger = logging.getLogger("dockai")

def run_command(command: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
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

def validate_docker_build_and_run(directory: str) -> Tuple[bool, str]:
    """
    Builds and runs the Dockerfile in the given directory.
    Returns (success, message).
    """
    image_name = f"dockai-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dockai-container-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Validating Dockerfile in {directory}...")
    
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
    
    # Wait for container to initialize
    time.sleep(5)
    
    # Check if running
    inspect_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
    code, stdout, stderr = run_command(inspect_cmd)
    
    is_running = stdout.strip() == "true"
    
    if is_running:
        logger.info("Container is running successfully.")
        # Cleanup
        run_command(["docker", "rm", "-f", container_name])
        run_command(["docker", "rmi", image_name])
        return True, "Build and Run successful."
    else:
        # Check exit code
        exit_code_cmd = ["docker", "inspect", "-f", "{{.State.ExitCode}}", container_name]
        _, exit_code_out, _ = run_command(exit_code_cmd)
        
        # Get logs
        logs_cmd = ["docker", "logs", container_name]
        _, logs_out, logs_err = run_command(logs_cmd)
        
        error_msg = f"Container stopped unexpectedly. Exit Code: {exit_code_out.strip()}\nLogs:\n{logs_out}\n{logs_err}"
        logger.error(f"Container stopped unexpectedly. Logs: {logs_out} {logs_err}")
        
        # Cleanup
        run_command(["docker", "rm", "-f", container_name])
        run_command(["docker", "rmi", image_name])
        
        return False, error_msg
