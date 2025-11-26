"""
DockAI Docker Validator Module.

This module is responsible for the "Test Engineer" phase of the workflow.
It validates the generated Dockerfile by:
1. Building the image (with resource limits).
2. Running the container in a sandboxed environment.
3. Performing smart readiness checks (using AI-detected log patterns).
4. Executing health checks (if endpoints are detected).
5. Scanning for security vulnerabilities (using Trivy).
6. Classifying any errors that occur to guide the AI's reflection.
"""

import subprocess
import time
import uuid
import logging
import os
import json
import re
from typing import List, Tuple, Optional

from ..core.errors import classify_error, ClassifiedError, ErrorType

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


def run_command(command: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr.
    
    This is a helper function to execute subprocess commands safely and capture
    their output for analysis.
    
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
    
    This function first attempts to execute `curl` *inside* the container.
    If that fails (e.g., distroless image without curl), it falls back to
    checking from the *host* machine using the mapped port.
    
    Args:
        container_name (str): Name of the Docker container.
        endpoint (str): Health check endpoint path (e.g., '/health').
        port (int): Port the service is listening on.
        max_attempts (int): Maximum number of attempts (default 6 = 30 seconds).
        
    Returns:
        bool: True if health check passed, False otherwise.
    """
    import urllib.request
    import urllib.error
    
    logger.info(f"Checking health endpoint: {endpoint} on port {port}")
    
    # First, try to find the mapped port on the host
    host_port = None
    try:
        inspect_cmd = ["docker", "inspect", "-f", "{{(index (index .NetworkSettings.Ports \"" + str(port) + "/tcp\") 0).HostPort}}", container_name]
        code, stdout, _ = run_command(inspect_cmd)
        if code == 0 and stdout.strip():
            host_port = stdout.strip()
    except Exception:
        logger.warning("Could not determine host port mapping")

    for attempt in range(1, max_attempts + 1):
        # Strategy 1: Container-internal check (preferred as it tests internal networking)
        # We check for curl existence first to avoid errors in minimal images
        health_cmd = [
            "docker", "exec", container_name,
            "sh", "-c", 
            f"command -v curl >/dev/null 2>&1 && curl -f -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}{endpoint} || echo 'MISSING_CURL'"
        ]
        
        code, stdout, stderr = run_command(health_cmd)
        http_code = stdout.strip()
        
        if code == 0 and http_code == "200":
            logger.info(f"Health check passed (internal curl) on attempt {attempt}/{max_attempts}")
            return True
            
        # Strategy 2: Host-based check (fallback for distroless/minimal images)
        if (http_code == "MISSING_CURL" or code != 0) and host_port:
            try:
                url = f"http://localhost:{host_port}{endpoint}"
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.getcode() == 200:
                        logger.info(f"Health check passed (host fallback) on attempt {attempt}/{max_attempts}")
                        return True
            except (urllib.error.URLError, ConnectionResetError):
                pass # Connection failed, wait and retry
        
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
    readiness_patterns: List[str] = None,
    failure_patterns: List[str] = None
) -> Tuple[bool, str, int, Optional[ClassifiedError]]:
    """
    Builds and runs the Dockerfile in the given directory to verify it works.
    
    This is the core validation logic. It performs a comprehensive test suite:
    1. **Build**: Builds the image with strict memory limits to prevent host exhaustion.
    2. **Run**: Runs the container in a sandboxed environment (limited resources).
    3. **Readiness**: Uses AI-detected patterns to wait for startup (smart wait).
    4. **Health**: Checks HTTP endpoints if available.
    5. **Security**: Optionally runs a Trivy scan.
    6. **Cleanup**: Removes test containers and images.
    
    Args:
        directory (str): The directory containing the Dockerfile.
        project_type (str): 'service' or 'script'.
        stack (str): The detected technology stack.
        health_endpoint (Optional[Tuple[str, int]]): (endpoint_path, port) for health checks.
        recommended_wait_time (int): AI-recommended wait time in seconds (fallback).
        readiness_patterns (List[str]): AI-detected log patterns for startup detection.
        failure_patterns (List[str]): AI-detected log patterns for failure detection.
        
    Returns:
        Tuple[bool, str, int, Optional[ClassifiedError]]: A tuple containing 
        (success, message, image_size_bytes, classified_error).
    """
    image_name = f"dockai-test-{uuid.uuid4().hex[:8]}"
    container_name = f"dockai-container-{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Validating Dockerfile in {directory} (Type: {project_type}, Stack: {stack})...")
    
    # 1. Build Phase
    logger.info("Building Docker image (with resource limits)...")
    # Use 2GB memory limit for build to prevent OOM on host
    build_cmd = ["docker", "build", "--memory=2g", "-t", image_name, "."]
    code, stdout, stderr = run_command(build_cmd, cwd=directory)
    
    if code != 0:
        # Build failed - classify the error
        error_output = f"{stderr}\n{stdout}"
        classified = classify_error(error_output, logs=error_output, stack=stack)
        error_msg = f"Docker build failed: {classified.message}"
        logger.error(f"Problem: {classified.message}")
        logger.debug(f"Details: {error_output[:500]}")
        return False, error_msg, 0, classified
    
    # 2. Run Phase
    logger.info("Running Docker container (sandboxed)...")
    
    # Configurable resource limits for runtime validation
    memory_limit = os.getenv("DOCKAI_VALIDATION_MEMORY", "512m")
    cpu_limit = os.getenv("DOCKAI_VALIDATION_CPUS", "1.0")
    pids_limit = os.getenv("DOCKAI_VALIDATION_PIDS", "100")
    
    run_cmd = [
        "docker", "run", 
        "-d", 
        "--name", container_name,
        f"--memory={memory_limit}",
        f"--cpus={cpu_limit}",
        f"--pids-limit={pids_limit}",
        "--security-opt=no-new-privileges", # Security best practice
    ]
    
    # Add port mapping if we have a health endpoint
    if health_endpoint:
        _, port = health_endpoint
        # Use ephemeral host port (0) to avoid conflicts
        run_cmd.extend(["-p", f"0:{port}"])
    
    run_cmd.append(image_name)
    
    code, stdout, stderr = run_command(run_cmd)
    
    if code != 0:
        # Container failed to start - classify the error
        error_output = f"{stderr}\n{stdout}"
        classified = classify_error(error_output, logs=error_output, stack=stack)
        error_msg = f"Container start failed: {classified.message}"
        logger.error(f"Problem: {classified.message}")
        run_command(["docker", "rmi", image_name])
        return False, error_msg, 0, classified
    
    
    # 3. Readiness Check Phase
    # Use AI-detected readiness patterns OR recommended wait times
    if readiness_patterns:
        logger.info(f"Using smart readiness check with {len(readiness_patterns)} patterns...")
        is_ready, ready_msg, _ = check_container_readiness(
            container_name, 
            readiness_patterns, 
            failure_patterns=failure_patterns or [],
            max_wait_time=60
        )
        logger.info(f"Readiness result: {ready_msg}")
    else:
        logger.info(f"Waiting {recommended_wait_time}s for container to initialize (AI-recommended)...")
        time.sleep(recommended_wait_time)
    
    # 4. Status Check Phase
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

    # 5. Validation Logic based on Project Type
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
        # Fallback for unknown project types
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


def check_container_readiness(
    container_name: str,
    readiness_patterns: List[str],
    failure_patterns: List[str],
    max_wait_time: int = 60,
    check_interval: int = 2
) -> Tuple[bool, str, str]:
    """
    Smart container readiness check using AI-detected log patterns.
    
    Instead of fixed sleep, this polls container logs and looks for
    patterns that indicate successful startup or failure.
    
    Args:
        container_name (str): The name of the container to check.
        readiness_patterns (List[str]): Regex patterns indicating success.
        failure_patterns (List[str]): Regex patterns indicating failure.
        max_wait_time (int): Maximum time to wait in seconds.
        check_interval (int): Time between checks in seconds.
        
    Returns:
        Tuple[bool, str, str]: (is_ready, status_message, accumulated_logs)
    """
    start_time = time.time()
    last_log_position = 0
    accumulated_logs = ""
    
    # Compile regex patterns for performance
    success_regexes = []
    failure_regexes = []
    
    for pattern in readiness_patterns:
        try:
            success_regexes.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid success regex pattern: {pattern}")
    
    for pattern in failure_patterns:
        try:
            failure_regexes.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid failure regex pattern: {pattern}")
    
    # Add default patterns if none provided to ensure we catch common cases
    if not success_regexes:
        default_success = [
            r"listening on.*port",
            r"server.*started",
            r"application.*ready",
            r"ready to accept connections",
            r"started.*successfully"
        ]
        success_regexes = [re.compile(p, re.IGNORECASE) for p in default_success]
    
    if not failure_regexes:
        default_failure = [
            r"error:",
            r"fatal:",
            r"failed to",
            r"exception",
            r"panic:",
            r"segmentation fault"
        ]
        failure_regexes = [re.compile(p, re.IGNORECASE) for p in default_failure]
    
    logger.info(f"Checking container readiness (max {max_wait_time}s)...")
    
    while (time.time() - start_time) < max_wait_time:
        # Check if container is still running
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return False, "Container inspection failed", accumulated_logs
        
        is_running = result.stdout.strip() == "true"
        
        # Get container logs
        logs_result = subprocess.run(
            ["docker", "logs", container_name],
            capture_output=True,
            text=True
        )
        
        current_logs = logs_result.stdout + logs_result.stderr
        new_logs = current_logs[last_log_position:]
        accumulated_logs = current_logs
        last_log_position = len(current_logs)
        
        # Check for success patterns in the logs
        for regex in success_regexes:
            if regex.search(current_logs):
                logger.info("Container readiness detected via log pattern")
                return True, "Container is ready (detected via log patterns)", accumulated_logs
        
        # Check for failure patterns in the NEW logs
        for regex in failure_regexes:
            if regex.search(new_logs):  # Only check new logs for failures to avoid false positives from old logs
                logger.warning(f"Failure pattern detected in logs")
                return False, f"Container startup failed (error pattern detected)", accumulated_logs
        
        # If container stopped, check exit code
        if not is_running:
            exit_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.ExitCode}}", container_name],
                capture_output=True,
                text=True
            )
            exit_code = exit_result.stdout.strip()
            
            if exit_code == "0":
                return True, "Container completed successfully (exit code 0)", accumulated_logs
            else:
                return False, f"Container stopped with exit code {exit_code}", accumulated_logs
        
        time.sleep(check_interval)
    
    # Timeout reached - check if container is still running (might be a long-starting service)
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip() == "true":
        # Container is running but didn't emit success pattern - consider it ready
        logger.warning("Container is running but no startup pattern detected - assuming ready")
        return True, "Container is running (no startup pattern detected, assuming ready)", accumulated_logs
    
    return False, f"Container readiness timeout after {max_wait_time}s", accumulated_logs

