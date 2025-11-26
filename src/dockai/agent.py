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

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from .schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult
)
from .callbacks import TokenUsageCallback
from .rate_limiter import with_rate_limit_handling, create_rate_limited_llm
from .prompts import get_prompt
from .llm_providers import create_llm

# Initialize the logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """
    Safely invoke a LangChain chain with rate limit handling.
    
    This wrapper adds automatic retry with exponential backoff for rate limit errors.
    
    Args:
        chain: The LangChain chain to invoke
        input_data: Input data dictionary
        callbacks: List of callbacks
        
    Returns:
        Chain invocation result
    """
    return chain.invoke(input_data, config={"callbacks": callbacks})


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
    # Create LLM using the provider factory for the planner agent
    llm = create_llm(agent_name="planner", temperature=0.2)
    
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
    
    # Define the default system prompt for the DevOps Architect persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to create a strategic plan before any code is written.

Think like a chess grandmaster - every move matters, and you must anticipate problems several steps ahead.

## Your Strategic Thinking Process

STEP 1 - UNDERSTAND THE GOAL: What exactly needs to be containerized?
  - What does the application do?
  - What must work for it to be "successful"?
  - What environment does it expect?

STEP 2 - ANALYZE THE CONSTRAINTS:
  - What runtime does the code require?
  - What build-time tools are needed vs runtime dependencies?
  - Are there any compiled artifacts vs interpreted code?
  - What files must exist in the final container?

STEP 3 - ANTICIPATE PROBLEMS: What could go wrong?
  - Dependency resolution issues?
  - Binary compatibility between build and runtime?
  - Missing system libraries or tools?
  - Permission or user context issues?
  - File path or working directory problems?

STEP 4 - DESIGN THE STRATEGY:
  - Should there be separate build and runtime stages?
  - What base image provides the right foundation?
  - How should dependencies be installed and cached?
  - What security measures are appropriate?

STEP 5 - LEARN FROM HISTORY (if retrying):
  - What specifically failed before?
  - Why did that approach not work?
  - How can you avoid the same mistake?

## Strategic Principles

- **Separation of Concerns**: Build tools don't belong in production images
- **Minimal Attack Surface**: Include only what's necessary to run
- **Reproducibility**: Pin versions, avoid moving targets
- **Security by Default**: Non-root execution, no embedded secrets
- **Fail Fast**: Detect problems early in the build process

## Key Questions to Answer

1. What image should each stage start from?
2. What gets built/compiled vs what gets copied?
3. What are the potential failure points?
4. How will you mitigate each risk?

{retry_context}

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("planner", default_prompt)

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
    
    # Execute the chain with the provided context (with rate limit handling)
    result = safe_invoke_chain(
        chain,
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
        [callback]
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
    # Create LLM using the provider factory for the reflector agent
    llm = create_llm(agent_name="reflector", temperature=0)
    
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
    
    # Define the default system prompt for the "Principal DevOps Engineer" persona
    default_prompt = """You are an autonomous AI reasoning agent conducting a post-mortem analysis. Your task is to understand why something failed and determine how to fix it.

Think like a detective investigating an incident - look at evidence, form hypotheses, test them against facts.

## Your Analytical Process

STEP 1 - EXAMINE THE EVIDENCE:
  - What is the exact error message?
  - At what stage did the failure occur (build vs runtime)?
  - What was the system trying to do when it failed?

STEP 2 - IDENTIFY THE SYMPTOM vs ROOT CAUSE:
  - The error message is the SYMPTOM - what is it telling you?
  - What underlying condition caused this symptom?
  - Could there be multiple contributing factors?

STEP 3 - TRACE THE CAUSALITY:
  - Work backwards from the failure point
  - What assumptions were made that turned out to be wrong?
  - What dependency or resource was missing or incorrect?

STEP 4 - FORMULATE THE FIX:
  - What is the minimal change that addresses the root cause?
  - Will this fix introduce new problems?
  - Are there alternative solutions with different tradeoffs?

STEP 5 - PREVENT RECURRENCE:
  - What lesson should be learned?
  - Should the overall strategy be reconsidered?
  - Is this a symptom of a larger problem?

## Debugging Principles

- **Evidence Over Assumption**: Base conclusions on what you observe, not what you expect
- **Root Cause Over Symptoms**: Fixing symptoms creates fragile solutions
- **Minimal Changes**: Surgical fixes are more reliable than rewrites
- **Validate Hypotheses**: Each proposed fix should be justified by evidence

## Key Questions to Answer

1. What exactly failed and why?
2. Is this fixable in the Dockerfile or is it a project issue?
3. What specific change will resolve this?
4. Could this fix break something else?

{retry_context}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("reflector", default_prompt)

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
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
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
        [callback]
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
    # Create LLM using the provider factory for the health detector agent
    llm = create_llm(agent_name="health_detector", temperature=0)
    
    # Configure the LLM to return a structured output matching the HealthEndpointDetectionResult schema
    structured_llm = llm.with_structured_output(HealthEndpointDetectionResult)
    
    # Define the default system prompt for the "Code Analyst" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to analyze source code and discover how to check if the application is healthy.

Think like a developer reading unfamiliar code - what clues tell you where the health check lives?

## Your Discovery Process

STEP 1 - UNDERSTAND THE APPLICATION:
  - What type of application is this (web server, API, worker, etc.)?
  - How does it handle incoming requests or connections?
  - What framework or patterns is it using?

