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
    reflect_on_failure,
    create_blueprint,
    generate_iterative_dockerfile
)
from ..core.llm_providers import get_model_for_agent
from ..utils.tracing import create_span

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


def _is_model_not_found_error(error_str: str) -> bool:
    """
    Check if an error indicates the model was not found.
    
    Handles various provider-specific error messages:
    - OpenAI: "model 'xyz' not found", "does not exist"
    - Anthropic: "model not found", "invalid model"
    - Gemini: "model not found", "not a valid model"
    - Azure: "model not found", "deployment not found"
    """
    model_error_patterns = [
        'model not found',
        'model_not_found',
        'does not exist',
        'invalid model',
        'not a valid model',
        'deployment not found',
        'no such model',
        'unknown model',
        'the model',  # Common in "The model 'x' does not exist"
    ]
    return any(pattern in error_str for pattern in model_error_patterns)


def _is_rate_limit_error(error_str: str) -> bool:
    """Check if an error indicates rate limiting."""
    return any(pattern in error_str for pattern in [
        'rate limit', '429', 'too many requests', 'quota exceeded'
    ])


def _is_auth_error(error_str: str) -> bool:
    """Check if an error indicates authentication failure."""
    return any(pattern in error_str for pattern in [
        'authentication', 'api key', 'unauthorized', '401', 
        'invalid api key', 'incorrect api key', 'api_key'
    ])


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
        
        try:
            file_tree = get_file_tree(path)
        except FileNotFoundError:
            logger.error(f"Directory does not exist: {path}")
            return {
                "file_tree": [],
                "error": f"Directory not found: {path}",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"The specified path does not exist: {path}",
                    "suggestion": "Please verify the path and try again.",
                    "should_retry": False
                }
            }
        except NotADirectoryError:
            logger.error(f"Path is not a directory: {path}")
            return {
                "file_tree": [],
                "error": f"Path is not a directory: {path}",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"The specified path is not a directory: {path}",
                    "suggestion": "Please specify a directory path, not a file.",
                    "should_retry": False
                }
            }
        except PermissionError as e:
            logger.error(f"Permission denied accessing directory: {path} - {e}")
            return {
                "file_tree": [],
                "error": f"Permission denied: {path}",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"Cannot access directory due to permissions: {path}",
                    "suggestion": "Check directory permissions or run with appropriate privileges.",
                    "should_retry": False
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error scanning directory: {path} - {e}")
            return {
                "file_tree": [],
                "error": f"Failed to scan directory: {e}",
                "error_details": {
                    "error_type": "environment_error",
                    "message": str(e),
                    "suggestion": "Check the directory path and permissions.",
                    "should_retry": False
                }
            }
        
        # Check for empty directory
        if not file_tree:
            logger.warning(f"No files found in directory: {path} (may be empty or all files are ignored)")
            return {
                "file_tree": [],
                "error": "Empty directory or all files ignored",
                "error_details": {
                    "error_type": "project_error",
                    "message": "No files found to analyze. The directory may be empty or all files match ignore patterns.",
                    "suggestion": "Ensure the directory contains source code files and check .gitignore/.dockerignore patterns.",
                    "should_retry": False
                }
            }
        
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
    file_tree = state.get("file_tree", [])
    config = state.get("config", {})
    instructions = config.get("analyzer_instructions", "")
    
    # Check for empty file tree (edge case - should have been caught in scan_node)
    if not file_tree:
        logger.error("Cannot analyze: file tree is empty")
        return {
            "analysis_result": {},
            "error": "No files to analyze",
            "error_details": {
                "error_type": "project_error",
                "message": "The file tree is empty. Cannot analyze a project with no files.",
                "suggestion": "Ensure the project directory contains source files.",
                "should_retry": False
            }
        }
    
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
        
        try:
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
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for model not found errors
            if _is_model_not_found_error(error_str):
                logger.error(f"Model not found during analysis: {e}")
                model_name = get_model_for_agent("analyzer")
                return {
                    "analysis_result": {},
                    "error": f"Model '{model_name}' not found",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": f"The specified model '{model_name}' was not found. Check your model configuration.",
                        "suggestion": f"Verify the model name is correct. Set DOCKAI_MODEL_ANALYZER to a valid model name for your provider.",
                        "should_retry": False
                    }
                }
            
            # Check for rate limit errors
            if _is_rate_limit_error(error_str):
                logger.error(f"Rate limit exceeded during analysis: {e}")
                return {
                    "analysis_result": {},
                    "error": "API rate limit exceeded",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": "The LLM API rate limit was exceeded. Please wait a few minutes and try again.",
                        "suggestion": "Wait a few minutes before retrying, or check your API quota.",
                        "should_retry": False
                    }
                }
            
            # Check for authentication errors
            if _is_auth_error(error_str):
                logger.error(f"Authentication error during analysis: {e}")
                return {
                    "analysis_result": {},
                    "error": "API authentication failed",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": "Failed to authenticate with the LLM provider. Check your API key.",
                        "suggestion": "Verify your API key is correct and has not expired.",
                        "should_retry": False
                    }
                }
            
            # Generic LLM error
            logger.error(f"LLM error during analysis: {e}")
            return {
                "analysis_result": {},
                "error": f"Analysis failed: {str(e)[:200]}",
                "error_details": {
                    "error_type": "dockerfile_error",
                    "message": f"The AI analysis failed unexpectedly: {str(e)[:200]}",
                    "suggestion": "This may be a temporary issue. Try again or check your LLM configuration.",
                    "should_retry": True
                }
            }


