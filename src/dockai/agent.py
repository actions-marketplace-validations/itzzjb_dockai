"""
DockAI Adaptive Agent Module.

This module implements the core AI-driven capabilities of the DockAI system.
It is responsible for the high-level cognitive tasks that allow the agent to
adapt, plan, and learn from its interactions.

Key Responsibilities:
1.  **Strategic Planning**: Analyzing project requirements to formulate a build strategy.
2.  **Failure Reflection**: Analyzing build or runtime failures to derive actionable insights.
3.  **Health Detection**: Intelligently identifying health check endpoints within the source code.
4.  **Readiness Pattern Analysis**: Determining how to detect when an application is ready to serve traffic.
5.  **Iterative Improvement**: Refining Dockerfiles based on feedback loops.

The components in this module leverage Large Language Models (LLMs) to simulate
the reasoning process of a human DevOps engineer.
"""

import os
import re
import logging
from typing import Tuple, Any, List, Dict, Optional

# Third-party imports for LangChain and OpenAI integration
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas and callbacks
from .schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult
)
from .callbacks import TokenUsageCallback

# Initialize the logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


def create_plan(
    analysis_result: Dict[str, Any],
    file_contents: str,
    retry_history: List[Dict[str, Any]] = None,
    custom_instructions: str = ""
) -> Tuple[PlanningResult, Dict[str, int]]:
    """
    Generates a strategic plan for Dockerfile creation using AI analysis.

    This function acts as the "architect" phase of the process. Before writing any code,
    it analyzes the project structure, requirements, and any previous failures to
    formulate a robust build strategy.

    Args:
        analysis_result (Dict[str, Any]): The results from the initial project analysis,
            including detected stack, project type, and suggested base images.
        file_contents (str): The actual content of critical files (e.g., package.json,
            requirements.txt) to provide context to the LLM.
        retry_history (List[Dict[str, Any]], optional): A list of previous attempts,
            including what was tried and why it failed. This enables the agent to
            learn from mistakes. Defaults to None.
        custom_instructions (str, optional): Specific instructions provided by the user
            to guide the planning process. Defaults to "".

    Returns:
        Tuple[PlanningResult, Dict[str, int]]: A tuple containing:
            - The structured planning result (PlanningResult object).
            - A dictionary tracking token usage for cost monitoring.
    """
    # Retrieve the model name from environment variables, defaulting to a cost-effective model
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    # Initialize the ChatOpenAI client with a low temperature for consistent, strategic output
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.2,  # Low temperature favors deterministic, logical planning
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Configure the LLM to return a structured output matching the PlanningResult schema
    structured_llm = llm.with_structured_output(PlanningResult)
    
    # Construct the context from previous retry attempts to facilitate learning
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
    
    # Define the system prompt to establish the agent's persona and constraints
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

    # Create the chat prompt template combining system instructions and user input
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
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain with the provided context
    result = chain.invoke(
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "project_type": analysis_result.get("project_type", "service"),
            "suggested_base_image": analysis_result.get("suggested_base_image", ""),
            "build_command": analysis_result.get("build_command", "None detected"),
            "start_command": analysis_result.get("start_command", "None detected"),
            "file_contents": file_contents[:8000],  # Truncate file contents to avoid token limits
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
    Analyzes a failed Dockerfile build or run to determine the root cause and solution.

    This function implements the "reflection" capability of the agent. When a failure
    occurs, it doesn't just blindly retry. Instead, it analyzes the error logs,
    the problematic Dockerfile, and the project context to understand *why* it failed
    and *how* to fix it.

    Args:
        dockerfile_content (str): The content of the Dockerfile that caused the failure.
        error_message (str): The primary error message returned by the Docker daemon or CLI.
        error_details (Dict[str, Any]): Additional structured details about the error
            (e.g., error code, stage where it failed).
        analysis_result (Dict[str, Any]): The original project analysis context.
        retry_history (List[Dict[str, Any]], optional): History of previous attempts to
            avoid cyclic failures. Defaults to None.
        container_logs (str, optional): Runtime logs from the container if the failure
            occurred after the build phase. Defaults to "".

    Returns:
        Tuple[ReflectionResult, Dict[str, int]]: A tuple containing:
            - The structured reflection result (ReflectionResult object) with specific fixes.
            - A dictionary tracking token usage.
    """
    # Use a more capable model (e.g., GPT-4o) for complex reasoning required in debugging
    model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    # Initialize the LLM with temperature 0 for maximum determinism and analytical precision
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Configure structured output for consistent parsing of the reflection
    structured_llm = llm.with_structured_output(ReflectionResult)
    
    # Construct the history of previous failures to provide context
    retry_context = ""
    if retry_history and len(retry_history) > 0:
        retry_context = "\n\nPREVIOUS FAILED ATTEMPTS:\n"
        for i, attempt in enumerate(retry_history, 1):
            retry_context += f"""
Attempt {i}: {attempt.get('what_was_tried', 'Unknown')} -> Failed: {attempt.get('why_it_failed', 'Unknown')}
"""
    
    # Define the system prompt for the "Principal DevOps Engineer" persona
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

    # Create the prompt template
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
    
    # Create the chain
    chain = prompt | structured_llm
    
    # Initialize token usage tracking
    callback = TokenUsageCallback()
    
    # Execute the chain
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
    Scans source code to identify potential health check endpoints and port configurations.

    This function uses AI to "read" the code, looking for common patterns that indicate
    where the application exposes its health status (e.g., /health, /ready). It also
    looks for port configurations to ensure the Dockerfile exposes the correct port.

    Args:
        file_contents (str): The raw content of the source files to be analyzed.
        analysis_result (Dict[str, Any]): The results from the initial project analysis.

    Returns:
        Tuple[HealthEndpointDetectionResult, Dict[str, int]]: A tuple containing:
            - The detection result (HealthEndpointDetectionResult object) with found endpoints.
            - A dictionary tracking token usage.
    """
    # Use a faster, lighter model for this pattern matching task
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,  # Deterministic output required
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(HealthEndpointDetectionResult)
    
    # Define the system prompt for the "Code Analyst" persona
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
            "file_contents": file_contents[:10000]  # Limit size to avoid context overflow
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()


def detect_readiness_patterns(
    file_contents: str,
    analysis_result: Dict[str, Any]
) -> Tuple[ReadinessPatternResult, Dict[str, int]]:
    """
    Analyzes application logs and code to determine how to detect when the app is ready.

    Instead of relying on arbitrary sleep times, this function identifies the specific
    log messages or output patterns that signify a successful startup (e.g., "Server
    running on port 8080"). It also identifies failure patterns to fail fast.

    Args:
        file_contents (str): The content of the source files.
        analysis_result (Dict[str, Any]): The results from the initial project analysis.

    Returns:
        Tuple[ReadinessPatternResult, Dict[str, int]]: A tuple containing:
            - The readiness pattern result (ReadinessPatternResult object) with regex patterns.
            - A dictionary tracking token usage.
    """
    # Use a cost-effective model for pattern recognition
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,  # Deterministic output required
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(ReadinessPatternResult)
    
    # Define the system prompt for the "Startup Pattern Expert" persona
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
            "file_contents": file_contents[:8000]  # Limit size
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
    Generates an improved Dockerfile by applying fixes identified in the reflection phase.

    This function represents the "iterative improvement" capability. It takes a
    failed Dockerfile and the analysis of why it failed (reflection), and produces
    a new version that addresses the specific issues while preserving what worked.

    Args:
        previous_dockerfile (str): The content of the failed Dockerfile.
        reflection (Dict[str, Any]): The structured reflection result containing
            root cause analysis and specific fix instructions.
        analysis_result (Dict[str, Any]): The original project analysis context.
        file_contents (str): Content of critical files to provide context.
        current_plan (Dict[str, Any]): The current build strategy/plan.
        verified_tags (str, optional): A list of verified Docker image tags to ensure
            valid base images are used. Defaults to "".
        custom_instructions (str, optional): User-provided instructions. Defaults to "".

    Returns:
        Tuple[IterativeDockerfileResult, Dict[str, int]]: A tuple containing:
            - The result containing the improved Dockerfile (IterativeDockerfileResult object).
            - A dictionary tracking token usage.
    """
    # Use a high-capability model for code generation and complex modification
    model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,  # Deterministic output required for code generation
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Define the system prompt for the "Senior Docker Engineer" persona
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



