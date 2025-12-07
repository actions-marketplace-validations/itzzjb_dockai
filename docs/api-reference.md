# API Reference

This document provides detailed documentation for DockAI's Python modules and functions. Use this reference when integrating DockAI into your own tools or extending its functionality.

---

## 📋 Table of Contents

1. [Package Structure](#package-structure)
2. [Agents Module](#agents-module)
3. [Core Module](#core-module)
4. [Utils Module](#utils-module)
5. [Workflow Module](#workflow-module)
6. [CLI Module](#cli-module)
7. [Error Classes](#error-classes)
8. [Type Definitions](#type-definitions)
9. [Usage Examples](#usage-examples)

---

## Package Structure

DockAI follows a modular architecture where each module has a specific responsibility:

```
dockai/
├── __init__.py           # Package version and metadata
├── agents/               # AI-powered agents for specific tasks
│   ├── analyzer.py       # Project analysis and stack detection
│   ├── generator.py      # Dockerfile generation
│   ├── reviewer.py       # Security review
│   └── agent_functions.py# Blueprint architect, reflector, and other agents
├── cli/                  # Command-line interface
│   ├── main.py           # Typer CLI commands
│   └── ui.py             # Rich console output helpers
├── core/                 # Core components and data structures
│   ├── agent_context.py  # Unified context for all agents
│   ├── schemas.py        # Pydantic models for structured output
│   ├── state.py          # LangGraph state definitions
│   ├── llm_providers.py  # LLM provider abstraction
│   ├── mcp_server.py     # Model Context Protocol server
│   └── errors.py         # Custom exceptions
├── utils/                # Utility functions
│   ├── scanner.py        # File tree scanning
│   ├── file_utils.py     # File reading and truncation
│   ├── validator.py      # Dockerfile validation
│   ├── registry.py       # Container registry client
│   ├── prompts.py        # Prompt configuration
│   ├── callbacks.py      # LLM callbacks
│   ├── rate_limiter.py   # API rate limiting
│   ├── tracing.py        # OpenTelemetry integration
│   └── ollama_docker.py  # Ollama Docker fallback
└── workflow/             # LangGraph workflow
    ├── graph.py          # Workflow graph definition
    └── nodes.py          # Individual node implementations
```

---

## Agents Module

The agents module contains AI-powered components that perform specific tasks in the Dockerfile generation workflow.

### `dockai.agents.analyzer`

#### `analyze_repo_needs(context: AgentContext) -> Tuple[AnalysisResult, Dict[str, int]]`

Performs AI-powered analysis of a repository to determine its technology stack and containerization requirements.

**Purpose**: This is the first AI step—understanding what we're containerizing before making any decisions.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `AgentContext` | Unified context containing `file_tree` and `custom_instructions` |

**Returns**: A tuple of:
- `AnalysisResult`: Structured analysis results
- `Dict[str, int]`: Token usage statistics

**What it determines**:
- Primary programming language and framework
- Project type (service vs script)
- Suggested base image
- Files that need to be read for more context
- Build and start commands

**Example**:

```python
from dockai.agents.analyzer import analyze_repo_needs
from dockai.core.agent_context import AgentContext

# Create context with file tree
context = AgentContext(
    file_tree=[
        "app.py",
        "requirements.txt",
        "README.md",
        "src/models.py",
        "src/routes.py",
        "tests/test_app.py"
    ],
    custom_instructions="Focus on Flask patterns"
)

# Analyze the repository
result, usage = analyze_repo_needs(context=context)

# Access results
print(f"Stack: {result.stack}")                    # "Python 3.11 with Flask"
print(f"Type: {result.project_type}")              # "service"
print(f"Base image: {result.suggested_base_image}") # "python:3.11-slim"
print(f"Files to read: {result.files_to_read}")    # ["app.py", "requirements.txt"]
print(f"Start command: {result.start_command}")    # "python app.py"
print(f"Tokens used: {usage}")                     # {"input_tokens": 500, "output_tokens": 200}
```

---

### `dockai.agents.generator`

#### `generate_dockerfile(context: AgentContext) -> Tuple[str, str, str, Any]`

Generates a complete Dockerfile based on analysis results and strategic planning.

**Purpose**: This is the core generation step—synthesizing all gathered context into a working Dockerfile.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `AgentContext` | Full context including analysis, file contents, plan, and retry history |

**Returns**: A tuple of:
- `str`: Generated Dockerfile content
- `str`: Project type ("service" or "script")
- `str`: AI's thought process (reasoning)
- `Any`: Token usage statistics

**What it considers**:
- Technology stack and requirements
- File contents for dependencies and configuration
- Strategic plan (base image, build strategy)
- Retry history (lessons from previous failures)
- Verified image tags (only uses tags that exist)
- Custom instructions

**Example**:

```python
from dockai.agents.generator import generate_dockerfile
from dockai.core.agent_context import AgentContext

context = AgentContext(
    file_tree=["app.py", "requirements.txt"],
    file_contents="""
=== requirements.txt ===
fastapi==0.100.0
uvicorn==0.23.0
    """,
    analysis_result={
        "stack": "Python 3.11 with FastAPI",
        "project_type": "service",
        "suggested_base_image": "python:3.11-slim"
    },
    current_plan={
        "base_image_strategy": "Use slim for smaller size",
        "build_strategy": "Single stage pip install"
    },
    custom_instructions="Use multi-stage build",
    verified_tags="python:3.11-slim (verified)",
    retry_count=0
)

dockerfile, project_type, thoughts, usage = generate_dockerfile(context=context)

print(dockerfile)
# FROM python:3.11-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# ...

print(f"Project type: {project_type}")  # "service"
print(f"Reasoning: {thoughts[:100]}...")
```

---

### `dockai.agents.reviewer`

#### `review_dockerfile(context: AgentContext) -> Tuple[SecurityReviewResult, Any]`

Performs a security audit of a generated Dockerfile, identifying vulnerabilities and best practice violations.

**Purpose**: Catch security issues before building. The reviewer acts as a security-focused code review.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `AgentContext` | Context containing `dockerfile_content` and project information |

**Returns**: A tuple of:
- `SecurityReviewResult`: Security findings and optionally a fixed Dockerfile
- `Any`: Token usage statistics

**What it checks**:
- Running as root (should be non-root)
- Hardcoded secrets or credentials
- Using `latest` tag instead of pinned versions
- Unnecessary packages or attack surface
- Missing security configurations
- Compliance with best practices

**Example**:

```python
from dockai.agents.reviewer import review_dockerfile
from dockai.core.agent_context import AgentContext

context = AgentContext(
    dockerfile_content="""
FROM python:latest
WORKDIR /app
COPY . .
ENV API_KEY=sk-secret-key-12345
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
    """,
    file_tree=["app.py", "requirements.txt"]
)

result, usage = review_dockerfile(context=context)

print(f"Is secure: {result.is_secure}")  # False
print(f"Issues found: {len(result.issues)}")  # 3

for issue in result.issues:
    print(f"- [{issue.severity}] {issue.description}")
    # - [HIGH] Container runs as root
    # - [CRITICAL] Hardcoded API key in ENV
    # - [MEDIUM] Using :latest tag instead of pinned version

if result.fixed_dockerfile:
    print("Fixed Dockerfile available")
```

---

### `dockai.agents.agent_functions`

This module contains additional agents that don't have their own files.

#### `create_blueprint(context: AgentContext) -> Tuple[BlueprintResult, Dict[str, int]]`

Creates a comprehensive blueprint for the Dockerfile generation process. This combines strategic planning and runtime configuration detection into a single step.

**Purpose**: The "Architect" phase. It decides *how* to build the image and *how* to run it, before any code is written.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `AgentContext` | Context with analysis, file contents, and retry history |

**Returns**: A tuple of:
- `BlueprintResult`: Combined plan and runtime config
- `Dict[str, int]`: Token usage

**Example**:

```python
from dockai.agents.agent_functions import create_blueprint
from dockai.core.agent_context import AgentContext

context = AgentContext(...)
result, usage = create_blueprint(context=context)

# Access Plan
print(f"Build Strategy: {result.plan.build_strategy}")
# "Multi-stage build with CGO_ENABLED=0"

# Access Runtime Config
if result.runtime_config.primary_health_endpoint:
    print(f"Health: {result.runtime_config.primary_health_endpoint.path}")
    # "/health"

print(f"Success Patterns: {result.runtime_config.startup_success_patterns}")
# ["Server listening on port 8080"]
```

---

#### `reflect_on_failure(context: AgentContext) -> Tuple[ReflectionResult, Dict[str, int]]`

Analyzes a failed attempt to understand what went wrong and how to fix it.

**Purpose**: Learn from failures. This is what makes DockAI self-correcting.

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `AgentContext` | Context with error details, logs, and previous attempts |

**Returns**: A tuple of:
- `ReflectionResult`: Root cause analysis and recommendations
- `Dict[str, int]`: Token usage

**Example**:

```python
from dockai.agents.agent_functions import reflect_on_failure
from dockai.core.agent_context import AgentContext

context = AgentContext(
    error_message="Error: pg_config executable not found",
    dockerfile_content="FROM python:3.11-alpine\nRUN pip install psycopg2\n...",
    container_logs="Collecting psycopg2\n  Building wheel...\n  Error: pg_config not found",
    retry_history=[],
    retry_count=1
)

result, usage = reflect_on_failure(context=context)

print(f"Classification: {result.error_classification}")
# "build_dependency_missing"

print(f"Root cause: {result.root_cause}")
# "psycopg2 requires PostgreSQL development headers to compile"

print(f"Strategy: {result.recommended_strategy}")
# "regenerate"

print(f"Fixes: {result.specific_fixes}")
# ["Install postgresql-dev: apk add postgresql-dev",
#  "Or use psycopg2-binary instead"]

print(f"Lessons: {result.lessons_learned}")
# ["Python packages with C extensions need build dependencies on Alpine"]
```

---

## Core Module

The core module contains fundamental data structures and services.

### `dockai.core.agent_context`

#### `AgentContext`

A dataclass that provides unified context to all AI agents. This ensures all agents have access to the same information.

**Why AgentContext exists**: Instead of each agent having different function signatures, all agents receive the same context. This makes the code consistent and extensible.

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `file_tree` | `List[str]` | List of all files in the project |
| `file_contents` | `str` | Concatenated contents of critical files |
| `analysis_result` | `Dict[str, Any]` | Results from the analyzer |
| `current_plan` | `Optional[Dict]` | Strategic plan for generation |
| `retry_history` | `List[Dict]` | Previous attempts and lessons learned |
| `dockerfile_content` | `Optional[str]` | Current or previous Dockerfile |
| `reflection` | `Optional[Dict]` | Failure analysis results |
| `error_message` | `Optional[str]` | Last error message |
| `error_details` | `Optional[Dict]` | Classified error information |
| `container_logs` | `str` | Logs from container execution |
| `custom_instructions` | `str` | User-provided guidance |
| `verified_tags` | `str` | Docker image tags verified to exist |
| `retry_count` | `int` | Current retry number |

**Example**:

```python
from dockai.core.agent_context import AgentContext

# Create a full context
context = AgentContext(
    file_tree=["app.py", "requirements.txt", "Dockerfile"],
    file_contents="flask==2.0.0\nrequests==2.28.0",
    analysis_result={
        "stack": "Python with Flask",
        "project_type": "service"
    },
    custom_instructions="Use Alpine base images",
    retry_count=0
)

# Agents access what they need
print(context.file_tree)
print(context.analysis_result.get("stack"))
```

---

### `dockai.core.schemas`

Pydantic models for structured LLM output. Using Pydantic ensures we get valid, typed responses from AI.

#### `AnalysisResult`

```python
class AnalysisResult(BaseModel):
    thought_process: str        # AI's reasoning
    stack: str                  # Detected stack (e.g., "Python 3.11 with FastAPI")
    project_type: Literal["service", "script"]
    files_to_read: List[str]    # Files needing deeper analysis
    build_command: Optional[str]
    start_command: Optional[str]
    suggested_base_image: str
    health_endpoint: Optional[HealthEndpoint]
    recommended_wait_time: int  # Seconds (3-60)
```

#### `PlanningResult`

```python
class PlanningResult(BaseModel):
    thought_process: str
    base_image_strategy: str    # Why this base image
    build_strategy: str         # Single vs multi-stage, etc.
    optimization_priorities: List[str]  # ["security", "size", "speed"]
    potential_challenges: List[str]     # Anticipated issues
```

#### `SecurityReviewResult`

```python
class SecurityReviewResult(BaseModel):
    thought_process: str
    is_secure: bool
    issues: List[SecurityIssue]
    fixed_dockerfile: Optional[str]  # Corrected version if issues found
    severity_summary: Dict[str, int]  # {"critical": 0, "high": 1, ...}
```

#### `ReflectionResult`

```python
class ReflectionResult(BaseModel):
    thought_process: str
    error_classification: str    # Type of error
    root_cause: str             # Why it failed
    recommended_strategy: str   # "regenerate", "replan", "reanalyze"
    specific_fixes: List[str]   # Concrete fixes to apply
    lessons_learned: List[str]  # Knowledge for future attempts
```

#### `HealthEndpointDetectionResult`

```python
class HealthEndpointDetectionResult(BaseModel):
    detected: bool
    endpoint: Optional[HealthEndpoint]  # {path, port, method}
    confidence: float           # 0.0 to 1.0
    evidence: List[str]         # Why we think this is the endpoint
```

#### `ReadinessPatternResult`

```python
class ReadinessPatternResult(BaseModel):
    success_patterns: List[str]  # Log patterns indicating success
    failure_patterns: List[str]  # Log patterns indicating failure
    estimated_startup_time: int  # Seconds
```

---

### `dockai.core.llm_providers`

Handles LLM provider abstraction, allowing DockAI to work with multiple AI providers.

#### `LLMProvider` (Enum)

```python
class LLMProvider(Enum):
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
```

#### `get_llm(agent_name: str, temperature: float = 0.0) -> BaseChatModel`

Gets the appropriate LLM for a specific agent.

**How it works**:
1. Checks for agent-specific model override (`DOCKAI_MODEL_<AGENT>`)
2. Falls back to provider default
3. Handles mixed provider prefixes (e.g., `openai/gpt-4o`)

**Example**:

```python
from dockai.core.llm_providers import get_llm

# Get LLM for the generator agent
llm = get_llm("generator", temperature=0.0)

# Use with LangChain
response = llm.invoke([HumanMessage(content="Generate a Dockerfile...")])
```

---

### `dockai.core.state`

#### `DockAIState` (TypedDict)

The central state object passed through the LangGraph workflow. This is the shared memory for the entire agentic system.

```python
class DockAIState(TypedDict):
    # ==================== INPUTS ====================
    path: str                              # Absolute path to project directory
    config: Dict[str, Any]                 # Configuration and custom instructions
    max_retries: int                       # Maximum allowed retry attempts

    # ==================== INTERMEDIATE ARTIFACTS ====================
    file_tree: List[str]                   # List of relative file paths in project
    file_contents: str                     # Concatenated critical file contents
    
    # Analysis & Planning
    analysis_result: Dict[str, Any]        # Initial project analysis (AnalysisResult)
    current_plan: Optional[Dict[str, Any]] # Strategic plan before coding (PlanningResult)
    
    # Generation
    dockerfile_content: str                # Current generated Dockerfile
    previous_dockerfile: Optional[str]     # Previous attempt for diffing
    
    # Validation & Execution
    validation_result: Dict[str, Any]      # Build/run validation result
    retry_count: int                       # Current retry attempt (0-indexed)
    
    # Error Handling
    error: Optional[str]                   # Raw error message
    error_details: Optional[Dict[str, Any]]# Classified error details
    logs: List[str]                        # Execution logs
    
    # ==================== ADAPTIVE INTELLIGENCE ====================
    retry_history: List[RetryAttempt]      # Full history of attempts and learnings
    reflection: Optional[Dict[str, Any]]   # AI analysis of most recent failure
    
    # Smart Detection
    detected_health_endpoint: Optional[Dict[str, Any]]  # Health endpoint from code
    readiness_patterns: List[str]          # Success patterns for startup detection
    failure_patterns: List[str]            # Failure patterns for startup detection
    
    # Control Flow
    needs_reanalysis: bool                 # Flag to trigger re-analysis phase
    
    # Observability
    usage_stats: List[Dict[str, Any]]      # Token usage for cost tracking
```

#### `RetryAttempt` (TypedDict)

Records a single retry attempt for learning purposes.

```python
class RetryAttempt(TypedDict):
    attempt_number: int     # Which attempt this was
    dockerfile_content: str # The Dockerfile that was tried
    error_message: str      # The error that occurred
    error_type: str         # Classified error type
    what_was_tried: str     # Summary of the approach
    why_it_failed: str      # Why it didn't work
    lesson_learned: str     # Key lesson for future attempts
```

---

## Utils Module

Utility functions supporting the core workflow.

### `dockai.utils.scanner`

#### `get_file_tree(root_path: str) -> List[str]`

Scans a directory and returns a filtered list of files.

**Features**:
- Respects `.gitignore` and `.dockerignore`
- Filters noise directories (`node_modules`, `venv`, `.git`, `__pycache__`)
- Returns relative paths

**Example**:

```python
from dockai.utils.scanner import get_file_tree

files = get_file_tree("/path/to/project")
# ["app.py", "requirements.txt", "src/main.py", "tests/test_app.py"]
```

---

### `dockai.utils.file_utils`

#### `estimate_tokens(text: str) -> int`

Estimates token count for a string (approximately 1 token per 4 characters).

```python
from dockai.utils.file_utils import estimate_tokens

tokens = estimate_tokens("Hello, world!")  # ~3 tokens
```

#### `smart_truncate(content: str, filename: str, max_chars: int, max_lines: int) -> str`

Truncates file content while preserving important parts (beginning and end).

**Why this approach**: The beginning of files typically has imports and configuration; the end often has main execution. The middle can be truncated with less information loss.

```python
from dockai.utils.file_utils import smart_truncate

truncated = smart_truncate(
    content=large_file_content,
    filename="big_file.py",
    max_chars=10000,
    max_lines=500
)
```

#### `read_critical_files(path: str, files_to_read: List[str], truncation_enabled: bool = None) -> str`

Reads and concatenates critical files with optional truncation.

```python
from dockai.utils.file_utils import read_critical_files

contents = read_critical_files(
    "/path/to/repo",
    ["app.py", "requirements.txt", "config.py"],
    truncation_enabled=False  # Read full files
)
# === app.py ===
# from flask import Flask
# ...
# === requirements.txt ===
# flask==2.0.0
# ...
```

---

### `dockai.utils.validator`

#### `validate_dockerfile(dockerfile_content: str, context_path: str, ...) -> ValidationResult`

Builds and tests a Dockerfile in a sandboxed environment.

**What it does**:
1. Writes Dockerfile to temp location
2. Runs Hadolint for linting (if available)
3. Builds Docker image
4. Starts container
5. Checks health endpoint (if configured)
6. Runs Trivy security scan (if enabled)
7. Cleans up

**Example**:

```python
from dockai.utils.validator import validate_dockerfile

result = validate_dockerfile(
    dockerfile_content="FROM python:3.11\n...",
    context_path="/path/to/project",
    health_endpoint={"path": "/health", "port": 8000},
    skip_security_scan=False,
    no_cache=False
)

if result.success:
    print(f"Built successfully in {result.build_time}s")
    print(f"Image size: {result.image_size / 1024 / 1024:.1f}MB")
else:
    print(f"Failed: {result.error}")
    print(f"Logs: {result.container_logs}")
```

---

### `dockai.utils.registry`

#### `get_docker_tags(image_name: str, limit: int = 5, target_version: str = None) -> List[str]`

Fetches valid tags for a Docker image from supported registries.

**Supported registries**:
- Docker Hub (with smart filtering)
- Google Container Registry (GCR)
- GitHub Container Registry (GHCR)
- Quay.io (with full pagination)
- AWS ECR (limited - requires AWS credentials)

**Smart Tag Fetching Strategy**:

DockAI uses an intelligent approach to fetch tags efficiently:

1. **Docker Hub**: Uses the `name=` filter parameter when `target_version` is specified (e.g., AI suggests "node:18"), returning only matching tags (~100 filtered results). If no matches found, falls back to Registry v2 API which returns ALL tags (8,000+).

2. **Quay.io**: Paginates through all pages (50 tags/page) to get the complete tag list.

3. **GCR/GHCR**: Uses OCI v2 API which returns all tags in a single request.

```python
from dockai.utils.registry import get_docker_tags

# Get tags for Node.js, filtering for version 18
tags = get_docker_tags("node", target_version="18")
# Returns: ["node:18-alpine", "node:18.20.8-alpine", "node:18-slim", ...]

# Get tags for Python without filtering
tags = get_docker_tags("python")
# Returns most recent tags with alpine/slim prioritized
```

#### `verify_image_tag(image: str, tag: str) -> bool`

Verifies a Docker image tag exists in the registry.

```python
from dockai.utils.registry import verify_image_tag

exists = verify_image_tag("python", "3.11-slim")  # True
exists = verify_image_tag("python", "9.99-invalid")  # False
```

---

### `dockai.utils.prompts`

#### `PromptConfig`

Configuration for custom prompts and instructions.

```python
@dataclass
class PromptConfig:
    analyzer: Optional[str] = None
    analyzer_instructions: Optional[str] = None
    blueprint: Optional[str] = None
    blueprint_instructions: Optional[str] = None
    generator: Optional[str] = None
    generator_instructions: Optional[str] = None
    # ... more agents
```

#### `load_prompt_config(repo_path: str) -> PromptConfig`

Loads configuration from environment variables and `.dockai` file.

```python
from dockai.utils.prompts import load_prompt_config

config = load_prompt_config("/path/to/project")
print(config.generator_instructions)  # From env or .dockai file
```

---

### `dockai.utils.callbacks`

#### `TokenUsageCallback`

LangChain callback handler for tracking token usage.

```python
from dockai.utils.callbacks import TokenUsageCallback

callback = TokenUsageCallback()
# Use with LLM calls...
usage = callback.get_usage()
# {"input_tokens": 1000, "output_tokens": 500}
```

---

### `dockai.utils.rate_limiter`

#### `RateLimiter`

Handles API rate limits with exponential backoff.

```python
from dockai.utils.rate_limiter import RateLimiter

limiter = RateLimiter(max_retries=3, base_delay=1.0)
result = limiter.execute(lambda: api_call())
```

---

## Workflow Module

### `dockai.workflow.graph`

#### `create_workflow() -> CompiledStateGraph`

Creates and compiles the LangGraph workflow.

**Example**:

```python
from dockai.workflow.graph import create_workflow

workflow = create_workflow()

# Run the workflow
result = workflow.invoke({
    "repo_path": "/path/to/project",
    "retry_count": 0,
    "retry_history": [],
    "token_usage": {}
})

print(result["final_dockerfile"])
```

---

## CLI Module

### `dockai.cli.main`

The main CLI entry point using Typer.

#### `build(project_path: str, verbose: bool = False, no_cache: bool = False)`

Main build command.

```python
# This is called by the CLI:
# dockai build /path/to/project --verbose
```

---

## Error Classes

### `dockai.core.errors`

```python
class DockAIError(Exception):
    """Base exception for all DockAI errors."""
    pass

class AnalysisError(DockAIError):
    """Error during project analysis."""
    pass

class GenerationError(DockAIError):
    """Error during Dockerfile generation."""
    pass

class ValidationError(DockAIError):
    """Error during Dockerfile validation."""
    pass

class ConfigurationError(DockAIError):
    """Error in configuration (missing API keys, etc.)."""
    pass
```

---

## Usage Examples

### Complete Workflow Example

```python
from dockai.workflow.graph import create_workflow
from dockai.utils.prompts import load_prompt_config

# Load configuration
config = load_prompt_config("/path/to/project")

# Create workflow
workflow = create_workflow()

# Run the complete workflow
result = workflow.invoke({
    "repo_path": "/path/to/project",
    "retry_count": 0,
    "retry_history": [],
    "token_usage": {},
    "custom_instructions": config.generator_instructions or ""
})

# Access results
if result.get("final_dockerfile"):
    print("Success!")
    print(result["final_dockerfile"])
    print(f"Total tokens: {sum(result['token_usage'].values())}")
else:
    print("Failed after max retries")
```

### Individual Agent Example

```python
from dockai.agents.analyzer import analyze_repo_needs
from dockai.agents.generator import generate_dockerfile
from dockai.core.agent_context import AgentContext
from dockai.utils.scanner import get_file_tree
from dockai.utils.file_utils import read_critical_files

# Step 1: Scan project
file_tree = get_file_tree("/path/to/project")

# Step 2: Analyze
context = AgentContext(file_tree=file_tree)
analysis, _ = analyze_repo_needs(context)

# Step 3: Read files
file_contents = read_critical_files(
    "/path/to/project",
    analysis.files_to_read
)

# Step 4: Generate
context = AgentContext(
    file_tree=file_tree,
    file_contents=file_contents,
    analysis_result=analysis.dict()
)
dockerfile, project_type, thoughts, _ = generate_dockerfile(context)

print(dockerfile)
```

---

## Next Steps

- **[Architecture](./architecture.md)**: Understand the design decisions
- **[Configuration](./configuration.md)**: All configuration options
- **[Customization](./customization.md)**: Tuning agents for your needs
