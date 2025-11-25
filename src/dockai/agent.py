"""
DockAI Adaptive Agent Module

This module contains AI-powered components that make DockAI a truly adaptive agent:
- Planning: Strategize before generation
- Reflection: Learn from failures
- Health Detection: Detect endpoints from code
- Readiness Detection: Smart container startup detection

These components work together to create an agent that learns and improves
with each iteration, similar to how a human engineer would approach the problem.
"""

import os
import re
import logging
from typing import Tuple, Any, List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult
)
from .callbacks import TokenUsageCallback

logger = logging.getLogger("dockai")


def create_plan(
    analysis_result: Dict[str, Any],
    file_contents: str,
    retry_history: List[Dict[str, Any]] = None,
    custom_instructions: str = ""
) -> Tuple[PlanningResult, Dict[str, int]]:
    """
    AI-powered planning phase before Dockerfile generation.
    
    This creates a strategic plan based on:
    - Project analysis results
    - File contents
    - Previous retry history (learning from mistakes)
    - Custom user instructions
    
    Args:
        analysis_result: Dictionary containing analysis results.
        file_contents: String containing content of critical files.
        retry_history: List of previous attempts and failures.
        custom_instructions: Custom instructions from the user.

    Returns:
        Tuple of (PlanningResult, usage_dict).
    """
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.2,  # Slight creativity for strategy
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(PlanningResult)
    
    # Build retry history context
    retry_context = ""
    if retry_history and len(retry_history) > 0:
        retry_context = "\n\nPREVIOUS ATTEMPTS (LEARN FROM THESE):\n"
        for i, attempt in enumerate(retry_history, 1):
            retry_context += f"""
--- Attempt {i} ---
What was tried: {attempt.get('what_was_tried', 'Unknown')}
Why it failed: {attempt.get('why_it_failed', 'Unknown')}
Lesson learned: {attempt.get('lesson_learned', 'Unknown')}
Error type: {attempt.get('error_type', 'Unknown')}
"""
        retry_context += "\nDO NOT repeat the same mistakes. Apply the lessons learned."
    
    system_prompt = """You are a Senior DevOps Architect working as an autonomous AI agent, planning a Dockerfile generation strategy.

Your role is to THINK DEEPLY before any code is generated. Like a chess grandmaster,
you must anticipate problems and plan multiple moves ahead.

You must work with ANY programming language, framework, or technology stack.

PLANNING PRINCIPLES:
1.  **ANALYZE** the detected stack thoroughly - understand build requirements, runtime needs, and dependencies.
2.  **ANTICIPATE** challenges - what could go wrong? Compatibility issues? Missing packages? Binary incompatibilities?
3.  **STRATEGIZE** - choose the right approach for this specific project and technology.
4.  **LEARN** - if there are previous failed attempts, understand WHY they failed and AVOID those mistakes.

CRITICAL CONSIDERATIONS (Apply intelligently based on detected technology):
-   **Build environment requirements**: compilers, development tools, headers.
-   **Runtime environment requirements**: minimal dependencies for security and size.
-   **Binary/artifact compatibility** between build and runtime environments.
-   **Package manager artifacts** and where they are installed.
-   **Static vs dynamic linking** considerations for compiled code.

MULTI-STAGE BUILD STRATEGY:
-   **BUILD stage**: Use images with all necessary build tools for the detected technology.
-   **RUNTIME stage**: Use minimal images appropriate for the technology, ensuring compatibility.

{retry_context}

{custom_instructions}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Create a strategic plan for generating a Dockerfile.

PROJECT ANALYSIS:
Stack: {stack}
Project Type: {project_type}
Suggested Base Image: {suggested_base_image}
Build Command: {build_command}
Start Command: {start_command}

KEY FILE CONTENTS:
{file_contents}

Generate a comprehensive plan that will guide the Dockerfile generation.
Start by explaining your thought process in detail.""")
    ])
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "project_type": analysis_result.get("project_type", "service"),
            "suggested_base_image": analysis_result.get("suggested_base_image", ""),
            "build_command": analysis_result.get("build_command", "None detected"),
            "start_command": analysis_result.get("start_command", "None detected"),
            "file_contents": file_contents[:8000],  # Limit size
            "retry_context": retry_context,
            "custom_instructions": custom_instructions
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()


