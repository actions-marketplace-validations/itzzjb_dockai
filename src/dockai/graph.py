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
        "model": os.getenv("MODEL_ANALYZER")
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
    # Retry 0: Use cheaper model (Analyzer Model)
    # Retry > 0: Use stronger model (Generator Model)
    retry_count = state.get("retry_count", 0)
    if retry_count == 0:
        model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
        logger.info(f"Using Draft Model ({model_name}) for initial generation.")
    else:
        model_name = os.getenv("MODEL_GENERATOR", "gpt-4o")
        logger.info(f"Using Expert Model ({model_name}) for retry {retry_count}.")

    logger.info("Generating Dockerfile...")
    dockerfile_content, project_type, thought_process, usage = generate_dockerfile(
        stack, 
        file_contents, 
        instructions, 
        feedback_error, 
        verified_tags=verified_tags_str,
        build_command=build_cmd,
        start_command=start_cmd,
        model_name=model_name
    )
    
    # Log the thought process
    logger.info(f"Architect's Reasoning:\n{thought_process}")
    
    # Update project type in analysis result if it changed or wasn't there
    analysis_result = state["analysis_result"].copy()
    analysis_result["project_type"] = project_type
    
    usage_dict = {
        "stage": "generator",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "model": os.getenv("MODEL_GENERATOR")
    }
    
    current_stats = state.get("usage_stats", [])
    
    return {
        "dockerfile_content": dockerfile_content,
        "analysis_result": analysis_result,
        "retry_count": state.get("retry_count", 0) + 1,
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
        "model": os.getenv("MODEL_ANALYZER")
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
    success, message, image_size = validate_docker_build_and_run(
        path, project_type, stack, health_endpoint, recommended_wait_time
    )
    
    # Check for image size optimization
    # Threshold: 250MB (Aggressive optimization)
    SIZE_THRESHOLD = 250 * 1024 * 1024
    
    if success and image_size > SIZE_THRESHOLD:
        size_mb = image_size / (1024 * 1024)
        warning_msg = f"Image size is {size_mb:.2f}MB, which exceeds the 250MB limit. Try to optimize using 'alpine' or 'slim' base images if compatible, or use multi-stage builds."
        logger.warning(warning_msg)
        return {
            "validation_result": {"success": False, "message": warning_msg},
            "error": warning_msg
        }
    
    if success:
        size_mb = image_size / (1024 * 1024)
        logger.info(f"Image size: {size_mb:.2f}MB (Optimized)")

    return {
        "validation_result": {"success": success, "message": message},
        "error": message if not success else None
    }



def should_retry(state: DockAIState) -> Literal["generate", "end"]:
    # Check if we have a validation result
    validation_result = state.get("validation_result")
    
    # If we have a security error (no validation result yet), retry
    if state.get("error") and not validation_result:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            logger.warning(f"Security check failed. Retrying ({retry_count}/{max_retries})...")
            return "generate"
        else:
            logger.error("Max retries reached. Security check failed.")
            return "end"

    # If we have a validation result, check success
    if validation_result:
        if validation_result["success"]:
            return "end"
        
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            logger.warning(f"Validation failed. Retrying ({retry_count}/{max_retries})...")
            return "generate"
        
        logger.error("Max retries reached. Validation failed.")
        return "end"
        
    return "end"

def check_security(state: DockAIState) -> Literal["validate", "generate", "end"]:
    # If there is an error from the review node, it means security failed
    if state.get("error"):
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retry_count < max_retries:
            return "generate"
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
    
    workflow.set_entry_point("scan")
    
    workflow.add_edge("scan", "analyze")
    workflow.add_edge("analyze", "read_files")
    workflow.add_edge("read_files", "generate")
    workflow.add_edge("generate", "review")
    
    workflow.add_conditional_edges(
        "review",
        check_security,
        {
            "validate": "validate",
            "generate": "generate",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "generate": "generate",
            "end": END
        }
    )
    
    return workflow.compile()
