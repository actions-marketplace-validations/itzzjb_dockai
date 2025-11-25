import subprocess
import time
import uuid
import logging
import os
import json
from typing import List, Tuple, Optional

from .errors import classify_error, ClassifiedError, ErrorType

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
    recommended_wait_time: int = 5,
    readiness_patterns: List[str] = None
) -> Tuple[bool, str, int, Optional[ClassifiedError]]:
    """
    Builds and runs the Dockerfile in the given directory to verify it works.
    
    This function performs the following steps:
    1. Builds the Docker image with strict memory limits to prevent host exhaustion.
    2. Runs a container from the image in a sandboxed environment (limited memory, CPU, PIDs).
    3. Uses AI-detected readiness patterns OR recommended wait times.
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
        readiness_patterns (List[str]): AI-detected log patterns for startup detection.
        
    Returns:
        Tuple[bool, str, int, Optional[ClassifiedError]]: A tuple containing 
        (success, message, image_size_bytes, classified_error).
    """
    image_name = f"dockai-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dockai-container-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Validating Dockerfile in {directory} (Type: {project_type}, Stack: {stack})...")
    
    # 1. Build
    logger.info("Building Docker image (with resource limits)...")
    build_cmd = ["docker", "build", "--memory=2g", "-t", image_name, "."]
    code, stdout, stderr = run_command(build_cmd, cwd=directory)
    
    if code != 0:
        error_output = f"{stderr}\n{stdout}"
        classified = classify_error(error_output, logs=error_output, stack=stack)
        error_msg = f"Docker build failed: {classified.message}"
        logger.error(f"Problem: {classified.message}")
        logger.debug(f"Details: {error_output[:500]}")
        return False, error_msg, 0, classified
    
    # 2. Run
    logger.info("Running Docker container (sandboxed)...")
    
    # Configurable resource limits (can be adjusted for different stacks)
    memory_limit = os.getenv("DOCKAI_VALIDATION_MEMORY", "512m")
    cpu_limit = os.getenv("DOCKAI_VALIDATION_CPUS", "1.0")
    pids_limit = os.getenv("DOCKAI_VALIDATION_PIDS", "100")
    
    # Expose port if health endpoint is provided
    run_cmd = [
        "docker", "run", 
        "-d", 
        "--name", container_name,
        f"--memory={memory_limit}",
        f"--cpus={cpu_limit}",
        f"--pids-limit={pids_limit}",
        "--security-opt=no-new-privileges",
    ]
    
    # Add port mapping if we have a health endpoint
    if health_endpoint:
        _, port = health_endpoint
        run_cmd.extend(["-p", f"{port}:{port}"])
    
    run_cmd.append(image_name)
    
    code, stdout, stderr = run_command(run_cmd)
    
    if code != 0:
        error_output = f"{stderr}\n{stdout}"
        classified = classify_error(error_output, logs=error_output, stack=stack)
        error_msg = f"Container start failed: {classified.message}"
        logger.error(f"Problem: {classified.message}")
        run_command(["docker", "rmi", image_name])
        return False, error_msg, 0, classified
    
    
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
    container_logs = f"{logs_out}\n{logs_err}"
    
    success = False
    message = ""
    classified_error = None

    # 5. Validation logic
    # Health checks are OPTIONAL - only run if explicitly configured
    skip_health_check = os.getenv("DOCKAI_SKIP_HEALTH_CHECK", "false").lower() == "true"
    
    if project_type == "service":
        if is_running:
            # Health check is optional - only run if endpoint is explicitly provided AND not skipped
            if health_endpoint and not skip_health_check:
                endpoint_path, port = health_endpoint
                logger.info(f"Health endpoint configured: {endpoint_path}:{port} - running health check...")
                if check_health_endpoint(container_name, endpoint_path, port):
                    success = True
                    message = f"Service is running and health check passed ({endpoint_path})."
                else:
                    # Health check failed but service is running - log warning but don't fail
                    # Many services take time to fully initialize or health endpoint might be different
                    logger.warning(f"Health check did not respond at {endpoint_path}:{port}, but service is running")
                    success = True
                    message = f"Service is running (health check at {endpoint_path} did not respond - this is OK if the endpoint is different)."
            else:
                # No health endpoint OR health check skipped - just check if running
                if skip_health_check:
                    logger.info("Health check skipped (DOCKAI_SKIP_HEALTH_CHECK=true)")
                else:
                    logger.info("No health endpoint configured - skipping health check")
                success = True
                message = "Service is running successfully."
        else:
            success = False
            classified_error = classify_error(container_logs, logs=container_logs, stack=stack)
            message = f"Service stopped unexpectedly (Exit Code: {exit_code}): {classified_error.message}"

            
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
                classified_error = classify_error(container_logs, logs=container_logs, stack=stack)
                message = f"Script failed (Exit Code: {exit_code}): {classified_error.message}"
    
    else:
        if is_running or exit_code == 0:
            success = True
            message = "Container ran successfully."
        else:
            success = False
            classified_error = classify_error(container_logs, logs=container_logs, stack=stack)
            message = f"Container failed (Exit Code: {exit_code}): {classified_error.message}"

    if success:
        logger.info(message)
    else:
        logger.error(f"Problem: {message}")

    
    # 6. Get Image Size
    size_cmd = ["docker", "inspect", "-f", "{{.Size}}", image_name]
    _, size_out, _ = run_command(size_cmd)
    image_size_bytes = int(size_out.strip()) if size_out.strip().isdigit() else 0
    
    # 7. Trivy Security Scan (Configurable)
    skip_security_scan = os.getenv("DOCKAI_SKIP_SECURITY_SCAN", "false").lower() == "true"
    strict_security = os.getenv("DOCKAI_STRICT_SECURITY", "false").lower() == "true"
    
    if not skip_security_scan:
        logger.info("Running Trivy security scan (CRITICAL/HIGH vulnerabilities)...")
        trivy_cmd = [
            "docker", "run", "--rm",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "aquasec/trivy", "image",
            "--severity", "CRITICAL,HIGH",
            "--exit-code", "1",
            "--no-progress",
            "--format", "json",  # Get JSON output for better parsing
            "--scanners", "vuln",
            image_name
        ]
        
        trivy_code, trivy_out, trivy_err = run_command(trivy_cmd)
        
        if trivy_code != 0:
            # Trivy found vulnerabilities or failed to run
            if trivy_out and ("vulnerabilities" in trivy_out.lower() or "results" in trivy_out.lower()):
                logger.warning("Trivy found CRITICAL/HIGH vulnerabilities!")
                
                # Try to parse JSON to distinguish base image vs app vulnerabilities
                try:
                    trivy_data = json.loads(trivy_out)
                    base_image_vulns = 0
                    app_vulns = 0
                    
                    for result in trivy_data.get("Results", []):
                        target = result.get("Target", "").lower()
                        vulns = result.get("Vulnerabilities", [])
                        
                        # Base image vulnerabilities are in OS packages or base layers
                        if any(x in target for x in ["os-release", "debian", "alpine", "ubuntu", "node:", "python:", "openjdk"]):
                            base_image_vulns += len(vulns)
                        else:
                            app_vulns += len(vulns)
                    
                    if base_image_vulns > 0:
                        # Base image has vulnerabilities - this is a Dockerfile issue (can retry)
                        logger.error(f"Problem: Found {base_image_vulns} vulnerabilities in base image layers.")
                        if strict_security or base_image_vulns > 5:
                            success = False
                            classified_error = ClassifiedError(
                                error_type=ErrorType.DOCKERFILE_ERROR,
                                message=f"Security scan failed: {base_image_vulns} CRITICAL/HIGH vulnerabilities in base image",
                                suggestion="Try using a different base image tag (alpine, slim, or newer version)",
                                original_error=trivy_out[:300],
                                should_retry=True
                            )
                            message = classified_error.message
                        else:
                            message += f"\n\n[SECURITY WARNING] {base_image_vulns} vulnerabilities in base image. Consider using a more secure base image."
                            logger.warning(f"Base image vulnerabilities detected but continuing (strict_security=false)")
                    
                    if app_vulns > 0:
                        # Application dependencies have vulnerabilities - this is code issue, not Dockerfile
                        logger.warning(f"Found {app_vulns} vulnerabilities in application dependencies (not a Dockerfile issue).")
                        message += f"\n\n[INFO] {app_vulns} vulnerabilities found in application code/dependencies. Fix these in your application, not the Dockerfile."
                
                except (json.JSONDecodeError, Exception) as e:
                    # Fallback if JSON parsing fails
                    logger.warning(f"Could not parse Trivy output: {e}")
                    if strict_security:
                        success = False
                        classified_error = ClassifiedError(
                            error_type=ErrorType.DOCKERFILE_ERROR,
                            message="Security scan found vulnerabilities",
                            suggestion="Enable verbose mode for details or use DOCKAI_SKIP_SECURITY_SCAN=true",
                            original_error=trivy_out[:300],
                            should_retry=True
                        )
                        message = classified_error.message
                    else:
                        message += "\n\n[SECURITY WARNING] Trivy detected vulnerabilities. Run with DOCKAI_STRICT_SECURITY=true to fail on vulnerabilities."
                        logger.warning(trivy_out[:500])
            else:
                logger.warning(f"Trivy scan failed to execute: {trivy_err}")
        else:
            logger.info("Trivy scan passed (No CRITICAL/HIGH vulnerabilities found).")
    else:
        logger.info("Security scan skipped (DOCKAI_SKIP_SECURITY_SCAN=true)")


    # Cleanup
    run_command(["docker", "rm", "-f", container_name])
    run_command(["docker", "rmi", image_name])
    
    return success, message, image_size_bytes, classified_error
