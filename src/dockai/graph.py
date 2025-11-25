"""
DockAI Adaptive Agent Graph

This module implements a truly adaptive agentic workflow that:
1. Plans before generating (strategic thinking)
2. Reflects on failures (learning from mistakes)
3. Iterates intelligently (targeted fixes, not full regeneration)
4. Detects health endpoints from code (not just file names)
5. Uses smart readiness detection (log patterns, not fixed sleep)
6. Re-analyzes when necessary (adapts to new information)

The workflow is designed to mimic how a senior engineer would approach
Dockerfile generation - with planning, learning, and adaptation.
"""

import os
import logging
from typing import Dict, Any, Literal, Optional
from langgraph.graph import StateGraph, END

from .state import DockAIState
from .scanner import get_file_tree
from .analyzer import analyze_repo_needs
from .generator import generate_dockerfile
from .reviewer import review_dockerfile
from .validator import validate_docker_build_and_run
from .errors import classify_error, ClassifiedError, ErrorType, format_error_for_display
from .registry import get_docker_tags
from .agent import (
    create_plan,
    reflect_on_failure,
    detect_health_endpoints,
    detect_readiness_patterns,
    generate_iterative_dockerfile,
    check_container_readiness
)

logger = logging.getLogger("dockai")


# ==================== NODE IMPLEMENTATIONS ====================

def scan_node(state: DockAIState) -> DockAIState:
    """
    Scan the repository directory tree.
    This is a fast, local operation that builds the file list.
    """
    path = state["path"]
    logger.info(f"📁 Scanning directory: {path}")
    file_tree = get_file_tree(path)
    logger.info(f"Found {len(file_tree)} files to analyze")
    return {"file_tree": file_tree}


def analyze_node(state: DockAIState) -> DockAIState:
    """
    AI-powered analysis of the repository.
    
    This node:
    - Analyzes the file tree to understand the project
    - Detects stack, build commands, and entry points
    - Identifies critical files to read
    - Suggests base images
    
    If needs_reanalysis is set, provides focused re-analysis context.
    """
    file_tree = state["file_tree"]
    config = state.get("config", {})
    instructions = config.get("analyzer_instructions", "")
    
    # Check if this is a re-analysis triggered by reflection
    needs_reanalysis = state.get("needs_reanalysis", False)
    reflection = state.get("reflection")
    
    if needs_reanalysis and reflection:
        # Add re-analysis focus to instructions
        focus = reflection.get("reanalysis_focus", "")
        if focus:
            instructions += f"\n\nRE-ANALYSIS FOCUS: {focus}\n"
            instructions += "The previous analysis may have been incorrect. Pay special attention to the focus area."
        logger.info(f"🔄 Re-analyzing with focus: {focus}")
    else:
        logger.info("🧠 Analyzing repository needs...")
    
    # Returns (AnalysisResult object, usage_dict)
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
        "needs_reanalysis": False  # Clear the flag
    }

def read_files_node(state: DockAIState) -> DockAIState:
    """
    Read critical files identified by the analyzer.
    
    This node reads the files that the AI determined are necessary
    for understanding the project's build and runtime requirements.
    """
    path = state["path"]
    files_to_read = state["analysis_result"].get("files_to_read", [])
    
    logger.info(f"📖 Reading {len(files_to_read)} critical files...")
    file_contents_str = ""
    files_read = 0
    files_failed = []
    
    for rel_path in files_to_read:
        abs_file_path = os.path.join(path, rel_path)
        try:
            with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                # Truncate if too large (50KB limit)
                MAX_SIZE = 50 * 1024
                if len(content) > MAX_SIZE:
                    content = content[:MAX_SIZE] + "\n... [TRUNCATED DUE TO SIZE] ..."
                    logger.warning(f"Truncated large file: {rel_path}")
                
                # Truncate if too many lines (1000 lines limit)
                lines = content.splitlines()
                if len(lines) > 1000:
                    content = "\n".join(lines[:1000]) + "\n... [TRUNCATED DUE TO LENGTH] ..."
                    logger.warning(f"Truncated long file: {rel_path}")
                    
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
    
    This is more accurate than the analyzer's file-name-based detection
    because it reads the actual route definitions in the code.
    """
    file_contents = state.get("file_contents", "")
    analysis_result = state.get("analysis_result", {})
    
    # Skip if already have health endpoint from analyzer with high confidence
    existing_health = analysis_result.get("health_endpoint")
    if existing_health:
        logger.info(f"Using analyzer-detected health endpoint: {existing_health.get('path')}:{existing_health.get('port')}")
        return {}
    
    logger.info("🔍 Detecting health endpoints from code...")
    
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
    
    This detects patterns in logs that indicate the application
    has started successfully, enabling smart readiness checking
    instead of fixed sleep times.
    """
    file_contents = state.get("file_contents", "")
    analysis_result = state.get("analysis_result", {})
    
    logger.info("🎯 Detecting startup readiness patterns...")
    
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
            "usage_stats": current_stats + [usage_dict]
        }
    except Exception as e:
        logger.warning(f"Readiness pattern detection failed: {e}")
        return {"readiness_patterns": []}


