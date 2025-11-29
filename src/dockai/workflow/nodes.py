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
from ..core.llm_providers import get_model_for_agent
from ..utils.tracing import create_span

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
    
    with create_span("node.scan", {"path": path}) as span:
        logger.info(f"Scanning directory: {path}")
        file_tree = get_file_tree(path)
        logger.info(f"Found {len(file_tree)} files to analyze")
        
        if span:
            span.set_attribute("files_found", len(file_tree))
        
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
    
    with create_span("node.analyze", {
        "files_count": len(file_tree),
        "is_reanalysis": needs_reanalysis
    }) as span:
        if needs_reanalysis and reflection:
            # Add re-analysis focus to instructions to guide the LLM
            focus = reflection.get("reanalysis_focus", "")
            if focus:
                instructions += f"\n\nRE-ANALYSIS FOCUS: {focus}\n"
                instructions += "The previous analysis may have been incorrect. Pay special attention to the focus area."
            logger.info(f"Re-analyzing with focus: {focus}")
        else:
            logger.info("Analyzing repository needs...")
        
        # Create unified context for the analyzer
        from ..core.agent_context import AgentContext
        analyzer_context = AgentContext(
            file_tree=file_tree,
            file_contents=state.get("file_contents", ""),
            analysis_result=state.get("analysis_result", {}),
            custom_instructions=instructions
        )
        
        # Execute analysis (returns AnalysisResult object and token usage)
        analysis_result_obj, usage = analyze_repo_needs(context=analyzer_context)
        
        logger.info(f"Analyzer Reasoning:\n{analysis_result_obj.thought_process}")
        
        # Convert Pydantic model to dict for state storage
        analysis_result = analysis_result_obj.model_dump()
        
        if span:
            span.set_attribute("detected_stack", analysis_result.get("stack", ""))
            span.set_attribute("project_type", analysis_result.get("project_type", ""))
            span.set_attribute("llm.total_tokens", usage.get("total_tokens", 0))
        
        usage_dict = {
            "stage": "analyzer" if not needs_reanalysis else "re-analyzer",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("analyzer")
        }
        
        current_stats = state.get("usage_stats", [])
        return {
            "analysis_result": analysis_result, 
            "usage_stats": current_stats + [usage_dict],
            "needs_reanalysis": False  # Clear the flag as analysis is done
        }


