"""
DockAI Graph Nodes.

This module contains the node functions for the LangGraph workflow.
Each node represents a distinct step in the adaptive agent process,
encapsulating specific logic for scanning, analysis, generation, validation,
and reflection.
"""

import os
import logging
from typing import Dict, Any, Literal, Optional

# Internal imports for state management and core logic
from ..core.state import DockAIState
from ..utils.scanner import get_file_tree
from ..agents.analyzer import analyze_repo_needs
from ..agents.generator import generate_dockerfile
from ..agents.reviewer import review_dockerfile
from ..utils.validator import validate_docker_build_and_run, check_container_readiness
from ..core.errors import classify_error, ClassifiedError, ErrorType, format_error_for_display
from ..utils.registry import get_docker_tags
from ..agents.agent_functions import (
    create_plan,
    reflect_on_failure,
    detect_health_endpoints,
    detect_readiness_patterns,
    generate_iterative_dockerfile
)

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


def scan_node(state: DockAIState) -> DockAIState:
    """
    Scans the repository directory tree.
    
    This is the initial step in the workflow. It performs a fast, local scan
    of the directory to build a file tree structure, which is used by subsequent
    nodes to understand the project layout without reading every file's content.

    Args:
        state (DockAIState): The current state containing the project path.

    Returns:
        DockAIState: Updated state with the 'file_tree' populated.
    """
    path = state["path"]
    logger.info(f"Scanning directory: {path}")
    file_tree = get_file_tree(path)
    logger.info(f"Found {len(file_tree)} files to analyze")
    return {"file_tree": file_tree}


def analyze_node(state: DockAIState) -> DockAIState:
    """
    Performs AI-powered analysis of the repository.
    
    This node acts as the "Brain" (Stage 1). It:
    - Analyzes the file tree to deduce the project type and stack.
    - Identifies build commands, start commands, and entry points.
    - Determines which critical files need to be read for deeper context.
    - Suggests an initial base image strategy.
    
    If 'needs_reanalysis' is set in the state (triggered by reflection),
    it performs a focused re-analysis based on the feedback.

    Args:
        state (DockAIState): The current state with file tree and config.

    Returns:
        DockAIState: Updated state with 'analysis_result', 'usage_stats',
        and clears the 'needs_reanalysis' flag.
    """
    file_tree = state["file_tree"]
    config = state.get("config", {})
    instructions = config.get("analyzer_instructions", "")
    
    # Check if this is a re-analysis triggered by reflection
    needs_reanalysis = state.get("needs_reanalysis", False)
    reflection = state.get("reflection")
    
    if needs_reanalysis and reflection:
        # Add re-analysis focus to instructions to guide the LLM
        focus = reflection.get("reanalysis_focus", "")
        if focus:
            instructions += f"\n\nRE-ANALYSIS FOCUS: {focus}\n"
            instructions += "The previous analysis may have been incorrect. Pay special attention to the focus area."
        logger.info(f"Re-analyzing with focus: {focus}")
    else:
        logger.info("Analyzing repository needs...")
    
    # Execute analysis (returns AnalysisResult object and token usage)
    analysis_result_obj, usage = analyze_repo_needs(file_tree, instructions)
    
    logger.info(f"Analyzer Reasoning:\n{analysis_result_obj.thought_process}")
    
    # Convert Pydantic model to dict for state storage
    analysis_result = analysis_result_obj.model_dump()
    
    usage_dict = {
        "stage": "analyzer" if not needs_reanalysis else "re-analyzer",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    }
    
    current_stats = state.get("usage_stats", [])
    return {
        "analysis_result": analysis_result, 
        "usage_stats": current_stats + [usage_dict],
        "needs_reanalysis": False  # Clear the flag as analysis is done
    }


from ..utils.file_utils import smart_truncate

