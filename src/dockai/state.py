from typing import TypedDict, List, Dict, Optional, Any

class DockAIState(TypedDict):
    path: str
    file_tree: List[str]
    analysis_result: Dict[str, Any]
    file_contents: str
    dockerfile_content: str
    validation_result: Dict[str, Any]
    retry_count: int
    max_retries: int
    error: Optional[str]
    logs: List[str]
    usage_stats: List[Dict[str, Any]]
    config: Dict[str, Any]