def reflect_on_failure(
    dockerfile_content: str,
    error_message: str,
    error_details: Dict[str, Any],
    analysis_result: Dict[str, Any],
    retry_history: List[Dict[str, Any]] = None,
    container_logs: str = ""
) -> Tuple[ReflectionResult, Dict[str, int]]:
    """
    AI-powered reflection on a failed Dockerfile attempt.
    
    This performs deep analysis of WHY something failed and HOW to fix it,
    learning from the failure to make the next attempt smarter.
    
    Args:
        dockerfile_content: The content of the failed Dockerfile.
        error_message: The error message returned.
        error_details: Detailed error information.
        analysis_result: Original analysis result.
        retry_history: History of previous retries.
        container_logs: Logs from the failed container.

    Returns:
        Tuple of (ReflectionResult, usage_dict).
    """
    model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")  # Use stronger model for reflection
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(ReflectionResult)
    
    # Build retry history context
    retry_context = ""
    if retry_history and len(retry_history) > 0:
        retry_context = "\n\nPREVIOUS FAILED ATTEMPTS:\n"
        for i, attempt in enumerate(retry_history, 1):
            retry_context += f"""
Attempt {i}: {attempt.get('what_was_tried', 'Unknown')} -> Failed: {attempt.get('why_it_failed', 'Unknown')}
"""
    
    system_prompt = """You are a Principal DevOps Engineer working as an autonomous AI agent, performing a POST-MORTEM analysis on a failed Dockerfile.

Your goal is to understand EXACTLY what went wrong and create a PRECISE fix.
Think like a senior engineer debugging a production incident.

You must work with ANY programming language, framework, or technology stack.

ANALYSIS FRAMEWORK:
1.  **IDENTIFY** the exact point of failure.
2.  **UNDERSTAND** the root cause (not just symptoms).
3.  **DETERMINE** if this is fixable by changing the Dockerfile or if it's a project issue.
4.  **CREATE** specific, actionable fixes.
5.  **ANTICIPATE** if this fix might cause other issues.

COMMON ROOT CAUSES (Apply intelligently based on detected technology):
-   Binary/runtime compatibility issues between build and runtime environments.
-   Missing build or runtime dependencies.
-   Incorrect commands for the detected technology.
-   Permission issues - files created as root, running as non-root.
-   Path issues - incorrect WORKDIR or COPY destinations.
-   Missing source files or artifacts not properly copied.

RE-ANALYSIS TRIGGERS (set needs_reanalysis=true):
-   Wrong technology/framework detected.
-   Missing critical configuration files.
-   Incorrect entrypoint assumptions.
-   Build system misidentified.

{retry_context}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze this failed Dockerfile and provide a detailed reflection.

FAILED DOCKERFILE:
{dockerfile}

ERROR MESSAGE:
{error_message}

ERROR CLASSIFICATION:
Type: {error_type}
Suggestion: {error_suggestion}

PROJECT CONTEXT:
Stack: {stack}
Project Type: {project_type}

CONTAINER LOGS:
{container_logs}

Perform a deep analysis and provide specific fixes.
Start by explaining your root cause analysis in the thought process.""")
    ])
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "dockerfile": dockerfile_content,
            "error_message": error_message,
            "error_type": error_details.get("error_type", "unknown"),
            "error_suggestion": error_details.get("suggestion", "None"),
            "stack": analysis_result.get("stack", "Unknown"),
            "project_type": analysis_result.get("project_type", "service"),
            "container_logs": container_logs[:3000] if container_logs else "No logs available",
            "retry_context": retry_context
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()


def detect_health_endpoints(
    file_contents: str,
    analysis_result: Dict[str, Any]
) -> Tuple[HealthEndpointDetectionResult, Dict[str, int]]:
    """
    AI-powered health endpoint detection from actual file contents.
    
    Instead of guessing from file names, this reads the actual code
    to find health check routes and their configurations.
    
    Args:
        file_contents: Content of files to analyze.
        analysis_result: Previous analysis result.

    Returns:
        Tuple of (HealthEndpointDetectionResult, usage_dict).
    """
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(HealthEndpointDetectionResult)
    
    system_prompt = """You are an expert code analyst working as an autonomous AI agent, specializing in detecting health check endpoints.

Your task is to analyze the provided source code and identify any health check endpoints.
You must work with ANY programming language, framework, or technology stack.

WHAT TO LOOK FOR:
1.  **Explicit health routes**: Common paths like /health, /healthz, /ready, /ping, /status, /api/health, or technology-specific health endpoints.
2.  **Technology-specific health patterns**: Analyze the code to find route definitions, endpoint handlers, or health check middleware.
3.  **Port configuration**:
    -   Look for PORT environment variable usage.
    -   Look for explicit port numbers in server/listen calls.
    -   Look for configuration files with port settings.

CONFIDENCE LEVELS:
-   **high**: Found explicit health endpoint with clear path and port.
-   **medium**: Found health-like endpoint but port unclear.
-   **low**: Found patterns that MIGHT be health endpoints.
-   **none**: No health endpoints detected.

DO NOT GUESS. Only report what you find in the code. Analyze the actual code patterns for the detected technology.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze these files to detect health check endpoints.

STACK: {stack}

FILE CONTENTS:
{file_contents}

Find any health check endpoints and their port configurations.
Explain your reasoning in the thought process.""")
    ])
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "file_contents": file_contents[:10000]  # Limit size
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()


