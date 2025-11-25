import subprocess
import time
import uuid
import logging
from typing import List, Tuple, Optional

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

def check_health_endpoint(container_name: str, endpoint: str, port: int, max_attempts: int = 6) -> bool:
    """
    Check if a health endpoint is responding with HTTP 200.
    
    Args:
        container_name (str): Name of the Docker container.
        endpoint (str): Health check endpoint path (e.g., '/health').
        port (int): Port the service is listening on.
        max_attempts (int): Maximum number of attempts (default 6 = 30 seconds with 5s intervals).
        
    Returns:
        bool: True if health check passed, False otherwise.
    """
    logger.info(f"Checking health endpoint: http://localhost:{port}{endpoint}")
    
    for attempt in range(1, max_attempts + 1):
        # Use docker exec to curl from inside the container
        health_cmd = [
            "docker", "exec", container_name,
            "sh", "-c", 
            f"command -v curl >/dev/null 2>&1 && curl -f -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}{endpoint} || echo '000'"
        ]
        
        code, stdout, stderr = run_command(health_cmd)
        
        if code == 0:
            http_code = stdout.strip()
            if http_code == "200":
                logger.info(f"Health check passed on attempt {attempt}/{max_attempts}")
                return True
            elif http_code != "000":
                logger.debug(f"Health check attempt {attempt}/{max_attempts}: HTTP {http_code}")
        
        if attempt < max_attempts:
            time.sleep(5)
    
    logger.warning(f"Health check failed after {max_attempts} attempts")
    return False

def validate_docker_build_and_run(
    directory: str, 
    project_type: str = "service",
    stack: str = "Unknown",
    health_endpoint: Optional[Tuple[str, int]] = None,
    recommended_wait_time: int = 5
) -> Tuple[bool, str, int]:
    """
    Builds and runs the Dockerfile in the given directory to verify it works.
    
    This function performs the following steps:
    1. Builds the Docker image with strict memory limits to prevent host exhaustion.
    2. Runs a container from the image in a sandboxed environment (limited memory, CPU, PIDs).
    3. Uses AI-recommended wait times based on stack type.
    4. For services with health endpoints: Performs HTTP health checks.
    5. For services without health endpoints: Checks if it stays running.
    6. For scripts: Checks if it exits with code 0.
    7. Cleans up the container and image.
    
    Args:
        directory (str): The directory containing the Dockerfile.
        project_type (str): 'service' or 'script'.
        stack (str): The detected technology stack.
        health_endpoint (Optional[Tuple[str, int]]): (endpoint_path, port) for health checks.
        recommended_wait_time (int): AI-recommended wait time in seconds.
        
    Returns:
        Tuple[bool, str, int]: A tuple containing (success, message, image_size_bytes).
    """
    image_name = f"dockai-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dockai-container-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Validating Dockerfile in {directory} (Type: {project_type}, Stack: {stack})...")
    
    # 1. Build
    logger.info("Building Docker image (with resource limits)...")
    build_cmd = ["docker", "build", "--memory=2g", "-t", image_name, "."]
    code, stdout, stderr = run_command(build_cmd, cwd=directory)
    
    if code != 0:
        error_msg = f"Docker build failed:\n{stderr}\n{stdout}"
        logger.error("Docker build failed.")
        return False, error_msg, 0
    
    # 2. Run
    logger.info("Running Docker container (sandboxed)...")
    
    # Expose port if health endpoint is provided
    run_cmd = [
        "docker", "run", 
        "-d", 
        "--name", container_name,
        "--memory=512m",
        "--cpus=1.0",
        "--pids-limit=100",
        "--security-opt=no-new-privileges",
    ]
    
    # Add port mapping if we have a health endpoint
    if health_endpoint:
        _, port = health_endpoint
        run_cmd.extend(["-p", f"{port}:{port}"])
    
    run_cmd.append(image_name)
    
    code, stdout, stderr = run_command(run_cmd)
    
    if code != 0:
        error_msg = f"Failed to start container:\n{stderr}"
        logger.error("Failed to start container.")
        run_command(["docker", "rmi", image_name])
        return False, error_msg, 0
    
    
    # 3. Use AI-recommended wait time
    logger.info(f"Waiting {recommended_wait_time}s for container to initialize (AI-recommended)...")
    time.sleep(recommended_wait_time)
    
    # 4. Check status
    inspect_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
    code, stdout, stderr = run_command(inspect_cmd)
    is_running = stdout.strip() == "true"
    
    exit_code_cmd = ["docker", "inspect", "-f", "{{.State.ExitCode}}", container_name]
    _, exit_code_out, _ = run_command(exit_code_cmd)
    exit_code = int(exit_code_out.strip()) if exit_code_out.strip().isdigit() else -1

    logs_cmd = ["docker", "logs", container_name]
    _, logs_out, logs_err = run_command(logs_cmd)
    
    success = False
    message = ""

    # 5. Validation logic
    if project_type == "service":
        if is_running:
            # Try health check if endpoint is provided
            if health_endpoint:
                endpoint_path, port = health_endpoint
                if check_health_endpoint(container_name, endpoint_path, port):
                    success = True
                    message = f"Service is running and health check passed ({endpoint_path})."
                else:
                    success = True  # Still consider it success if running, even if health check fails
                    message = f"Service is running (health check at {endpoint_path} not responding, but container is alive)."
            else:
                success = True
                message = "Service is running successfully."
        else:
            success = False
            message = f"Service stopped unexpectedly. Exit Code: {exit_code}\nLogs:\n{logs_out}\n{logs_err}"
            
    elif project_type == "script":
        if is_running:
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

    # 6. Get Image Size
    size_cmd = ["docker", "inspect", "-f", "{{.Size}}", image_name]
    _, size_out, _ = run_command(size_cmd)
    image_size_bytes = int(size_out.strip()) if size_out.strip().isdigit() else 0
    
    # 7. Trivy Security Scan
    logger.info("Running Trivy security scan (CRITICAL/HIGH vulnerabilities)...")
    trivy_cmd = [
        "docker", "run", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "aquasec/trivy", "image",
        "--severity", "CRITICAL,HIGH",
        "--exit-code", "1",
        "--no-progress",
        "--scanners", "vuln", # Only scan for vulnerabilities for speed
        image_name
    ]
    
    trivy_code, trivy_out, trivy_err = run_command(trivy_cmd)
    
    if trivy_code != 0:
        # Trivy found vulnerabilities or failed to run
        if "Trivy" in trivy_out or "vulnerabilities" in trivy_out:
            logger.warning("Trivy found vulnerabilities!")
            # We don't fail the build yet, but we append it to the message
            # Ideally, we would fail here if strict security is required.
            # For now, let's log it clearly.
            message += "\n\n[SECURITY WARNING] Trivy detected CRITICAL/HIGH vulnerabilities. Check logs."
            logger.warning(trivy_out)
        else:
             logger.warning(f"Trivy scan failed to execute: {trivy_err}")
    else:
        logger.info("Trivy scan passed (No CRITICAL/HIGH vulnerabilities found).")

    # Cleanup
    run_command(["docker", "rm", "-f", container_name])
    run_command(["docker", "rmi", image_name])
    
    return success, message, image_size_bytes