def plan_node(state: DockAIState) -> DockAIState:
    """
    AI-powered planning before Dockerfile generation.
    
    This creates a strategic plan that considers:
    - The specific technology stack
    - Previous retry history (learning from mistakes)
    - Potential challenges and mitigations
    - Optimal build strategy
    """
    analysis_result = state.get("analysis_result", {})
    file_contents = state.get("file_contents", "")
    retry_history = state.get("retry_history", [])
    config = state.get("config", {})
    instructions = config.get("generator_instructions", "")
    
    logger.info("📋 Creating generation plan...")
    
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
    
    This node handles both:
    1. Initial generation (fresh Dockerfile based on plan)
    2. Iterative improvement (targeted fixes based on reflection)
    
    The decision is based on whether we have a reflection from a previous failure.
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
    
    # Fetch verified tags dynamically
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
        # No specific image suggested - let AI determine best approach
        logger.warning("No suggested base image from analysis. AI will determine the best base image.")
    
    verified_tags_str = ", ".join(verified_tags) if verified_tags else "Use your best judgement based on the detected technology stack."
    
    # Dynamic Model Selection
    if retry_count == 0:
        model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        logger.info(f"🏗️ Generating Dockerfile (Draft Model: {model_name})...")
    else:
        model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
        logger.info(f"🔧 Improving Dockerfile (Expert Model: {model_name}, attempt {retry_count + 1})...")
    
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
    
    This node checks for security issues and provides structured
    fixes that can be directly applied in the next iteration.
    """
    dockerfile_content = state["dockerfile_content"]
    
    logger.info("🔒 Performing Security Review...")
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
    
    logger.info("✅ Security Review Passed.")
    return {
        "usage_stats": current_stats + [usage_dict]
    }

def validate_node(state: DockAIState) -> DockAIState:
    """
    Validate the Dockerfile by building and running the container.
    
    This node:
    1. Builds the Docker image
    2. Runs the container with resource limits
    3. Uses AI-detected readiness patterns for smart waiting
    4. Performs health checks if endpoint is detected
    5. Classifies any errors using AI
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
        
    logger.info("🐳 Validating Dockerfile...")
    
    # Use AI-detected readiness patterns if available
    readiness_patterns = state.get("readiness_patterns", [])
    
    success, message, image_size, classified_error = validate_docker_build_and_run(
        path, 
        project_type, 
        stack, 
        health_endpoint, 
        recommended_wait_time,
        readiness_patterns=readiness_patterns
    )
    
    # Store classified error details for better error handling
    error_details = None
    container_logs = ""
    
    if classified_error:
        error_details = classified_error.to_dict()
        container_logs = classified_error.original_error
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
        logger.info(f"✅ Validation Passed! Image size: {size_mb:.2f}MB")

    return {
        "validation_result": {"success": success, "message": message},
        "error": message if not success else None,
        "error_details": error_details
    }


def reflect_node(state: DockAIState) -> DockAIState:
    """
    AI-powered reflection on failure.
    
    This is the key to adaptive behavior - the agent reflects on
    what went wrong and creates a strategy for the next attempt.
    """
    dockerfile_content = state.get("dockerfile_content", "")
    error_message = state.get("error", "Unknown error")
    error_details = state.get("error_details", {})
    analysis_result = state.get("analysis_result", {})
    retry_history = state.get("retry_history", [])
    
    logger.info("🤔 Reflecting on failure...")
    
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
    """Helper node to increment retry count."""
    current_count = state.get("retry_count", 0)
    logger.info(f"🔄 Retry {current_count + 1}...")
    return {"retry_count": current_count + 1}


