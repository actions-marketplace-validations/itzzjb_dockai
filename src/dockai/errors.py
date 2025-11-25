"""
DockAI Error Classification System

This module provides AI-powered error classification to distinguish between:
1. PROJECT_ERROR: Developer-side issues that cannot be fixed by regenerating the Dockerfile
   (e.g., missing lock files, invalid code, missing dependencies)
2. DOCKERFILE_ERROR: Issues with the generated Dockerfile that can potentially be fixed by retry
   (e.g., wrong base image, incorrect commands, build failures)
3. ENVIRONMENT_ERROR: Issues with the local environment (Docker not running, network issues)

The classification is done dynamically using AI, making it work for any programming language.
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger("dockai")


class ErrorType(Enum):
    """Classification of error types."""
    PROJECT_ERROR = "project_error"       # Developer must fix - no retry
    DOCKERFILE_ERROR = "dockerfile_error"  # Can be fixed by retry
    ENVIRONMENT_ERROR = "environment_error"  # Local setup issue - no retry
    UNKNOWN_ERROR = "unknown_error"        # Default - attempt retry


class ErrorAnalysisResult(BaseModel):
    """Structured output for AI error analysis."""
    error_type: Literal["project_error", "dockerfile_error", "environment_error", "unknown_error"] = Field(
        description="Classification of the error: 'project_error' for issues the developer must fix in their code/config, 'dockerfile_error' for issues that can be fixed by regenerating the Dockerfile, 'environment_error' for local Docker/system issues, 'unknown_error' if unclear"
    )
    problem_summary: str = Field(
        description="A clear, one-sentence summary of what went wrong"
    )
    root_cause: str = Field(
        description="The underlying cause of the error"
    )
    suggestion: str = Field(
        description="Actionable steps the user should take to fix this issue. Include exact commands if applicable."
    )
    can_retry: bool = Field(
        description="True if regenerating the Dockerfile might fix this, False if the user must take action first"
    )
    thought_process: str = Field(
        description="Step-by-step reasoning about the error classification"
    )
    # New fields for smarter recovery
    dockerfile_fix: Optional[str] = Field(
        default=None,
        description="If this is a Dockerfile error, provide the specific fix to apply (e.g., 'use standard image for build stage', 'add apt-get install libcap2-bin')"
    )
    image_suggestion: Optional[str] = Field(
        default=None,
        description="If the error is related to missing dependencies in the image, suggest a better base image (e.g., use standard/full variant for build stage instead of slim/alpine to get system packages)"
    )


@dataclass
class ClassifiedError:
    """Represents a classified error with details."""
    error_type: ErrorType
    message: str
    suggestion: str
    original_error: str
    should_retry: bool
    dockerfile_fix: Optional[str] = None  # Specific fix for Dockerfile issues
    image_suggestion: Optional[str] = None  # Better image to use
    
    def to_dict(self):
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "original_error": self.original_error,
            "should_retry": self.should_retry,
            "dockerfile_fix": self.dockerfile_fix,
            "image_suggestion": self.image_suggestion
        }


def analyze_error_with_ai(error_message: str, logs: str = "", stack: str = "") -> ClassifiedError:
    """
    Use AI to analyze and classify an error.
    
    This works for any programming language or framework - the AI will understand
    the error context and provide appropriate classification and suggestions.
    
    Args:
        error_message: The error message to classify
        logs: Additional logs for context
        stack: The technology stack being used
        
    Returns:
        ClassifiedError with type, message, and suggestions
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from .callbacks import TokenUsageCallback
    
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        structured_llm = llm.with_structured_output(ErrorAnalysisResult)
        
        system_prompt = """You are an expert DevOps engineer working as an autonomous AI agent, analyzing Docker build and runtime errors.
You have deep knowledge of ALL programming languages, frameworks, package managers, and build systems.
Your goal is to analyze errors like a senior engineer would - understanding the root cause and providing actionable solutions.

You must work with ANY technology stack - do not limit yourself to specific languages or frameworks.

THINK STEP BY STEP like an AI agent:
1. Read the error carefully
2. Identify the exact failure point
3. Determine if this is a user's project issue or a Dockerfile generation issue
4. If it's fixable by regenerating the Dockerfile, explain HOW to fix it

ERROR CLASSIFICATION RULES:

1. PROJECT_ERROR (Developer must fix - no retry):
   - Missing lock files for the project's package manager (dependency lock files that should be committed)
   - Syntax errors in source code
   - Import/module/package errors in source code
   - Missing required project configuration files
   - Invalid configuration files (malformed syntax)
   - Missing entry point files referenced in code
   - Dependency version conflicts that require manual resolution
   - Missing environment variables that should be defined by the user
   - Code compilation errors in the source code itself
   - Test failures in source code
   - Missing required arguments for scripts

2. DOCKERFILE_ERROR (Can be fixed by regenerating Dockerfile - AI can learn):
   - Wrong base image or tag selection
   - Missing system packages required for build or runtime
   - Incorrect build or run commands in Dockerfile
   - Missing or wrong WORKDIR configuration
   - COPY/ADD commands with incorrect paths
   - SOURCE FILES NOT COPIED TO CONTAINER (COPY missed application code)
   - Permission issues that can be fixed with chmod/chown
   - Missing package installation commands
   - Image size issues (can use different base image or multi-stage)
   - Health check configuration issues
   - Port exposure issues
   - User/group creation syntax errors
   - Binary compatibility issues between build and runtime environments
   - Missing runtime dependencies in final stage
   - Executable not found in runtime stage (binary built but not properly copied or incompatible)
   
   IMPORTANT FOR DOCKERFILE ERRORS:
   - If error says a command/tool is not found, the fix is to install the appropriate package
   - If using minimal images and build fails due to missing tools, suggest using a fuller image for BUILD stage
   - If binary built in one environment fails in another, suggest using compatible environments OR static linking
   - Always consider multi-stage builds: appropriate image for build, minimal for runtime
   - Provide specific dockerfile_fix with exact changes needed
   
   CRITICAL - SOURCE FILE NOT FOUND IN CONTAINER:
   - If error says a source file is missing or not found:
     This is ALWAYS a DOCKERFILE_ERROR because the COPY command didn't copy the source files!
     - The file exists in the project, but the Dockerfile failed to COPY it to the container
     - dockerfile_fix MUST indicate adding COPY command for the missing source files
     - This is NOT a project error - the file exists, it just wasn't copied
   
   CRITICAL - BINARY NOT FOUND / EXECUTABLE NOT FOUND ERRORS:
   - If error says an executable is "not found" or "No such file or directory" for a binary that EXISTS:
     This is likely a binary compatibility issue between build and runtime environments
     - dockerfile_fix MUST explain: Use static linking OR use compatible build/runtime environments
     - image_suggestion: Suggest using compatible base images for both stages

3. ENVIRONMENT_ERROR (Local system issue - no retry):
   - Docker daemon not running
   - Network connectivity issues (cannot pull images)
   - Disk space issues
   - Memory issues (OOM)
   - Docker permission issues on host system
   - Docker socket issues

4. UNKNOWN_ERROR (Cannot determine - attempt retry):
   - Use this only if the error is truly ambiguous

IMAGE SELECTION STRATEGY (for dockerfile_fix and image_suggestion):
- BUILD STAGE: Use images with build tools appropriate for the detected technology
- RUNTIME STAGE: Use minimal images appropriate for the technology, ensuring compatibility
- If error mentions missing system tool in minimal image, suggest fuller image for BUILD
- For compiled code, prefer static linking to allow maximum flexibility in runtime image choice

IMPORTANT:
- Be specific about what file or command the user needs to create/run
- For PROJECT_ERROR, include the exact command or action to fix it
- For DOCKERFILE_ERROR, always provide dockerfile_fix with the specific change needed
- Consider the technology stack when determining the root cause
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", """Analyze this error and classify it:

