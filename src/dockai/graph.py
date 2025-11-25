import os
import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from .state import DockAIState
from .scanner import get_file_tree
from .analyzer import analyze_repo_needs
from .generator import generate_dockerfile
from .reviewer import review_dockerfile
from .validator import validate_docker_build_and_run
from .errors import classify_error, ClassifiedError, ErrorType, format_error_for_display

logger = logging.getLogger("dockai")

def scan_node(state: DockAIState) -> DockAIState:
    path = state["path"]
    logger.info(f"Scanning directory: {path}")
    file_tree = get_file_tree(path)
    return {"file_tree": file_tree}

def analyze_node(state: DockAIState) -> DockAIState:
    file_tree = state["file_tree"]
    config = state.get("config", {})
    instructions = config.get("analyzer_instructions", "")
    
    logger.info("Analyzing repository needs...")
    # Returns (AnalysisResult object, usage_dict)
    analysis_result_obj, usage = analyze_repo_needs(file_tree, instructions)
    
    logger.info(f"Analyzer Reasoning:\n{analysis_result_obj.thought_process}")
    
    # Convert Pydantic model to dict for state storage
    analysis_result = analysis_result_obj.model_dump()
    
    usage_dict = {
        "stage": "analyzer",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    }
    
    current_stats = state.get("usage_stats", [])
    return {"analysis_result": analysis_result, "usage_stats": current_stats + [usage_dict]}

def read_files_node(state: DockAIState) -> DockAIState:
    path = state["path"]
    files_to_read = state["analysis_result"].get("files_to_read", [])
    
    logger.info(f"Reading {len(files_to_read)} critical files...")
    file_contents_str = ""
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
        except Exception as e:
            logger.warning(f"Could not read {rel_path}: {e}")
            
    return {"file_contents": file_contents_str}

from .registry import get_docker_tags

def generate_node(state: DockAIState) -> DockAIState:
    stack = state["analysis_result"].get("stack", "Unknown")
    file_contents = state["file_contents"]
    config = state.get("config", {})
    instructions = config.get("generator_instructions", "")
    feedback_error = state.get("error")
    
    # Get AI suggestions from previous error analysis (if any)
    error_details = state.get("error_details", {})
    dockerfile_fix = error_details.get("dockerfile_fix") if error_details else None
    image_suggestion = error_details.get("image_suggestion") if error_details else None
    
    # Fetch verified tags dynamically based on analysis
    suggested_image = state["analysis_result"].get("suggested_base_image", "").strip()
    verified_tags = []
    
    if suggested_image:
        logger.info(f"Fetching tags for suggested image: {suggested_image}")
        verified_tags = get_docker_tags(suggested_image)
    else:
        # Fallback if analysis didn't provide an image (should be rare)
        logger.warning("No suggested base image found. Falling back to heuristic.")
        if "node" in stack.lower(): verified_tags = get_docker_tags("node")
        elif "python" in stack.lower(): verified_tags = get_docker_tags("python")
        elif "go" in stack.lower(): verified_tags = get_docker_tags("golang")
        elif "rust" in stack.lower(): verified_tags = get_docker_tags("rust")
        elif "java" in stack.lower(): verified_tags = get_docker_tags("openjdk")
    
    verified_tags_str = ", ".join(verified_tags) if verified_tags else "Verification Skipped - Use your best judgement based on the suggested image."
    logger.info(f"Fetched verified base images: {verified_tags_str}")
    
    # Get extracted commands
    build_cmd = state["analysis_result"].get("build_command", "None detected")
    start_cmd = state["analysis_result"].get("start_command", "None detected")
    
    # Dynamic Model Selection
    # First attempt (retry_count=0): Use cheaper model (Analyzer Model)
    # Subsequent retries (retry_count>0): Use stronger model (Generator Model)
    retry_count = state.get("retry_count", 0)
    if retry_count == 0:
        model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        logger.info(f"Using Draft Model ({model_name}) for initial generation.")
    else:
        model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
        logger.info(f"Using Expert Model ({model_name}) for retry attempt {retry_count}.")

    logger.info("Generating Dockerfile...")
    dockerfile_content, project_type, thought_process, usage = generate_dockerfile(
        stack, 
        file_contents, 
        instructions, 
        feedback_error, 
        verified_tags=verified_tags_str,
        build_command=build_cmd,
        start_command=start_cmd,
        model_name=model_name,
        dockerfile_fix=dockerfile_fix,
        image_suggestion=image_suggestion
    )
    
    # Log the thought process
    logger.info(f"Architect's Reasoning:\n{thought_process}")
    
    # Update project type in analysis result if it changed or wasn't there
    analysis_result = state["analysis_result"].copy()
    analysis_result["project_type"] = project_type
    
    # Record actual model used (not the env var default)
    usage_dict = {
        "stage": "generator",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": model_name  # Use actual model that was selected
    }
    
    current_stats = state.get("usage_stats", [])
    
    # Don't increment retry_count here - it will be incremented in conditional edges when actually retrying
    return {
        "dockerfile_content": dockerfile_content,
        "analysis_result": analysis_result,
        "usage_stats": current_stats + [usage_dict],
        "error": None # Clear error on new generation
    }