from ..utils.file_utils import smart_truncate, read_critical_files

def read_files_node(state: DockAIState) -> DockAIState:
    """
    Reads project files for LLM context using RAG.
    
    This node uses semantic search and AST analysis to retrieve only the 
    most relevant context for Dockerfile generation, ensuring high quality
    output even for large repositories.

    Environment Variables:
        DOCKAI_READ_ALL_FILES: In standard mode, read all vs priority files (default: true)
    
    Args:
        state (DockAIState): The current state with analysis results.

    Returns:
        DockAIState: Updated state with 'file_contents' string and optionally 'code_intelligence'.
    """
    path = state["path"]
    analysis_result = state.get("analysis_result", {})
    file_tree = state.get("file_tree", [])
    config = state.get("config", {})
    
    # --- RAG STRATEGY ---
    return _read_files_rag(path, file_tree, config, analysis_result)


def _read_files_rag(path: str, file_tree: list, config: dict, analysis_result: dict) -> dict:
    """
    Read files using RAG (Retrieval-Augmented Generation).
    
    This is the primary (and only) supported context strategy in v4.0.
    """
    try:
        from ..utils.indexer import ProjectIndex
        from ..utils.context_retriever import ContextRetriever
    except ImportError as e:
        logger.error(f"Critical RAG dependencies missing: {e}. Please reinstall dockai-cli.")
        return _fallback_read_simple(path, file_tree, config)
    
    logger.info("Using RAG mode for intelligent context retrieval...")
    
    try:
        # Initialize and build the index
        index = ProjectIndex(use_embeddings=True)
        index.index_project(path, file_tree)
        
        # Get token limit from config or env
        token_limit = config.get("token_limit") or int(os.getenv("DOCKAI_TOKEN_LIMIT", "50000"))
        
        # Retrieve optimized context
        retriever = ContextRetriever(index, analysis_result)
        file_contents_str = retriever.get_dockerfile_context(max_tokens=token_limit)
        
        # Get code intelligence summary for logging/debugging
        summary = retriever.get_quick_summary()
        logger.info(
            f"RAG: indexed {summary['files_indexed']} chunks, "
            f"analyzed {summary['files_analyzed']} files, "
            f"found {len(summary['entry_points'])} entry points, "
            f"detected frameworks: {summary['frameworks']}"
        )
        
        # Store code intelligence for use by other nodes
        code_intelligence = {
            "entry_points": summary["entry_points"],
            "env_vars": summary["env_vars"],
            "ports": summary["ports"],
            "frameworks": summary["frameworks"],
            "embeddings_available": summary["embeddings_available"],
        }
        
        return {
            "file_contents": file_contents_str,
            "code_intelligence": code_intelligence
        }
        
    except Exception as e:
        logger.error(f"RAG indexing failed: {e}. Falling back to simple read.")
        return _fallback_read_simple(path, file_tree, config)


