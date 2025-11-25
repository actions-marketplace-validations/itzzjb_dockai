import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger("dockai")

def detect_health_endpoint(file_contents: str, stack: str) -> Optional[Tuple[str, int]]:
    """
    Detect health check endpoints from application code.
    
    Scans for common health check patterns in various frameworks:
    - Express.js: app.get('/health', ...)
    - Flask/FastAPI: @app.get('/health')
    - Go: http.HandleFunc("/health", ...)
    - Spring Boot: @GetMapping("/health")
    
    Args:
        file_contents (str): The concatenated contents of critical files.
        stack (str): The detected technology stack.
        
    Returns:
        Optional[Tuple[str, int]]: (endpoint_path, port) if found, None otherwise.
    """
    
    # Common health check endpoint patterns
    health_patterns = [
        r'["\']/(health|healthz|ping|status|ready|live|liveness|readiness)["\']',
        r'@app\.(get|route)\(["\']/(health|healthz|ping)["\']',
        r'app\.get\(["\']/(health|healthz|ping)["\']',
        r'http\.HandleFunc\(["\']/(health|healthz|ping)["\']',
        r'@GetMapping\(["\']/(health|healthz|ping)["\']',
        r'@RequestMapping\(["\']/(health|healthz|ping)["\']',
    ]
    
    detected_endpoint = None
    
    for pattern in health_patterns:
        match = re.search(pattern, file_contents, re.IGNORECASE)
        if match:
            # Extract the endpoint path - look for the full path including variations
            endpoint_match = re.search(r'/(health\w*|ping|status|ready|live\w*)', match.group(), re.IGNORECASE)
            if endpoint_match:
                detected_endpoint = endpoint_match.group().lower()
                logger.info(f"Detected health check endpoint: {detected_endpoint}")
                break
    
    # Detect port from common patterns
    port = detect_port(file_contents, stack)
    
    if detected_endpoint:
        return (detected_endpoint, port)
    
    # Fallback: Use common defaults based on stack
    default_endpoints = {
        "node": ("/health", 3000),
        "express": ("/health", 3000),
        "python": ("/health", 8000),
        "flask": ("/health", 5000),
        "fastapi": ("/health", 8000),
        "django": ("/health", 8000),
        "go": ("/health", 8080),
        "spring": ("/actuator/health", 8080),
        "java": ("/health", 8080),
    }
    
    stack_lower = stack.lower()
    for key, (endpoint, default_port) in default_endpoints.items():
        if key in stack_lower:
            logger.info(f"Using default health endpoint for {key}: {endpoint}:{default_port}")
            return (endpoint, default_port)
    
    return None

def detect_port(file_contents: str, stack: str) -> int:
    """
    Detect the port the application listens on.
    
    Args:
        file_contents (str): The concatenated contents of critical files.
        stack (str): The detected technology stack.
        
    Returns:
        int: The detected port, or a default based on stack.
    """
    
    # Port detection patterns
    port_patterns = [
        r'listen\((\d+)',                    # Go: http.ListenAndServe(":8080", nil)
        r'listen\(["\']:(\d+)["\']',         # Node: server.listen(3000)
        r'port["\']?\s*[:=]\s*(\d+)',        # Generic: port: 3000, PORT=3000
        r'PORT\s*=\s*(\d+)',                 # ENV: PORT=8080
        r'server\.port\s*=\s*(\d+)',         # Spring: server.port=8080
        r'app\.run\(.*port\s*=\s*(\d+)',     # Flask: app.run(port=5000)
        r'uvicorn\.run\(.*port\s*=\s*(\d+)', # FastAPI: uvicorn.run(app, port=8000)
    ]
    
    for pattern in port_patterns:
        match = re.search(pattern, file_contents, re.IGNORECASE)
        if match:
            port = int(match.group(1))
            logger.info(f"Detected port: {port}")
            return port
    
    # Fallback to stack-based defaults
    default_ports = {
        "node": 3000,
        "express": 3000,
        "python": 8000,
        "flask": 5000,
        "fastapi": 8000,
        "django": 8000,
        "go": 8080,
        "spring": 8080,
        "java": 8080,
    }
    
    stack_lower = stack.lower()
    for key, default_port in default_ports.items():
        if key in stack_lower:
            logger.info(f"Using default port for {key}: {default_port}")
            return default_port
    
    # Ultimate fallback
    logger.warning("Could not detect port, using default: 8080")
    return 8080
