"""
DockAI Agent Context Module.

This module defines a standardized context object that is passed to all AI agents,
ensuring they have access to all relevant information without having to pass
dozens of individual parameters.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AgentContext:
    """
    Standardized context object passed to all AI agents.
    
    This encapsulates all the information an agent might need to make decisions,
    preventing parameter proliferation and ensuring consistency across agents.
    
    Attributes:
        file_tree: List of all files in the project (relative paths)
        file_contents: Concatenated contents of critical files
        analysis_result: Results from the initial project analysis
        current_plan: The strategic Dockerfile generation plan (if created)
        retry_history: List of previous retry attempts with lessons learned
        dockerfile_content: The current/previous Dockerfile content (if exists)
        reflection: Reflection on the most recent failure (if exists)
        error_message: The most recent error message (if exists)
        error_details: Classified error details (if exists)
        container_logs: Container runtime logs (if available)
        custom_instructions: User-provided instructions specific to this agent
        verified_tags: Verified Docker image tags from registry
        retry_count: Current retry attempt number
    """
    # Core project information (always available)
    file_tree: List[str] = field(default_factory=list)
    file_contents: str = ""
    analysis_result: Dict[str, Any] = field(default_factory=dict)
    
    # Strategic planning (available after planning phase)
    current_plan: Optional[Dict[str, Any]] = None
    
    # Retry and failure context (available during retries)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    dockerfile_content: Optional[str] = None
    reflection: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    container_logs: str = ""
    retry_count: int = 0
    
    # Agent-specific customization
    custom_instructions: str = ""
    
    # External data
    verified_tags: str = ""
    
    @classmethod
    def from_state(cls, state: Dict[str, Any], agent_name: str = "") -> "AgentContext":
        """
        Creates an AgentContext from a DockAIState dictionary.
        
        Args:
            state: The workflow state dictionary
            agent_name: Name of the agent (for custom instructions)
            
        Returns:
            AgentContext: Populated context object
        """
        config = state.get("config", {})
        instructions_key = f"{agent_name}_instructions" if agent_name else "custom_instructions"
        
        return cls(
            file_tree=state.get("file_tree", []),
            file_contents=state.get("file_contents", ""),
            analysis_result=state.get("analysis_result", {}),
            current_plan=state.get("current_plan"),
            retry_history=state.get("retry_history", []),
            dockerfile_content=state.get("dockerfile_content") or state.get("previous_dockerfile"),
            reflection=state.get("reflection"),
            error_message=state.get("error"),
            error_details=state.get("error_details"),
            container_logs="",  # Can be populated from error_details if needed
            retry_count=state.get("retry_count", 0),
            custom_instructions=config.get(instructions_key, ""),
            verified_tags=""  # Populated separately when needed
        )
