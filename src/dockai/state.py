from typing import TypedDict, List, Dict, Optional, Any

class RetryAttempt(TypedDict):
    """Records a single retry attempt for learning."""
    attempt_number: int
    dockerfile_content: str
    error_message: str
    error_type: str
    what_was_tried: str
    why_it_failed: str
    lesson_learned: str

class DockAIState(TypedDict):
    path: str
    file_tree: List[str]
    analysis_result: Dict[str, Any]
    file_contents: str
    dockerfile_content: str
    previous_dockerfile: Optional[str]  # Previous attempt for iterative improvement
    validation_result: Dict[str, Any]
    retry_count: int
    max_retries: int
    error: Optional[str]
    error_details: Optional[Dict[str, Any]]  # Classified error details
    logs: List[str]
    usage_stats: List[Dict[str, Any]]
    config: Dict[str, Any]
    # New fields for adaptive agent behavior
    retry_history: List[RetryAttempt]  # Full history of what was tried and learned
    current_plan: Optional[Dict[str, Any]]  # AI-generated plan before generation
    reflection: Optional[Dict[str, Any]]  # AI reflection on failures
    detected_health_endpoint: Optional[Dict[str, Any]]  # AI-detected from file contents
    readiness_patterns: List[str]  # AI-detected startup log patterns
    failure_patterns: List[str]  # AI-detected failure log patterns
    needs_reanalysis: bool  # Flag to trigger re-analysis on certain errors