def read_files_node(state: DockAIState) -> DockAIState:
    """
    Reads critical files identified by the analyzer.
    
    This node fetches the actual content of the files that the AI determined
    are necessary for understanding the project's build and runtime requirements.
    
    Improvements:
    - Skips lock files (package-lock.json, yarn.lock) to save tokens.
    - Configurable limits via env vars (DOCKAI_MAX_FILE_CHARS, DOCKAI_MAX_FILE_LINES).
    - Higher default limits (200KB / 5000 lines) for better context.
    - Smart truncation to preserve file structure.

    Args:
        state (DockAIState): The current state with analysis results.

    Returns:
        DockAIState: Updated state with 'file_contents' string.
    """
    path = state["path"]
    files_to_read = state["analysis_result"].get("files_to_read", [])
    
    logger.info(f"Reading {len(files_to_read)} critical files...")
    file_contents_str = ""
    files_read = 0
    files_failed = []
    
    # Files that should be read fully if possible (dependencies)
    CRITICAL_DEPENDENCY_FILES = ["package.json", "requirements.txt", "Gemfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle"]
    # Files to skip
    SKIP_FILES = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Gemfile.lock", "go.sum", "Cargo.lock"]

    # Get limits from env or use new higher defaults
    # Default: 200KB chars (approx 50k tokens), 5000 lines
    try:
        MAX_CHARS = int(os.getenv("DOCKAI_MAX_FILE_CHARS", "200000"))
        MAX_LINES = int(os.getenv("DOCKAI_MAX_FILE_LINES", "5000"))
    except ValueError:
        MAX_CHARS = 200000
        MAX_LINES = 5000

    for rel_path in files_to_read:
        basename = os.path.basename(rel_path)
        
        if basename in SKIP_FILES:
            logger.info(f"Skipping lock file: {rel_path}")
            continue
            
        abs_file_path = os.path.join(path, rel_path)
        try:
            with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                # Determine limits based on file type
                is_dependency_file = basename in CRITICAL_DEPENDENCY_FILES
                
                # Dependency files get double the line limit but same char limit
                # (We really want to see all dependencies)
                current_max_lines = MAX_LINES * 2 if is_dependency_file else MAX_LINES
                current_max_chars = MAX_CHARS  # Keep char limit hard to prevent context overflow
                
                original_len = len(content)
                content = smart_truncate(content, basename, current_max_chars, current_max_lines)
                
                if len(content) < original_len:
                    logger.warning(f"Truncated {rel_path}: {original_len} -> {len(content)} chars")
                    
                file_contents_str += f"--- FILE: {rel_path} ---\n{content}\n\n"
                files_read += 1
        except Exception as e:
            logger.warning(f"Could not read {rel_path}: {e}")
            files_failed.append(rel_path)
    
    logger.info(f"Successfully read {files_read} files" + (f", {len(files_failed)} failed" if files_failed else ""))
    
    return {"file_contents": file_contents_str}


def detect_health_node(state: DockAIState) -> DockAIState:
    """
    AI-powered health endpoint detection from actual file contents.
    
    Unlike the initial analysis which might guess based on filenames, this node
    uses an LLM to scan the code content for route definitions (e.g., @app.get('/health'))
    to accurately identify health check endpoints.

    Args:
        state (DockAIState): The current state with file contents.

    Returns:
        DockAIState: Updated state with 'detected_health_endpoint' and usage stats.
    """
    file_contents = state.get("file_contents", "")
    analysis_result = state.get("analysis_result", {})
    
    # Skip if analyzer already found a high-confidence endpoint
    existing_health = analysis_result.get("health_endpoint")
    if existing_health:
        logger.info(f"Using analyzer-detected health endpoint: {existing_health.get('path')}:{existing_health.get('port')}")
        return {}
    
    logger.info("Detecting health endpoints from code...")
    
    try:
        detection_result, usage = detect_health_endpoints(file_contents, analysis_result)
        
        usage_dict = {
            "stage": "health_detection",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        }
        
        current_stats = state.get("usage_stats", [])
        
        # Store detected health endpoint
        detected_endpoint = None
        if detection_result.primary_health_endpoint:
            detected_endpoint = detection_result.primary_health_endpoint.model_dump() if hasattr(detection_result.primary_health_endpoint, 'model_dump') else detection_result.primary_health_endpoint
            logger.info(f"Detected health endpoint: {detected_endpoint}")
        elif detection_result.confidence != "none":
            logger.info(f"Health detection confidence: {detection_result.confidence}")
        
        return {
            "detected_health_endpoint": detected_endpoint,
            "usage_stats": current_stats + [usage_dict]
        }
    except Exception as e:
        logger.warning(f"Health endpoint detection failed: {e}")
        return {}