def _fallback_read_simple(path: str, file_tree: list, config: dict) -> dict:
    """
    Emergency fallback: Read all text files until token limit.
    Used ONLY if RAG crashes.
    """
    from ..utils.file_utils import smart_truncate
    
    token_limit = config.get("token_limit") or int(os.getenv("DOCKAI_TOKEN_LIMIT", "50000"))
    content_buffer = []
    current_tokens = 0
    
    logger.info("Performing fallback file read (Simple Mode)...")
    
    for relative_path in file_tree:
        # Skip lock files/ignored in fallback
        if "lock" in relative_path or ".git" in relative_path:
            continue
            
        full_path = os.path.join(path, relative_path)
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Truncate large files
            content = smart_truncate(content, max_tokens=2000)
            
            # Form header
            header = f"\n\n--- FILE: {relative_path} ---\n"
            entry_len = len(header) + len(content)
            
            if current_tokens + (entry_len // 4) > token_limit:
                break
                
            content_buffer.append(header)
            content_buffer.append(content)
            current_tokens += (entry_len // 4)
            
        except Exception:
            continue
            
    return {"file_contents": "".join(content_buffer)}
    





def blueprint_node(state: DockAIState) -> DockAIState:
    """
    AI-powered architectural blueprinting (Plan + Runtime Config).
    
    This node acts as the 'Chief Architect', analyzing the code to determine
    BOTH the build strategy and the runtime configuration in a single pass.
    
    Args:
        state (DockAIState): The current state with file contents.
        
    Returns:
        DockAIState: Updated state with 'current_plan', 'detected_health_endpoint',
                     'readiness_patterns', and usage stats.
    """
    file_contents = state.get("file_contents", "")
    analysis_result = state.get("analysis_result", {})
    retry_history = state.get("retry_history", [])
    
    logger.info("Creating architectural blueprint (Plan + Runtime Config)...")
    
    try:
        from ..core.agent_context import AgentContext
        context = AgentContext(
            file_tree=state.get("file_tree", []),
            file_contents=file_contents,
            analysis_result=analysis_result,
            retry_history=retry_history
        )
        
        blueprint, usage = create_blueprint(context=context)
        
        usage_dict = {
            "stage": "blueprint_architect",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": get_model_for_agent("blueprint")
        }
        
        current_stats = state.get("usage_stats", [])
        
        # Process Plan
        logger.info(f"Build Strategy: {blueprint.plan.build_strategy}")
        if blueprint.plan.use_multi_stage:
            logger.info("Using multi-stage build strategy")
            
        # Process Runtime Config
        detected_endpoint = None
        if blueprint.runtime_config.primary_health_endpoint:
            detected_endpoint = blueprint.runtime_config.primary_health_endpoint.model_dump() if hasattr(blueprint.runtime_config.primary_health_endpoint, 'model_dump') else blueprint.runtime_config.primary_health_endpoint
            logger.info(f"Detected health endpoint: {detected_endpoint}")
            
        logger.info(f"Detected {len(blueprint.runtime_config.startup_success_patterns)} success patterns")
        
        return {
            "current_plan": blueprint.plan.model_dump() if hasattr(blueprint.plan, 'model_dump') else blueprint.plan,
            "detected_health_endpoint": detected_endpoint,
            "readiness_patterns": blueprint.runtime_config.startup_success_patterns,
            "failure_patterns": blueprint.runtime_config.startup_failure_patterns,
            "usage_stats": current_stats + [usage_dict]
        }
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for model not found errors
        if _is_model_not_found_error(error_str):
            logger.error(f"Model not found during blueprint creation: {e}")
            model_name = get_model_for_agent("blueprint")
            return {
                "current_plan": {},
                "error": f"Model '{model_name}' not found",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"The specified model '{model_name}' was not found. Check your model configuration.",
                    "suggestion": f"Verify the model name is correct. Set DOCKAI_MODEL_BLUEPRINT to a valid model name for your provider.",
                    "should_retry": False
                }
            }
        
        # Check for rate limit errors
        if _is_rate_limit_error(error_str):
            logger.error(f"Rate limit exceeded during blueprint creation: {e}")
            return {
                "current_plan": {},
                "error": "API rate limit exceeded",
                "error_details": {
                    "error_type": "environment_error",
                    "message": "The LLM API rate limit was exceeded.",
                    "suggestion": "Wait a few minutes before retrying.",
                    "should_retry": False
                }
            }
        
        # Check for authentication errors
        if _is_auth_error(error_str):
            logger.error(f"Authentication error during blueprint creation: {e}")
            return {
                "current_plan": {},
                "error": "API authentication failed",
                "error_details": {
                    "error_type": "environment_error",
                    "message": "Failed to authenticate with the LLM provider. Check your API key.",
                    "suggestion": "Verify your API key is correct and has not expired.",
                    "should_retry": False
                }
            }
        
        logger.warning(f"Blueprint creation failed: {e}")
        return {
            "current_plan": {},
            "error": f"Blueprint creation failed: {str(e)[:200]}",
            "error_details": {
                "error_type": "dockerfile_error",
                "message": f"Failed to create blueprint: {str(e)[:200]}",
                "suggestion": "This may be a temporary issue. Will continue without blueprint.",
                "should_retry": True
            }
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
    
    # Edge case: Check for empty analysis result
    if not analysis_result:
        logger.error("Cannot generate Dockerfile: analysis result is empty")
        return {
            "dockerfile_content": "",
            "error": "No analysis result available",
            "error_details": {
                "error_type": "dockerfile_error",
                "message": "Cannot generate Dockerfile without analysis results.",
                "suggestion": "This is an internal error. The analysis step may have failed.",
                "should_retry": True
            }
        }
    
    with create_span("node.generate", {"stack": stack, "retry_count": retry_count}) as span:
        file_contents = state.get("file_contents", "")
        config = state.get("config", {})
        instructions = config.get("generator_instructions", "")
        current_plan = state.get("current_plan", {})
        reflection = state.get("reflection")
        previous_dockerfile = state.get("previous_dockerfile")
        
        # Edge case: Check for empty file contents (non-critical but log it)
        if not file_contents:
            logger.warning("File contents are empty - generating Dockerfile with limited context")
        
        try:
            # Fetch verified tags dynamically to ensure image existence
            suggested_image = analysis_result.get("suggested_base_image", "").strip()
            
            # Get detected runtime version from analyzer (e.g., "3.11" from pyproject.toml)
            detected_version = analysis_result.get("detected_runtime_version")
            
            # Check if reflection suggests a different base image
            if reflection and reflection.get("should_change_base_image"):
                suggested_image = reflection.get("suggested_base_image", suggested_image)
                logger.info(f"Using reflection-suggested base image: {suggested_image}")
                # Clear detected version when switching base images (reflection may suggest different tech)
                detected_version = None
            
            verified_tags = []
            if suggested_image:
                logger.info(f"Fetching tags for: {suggested_image}" + 
                           (f" (target version: {detected_version})" if detected_version else ""))
                try:
                    verified_tags = get_docker_tags(suggested_image, target_version=detected_version)
                except Exception as e:
                    logger.warning(f"Failed to fetch Docker tags for {suggested_image}: {e}")
                    verified_tags = []
            else:
                logger.warning("No suggested base image from analysis. AI will determine the best base image.")
            
            verified_tags_str = ", ".join(verified_tags) if verified_tags else "Use your best judgement based on the detected technology stack."
            
            # Use powerful model for initial generation - better quality upfront reduces retries
            # This optimization reduces total token usage by avoiding costly retry cycles
            model_name = get_model_for_agent("generator")  # Always use powerful model
            if retry_count == 0:
                logger.info(f"Generating Dockerfile (Model: {model_name})...")
            else:
                logger.info(f"Improving Dockerfile (Model: {model_name}, attempt {retry_count + 1})...")
            
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
            if span:
                span.set_attribute("project_type", project_type)
            
            # Edge case: Check if generated Dockerfile is empty
            if not dockerfile_content or not dockerfile_content.strip():
                logger.error("Generated Dockerfile is empty")
                return {
                    "dockerfile_content": "",
                    "error": "Empty Dockerfile generated",
                    "error_details": {
                        "error_type": "dockerfile_error",
                        "message": "The AI generated an empty Dockerfile.",
                        "suggestion": "This may be a temporary LLM issue. Retrying...",
                        "should_retry": True
                    }
                }
            
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
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for model not found errors
            if _is_model_not_found_error(error_str):
                logger.error(f"Model not found during generation: {e}")
                model_name = get_model_for_agent("generator")
                return {
                    "dockerfile_content": "",
                    "error": f"Model '{model_name}' not found",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": f"The specified model '{model_name}' was not found. Check your model configuration.",
                        "suggestion": f"Verify the model name is correct. Set DOCKAI_MODEL_GENERATOR to a valid model name for your provider.",
                        "should_retry": False
                    }
                }
            
            # Check for rate limit errors
            if _is_rate_limit_error(error_str):
                logger.error(f"Rate limit exceeded during generation: {e}")
                return {
                    "dockerfile_content": "",
                    "error": "API rate limit exceeded",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": "The LLM API rate limit was exceeded.",
                        "suggestion": "Wait a few minutes before retrying, or check your API quota.",
                        "should_retry": False
                    }
                }
            
            # Check for authentication errors
            if _is_auth_error(error_str):
                logger.error(f"Authentication error during generation: {e}")
                return {
                    "dockerfile_content": "",
                    "error": "API authentication failed",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": "Failed to authenticate with the LLM provider. Check your API key.",
                        "suggestion": "Verify your API key is correct and has not expired.",
                        "should_retry": False
                    }
                }
            
            # Generic LLM error
            logger.error(f"Dockerfile generation failed: {e}")
            return {
                "dockerfile_content": "",
                "error": f"Generation failed: {str(e)[:200]}",
                "error_details": {
                    "error_type": "dockerfile_error",
                    "message": f"Failed to generate Dockerfile: {str(e)[:200]}",
                    "suggestion": "This may be a temporary issue. Retrying...",
                    "should_retry": True
                }
            }


