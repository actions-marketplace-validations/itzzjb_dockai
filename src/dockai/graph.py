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

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from .state import DockAIState
from .errors import ErrorType
from .nodes import (
    scan_node,
    analyze_node,
    read_files_node,
    detect_health_node,
    detect_readiness_node,
    plan_node,
    generate_node,
    review_node,
    validate_node,
    reflect_node,
    increment_retry
)

logger = logging.getLogger("dockai")


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