Technology Stack: {stack}

Error Message:
{error_message}

Container/Build Logs:
{logs}

Classify this error and provide guidance.""")
        ])
        
        chain = prompt | structured_llm
        
        # Use callback to track tokens (optional, for logging)
        callback = TokenUsageCallback()
        
        result = chain.invoke(
            {
                "stack": stack or "Unknown",
                "error_message": error_message[:2000],  # Limit size
                "logs": logs[:3000] if logs else "No additional logs"
            },
            config={"callbacks": [callback]}
        )
        
        # Log token usage
        usage = callback.get_usage()
        logger.debug(f"Error analysis used {usage.get('total_tokens', 0)} tokens")
        
        # Map string to enum
        error_type_map = {
            "project_error": ErrorType.PROJECT_ERROR,
            "dockerfile_error": ErrorType.DOCKERFILE_ERROR,
            "environment_error": ErrorType.ENVIRONMENT_ERROR,
            "unknown_error": ErrorType.UNKNOWN_ERROR
        }
        
        error_type = error_type_map.get(result.error_type, ErrorType.UNKNOWN_ERROR)
        
        logger.debug(f"AI Error Analysis: {result.thought_process}")
        
        return ClassifiedError(
            error_type=error_type,
            message=result.problem_summary,
            suggestion=result.suggestion,
            original_error=error_message[:500],
            should_retry=result.can_retry,
            dockerfile_fix=result.dockerfile_fix,
            image_suggestion=result.image_suggestion
        )
        
    except Exception as e:
        logger.error(f"Problem: AI error analysis failed - {e}")
        # Return unknown error - let user see the raw error and decide
        return ClassifiedError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Error analysis failed - see details below",
            suggestion="Check the error details and logs. If the issue persists, please report it.",
            original_error=error_message[:500],
            should_retry=True
        )


def classify_error(error_message: str, logs: str = "", stack: str = "") -> ClassifiedError:
    """
    Classify an error using AI.
    
    This function works for ANY programming language or framework.
    The AI dynamically analyzes the error and provides appropriate guidance.
    
    Args:
        error_message: The error message to classify
        logs: Additional logs for context  
        stack: The technology stack being used (helps AI give better suggestions)
        
    Returns:
        ClassifiedError with type, message, and suggestions
    """
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("Problem: OPENAI_API_KEY not set - cannot analyze error")
        return ClassifiedError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message="Cannot analyze error - API key not configured",
            suggestion="Set OPENAI_API_KEY in your .env file to enable AI error analysis",
            original_error=error_message[:500],
            should_retry=True
        )
    
    return analyze_error_with_ai(error_message, logs, stack)


def format_error_for_display(classified_error: ClassifiedError, verbose: bool = False) -> str:
    """
    Format a classified error for user-friendly display.
    
    Args:
        classified_error: The classified error to format
        verbose: Whether to include full original error
        
    Returns:
        Formatted error string
    """
    error_type_display = {
        ErrorType.PROJECT_ERROR: "[PROJECT ERROR] Fix Required",
        ErrorType.DOCKERFILE_ERROR: "[DOCKERFILE ERROR] Retrying...",
        ErrorType.ENVIRONMENT_ERROR: "[ENVIRONMENT ERROR]",
        ErrorType.UNKNOWN_ERROR: "[UNKNOWN ERROR]"
    }
    
    lines = [
        f"\n{'='*60}",
        f"{error_type_display.get(classified_error.error_type, 'Error')}",
        f"{'='*60}",
        f"\nProblem: {classified_error.message}",
        f"\nSolution: {classified_error.suggestion}",
    ]
    
    if verbose and classified_error.original_error:
        lines.extend([
            f"\nDetails:",
            f"   {classified_error.original_error[:300]}..."
        ])
    
    if not classified_error.should_retry:
        lines.append(f"\nThis error cannot be fixed by retrying. Please fix the issue and try again.")
    
    lines.append(f"{'='*60}\n")
    
    return "\n".join(lines)