def detect_readiness_patterns(
    file_contents: str,
    analysis_result: Dict[str, Any]
) -> Tuple[ReadinessPatternResult, Dict[str, int]]:
    """
    AI-powered detection of startup/readiness log patterns.
    
    Instead of fixed sleep times, this detects patterns in logs
    that indicate the application has started successfully.
    
    Args:
        file_contents: Content of files to analyze.
        analysis_result: Previous analysis result.

    Returns:
        Tuple of (ReadinessPatternResult, usage_dict).
    """
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(ReadinessPatternResult)
    
    system_prompt = """You are an expert at understanding application startup patterns, working as an autonomous AI agent.

Your task is to analyze source code and determine:
1.  What log messages indicate successful startup.
2.  What log messages indicate failure.
3.  How long the application typically takes to start.

You must work with ANY programming language, framework, or technology stack.

APPROACH:
-   Analyze the detected technology and understand its common startup patterns.
-   Look for logging statements, print statements, or output patterns in the code.
-   Identify success indicators (server started, listening, ready, initialized).
-   Identify failure indicators (error, fatal, failed, exception, panic).

FAILURE PATTERNS (Common across technologies):
-   Error messages, exception traces, panic/crash indicators.
-   Connection failures, module not found errors.
-   Any indication of startup failure.

Generate REGEX patterns that can be used to detect these in container logs.
Use Python-compatible regex syntax.
Analyze the actual code to determine technology-specific patterns.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze these files to determine startup patterns.

STACK: {stack}
PROJECT TYPE: {project_type}

FILE CONTENTS:
{file_contents}

Identify log patterns that indicate successful startup or failure.
Explain your reasoning in the thought process.""")
    ])
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "project_type": analysis_result.get("project_type", "service"),
            "file_contents": file_contents[:8000]
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()


def generate_iterative_dockerfile(
    previous_dockerfile: str,
    reflection: Dict[str, Any],
    analysis_result: Dict[str, Any],
    file_contents: str,
    current_plan: Dict[str, Any],
    verified_tags: str = "",
    custom_instructions: str = ""
) -> Tuple[IterativeDockerfileResult, Dict[str, int]]:
    """
    Generate an improved Dockerfile based on reflection and previous attempt.
    
    Unlike fresh generation, this specifically targets the issues identified
    in the reflection, making minimal changes to fix the problems.
    
    Args:
        previous_dockerfile: The previous, failed Dockerfile.
        reflection: The reflection result containing analysis of failure.
        analysis_result: Original analysis result.
        file_contents: Content of critical files.
        current_plan: The current generation plan.
        verified_tags: List of verified Docker tags.
        custom_instructions: Custom instructions.

    Returns:
        Tuple of (IterativeDockerfileResult, usage_dict).
    """
    model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    system_prompt = """You are a Senior Docker Engineer working as an autonomous AI agent, iterating on a failed Dockerfile.

CRITICAL: You are NOT starting from scratch. You are IMPROVING an existing Dockerfile
based on specific feedback about what went wrong.

You must work with ANY programming language, framework, or technology stack.

APPROACH:
1.  **UNDERSTAND** what was wrong with the previous Dockerfile.
2.  **APPLY** the specific fixes from the reflection.
3.  **PRESERVE** what was working correctly.
4.  **MAKE MINIMAL CHANGES** - don't rewrite everything, fix what's broken.

REFLECTION GUIDANCE:
-   Root cause: {root_cause}
-   Specific fixes to apply: {specific_fixes}
-   Should change base image: {should_change_base_image}
-   Suggested base image: {suggested_base_image}
-   Should change build strategy: {should_change_build_strategy}
-   New strategy: {new_build_strategy}

PLAN GUIDANCE:
-   Base image strategy: {base_image_strategy}
-   Build strategy: {build_strategy}
-   Use multi-stage: {use_multi_stage}
-   Use minimal runtime: {use_minimal_runtime}
-   Use static linking: {use_static_linking}

VERIFIED BASE IMAGES: {verified_tags}

{custom_instructions}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Improve this Dockerfile based on the reflection.

PREVIOUS DOCKERFILE (FIX THIS):
{previous_dockerfile}

PROJECT CONTEXT:
Stack: {stack}
Build Command: {build_command}
Start Command: {start_command}

KEY FILES:
{file_contents}

Apply the fixes and return an improved Dockerfile.
Explain your changes in the thought process.""")
    ])
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "previous_dockerfile": previous_dockerfile,
            "root_cause": reflection.get("root_cause_analysis", "Unknown"),
            "specific_fixes": ", ".join(reflection.get("specific_fixes", [])),
            "should_change_base_image": reflection.get("should_change_base_image", False),
            "suggested_base_image": reflection.get("suggested_base_image", ""),
            "should_change_build_strategy": reflection.get("should_change_build_strategy", False),
            "new_build_strategy": reflection.get("new_build_strategy", ""),
            "base_image_strategy": current_plan.get("base_image_strategy", ""),
            "build_strategy": current_plan.get("build_strategy", ""),
            "use_multi_stage": current_plan.get("use_multi_stage", True),
            "use_minimal_runtime": current_plan.get("use_minimal_runtime", False),
            "use_static_linking": current_plan.get("use_static_linking", False),
            "verified_tags": verified_tags,
            "stack": analysis_result.get("stack", "Unknown"),
            "build_command": analysis_result.get("build_command", "None"),
            "start_command": analysis_result.get("start_command", "None"),
            "file_contents": file_contents[:6000],
            "custom_instructions": custom_instructions
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()



