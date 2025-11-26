"""
DockAI State Management.

This module defines the state structures used by the LangGraph workflow.
The state acts as the shared memory for the agent, persisting data across
different nodes (steps) of the execution graph. It includes not just the
current artifacts (like the Dockerfile) but also the agent's "memory" of
past attempts, plans, and reflections.
"""

from typing import TypedDict, List, Dict, Optional, Any

class RetryAttempt(TypedDict):
    """
    Records a single retry attempt for learning purposes.
    
    This structure allows the agent to build a history of what has been tried,
    why it failed, and what was learned. This "episodic memory" is crucial
    for the agent to avoid repeating the same mistakes.
    """
    attempt_number: int
    dockerfile_content: str
    error_message: str
    error_type: str
    what_was_tried: str
    why_it_failed: str
    lesson_learned: str

class DockAIState(TypedDict):
    """
    The central state object for the DockAI workflow.
    
    This TypedDict defines all the data that flows through the graph.
    It is mutable and updated by each node in the workflow.
    """
    # ==================== INPUTS ====================
    path: str  # The absolute path to the project directory being analyzed
    config: Dict[str, Any]  # Configuration options and custom instructions
    max_retries: int  # Maximum number of allowed retry attempts

    # ==================== INTERMEDIATE ARTIFACTS ====================
    file_tree: List[str]  # List of relative file paths in the project
    file_contents: str  # Concatenated content of critical files for LLM context
    
    # Analysis & Planning
    analysis_result: Dict[str, Any]  # The result of the initial project analysis (AnalysisResult)
    current_plan: Optional[Dict[str, Any]]  # The strategic plan generated before coding (PlanningResult)
    
    # Generation
    dockerfile_content: str  # The current generated Dockerfile content
    previous_dockerfile: Optional[str]  # The Dockerfile from the previous attempt (for diffing/iteration)
    
    # Validation & Execution
    validation_result: Dict[str, Any]  # Result of the build/run validation step
    retry_count: int  # Current retry attempt number (0-indexed)
    
    # Error Handling
    error: Optional[str]  # The raw error message if validation failed
    error_details: Optional[Dict[str, Any]]  # Structured, classified error details (ClassifiedError)
    logs: List[str]  # Execution logs (stdout/stderr)
    
    # ==================== ADAPTIVE INTELLIGENCE ====================
    # These fields enable the "Agentic" behavior
    
    retry_history: List[RetryAttempt]  # Full history of attempts, failures, and learnings
    reflection: Optional[Dict[str, Any]]  # The AI's analysis of the most recent failure (ReflectionResult)
    
    # Smart Detection
    detected_health_endpoint: Optional[Dict[str, Any]]  # Health endpoint detected from deep code analysis
    readiness_patterns: List[str]  # Regex patterns for detecting successful startup from logs
    failure_patterns: List[str]  # Regex patterns for detecting startup failure from logs
    
    # Control Flow
    needs_reanalysis: bool  # Flag to trigger a jump back to the analysis phase if assumptions were wrong
    
    # Observability
    usage_stats: List[Dict[str, Any]]  # Token usage statistics for cost tracking
