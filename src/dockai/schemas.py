from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class HealthEndpoint(BaseModel):
    path: str = Field(description="The path of the health check endpoint, e.g., '/health' or '/api/health'")
    port: int = Field(description="The port the service listens on")

class AnalysisResult(BaseModel):
    thought_process: str = Field(description="Step-by-step reasoning about the stack and requirements")
    stack: str = Field(description="Detailed description of the technology stack")
    project_type: Literal["service", "script"] = Field(description="Type of the project: 'service' (long-running) or 'script' (runs once)")
    files_to_read: List[str] = Field(description="List of critical files to read for context")
    build_command: Optional[str] = Field(description="The command to build the application based on the detected stack and build system")
    start_command: Optional[str] = Field(description="The command to start/run the application based on the detected stack")
    suggested_base_image: str = Field(description="The official Docker Hub image name appropriate for this stack")
    health_endpoint: Optional[HealthEndpoint] = Field(
        default=None,
        description="Health endpoint details if CLEARLY defined in routing files (e.g., /health, /api/health). Set to null if no health endpoint is found - do NOT guess."
    )
    recommended_wait_time: int = Field(description="Estimated initialization time in seconds (3-30)", ge=3, le=60)

class DockerfileResult(BaseModel):
    thought_process: str = Field(description="Reasoning for the Dockerfile design choices and optimizations")
    dockerfile: str = Field(description="The full content of the generated Dockerfile")
    project_type: Literal["service", "script"] = Field(description="Re-confirmed project type based on deep analysis")

class SecurityIssue(BaseModel):
    severity: Literal["critical", "high", "medium", "low"] = Field(description="Severity of the security issue")
    description: str = Field(description="Description of the security issue")
    line_number: Optional[int] = Field(description="Approximate line number in the Dockerfile")
    suggestion: str = Field(description="How to fix the issue")

class SecurityReviewResult(BaseModel):
    is_secure: bool = Field(description="True if the Dockerfile is secure enough to proceed, False if critical/high issues exist")
    issues: List[SecurityIssue] = Field(description="List of detected security issues")
    thought_process: str = Field(description="Reasoning for the security assessment")