from ..utils.file_utils import smart_truncate, read_critical_files

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
    config = state.get("config", {})
    
    # Truncation setting priority:
    # 1. Config value (if explicitly set)
    # 2. Environment variable DOCKAI_TRUNCATION_ENABLED
    # 3. Default: None (let read_critical_files decide, will auto-enable if token limit exceeded)
    truncation_enabled = config.get("truncation_enabled", None)
    
    logger.info(f"Reading {len(files_to_read)} critical files...")
    
    file_contents_str = read_critical_files(path, files_to_read, truncation_enabled=truncation_enabled)
    
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
        from ..core.agent_context import AgentContext
        health_context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=file_contents,
            analysis_result=analysis_result
        )
        detection_result, usage = detect_health_endpoints(context=health_context)
        
        usage_dict = {
            "stage": "health_detection",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("health_detector")
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
        from ..core.agent_context import AgentContext
        readiness_context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=file_contents,
            analysis_result=analysis_result
        )
        patterns_result, usage = detect_readiness_patterns(context=readiness_context)
        
        usage_dict = {
            "stage": "readiness_detection",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("readiness_detector")
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
    
    with create_span("node.plan", {
        "stack": analysis_result.get("stack", ""),
        "retry_history_count": len(retry_history)
    }) as span:
        logger.info("Creating generation plan...")
        
        # Create unified context for the planner
        from ..core.agent_context import AgentContext
        planner_context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=file_contents,
            analysis_result=analysis_result,
            retry_history=retry_history,
            custom_instructions=instructions
        )
        
        plan_result, usage = create_plan(context=planner_context)
        
        if span:
            span.set_attribute("build_strategy", plan_result.build_strategy)
            span.set_attribute("llm.total_tokens", usage.get("total_tokens", 0))
        
        usage_dict = {
            "stage": "planner",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("planner")
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
    retry_count = state.get("retry_count", 0)
    
    with create_span("node.generate", {"stack": stack, "retry_count": retry_count}) as span:
        file_contents = state["file_contents"]
        config = state.get("config", {})
        instructions = config.get("generator_instructions", "")
        current_plan = state.get("current_plan", {})
        reflection = state.get("reflection")
        previous_dockerfile = state.get("previous_dockerfile")
        
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
            model_name = get_model_for_agent("analyzer") # Use fast model for draft
            logger.info(f"Generating Dockerfile (Draft Model: {model_name})...")
        else:
            model_name = get_model_for_agent("generator") # Use powerful model for fixes
            logger.info(f"Improving Dockerfile (Expert Model: {model_name}, attempt {retry_count + 1})...")
        
        # Decide: Fresh generation or iterative improvement?
        if reflection and previous_dockerfile and retry_count > 0:
            # Iterative improvement based on reflection
            logger.info("Using iterative improvement strategy...")
            
            from ..core.agent_context import AgentContext
            iterative_context = AgentContext(
                file_tree=state.get("file_tree", []),
                file_contents=file_contents,
                analysis_result=analysis_result,
                current_plan=current_plan,
                dockerfile_content=previous_dockerfile,
                reflection=reflection,
                verified_tags=verified_tags_str,
                custom_instructions=instructions
            )
            
            iteration_result, usage = generate_iterative_dockerfile(context=iterative_context)
            
            dockerfile_content = iteration_result.dockerfile
            project_type = iteration_result.project_type
            thought_process = iteration_result.thought_process
            
            logger.info(f"Changes made: {', '.join(iteration_result.changes_summary[:3])}")
            logger.info(f"Confidence: {iteration_result.confidence_in_fix}")
            
        else:
            # Fresh generation with AgentContext
            from ..core.agent_context import AgentContext
            file_tree = state.get("file_tree", [])
            
            generator_context = AgentContext(
                file_tree=file_tree,
                file_contents=file_contents,
                analysis_result=analysis_result,
                current_plan=current_plan,
                retry_history=state.get("retry_history", []),
                error_message=state.get("error"),
                error_details=state.get("error_details"),
                verified_tags=verified_tags_str,
                custom_instructions=instructions
            )
            
            dockerfile_content, project_type, thought_process, usage = generate_dockerfile(context=generator_context)
        
        logger.info(f"Architect's Reasoning:\n{thought_process}")
        span.set_attribute("project_type", project_type)
        
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
    
    with create_span("node.review", {}) as span:
        logger.info("Performing Security Review...")
        
        # Create unified context for the reviewer
        from ..core.agent_context import AgentContext
        reviewer_context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=state.get("file_contents", ""),
            analysis_result=state.get("analysis_result", {}),
            dockerfile_content=dockerfile_content
        )
        
        review_result, usage = review_dockerfile(context=reviewer_context)
        
        usage_dict = {
            "stage": "reviewer",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("reviewer")
        }
        
        current_stats = state.get("usage_stats", [])
        span.set_attribute("is_secure", review_result.is_secure)
        
        if not review_result.is_secure:
            # Construct detailed error with structured fixes
            issues_str = "\n".join([
                f"- [{issue.severity}] {issue.description} (Fix: {issue.suggestion})" 
                for issue in review_result.issues
            ])
            error_msg = f"Security Review Failed:\n{issues_str}"
            logger.warning(error_msg)
            span.set_attribute("issues_count", len(review_result.issues))
            
            # Check if reviewer provided a fixed dockerfile
            if review_result.fixed_dockerfile:
                logger.info("Reviewer provided a corrected Dockerfile - will use it directly")
                span.set_attribute("auto_fixed", True)
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
    
    with create_span("node.validate", {
        "project_type": project_type,
        "stack": stack,
        "retry_count": state.get("retry_count", 0)
    }) as span:
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
        
        config = state.get("config", {})
        no_cache = config.get("no_cache", False)
        
        success, message, image_size, classified_error = validate_docker_build_and_run(
            path, 
            project_type, 
            stack, 
            health_endpoint, 
            recommended_wait_time,
            readiness_patterns=readiness_patterns,
            failure_patterns=failure_patterns,
            no_cache=no_cache
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
                if span:
                    span.set_attribute("validation.success", False)
                    span.set_attribute("validation.error", "image_size_exceeded")
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
            if span:
                span.set_attribute("validation.success", True)
                span.set_attribute("validation.image_size_mb", size_mb)
        else:
            if span:
                span.set_attribute("validation.success", False)
                span.set_attribute("validation.error", message[:200] if message else "")

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
    retry_count = state.get("retry_count", 0)
    error_type = state.get("error_details", {}).get("error_type", "unknown") if state.get("error_details") else "unknown"
    
    with create_span("node.reflect", {"retry_count": retry_count, "error_type": error_type}) as span:
        dockerfile_content = state.get("dockerfile_content", "")
        error_message = state.get("error", "Unknown error")
        error_details = state.get("error_details", {})
        analysis_result = state.get("analysis_result", {})
        retry_history = state.get("retry_history", [])
        
        logger.info("Reflecting on failure...")
        
        # Get container logs from error details if available
        container_logs = error_details.get("original_error", "") if error_details else ""
        
        from ..core.agent_context import AgentContext
        reflect_context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=state.get("file_contents", ""),
            analysis_result=analysis_result,
            dockerfile_content=dockerfile_content,
            error_message=error_message,
            error_details=error_details,
            retry_history=retry_history,
            container_logs=container_logs
        )
        
        reflection_result, usage = reflect_on_failure(context=reflect_context)
        
        usage_dict = {
            "stage": "reflector",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("reflector")
        }
        
        current_stats = state.get("usage_stats", [])
        
        # Convert reflection to dict
        reflection_dict = reflection_result.model_dump()
        
        logger.info(f"Root Cause: {reflection_result.root_cause_analysis}")
        logger.info(f"Fix Strategy: {', '.join(reflection_result.specific_fixes[:2])}")
        logger.info(f"Confidence: {reflection_result.confidence_in_fix}")
        
        span.set_attribute("root_cause", reflection_result.root_cause_analysis[:200])
        span.set_attribute("confidence", reflection_result.confidence_in_fix)
        span.set_attribute("needs_reanalysis", reflection_result.needs_reanalysis)
        
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