def review_node(state: DockAIState) -> DockAIState:
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
        # Construct error message from issues
        issues_str = "\n".join([f"- [{issue.severity}] {issue.description} (Fix: {issue.suggestion})" for issue in review_result.issues])
        error_msg = f"Security Review Failed:\n{issues_str}"
        logger.warning(error_msg)
        return {
            "error": error_msg,
            "usage_stats": current_stats + [usage_dict]
        }
    
    logger.info("Security Review Passed.")
    return {
        "usage_stats": current_stats + [usage_dict]
    }

def validate_node(state: DockAIState) -> DockAIState:
    path = state["path"]
    dockerfile_content = state["dockerfile_content"]
    analysis_result = state["analysis_result"]
    
    project_type = analysis_result.get("project_type", "service")
    stack = analysis_result.get("stack", "Unknown")
    health_endpoint_data = analysis_result.get("health_endpoint")
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
    success, message, image_size, classified_error = validate_docker_build_and_run(
        path, project_type, stack, health_endpoint, recommended_wait_time
    )
    
    # Store classified error details for better error handling
    error_details = None
    if classified_error:
        error_details = classified_error.to_dict()
        # Log the classified error for better visibility
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
            warning_msg = f"Image size is {size_mb:.2f}MB, which exceeds the {max_size_mb}MB limit. Try to optimize using 'alpine' or 'slim' base images if compatible, or use multi-stage builds."
            logger.warning(warning_msg)
            # Image size issues are Dockerfile errors (can be fixed by retry)
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
        size_mb = image_size / (1024 * 1024)
        logger.info(f"Image size: {size_mb:.2f}MB (Optimized)")

    return {
        "validation_result": {"success": success, "message": message},
        "error": message if not success else None,
        "error_details": error_details
    }



def increment_retry(state: DockAIState) -> DockAIState:
    """Helper node to increment retry count when actually retrying."""
    current_count = state.get("retry_count", 0)
    logger.debug(f"Incrementing retry count from {current_count} to {current_count + 1}")
    return {"retry_count": current_count + 1}


def should_retry(state: DockAIState) -> Literal["increment_retry", "end"]:
    """
    Determine if we should retry based on error classification.
    
    Only retry for DOCKERFILE_ERROR and UNKNOWN_ERROR types.
    Do NOT retry for PROJECT_ERROR or ENVIRONMENT_ERROR.
    """
    # Check if we have error details with classification
    error_details = state.get("error_details")
    
    if error_details:
        error_type = error_details.get("error_type", "")
        should_retry_flag = error_details.get("should_retry", True)
        
        # Don't retry for project errors or environment errors
        if error_type in [ErrorType.PROJECT_ERROR.value, ErrorType.ENVIRONMENT_ERROR.value]:
            logger.error(f"Problem: {error_details.get('message', 'Unknown error')}")
            logger.info(f"Solution: {error_details.get('suggestion', 'Check the error and try again')}")
            return "end"
        
        # If classified error says don't retry, respect that
        if not should_retry_flag:
            logger.error(f"Problem: {error_details.get('message', 'Unknown error')}")
            return "end"
    
    # Check if we have a validation result
    validation_result = state.get("validation_result")
    
    # If we have a security error (no validation result yet), retry
    if state.get("error") and not validation_result:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            logger.warning(f"Security check failed. Retrying (attempt {retry_count + 1}/{max_retries})...")
            return "increment_retry"
        else:
            logger.error("Problem: Max retries reached - security check failed.")
            return "end"

    # If we have a validation result, check success
    if validation_result:
        if validation_result["success"]:
            return "end"
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            logger.warning(f"Validation failed. Retrying (attempt {retry_count + 1}/{max_retries})...")
            return "increment_retry"
        
        logger.error("Problem: Max retries reached - validation failed.")
        return "end"
        
    return "end"

def check_security(state: DockAIState) -> Literal["validate", "increment_retry", "end"]:
    # If there is an error from the review node, it means security failed
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            logger.warning(f"Security review failed. Retrying (attempt {retry_count + 1}/{max_retries})...")
            return "increment_retry"
        return "end"
    return "validate"


def create_graph():
    workflow = StateGraph(DockAIState)
    
    workflow.add_node("scan", scan_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("read_files", read_files_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("review", review_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("increment_retry", increment_retry)
    
    workflow.set_entry_point("scan")
    
    workflow.add_edge("scan", "analyze")
    workflow.add_edge("analyze", "read_files")
    workflow.add_edge("read_files", "generate")
    workflow.add_edge("generate", "review")
    workflow.add_edge("increment_retry", "generate")  # After incrementing, go back to generate
    
    workflow.add_conditional_edges(
        "review",
        check_security,
        {
            "validate": "validate",
            "increment_retry": "increment_retry",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "increment_retry": "increment_retry",
            "end": END
        }
    )
    
    return workflow.compile()

