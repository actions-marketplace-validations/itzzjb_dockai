import re
import logging
from typing import List, Tuple

logger = logging.getLogger("dockai")

def parse_docker_error(error_output: str) -> Tuple[str, List[str]]:
    """
    Parse Docker build/run errors and provide human-readable explanations with fixes.
    
    Args:
        error_output (str): The raw error output from Docker.
        
    Returns:
        Tuple[str, List[str]]: (error_type, suggested_fixes)
    """
    
    error_output_lower = error_output.lower()
    
    # Pattern matching for common errors
    error_patterns = {
        "missing_file": {
            "patterns": [
                r"no such file or directory",
                r"cannot find",
                r"not found",
                r"failed to compute cache key.*not found"
            ],
            "type": "Missing File or Directory",
            "fixes": [
                "Ensure all files referenced in COPY commands exist in your project",
                "Check that file paths are relative to the build context (usually project root)",
                "Verify .dockerignore is not excluding required files",
                "For lock files (go.sum, package-lock.json), run 'go mod tidy' or 'npm install' first"
            ]
        },
        "permission_denied": {
            "patterns": [
                r"permission denied",
                r"cannot access",
                r"operation not permitted"
            ],
            "type": "Permission Denied",
            "fixes": [
                "Ensure the Dockerfile uses appropriate file permissions",
                "Check that the non-root user has access to required directories",
                "Use 'RUN chown -R user:group /path' to fix ownership",
                "Verify the base image supports the required operations"
            ]
        },
        "network_error": {
            "patterns": [
                r"failed to fetch",
                r"connection refused",
                r"network.*timeout",
                r"could not resolve host",
                r"temporary failure in name resolution"
            ],
            "type": "Network Error",
            "fixes": [
                "Check your internet connection",
                "Verify package repository URLs are correct",
                "Try using a different package mirror if available",
                "Check if you're behind a proxy and configure Docker accordingly"
            ]
        },
        "package_not_found": {
            "patterns": [
                r"package.*not found",
                r"module.*not found",
                r"unable to locate package",
                r"no matching distribution found",
                r"could not find.*version"
            ],
            "type": "Package Not Found",
            "fixes": [
                "Verify the package name is spelled correctly",
                "Check that the package version exists in the repository",
                "Update package manager indexes (apt-get update, apk update, etc.)",
                "For Python: Ensure requirements.txt has correct package names",
                "For Node: Check package.json for typos",
                "For Go: Run 'go mod tidy' to sync dependencies"
            ]
        },
        "syntax_error": {
            "patterns": [
                r"syntax error",
                r"unexpected.*expecting",
                r"invalid.*instruction",
                r"unknown instruction"
            ],
            "type": "Dockerfile Syntax Error",
            "fixes": [
                "Check Dockerfile syntax - each instruction should be on a new line",
                "Ensure proper escaping of special characters",
                "Verify ENV instructions don't have inline comments",
                "Use proper JSON array format for CMD/ENTRYPOINT: [\"cmd\", \"arg1\"]"
            ]
        },
        "out_of_memory": {
            "patterns": [
                r"out of memory",
                r"cannot allocate memory",
                r"killed.*memory"
            ],
            "type": "Out of Memory",
            "fixes": [
                "Increase Docker memory limits",
                "Use multi-stage builds to reduce final image size",
                "Clean up temporary files in the same RUN command",
                "Consider using Alpine-based images for smaller footprint"
            ]
        },
        "port_conflict": {
            "patterns": [
                r"port.*already.*allocated",
                r"address already in use",
                r"bind.*failed.*port"
            ],
            "type": "Port Conflict",
            "fixes": [
                "Stop other containers using the same port",
                "Use 'docker ps' to check running containers",
                "Change the port mapping in docker run command",
                "Use 'docker rm -f <container>' to force remove conflicting containers"
            ]
        },
        "base_image_error": {
            "patterns": [
                r"pull access denied",
                r"manifest.*not found",
                r"image.*not found",
                r"no such image"
            ],
            "type": "Base Image Error",
            "fixes": [
                "Verify the base image name and tag are correct",
                "Check if the image exists on Docker Hub or your registry",
                "Try using a specific version tag instead of 'latest'",
                "Ensure you have access to private registries if applicable"
            ]
        },
        "build_command_failed": {
            "patterns": [
                r"returned a non-zero code",
                r"command.*failed",
                r"error.*exit status"
            ],
            "type": "Build Command Failed",
            "fixes": [
                "Check the command output for specific error messages",
                "Verify all build dependencies are installed",
                "Ensure the working directory is set correctly with WORKDIR",
                "Try running the command manually to debug",
                "Check for missing environment variables"
            ]
        }
    }
    
    # Find matching error pattern
    for error_key, error_info in error_patterns.items():
        for pattern in error_info["patterns"]:
            if re.search(pattern, error_output_lower):
                logger.info(f"Identified error type: {error_info['type']}")
                return error_info["type"], error_info["fixes"]
    
    # Generic fallback
    return "Unknown Error", [
        "Review the full error output above for specific details",
        "Check Docker documentation for the failing command",
        "Verify all file paths and dependencies are correct",
        "Try building with --no-cache flag to rule out caching issues"
    ]

def format_error_message(error_type: str, error_output: str, suggested_fixes: List[str]) -> str:
    """
    Format a user-friendly error message with suggestions.
    
    Args:
        error_type (str): The identified error type.
        error_output (str): The raw error output.
        suggested_fixes (List[str]): List of suggested fixes.
        
    Returns:
        str: Formatted error message.
    """
    
    # Extract the most relevant error line
    error_lines = error_output.strip().split('\n')
    relevant_error = ""
    
    for line in reversed(error_lines):
        if any(keyword in line.lower() for keyword in ["error", "failed", "fatal", "exception"]):
            relevant_error = line.strip()
            break
    
    if not relevant_error and error_lines:
        relevant_error = error_lines[-1].strip()
    
    message = f"\n{'='*80}\n"
    message += f"❌ {error_type}\n"
    message += f"{'='*80}\n\n"
    
    if relevant_error:
        message += f"Error Details:\n{relevant_error}\n\n"
    
    message += "💡 Suggested Fixes:\n"
    for i, fix in enumerate(suggested_fixes, 1):
        message += f"  {i}. {fix}\n"
    
    message += f"\n{'='*80}\n"
    
    return message

def enhance_error_feedback(error_output: str) -> str:
    """
    Main function to enhance error messages with human-readable explanations.
    
    Args:
        error_output (str): The raw error output from Docker.
        
    Returns:
        str: Enhanced error message with suggestions.
    """
    error_type, suggested_fixes = parse_docker_error(error_output)
    return format_error_message(error_type, error_output, suggested_fixes)