def detect_readiness_node(state: DockAIState) -> DockAIState:
    """
    AI-powered detection of startup log patterns.
    
    This node analyzes the code to predict what the application will log when
    it starts successfully (e.g., "Server listening on port 8080"). This allows
    for smart readiness checking instead of relying on arbitrary sleep times.

    Args:
        state (DockAIState): The current state with file contents.

    Returns:
        DockAIState: Updated state with 'readiness_patterns', 'failure_patterns', and usage stats.
    """
    file_contents = state.get("file_contents", "")
    analysis_result = state.get("analysis_result", {})
    
    logger.info("Detecting startup readiness patterns...")
    
    try:
        patterns_result, usage = detect_readiness_patterns(file_contents, analysis_result)
        
        usage_dict = {
            "stage": "readiness_detection",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        }
        
        current_stats = state.get("usage_stats", [])
        
        logger.info(f"Detected {len(patterns_result.startup_success_patterns)} success patterns, {len(patterns_result.startup_failure_patterns)} failure patterns")
        logger.info(f"Estimated startup time: {patterns_result.estimated_startup_time}s (max wait: {patterns_result.max_wait_time}s)")
        
        return {
            "readiness_patterns": patterns_result.startup_success_patterns,
            "failure_patterns": patterns_result.startup_failure_patterns,
            "usage_stats": current_stats + [usage_dict]
        }
    except Exception as e:
        logger.warning(f"Readiness pattern detection failed: {e}")
        return {"readiness_patterns": [], "failure_patterns": []}


def plan_node(state: DockAIState) -> DockAIState:
    """
    AI-powered planning before Dockerfile generation.
    
    This node creates a strategic plan ("The Architect" phase). It considers:
    - The specific technology stack.
    - Previous retry history (to learn from mistakes).
    - Potential challenges and mitigations.
    - Optimal build strategy (e.g., multi-stage, static linking).
    
    This planning step ensures the generator has a solid blueprint to follow.

    Args:
        state (DockAIState): The current state with analysis and history.

    Returns:
        DockAIState: Updated state with 'current_plan' and usage stats.
    """
    analysis_result = state.get("analysis_result", {})
    file_contents = state.get("file_contents", "")
    retry_history = state.get("retry_history", [])
    config = state.get("config", {})
    instructions = config.get("generator_instructions", "")
    
    logger.info("Creating generation plan...")
    
    plan_result, usage = create_plan(
        analysis_result=analysis_result,
        file_contents=file_contents,
        retry_history=retry_history,
        custom_instructions=instructions
    )
    
    usage_dict = {
        "stage": "planner",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    }
    
    current_stats = state.get("usage_stats", [])
    
    # Convert plan to dict for state storage
    plan_dict = plan_result.model_dump()
    
    logger.info(f"Plan Strategy: {plan_result.base_image_strategy}")
    logger.info(f"Anticipated Challenges: {', '.join(plan_result.potential_challenges[:3])}")
    if plan_result.lessons_applied:
        logger.info(f"Lessons Applied: {', '.join(plan_result.lessons_applied)}")
    
    return {
        "current_plan": plan_dict,
        "usage_stats": current_stats + [usage_dict]
    }


