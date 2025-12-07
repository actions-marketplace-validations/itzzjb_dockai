"""
DockAI Pydantic Schemas.

This module defines the structured data models used throughout the DockAI system.
These schemas are critical for ensuring type safety and structured output from
the LLMs (Large Language Models). They cover analysis, planning, generation,
security review, and reflection phases.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ==================== CORE ANALYSIS SCHEMAS ====================

class HealthEndpoint(BaseModel):
    """Represents a detected health check endpoint."""
    path: str = Field(description="The path of the health check endpoint, e.g., '/health' or '/api/health'")
    port: int = Field(description="The port the service listens on")

class AnalysisResult(BaseModel):
    """
    Structured output for the repository analysis phase.
    
    This model captures the AI's understanding of the project structure,
    technology stack, and requirements before any Dockerfile generation begins.
    """
    thought_process: str = Field(description="Step-by-step reasoning about the technology stack, architecture, and requirements")
    stack: str = Field(description="Detailed description of the detected technology stack, frameworks, and tools")
    project_type: Literal["service", "script"] = Field(description="Type of the project: 'service' (long-running process) or 'script' (runs once and exits)")
    files_to_read: List[str] = Field(description="List of critical files needed to understand dependencies, configuration, entrypoints, and build requirements")
    build_command: Optional[str] = Field(description="The command to build/compile the application, if applicable. Determined from project analysis.")
    start_command: Optional[str] = Field(description="The command to start/run the application. Determined from project analysis.")
    
    # Version detection from project files
    detected_runtime_version: Optional[str] = Field(
        default=None,
        description="The exact runtime version detected from project files (e.g., '3.11' from pyproject.toml, '20' from .nvmrc, '1.21' from go.mod). Extract from package.json engines.node, python_requires, .nvmrc, .python-version, go.mod, etc."
    )
    version_source: Optional[str] = Field(
        default=None,
        description="The file where the runtime version was detected (e.g., 'package.json', '.nvmrc', 'pyproject.toml')"
    )
    
    suggested_base_image: str = Field(description="The most appropriate Docker Hub base image for this technology stack. MUST use the detected_runtime_version if available (e.g., node:20-alpine, python:3.11-slim)")
    health_endpoint: Optional[HealthEndpoint] = Field(
        default=None,
        description="Health endpoint details if explicitly defined in the codebase. Set to null if no health endpoint is detected - do NOT guess."
    )
    recommended_wait_time: int = Field(description="Estimated container initialization time in seconds based on the detected stack", ge=3, le=60)

class DockerfileResult(BaseModel):
    """Structured output for the Dockerfile generation phase."""
    thought_process: str = Field(description="Reasoning for the Dockerfile design choices and optimizations")
    dockerfile: str = Field(description="The full content of the generated Dockerfile")
    project_type: Literal["service", "script"] = Field(description="Re-confirmed project type based on deep analysis")

# ==================== SECURITY REVIEW SCHEMAS ====================

class SecurityIssue(BaseModel):
    """Represents a single security issue found in the Dockerfile."""
    severity: Literal["critical", "high", "medium", "low"] = Field(description="Severity of the security issue")
    description: str = Field(description="Description of the security issue")
    line_number: Optional[int] = Field(description="Approximate line number in the Dockerfile")
    suggestion: str = Field(description="How to fix the issue")

class SecurityReviewResult(BaseModel):
    """
    Structured output for the security review phase.
    
    This model captures the results of the static security analysis, including
    a boolean pass/fail flag, a list of issues, and potentially a corrected Dockerfile.
    """
    is_secure: bool = Field(description="True if the Dockerfile is secure enough to proceed, False if critical/high issues exist")
    issues: List[SecurityIssue] = Field(description="List of detected security issues")
    thought_process: str = Field(description="Reasoning for the security assessment")
    
    # Structured fixes for the generator to apply
    dockerfile_fixes: List[str] = Field(
        default=[],
        description="List of specific, actionable fixes to apply to the Dockerfile. Each fix should be a clear instruction."
    )
    fixed_dockerfile: Optional[str] = Field(
        default=None,
        description="If issues are found, provide a corrected version of the Dockerfile with all security issues fixed"
    )

# ==================== ADAPTIVE AGENT SCHEMAS ====================

class PlanningResult(BaseModel):
    """
    AI-generated strategic plan before Dockerfile generation.
    
    This model represents the "Architect" phase, where the agent decides on the
    best approach (e.g., multi-stage builds, specific base images) before writing code.
    """
    thought_process: str = Field(description="Step-by-step reasoning about the approach and strategy")
    
    # Strategy selection
    base_image_strategy: str = Field(
        description="Detailed strategy for base image selection. Consider build stage needs vs runtime stage needs, binary compatibility requirements, and security."
    )
    build_strategy: str = Field(
        description="How to build the application: single-stage, multi-stage, builder pattern, etc. Based on project analysis."
    )
    optimization_priorities: List[str] = Field(
        description="Ordered list of optimization priorities based on project needs: security, size, build speed, compatibility"
    )
    
    # Anticipated challenges
    potential_challenges: List[str] = Field(
        description="Anticipated challenges based on the detected stack and requirements"
    )
    mitigation_strategies: List[str] = Field(
        description="Strategies to mitigate each potential challenge"
    )
    
    # Learning from history (if retrying)
    lessons_applied: List[str] = Field(
        default=[],
        description="Lessons from previous attempts that will be applied in this plan"
    )
    
    # Specific decisions - determined by AI based on project analysis
    use_multi_stage: bool = Field(description="Whether to use multi-stage build - determined based on project requirements")
    use_minimal_runtime: bool = Field(description="Whether to use a minimal runtime image - determined based on compatibility analysis")
    use_static_linking: bool = Field(description="Whether to use static linking - determined based on compilation requirements")
    estimated_image_size: str = Field(description="Estimated final image size range based on project analysis")


class ReflectionResult(BaseModel):
    """
    AI reflection on a failed attempt to learn and adapt.
    
    This model captures the "Post-Mortem" analysis, allowing the agent to understand
    why a previous attempt failed and how to fix it in the next iteration.
    """
    thought_process: str = Field(description="Deep analysis of what went wrong and why")
    
    # Error analysis
    root_cause_analysis: str = Field(
        description="Detailed root cause analysis of the failure. Go beyond the surface error."
    )
    was_error_predictable: bool = Field(
        description="Could this error have been anticipated from the project analysis?"
    )
    
    # Learning
    what_was_tried: str = Field(description="Summary of what approach was attempted")
    why_it_failed: str = Field(description="Why that specific approach failed")
    lesson_learned: str = Field(description="Key lesson to remember for future attempts")
    
    # Adaptation strategy
    should_change_base_image: bool = Field(description="Should we try a different base image?")
    suggested_base_image: Optional[str] = Field(
        default=None, 
        description="If changing base image, what should it be?"
    )
    should_change_build_strategy: bool = Field(description="Should we change the build approach?")
    new_build_strategy: Optional[str] = Field(
        default=None,
        description="If changing strategy, describe the new approach"
    )
    
    # Specific fixes
    specific_fixes: List[str] = Field(
        description="List of specific, actionable fixes to apply"
    )
    dockerfile_diff: Optional[str] = Field(
        default=None,
        description="If possible, provide a diff-like description of changes needed"
    )
    
    # Re-analysis decision
    needs_reanalysis: bool = Field(
        description="Should we re-analyze the project? True if the error suggests wrong assumptions about the project"
    )
    reanalysis_focus: Optional[str] = Field(
        default=None,
        description="If re-analysis needed, what should we focus on?"
    )
    
    # Confidence
    confidence_in_fix: Literal["high", "medium", "low"] = Field(
        description="How confident are we that the proposed fixes will work?"
    )
    alternative_approaches: List[str] = Field(
        default=[],
        description="Alternative approaches to try if the main fix doesn't work"
    )


class HealthEndpointDetectionResult(BaseModel):
    """
    AI-detected health endpoints from actual file contents.
    
    This model captures the result of scanning source code for route definitions
    to identify valid health check paths.
    """
    thought_process: str = Field(description="Reasoning about health endpoint detection")
    
    # Detection results
    health_endpoints_found: List[HealthEndpoint] = Field(
        default=[],
        description="List of detected health endpoints with their paths and ports"
    )
    primary_health_endpoint: Optional[HealthEndpoint] = Field(
        default=None,
        description="The primary health endpoint to use for validation"
    )
    
    # Confidence and evidence
    confidence: Literal["high", "medium", "low", "none"] = Field(
        description="Confidence in the detection"
    )
    evidence: List[str] = Field(
        description="Code snippets or file references that support the detection"
    )
    
    # Fallback
    suggested_health_path: Optional[str] = Field(
        default=None,
        description="If no explicit health endpoint found, suggest a common one for this framework"
    )


class ReadinessPatternResult(BaseModel):
    """
    AI-detected patterns to determine container readiness from logs.
    
    This model allows the system to smartly wait for application startup by
    monitoring logs for specific success/failure patterns instead of using fixed timeouts.
    """
    thought_process: str = Field(description="Reasoning about readiness pattern detection based on code analysis")
    
    # Patterns - AI determines these from code analysis
    startup_success_patterns: List[str] = Field(
        description="Regex patterns that indicate successful startup, derived from analyzing the application code"
    )
    startup_failure_patterns: List[str] = Field(
        description="Regex patterns that indicate startup failure, derived from analyzing the application code"
    )
    
    # Timing - AI estimates based on project analysis
    estimated_startup_time: int = Field(
        description="Estimated time in seconds for the application to start, based on project analysis",
        ge=1,
        le=300
    )
    max_wait_time: int = Field(
        description="Maximum time to wait before considering startup failed, based on project complexity",
        ge=5,
        le=600
    )
    
    # Framework/Technology detection
    technology_detected: Optional[str] = Field(
        default=None,
        description="The primary technology/framework detected from the codebase"
    )
    technology_specific_patterns: List[str] = Field(
        default=[],
        description="Technology-specific patterns derived from the application"
    )


class IterativeDockerfileResult(BaseModel):
    """
    Result from iterative Dockerfile improvement.
    
    This model captures the output of a refinement step, where the AI modifies
    an existing Dockerfile based on feedback/errors rather than generating from scratch.
    """
    thought_process: str = Field(description="Reasoning for the changes made")
    
    # Analysis of previous attempt
    previous_issues_addressed: List[str] = Field(
        description="List of issues from the previous attempt that are now addressed"
    )
    
    # The improved Dockerfile
    dockerfile: str = Field(description="The improved Dockerfile content")
    
    # Changes made
    changes_summary: List[str] = Field(
        description="Summary of changes made from the previous version"
    )
    
    # Confidence
    confidence_in_fix: Literal["high", "medium", "low"] = Field(
        description="Confidence that this version will work"
    )
    
    # What to try if this fails
    fallback_strategy: Optional[str] = Field(
        default=None,
        description="What to try if this version also fails"
    )
    
    project_type: Literal["service", "script"] = Field(description="Re-confirmed project type")


class RuntimeConfigResult(BaseModel):
    """
    Combined result for runtime configuration detection (health endpoints and readiness patterns).
    
    This model combines health detection and readiness pattern analysis into a single
    LLM call to improve efficiency.
    """
    thought_process: str = Field(description="Reasoning about runtime configuration detection")
    
    # Health Detection
    health_endpoints_found: List[HealthEndpoint] = Field(
        default=[],
        description="List of detected health endpoints with their paths and ports"
    )
    primary_health_endpoint: Optional[HealthEndpoint] = Field(
        default=None,
        description="The primary health endpoint to use for validation"
    )
    health_confidence: Literal["high", "medium", "low", "none"] = Field(
        description="Confidence in the health detection"
    )
    
    # Readiness Detection
    startup_success_patterns: List[str] = Field(
        description="Regex patterns that indicate successful startup"
    )
    startup_failure_patterns: List[str] = Field(
        description="Regex patterns that indicate startup failure"
    )
    estimated_startup_time: int = Field(
        description="Estimated time in seconds for the application to start",
        ge=1,
        le=300
    )
    max_wait_time: int = Field(
        description="Maximum time to wait before considering startup failed",
        ge=5,
        le=600
    )


class BlueprintResult(BaseModel):
    """
    Combined result for the 'Blueprint' phase.
    
    This merges Planning and Runtime Configuration into a single artifact,
    representing the complete architectural blueprint before code generation.
    """
    thought_process: str = Field(description="Comprehensive reasoning about build strategy and runtime configuration")
    
    # Plan Section
    plan: PlanningResult = Field(description="The strategic build plan")
    
    # Runtime Config Section
    runtime_config: RuntimeConfigResult = Field(description="The detected runtime configuration (health + readiness)")
