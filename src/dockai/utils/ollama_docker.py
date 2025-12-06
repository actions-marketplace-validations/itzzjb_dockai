"""
DockAI Ollama Docker Support.

This module provides functionality to run Ollama via Docker when it's not
installed locally. Similar to how Trivy falls back to its Docker image,
this allows users to use Ollama-based models without installing Ollama.

Usage:
    The module automatically detects if Ollama is available locally.
    If not, it starts an Ollama container and manages its lifecycle.
"""

import os
import time
import logging
import subprocess
import atexit
from typing import Optional, Tuple

import httpx

logger = logging.getLogger("dockai")

# Global state for container management
_ollama_container_id: Optional[str] = None
_ollama_docker_url: Optional[str] = None

# Default Ollama Docker configuration
OLLAMA_DOCKER_IMAGE = "ollama/ollama:latest"
OLLAMA_CONTAINER_NAME = "dockai-ollama"
OLLAMA_DEFAULT_PORT = 11434


def is_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """
    Check if Ollama is available at the given URL.
    
    Args:
        base_url: The Ollama API base URL to check.
        
    Returns:
        bool: True if Ollama is responding, False otherwise.
    """
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def is_ollama_installed() -> bool:
    """
    Check if Ollama CLI is installed locally.
    
    Returns:
        bool: True if Ollama is installed, False otherwise.
    """
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_docker_available() -> bool:
    """
    Check if Docker is available and running.
    
    Returns:
        bool: True if Docker is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _find_available_port(start_port: int = 11434) -> int:
    """Find an available port starting from the given port."""
    import socket
    
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    
    raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + 100}")


def _run_command(cmd: list) -> Tuple[int, str, str]:
    """Run a command and return (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for model pulls
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def start_ollama_container(model_name: str = "llama3") -> str:
    """
    Start an Ollama Docker container and pull the specified model.
    
    Args:
        model_name: The model to pull and use (default: llama3).
        
    Returns:
        str: The base URL for the Ollama API in the container.
        
    Raises:
        RuntimeError: If the container fails to start or model fails to pull.
    """
    global _ollama_container_id, _ollama_docker_url
    
    # If we already have a running container, return its URL
    if _ollama_container_id and _ollama_docker_url:
        if is_ollama_available(_ollama_docker_url):
            return _ollama_docker_url
    
    if not is_docker_available():
        raise RuntimeError(
            "Docker is not available. Please install Docker or Ollama locally.\n"
            "  - Install Docker: https://docs.docker.com/get-docker/\n"
            "  - Install Ollama: https://ollama.ai/download"
        )
    
    logger.info("Ollama not found locally. Starting Ollama via Docker...")
    
    # Check if there's an existing container we can reuse
    check_cmd = ["docker", "ps", "-a", "-q", "-f", f"name={OLLAMA_CONTAINER_NAME}"]
    code, stdout, _ = _run_command(check_cmd)
    
    if code == 0 and stdout.strip():
        existing_container = stdout.strip()
        logger.debug(f"Found existing Ollama container: {existing_container}")
        
        # Check if it's running
        inspect_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", existing_container]
        code, running, _ = _run_command(inspect_cmd)
        
        if code == 0 and running.strip() == "true":
            # Get the port mapping
            port_cmd = ["docker", "port", existing_container, "11434"]
            code, port_out, _ = _run_command(port_cmd)
            
            if code == 0 and port_out.strip():
                # Parse port like "0.0.0.0:11434" or ":::11434"
                port_mapping = port_out.strip().split(":")[-1]
                _ollama_docker_url = f"http://localhost:{port_mapping}"
                _ollama_container_id = existing_container
                
                if is_ollama_available(_ollama_docker_url):
                    logger.info(f"Reusing existing Ollama container at {_ollama_docker_url}")
                    return _ollama_docker_url
        
        # Container exists but not running properly, remove it
        logger.debug("Removing stale Ollama container...")
        _run_command(["docker", "rm", "-f", existing_container])
    
    # Find an available port
    port = _find_available_port(OLLAMA_DEFAULT_PORT)
    _ollama_docker_url = f"http://localhost:{port}"
    
    # Pull the Ollama image first
    logger.info(f"Pulling Ollama Docker image ({OLLAMA_DOCKER_IMAGE})...")
    pull_cmd = ["docker", "pull", OLLAMA_DOCKER_IMAGE]
    code, _, stderr = _run_command(pull_cmd)
    
    if code != 0:
        logger.warning(f"Failed to pull latest Ollama image: {stderr}")
        # Continue anyway, might have a cached image
    
    # Start the container
    logger.info(f"Starting Ollama container on port {port}...")
    
    run_cmd = [
        "docker", "run", "-d",
        "--name", OLLAMA_CONTAINER_NAME,
        "-p", f"{port}:11434",
        "-v", "ollama_models:/root/.ollama",  # Persist models
        OLLAMA_DOCKER_IMAGE
    ]
    
    code, container_id, stderr = _run_command(run_cmd)
    
    if code != 0:
        raise RuntimeError(f"Failed to start Ollama container: {stderr}")
    
    _ollama_container_id = container_id.strip()
    logger.debug(f"Started Ollama container: {_ollama_container_id[:12]}")
    
    # Register cleanup handler
    atexit.register(stop_ollama_container)
    
    # Wait for Ollama to be ready
    logger.info("Waiting for Ollama to be ready...")
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if is_ollama_available(_ollama_docker_url):
            logger.info(f"Ollama is ready at {_ollama_docker_url}")
            break
        time.sleep(2)
    else:
        stop_ollama_container()
        raise RuntimeError(f"Ollama container failed to start within {max_wait} seconds")
    
    # Pull the model inside the container
    logger.info(f"Pulling model '{model_name}' (this may take a few minutes on first run)...")
    
    pull_model_cmd = [
        "docker", "exec", _ollama_container_id,
        "ollama", "pull", model_name
    ]
    
    code, stdout, stderr = _run_command(pull_model_cmd)
    
    if code != 0:
        logger.warning(f"Failed to pull model {model_name}: {stderr}")
        # Don't fail here - the model might already exist or will be pulled on first use
    else:
        logger.info(f"Model '{model_name}' is ready")
    
    return _ollama_docker_url


def stop_ollama_container() -> None:
    """
    Stop and remove the Ollama Docker container.
    
    This is registered as an atexit handler but can also be called manually.
    """
    global _ollama_container_id, _ollama_docker_url
    
    if _ollama_container_id:
        logger.debug(f"Stopping Ollama container: {_ollama_container_id[:12]}")
        
        # Stop the container (don't remove - preserve cached models)
        _run_command(["docker", "stop", _ollama_container_id])
        
        _ollama_container_id = None
        _ollama_docker_url = None


def get_ollama_url(model_name: str = "llama3", preferred_url: str = "http://localhost:11434") -> str:
    """
    Get the Ollama API URL, starting Docker container if necessary.
    
    This is the main entry point for getting an Ollama URL. It:
    1. Checks if Ollama is available at the preferred URL
    2. If not, checks if Ollama is installed locally and starts it
    3. If not installed, starts Ollama via Docker
    
    Args:
        model_name: The model to ensure is available (for Docker fallback).
        preferred_url: The preferred Ollama URL to check first.
        
    Returns:
        str: The Ollama API base URL to use.
        
    Raises:
        RuntimeError: If Ollama cannot be made available.
    """
    # Check if Ollama is already available at preferred URL
    if is_ollama_available(preferred_url):
        logger.debug(f"Using existing Ollama at {preferred_url}")
        return preferred_url
    
    # Check if we already have a Docker container running
    if _ollama_docker_url and is_ollama_available(_ollama_docker_url):
        return _ollama_docker_url
    
    # Check if Ollama is installed locally but not running
    if is_ollama_installed():
        logger.warning(
            "Ollama is installed but not running. "
            "Please start Ollama with: ollama serve"
        )
        # Fall through to Docker fallback
    
    # Start Ollama via Docker
    return start_ollama_container(model_name)