def generate_node(state: DockAIState) -> DockAIState:
    """
    AI-powered Dockerfile generation.
    
    This node handles the actual code generation ("The Builder"). It supports two modes:
    1.  **Initial Generation**: Creates a fresh Dockerfile based on the strategic plan.
    2.  **Iterative Improvement**: If a previous attempt failed, it uses the reflection
        data to make targeted, surgical fixes to the existing Dockerfile instead of
        starting from scratch.
    
    It also dynamically fetches verified Docker image tags to prevent hallucinations.

    Args:
        state (DockAIState): The current state with plan, history, and reflection.

    Returns:
        DockAIState: Updated state with 'dockerfile_content', updated 'analysis_result',
        usage stats, and clears error/reflection flags.
    """
    analysis_result = state.get("analysis_result", {})
    stack = analysis_result.get("stack", "Unknown")
    file_contents = state["file_contents"]
    config = state.get("config", {})
    instructions = config.get("generator_instructions", "")
    current_plan = state.get("current_plan", {})
    reflection = state.get("reflection")
    previous_dockerfile = state.get("previous_dockerfile")
    retry_count = state.get("retry_count", 0)
    
    # Fetch verified tags dynamically to ensure image existence
    suggested_image = analysis_result.get("suggested_base_image", "").strip()
    
    # Check if reflection suggests a different base image
    if reflection and reflection.get("should_change_base_image"):
        suggested_image = reflection.get("suggested_base_image", suggested_image)
        logger.info(f"Using reflection-suggested base image: {suggested_image}")
    
    verified_tags = []
    if suggested_image:
        logger.info(f"Fetching tags for: {suggested_image}")
        verified_tags = get_docker_tags(suggested_image)
    else:
        logger.warning("No suggested base image from analysis. AI will determine the best base image.")
    
    verified_tags_str = ", ".join(verified_tags) if verified_tags else "Use your best judgement based on the detected technology stack."
    
    # Dynamic Model Selection: Use smarter model for retries/complex tasks
    if retry_count == 0:
        model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        logger.info(f"Generating Dockerfile (Draft Model: {model_name})...")
    else:
        model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
        logger.info(f"Improving Dockerfile (Expert Model: {model_name}, attempt {retry_count + 1})...")
    
    # Decide: Fresh generation or iterative improvement?
    if reflection and previous_dockerfile and retry_count > 0:
        # Iterative improvement based on reflection
        logger.info("Using iterative improvement strategy...")
        
        iteration_result, usage = generate_iterative_dockerfile(
            previous_dockerfile=previous_dockerfile,
            reflection=reflection,
            analysis_result=analysis_result,
            file_contents=file_contents,
            current_plan=current_plan,
            verified_tags=verified_tags_str,
            custom_instructions=instructions
        )
        
        dockerfile_content = iteration_result.dockerfile
        project_type = iteration_result.project_type
        thought_process = iteration_result.thought_process
        
        logger.info(f"Changes made: {', '.join(iteration_result.changes_summary[:3])}")
        logger.info(f"Confidence: {iteration_result.confidence_in_fix}")
        
    else:
        # Fresh generation
        build_cmd = analysis_result.get("build_command", "None detected")
        start_cmd = analysis_result.get("start_command", "None detected")
        
        dockerfile_content, project_type, thought_process, usage = generate_dockerfile(
            stack, 
            file_contents, 
            instructions, 
            feedback_error=state.get("error"),
            verified_tags=verified_tags_str,
            build_command=build_cmd,
            start_command=start_cmd,
            model_name=model_name,
            dockerfile_fix=state.get("error_details", {}).get("dockerfile_fix") if state.get("error_details") else None,
            image_suggestion=state.get("error_details", {}).get("image_suggestion") if state.get("error_details") else None,
            current_plan=current_plan
        )
    
    logger.info(f"Architect's Reasoning:\n{thought_process}")
    
    # Update analysis result with confirmed project type
    updated_analysis = analysis_result.copy()
    updated_analysis["project_type"] = project_type
    
    usage_dict = {
        "stage": "generator" if retry_count == 0 else f"generator_retry_{retry_count}",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": model_name
    }
    
    current_stats = state.get("usage_stats", [])
    
    return {
        "dockerfile_content": dockerfile_content,
        "analysis_result": updated_analysis,
        "usage_stats": current_stats + [usage_dict],
        "error": None,  # Clear previous error
        "error_details": None,
        "reflection": None  # Clear reflection after using it
    }