STEP 2 - SEARCH FOR HEALTH INDICATORS:
  - Look for route definitions, URL handlers, or endpoints
  - Search for patterns like health, ready, alive, ping, status
  - Check for monitoring or observability middleware/integrations

STEP 3 - IDENTIFY THE PORT:
  - How does the application know which port to listen on?
  - Is it hardcoded, environment variable, or configuration file?
  - Are there multiple ports for different services?

STEP 4 - ASSESS CONFIDENCE:
  - What evidence supports your conclusion?
  - Is this definitive or a best guess?
  - What could you be wrong about?

## Discovery Principles

- **Evidence-Based**: Only report what you actually find in the code
- **Pattern Recognition**: Health endpoints follow common patterns across frameworks
- **Context Matters**: The same pattern might mean different things in different frameworks
- **Uncertainty is Valid**: It's better to say "low confidence" than to guess

## Key Questions to Answer

1. Is there a dedicated health check endpoint?
2. What URL path would you hit to check health?
3. What port is the application listening on?
4. How confident are you in these findings?
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("health_detector", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze these files to detect health check endpoints.

STACK: {stack}

FILE CONTENTS:
{file_contents}

Find any health check endpoints and their port configurations.
Explain your reasoning in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "file_contents": file_contents[:10000]  # Limit size to avoid context overflow
        },
        [callback]
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
    # Create LLM using the provider factory for the readiness detector agent
    llm = create_llm(agent_name="readiness_detector", temperature=0)
    
    # Configure the LLM to return a structured output matching the ReadinessPatternResult schema
    structured_llm = llm.with_structured_output(ReadinessPatternResult)
    
    # Define the default system prompt for the "Startup Pattern Expert" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to figure out how to tell when an application has successfully started (or failed to start).

Think like someone watching the logs scroll by - what would you look for to know it's ready?

## Your Analysis Process

STEP 1 - UNDERSTAND STARTUP BEHAVIOR:
  - What happens when this application starts?
  - What resources does it connect to or initialize?
  - What's the final step before it's ready to serve?

STEP 2 - FIND SUCCESS INDICATORS:
  - Look for logging statements that announce readiness
  - Find print/output statements that signal completion
  - Identify messages that mention listening, started, ready, initialized

STEP 3 - FIND FAILURE INDICATORS:
  - What would the application print if something went wrong?
  - Look for error handling, exception logging, fatal messages
  - Consider connection failures, missing dependencies, crashes

STEP 4 - ESTIMATE TIMING:
  - Based on what the application does at startup, how long should it take?
  - Is it connecting to external services (longer wait)?
  - Is it just loading code (shorter wait)?

## Analysis Principles

- **Observe the Code**: Base patterns on actual logging/print statements you see
- **Be Specific**: A pattern like "started" is too generic; find unique markers
- **Cover Both Cases**: Know what success AND failure look like
- **Consider Variants**: The same message might have slight variations

## Key Questions to Answer

1. What log message definitively means "the app is ready"?
2. What log message means "startup failed"?
3. How long is reasonable to wait for startup?
4. What regex pattern would match the success message?
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("readiness_detector", default_prompt)

    # Create the chat prompt template
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
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "stack": analysis_result.get("stack", "Unknown"),
            "project_type": analysis_result.get("project_type", "service"),
            "file_contents": file_contents[:8000]  # Limit size
        },
        [callback]
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
    # Create LLM using the provider factory for the iterative improver agent
    llm = create_llm(agent_name="iterative_improver", temperature=0)
    
    # Configure the LLM to return a structured output matching the IterativeDockerfileResult schema
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Define the default system prompt for the "Senior Docker Engineer" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to improve a failed Dockerfile based on specific feedback.

Think like a surgeon making precise corrections - preserve what works, fix what doesn't.

## Your Improvement Process

STEP 1 - UNDERSTAND THE FAILURE:
  - What specific error or issue occurred?
  - What line(s) in the Dockerfile are implicated?
  - What was the intended behavior vs actual behavior?

STEP 2 - REVIEW THE DIAGNOSIS:
  - Root cause identified: {root_cause}
  - Suggested fixes: {specific_fixes}
  - Image change recommended: {should_change_base_image} -> {suggested_base_image}
  - Strategy change recommended: {should_change_build_strategy} -> {new_build_strategy}

STEP 3 - PLAN YOUR CHANGES:
  - What is the minimal change that addresses the root cause?
  - What parts of the Dockerfile are working and should be preserved?
  - Could your fix have unintended side effects?

STEP 4 - APPLY SURGICALLY:
  - Make targeted changes, not rewrites
  - Ensure the fix actually addresses the root cause
  - Verify no new problems are introduced

## Improvement Principles

- **Minimal Intervention**: The best fix changes the least amount of code
- **Preserve Working Code**: If it wasn't broken, don't touch it
- **Address Root Cause**: Fixing symptoms leads to whack-a-mole debugging
- **Explain Your Changes**: Be clear about what you changed and why

## Context

Plan guidance:
- Base image strategy: {base_image_strategy}
- Build strategy: {build_strategy}
- Multi-stage: {use_multi_stage}
- Minimal runtime: {use_minimal_runtime}
- Static linking: {use_static_linking}

Verified images: {verified_tags}

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("iterative_improver", default_prompt)

    # Create the chat prompt template
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
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
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
        [callback]
    )
    
    return result, callback.get_usage()