def review_node(state: DockAIState) -> DockAIState:
    """
    AI-powered security review of the generated Dockerfile.
    
    This node acts as a "Security Auditor". It checks the generated Dockerfile
    for common security vulnerabilities (e.g., running as root, exposing sensitive ports)
    and provides structured fixes.
    
    If the reviewer can fix the issue automatically, it does so. Otherwise, it
    flags the error for the next iteration.
    
    Optimization: Script projects skip the expensive AI security review since they
    are single-run and carry less security risk than long-running services.

    Args:
        state (DockAIState): The current state with the generated Dockerfile.

    Returns:
        DockAIState: Updated state with potential errors or a fixed Dockerfile.
    """
    dockerfile_content = state.get("dockerfile_content", "")
    analysis_result = state.get("analysis_result", {})
    project_type = analysis_result.get("project_type", "service")
    
    # Edge case: Check for empty dockerfile
    if not dockerfile_content or not dockerfile_content.strip():
        logger.error("Cannot review: dockerfile_content is empty")
        return {
            "error": "No Dockerfile to review",
            "error_details": {
                "error_type": "dockerfile_error",
                "message": "Cannot perform security review on empty Dockerfile.",
                "suggestion": "Dockerfile generation may have failed.",
                "should_retry": True
            }
        }
    
    # OPTIMIZATION: Skip expensive AI security review for script projects
    # Scripts are single-run and carry less security risk than long-running services
    skip_review = os.getenv("DOCKAI_SKIP_SECURITY_REVIEW", "false").lower() == "true"
    
    if project_type == "script" or skip_review:
        if project_type == "script":
            logger.info("Skipping security review for script project (single-run, lower risk)")
        else:
            logger.info("Security review skipped (DOCKAI_SKIP_SECURITY_REVIEW=true)")
        return {}  # No changes, proceed to validation
    
    with create_span("node.review", {}) as span:
        logger.info("Performing Security Review...")
        
        try:
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
            if span:
                span.set_attribute("is_secure", review_result.is_secure)
            
            if not review_result.is_secure:
                # Construct detailed error with structured fixes
                issues_str = "\n".join([
                    f"- [{issue.severity}] {issue.description} (Fix: {issue.suggestion})" 
                    for issue in review_result.issues
                ])
                error_msg = f"Security Review Failed:\n{issues_str}"
                logger.warning(error_msg)
                if span:
                    span.set_attribute("issues_count", len(review_result.issues))
                
                # Check if reviewer provided a fixed dockerfile
                if review_result.fixed_dockerfile:

                    logger.info("Reviewer provided a corrected Dockerfile - will use it directly")
                    if span:
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
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if 'rate limit' in error_str or '429' in error_str or 'quota exceeded' in error_str:
                logger.error(f"Rate limit exceeded during security review: {e}")
                return {
                    "error": "API rate limit exceeded",
                    "error_details": {
                        "error_type": "environment_error",
                        "message": "The LLM API rate limit was exceeded.",
                        "suggestion": "Wait a few minutes before retrying.",
                        "should_retry": False
                    }
                }
            
            # For other errors, skip the review and proceed (non-critical)
            logger.warning(f"Security review failed (continuing without review): {e}")
            return {}  # Proceed to validation without blocking


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
        try:
            with open(output_path, "w") as f:
                f.write(dockerfile_content)
        except PermissionError as e:
            logger.error(f"Permission denied writing Dockerfile: {output_path}")
            return {
                "validation_result": {"success": False, "message": f"Permission denied: {e}"},
                "error": f"Cannot write Dockerfile: Permission denied",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"Cannot write Dockerfile to {output_path}: Permission denied",
                    "suggestion": "Check directory permissions or run with appropriate privileges.",
                    "should_retry": False
                }
            }
        except OSError as e:
            logger.error(f"Failed to write Dockerfile: {e}")
            return {
                "validation_result": {"success": False, "message": str(e)},
                "error": f"Cannot write Dockerfile: {e}",
                "error_details": {
                    "error_type": "environment_error",
                    "message": f"Failed to write Dockerfile to {output_path}: {e}",
                    "suggestion": "Check disk space and directory permissions.",
                    "should_retry": False
                }
            }
            
        logger.info("Validating Dockerfile...")
        
        # Use AI-detected readiness patterns if available
        readiness_patterns = state.get("readiness_patterns", [])
        failure_patterns = state.get("failure_patterns", [])
        
        config = state.get("config", {})
        no_cache = config.get("no_cache", False)
        
        success, message, image_size, classified_error = validate_docker_build_and_run(
            directory=path,
            project_type=project_type,
            stack=stack,
            health_endpoint=health_endpoint,
            recommended_wait_time=recommended_wait_time,
            readiness_patterns=analysis_result.get("readiness_patterns"),
            failure_patterns=analysis_result.get("failure_patterns"),
            no_cache=True if state.get("retry_count", 0) > 0 else False,
            analysis_result=analysis_result
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
        
        try:
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
            
            if span:
                span.set_attribute("root_cause", reflection_result.root_cause_analysis[:200])
                span.set_attribute("confidence", reflection_result.confidence_in_fix)
                span.set_attribute("needs_reanalysis", reflection_result.needs_reanalysis)
            
            # Add to retry history for learning (compact format to save tokens)
            # We intentionally exclude full dockerfile_content - it's stored in previous_dockerfile
            # and including it here would bloat context on subsequent retries
            new_retry_entry = {
                "attempt_number": state.get("retry_count", 0) + 1,
                "error_type": error_details.get("error_type", "unknown") if error_details else "unknown",
                "error_summary": error_message[:200] if error_message else "Unknown",  # Truncate long errors
                "what_was_tried": reflection_result.what_was_tried,
                "why_it_failed": reflection_result.why_it_failed,
                "lesson_learned": reflection_result.lesson_learned,
                "fix_applied": ", ".join(reflection_result.specific_fixes[:2]) if reflection_result.specific_fixes else ""  # Top 2 fixes only
            }
            
            updated_history = retry_history + [new_retry_entry]
            
            return {
                "reflection": reflection_dict,
                "previous_dockerfile": dockerfile_content,  # Store for iterative improvement
                "needs_reanalysis": reflection_result.needs_reanalysis,
                "retry_history": updated_history,
                "usage_stats": current_stats + [usage_dict]
            }
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if 'rate limit' in error_str or '429' in error_str or 'quota exceeded' in error_str:
                logger.error(f"Rate limit exceeded during reflection: {e}")
                # Return a basic reflection that suggests retrying
                return {
                    "reflection": {
                        "root_cause_analysis": "Rate limit exceeded during analysis",
                        "specific_fixes": ["Wait and retry"],
                        "confidence_in_fix": 0.5,
                        "needs_reanalysis": False,
                        "what_was_tried": "Attempted to analyze failure",
                        "why_it_failed": "API rate limit exceeded",
                        "lesson_learned": "Rate limits can cause reflection failures"
                    },
                    "previous_dockerfile": dockerfile_content,
                    "needs_reanalysis": False,
                    "retry_history": retry_history + [{
                        "attempt_number": retry_count + 1,
                        "error_type": "rate_limit",
                        "error_summary": "Rate limit exceeded during reflection",
                        "what_was_tried": "Unknown",
                        "why_it_failed": "Rate limit",
                        "lesson_learned": "N/A",
                        "fix_applied": "Retry with basic fix approach"
                    }]
                }
            
            # For other errors, provide a basic fallback reflection
            logger.error(f"Reflection failed: {e}")
            return {
                "reflection": {
                    "root_cause_analysis": f"Reflection failed: {str(e)[:200]}",
                    "specific_fixes": ["Review error details manually", "Check Dockerfile syntax"],
                    "confidence_in_fix": 0.3,
                    "needs_reanalysis": True,
                    "what_was_tried": "Unknown - reflection failed",
                    "why_it_failed": str(e)[:200],
                    "lesson_learned": "Reflection can fail on complex errors"
                },
                "previous_dockerfile": dockerfile_content,
                "needs_reanalysis": True,
                "retry_history": retry_history + [{
                    "attempt_number": retry_count + 1,
                    "error_type": error_type,
                    "error_summary": error_message[:200] if error_message else "Unknown",
                    "what_was_tried": "Unknown - reflection failed",
                    "why_it_failed": str(e)[:100],
                    "lesson_learned": "Reflection failed",
                    "fix_applied": "Attempting basic fixes"
                }]
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