def review_node(state: DockAIState) -> DockAIState:
    """
    AI-powered security review of the generated Dockerfile.
    
    This node acts as a "Security Auditor". It checks the generated Dockerfile
    for common security vulnerabilities (e.g., running as root, exposing sensitive ports)
    and provides structured fixes.
    
    If the reviewer can fix the issue automatically, it does so. Otherwise, it
    flags the error for the next iteration.

    Args:
        state (DockAIState): The current state with the generated Dockerfile.

    Returns:
        DockAIState: Updated state with potential errors or a fixed Dockerfile.
    """
    dockerfile_content = state["dockerfile_content"]
    
    logger.info("Performing Security Review...")
    review_result, usage = review_dockerfile(dockerfile_content)
    
    usage_dict = {
        "stage": "reviewer",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    }
    
    current_stats = state.get("usage_stats", [])
    
    if not review_result.is_secure:
        # Construct detailed error with structured fixes
        issues_str = "\n".join([
            f"- [{issue.severity}] {issue.description} (Fix: {issue.suggestion})" 
            for issue in review_result.issues
        ])
        error_msg = f"Security Review Failed:\n{issues_str}"
        logger.warning(error_msg)
        
        # Check if reviewer provided a fixed dockerfile
        if review_result.fixed_dockerfile:
            logger.info("Reviewer provided a corrected Dockerfile - will use it directly")
            return {
                "dockerfile_content": review_result.fixed_dockerfile,
                "error": None,
                "usage_stats": current_stats + [usage_dict]
            }
        
        # Otherwise, pass the fixes to the next iteration
        return {
            "error": error_msg,
            "error_details": {
                "error_type": "security_review",
                "message": error_msg,
                "dockerfile_fixes": review_result.dockerfile_fixes,
                "should_retry": True
            },
            "usage_stats": current_stats + [usage_dict]
        }
    
    logger.info("Security Review Passed.")
    return {
        "usage_stats": current_stats + [usage_dict]
    }


def validate_node(state: DockAIState) -> DockAIState:
    """
    Validates the Dockerfile by building and running the container.
    
    This is the "Test Engineer" phase. It:
    1. Builds the Docker image.
    2. Runs the container with resource limits.
    3. Uses AI-detected readiness patterns to smartly wait for startup.
    4. Performs health checks if an endpoint was detected.
    5. Classifies any errors using AI to determine if they are fixable.
    
    It also checks for image size constraints.

    Args:
        state (DockAIState): The current state with the Dockerfile and analysis.

    Returns:
        DockAIState: Updated state with 'validation_result', 'error', and 'error_details'.
    """
    path = state["path"]
    dockerfile_content = state["dockerfile_content"]
    analysis_result = state["analysis_result"]
    
    project_type = analysis_result.get("project_type", "service")
    stack = analysis_result.get("stack", "Unknown")
    
    # Use AI-detected health endpoint if available, otherwise fall back to analyzer
    health_endpoint_data = state.get("detected_health_endpoint") or analysis_result.get("health_endpoint")
    recommended_wait_time = analysis_result.get("recommended_wait_time", 5)
    
    # Convert health endpoint to tuple
    health_endpoint = None
    if health_endpoint_data and isinstance(health_endpoint_data, dict):
        health_endpoint = (health_endpoint_data.get("path"), health_endpoint_data.get("port"))
    
    # Save Dockerfile for validation
    output_path = os.path.join(path, "Dockerfile")
    with open(output_path, "w") as f:
        f.write(dockerfile_content)
        
    logger.info("Validating Dockerfile...")
    
    # Use AI-detected readiness patterns if available
    readiness_patterns = state.get("readiness_patterns", [])
    failure_patterns = state.get("failure_patterns", [])
    
    success, message, image_size, classified_error = validate_docker_build_and_run(
        path, 
        project_type, 
        stack, 
        health_endpoint, 
        recommended_wait_time,
        readiness_patterns=readiness_patterns,
        failure_patterns=failure_patterns
    )
    
    # Store classified error details for better error handling
    error_details = None
    
    if classified_error:
        error_details = classified_error.to_dict()
        logger.info(format_error_for_display(classified_error, verbose=False))
    
    # Check for image size optimization (configurable)
    try:
        max_size_mb = int(os.getenv("DOCKAI_MAX_IMAGE_SIZE_MB", "500"))
    except ValueError:
        logger.warning("Invalid DOCKAI_MAX_IMAGE_SIZE_MB value, using default 500MB")
        max_size_mb = 500
    
    if max_size_mb > 0 and success and image_size > 0:
        SIZE_THRESHOLD = max_size_mb * 1024 * 1024
        
        if image_size > SIZE_THRESHOLD:
            size_mb = image_size / (1024 * 1024)
            warning_msg = f"Image size is {size_mb:.2f}MB, exceeds {max_size_mb}MB limit. Optimize using alpine/slim base images or multi-stage builds."
            logger.warning(warning_msg)
            error_details = {
                "error_type": ErrorType.DOCKERFILE_ERROR.value,
                "message": warning_msg,
                "suggestion": "Use alpine or slim base images, or enable multi-stage builds",
                "should_retry": True
            }
            return {
                "validation_result": {"success": False, "message": warning_msg},
                "error": warning_msg,
                "error_details": error_details
            }
    
    if success:
        size_mb = image_size / (1024 * 1024) if image_size > 0 else 0
        logger.info(f"Validation Passed! Image size: {size_mb:.2f}MB")

    return {
        "validation_result": {"success": success, "message": message},
        "error": message if not success else None,
        "error_details": error_details
    }