# ==================== CONDITIONAL EDGE FUNCTIONS ====================

def should_retry(state: DockAIState) -> Literal["reflect", "end"]:
    """
    Determine if we should retry based on error classification.
    
    Routes to reflection node for learning before retry,
    or ends if retry is not appropriate.
    """
    error_details = state.get("error_details")
    
    if error_details:
        error_type = error_details.get("error_type", "")
        should_retry_flag = error_details.get("should_retry", True)
        
        # Don't retry for project errors or environment errors
        if error_type in [ErrorType.PROJECT_ERROR.value, ErrorType.ENVIRONMENT_ERROR.value]:
            logger.error(f"❌ Cannot retry: {error_details.get('message', 'Unknown error')}")
            logger.info(f"💡 Solution: {error_details.get('suggestion', 'Check the error and try again')}")
            return "end"
        
        if not should_retry_flag:
            logger.error(f"❌ {error_details.get('message', 'Unknown error')}")
            return "end"
    
    # Check retry limits
    validation_result = state.get("validation_result")
    
    if state.get("error") and not validation_result:
        # Security error
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        else:
            logger.error("❌ Max retries reached - security check failed.")
            return "end"

    if validation_result:
        if validation_result["success"]:
            return "end"
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        
        logger.error("❌ Max retries reached - validation failed.")
        return "end"
        
    return "end"


def check_security(state: DockAIState) -> Literal["validate", "reflect", "end"]:
    """Check if security review passed, route to validation or retry."""
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            return "reflect"  # Go to reflection before retry
        return "end"
    return "validate"


def check_reanalysis(state: DockAIState) -> Literal["analyze", "plan", "generate"]:
    """
    After reflection, check if we need to re-analyze the project.
    
    Routes to:
    - analyze: If reflection says we need to re-analyze
    - plan: If we need a new plan but analysis is OK
    - generate: If we can directly apply fixes
    """
    needs_reanalysis = state.get("needs_reanalysis", False)
    reflection = state.get("reflection", {})
    
    if needs_reanalysis:
        logger.info("Re-analysis needed based on reflection")
        return "analyze"
    
    # Check if reflection suggests major strategy change
    if reflection:
        if reflection.get("should_change_build_strategy"):
            logger.info("Strategy change needed - creating new plan")
            return "plan"
    
    # For targeted fixes, go directly to generate
    return "generate"


# ==================== GRAPH CONSTRUCTION ====================

def create_graph():
    """
    Create the adaptive agent workflow graph.
    
    The workflow structure:
    
    scan → analyze → read_files → detect_health → detect_readiness → plan → generate → review
                                                                                           ↓
                                                                                       validate
                                                                                           ↓
                                                                            (if failed) reflect → (check_reanalysis)
                                                                                                        ↓
                                                                            ← ← ← ← ← ← ← ← ← ← ← analyze/plan/generate
    """
    workflow = StateGraph(DockAIState)
    
    # Add nodes
    workflow.add_node("scan", scan_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("read_files", read_files_node)
    workflow.add_node("detect_health", detect_health_node)
    workflow.add_node("detect_readiness", detect_readiness_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("review", review_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("increment_retry", increment_retry)
    
    # Set entry point
    workflow.set_entry_point("scan")
    
    # Main flow edges
    workflow.add_edge("scan", "analyze")
    workflow.add_edge("analyze", "read_files")
    workflow.add_edge("read_files", "detect_health")
    workflow.add_edge("detect_health", "detect_readiness")
    workflow.add_edge("detect_readiness", "plan")
    workflow.add_edge("plan", "generate")
    workflow.add_edge("generate", "review")
    
    # Security check routing
    workflow.add_conditional_edges(
        "review",
        check_security,
        {
            "validate": "validate",
            "reflect": "reflect",
            "end": END
        }
    )
    
    # Validation result routing
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "reflect": "reflect",
            "end": END
        }
    )
    
    # After reflection, decide next step
    workflow.add_edge("reflect", "increment_retry")
    
    workflow.add_conditional_edges(
        "increment_retry",
        check_reanalysis,
        {
            "analyze": "analyze",
            "plan": "plan",
            "generate": "generate"
        }
    )
    
    return workflow.compile()