def reflect_node(state: DockAIState) -> DockAIState:
    """
    AI-powered reflection on failure.
    
    This node acts as the "Post-Mortem Analyst". It is the key to adaptive behavior.
    It analyzes the error logs, the failed Dockerfile, and the previous plan to:
    1. Determine the root cause of the failure.
    2. Decide if a re-analysis of the project is needed.
    3. Formulate specific, actionable fixes for the next iteration.
    
    This allows the agent to learn from its mistakes rather than blindly retrying.

    Args:
        state (DockAIState): The current state with error details and history.

    Returns:
        DockAIState: Updated state with 'reflection', 'retry_history', and 'needs_reanalysis'.
    """
    dockerfile_content = state.get("dockerfile_content", "")
    error_message = state.get("error", "Unknown error")
    error_details = state.get("error_details", {})
    analysis_result = state.get("analysis_result", {})
    retry_history = state.get("retry_history", [])
    
    logger.info("Reflecting on failure...")
    
    # Get container logs from error details if available
    container_logs = error_details.get("original_error", "") if error_details else ""
    
    reflection_result, usage = reflect_on_failure(
        dockerfile_content=dockerfile_content,
        error_message=error_message,
        error_details=error_details,
        analysis_result=analysis_result,
        retry_history=retry_history,
        container_logs=container_logs
    )
    
    usage_dict = {
        "stage": "reflector",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_GENERATOR", "gpt-4o")
    }
    
    current_stats = state.get("usage_stats", [])
    
    # Convert reflection to dict
    reflection_dict = reflection_result.model_dump()
    
    logger.info(f"Root Cause: {reflection_result.root_cause_analysis}")
    logger.info(f"Fix Strategy: {', '.join(reflection_result.specific_fixes[:2])}")
    logger.info(f"Confidence: {reflection_result.confidence_in_fix}")
    
    # Add to retry history for learning
    new_retry_entry = {
        "attempt_number": state.get("retry_count", 0) + 1,
        "dockerfile_content": dockerfile_content,
        "error_message": error_message,
        "error_type": error_details.get("error_type", "unknown") if error_details else "unknown",
        "what_was_tried": reflection_result.what_was_tried,
        "why_it_failed": reflection_result.why_it_failed,
        "lesson_learned": reflection_result.lesson_learned
    }
    
    updated_history = retry_history + [new_retry_entry]
    
    return {
        "reflection": reflection_dict,
        "previous_dockerfile": dockerfile_content,  # Store for iterative improvement
        "needs_reanalysis": reflection_result.needs_reanalysis,
        "retry_history": updated_history,
        "usage_stats": current_stats + [usage_dict]
    }


def increment_retry(state: DockAIState) -> DockAIState:
    """
    Helper node to increment the retry counter.
    
    This is used to track the number of attempts and enforce the maximum retry limit.

    Args:
        state (DockAIState): The current state.

    Returns:
        DockAIState: Updated state with incremented 'retry_count'.
    """
    current_count = state.get("retry_count", 0)
    logger.info(f"Retry {current_count + 1}...")
    return {"retry_count": current_count + 1}
