# API Reference

Detailed documentation for DockAI's modules and functions.

---

## Package Structure

```
dockai/
├── agents/          # AI-powered agents
├── cli/             # Command-line interface
├── core/            # Core components
├── utils/           # Utility functions
└── workflow/        # Workflow orchestration
```

---

## Agents Module

### `dockai.agents.analyzer`

#### `analyze_repo_needs(context: AgentContext)`

Performs AI-powered analysis of the repository to determine project requirements.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `file_tree` and `custom_instructions` |

**Returns:** `Tuple[AnalysisResult, Dict[str, int]]`

**Example:**

```python
from dockai.agents.analyzer import analyze_repo_needs
from dockai.core.agent_context import AgentContext

context = AgentContext(
    file_tree=["app.py", "requirements.txt", "README.md"],
    custom_instructions="Focus on Flask patterns"
)
result, usage = analyze_repo_needs(context=context)

print(result.stack)              # "Python with Flask"
print(result.project_type)       # "service"
print(result.suggested_base_image)  # "python:3.11-slim"
print(result.files_to_read)      # ["app.py", "requirements.txt"]
```

---

### `dockai.agents.generator`

#### `generate_dockerfile(context: AgentContext)`

Generates a Dockerfile based on analysis results and strategic plan.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with all project information |

**Returns:** `Tuple[str, str, str, Any]` - (dockerfile, project_type, thought_process, usage)

**Example:**

```python
from dockai.agents.generator import generate_dockerfile
from dockai.core.agent_context import AgentContext

context = AgentContext(
    analysis_result={"stack": "Python 3.11 with FastAPI"},
    file_contents="fastapi==0.100.0\nuvicorn==0.23.0",
    custom_instructions="Use multi-stage build"
)
dockerfile, project_type, thoughts, usage = generate_dockerfile(context=context)

print(dockerfile)      # Generated Dockerfile content
print(project_type)    # "service"
```

---

### `dockai.agents.reviewer`

#### `review_dockerfile(context: AgentContext)`

Performs security review of a generated Dockerfile.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `dockerfile_content` |

**Returns:** `Tuple[SecurityReviewResult, Any]`

**Example:**

```python
from dockai.agents.reviewer import review_dockerfile
from dockai.core.agent_context import AgentContext

context = AgentContext(
    dockerfile_content="""
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
"""
)
result, usage = review_dockerfile(context=context)

print(result.is_secure)         # False (running as root)
print(len(result.issues))       # Number of issues found
print(result.fixed_dockerfile)  # Corrected version
```

---

### `dockai.agents.agent_functions`

#### `create_plan(context: AgentContext)`

Creates a strategic plan for Dockerfile generation.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `analysis_result`, `file_contents`, `retry_history` |

**Returns:** `Tuple[PlanningResult, Dict[str, int]]`

---

#### `reflect_on_failure(context: AgentContext)`

Analyzes a failed attempt to learn and adapt.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `error_message`, `dockerfile_content`, `container_logs`, `retry_history` |

**Returns:** `Tuple[ReflectionResult, Dict[str, int]]`

---

#### `detect_health_endpoints(context: AgentContext)`

Detects health check endpoints from source code.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `file_contents` and `analysis_result` |

**Returns:** `Tuple[HealthEndpointDetectionResult, Dict[str, int]]`

---

#### `detect_readiness_patterns(context: AgentContext)`

Detects application startup patterns for readiness checks.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `context` | `AgentContext` | Unified context with `file_contents` and `analysis_result` |

**Returns:** `Tuple[ReadinessPatternResult, Dict[str, int]]`

---

## Core Module

### `dockai.core.agent_context`

#### `AgentContext`

Dataclass that provides unified context to all AI agents.

| Field | Type | Description |
|-------|------|-------------|
| `file_tree` | `List[str]` | List of project files |
| `file_contents` | `str` | Critical file contents |
| `analysis_result` | `Dict[str, Any]` | Stack detection results |
| `current_plan` | `Optional[Dict]` | Strategic build plan |
| `retry_history` | `List[Dict]` | Previous attempts & lessons |
| `dockerfile_content` | `Optional[str]` | Current/previous Dockerfile |
| `reflection` | `Optional[Dict]` | Failure analysis |
| `error_message` | `Optional[str]` | Last error message |
| `error_details` | `Optional[Dict]` | Classified error details |
| `container_logs` | `str` | Container runtime logs |
| `custom_instructions` | `str` | User guidance |
| `verified_tags` | `str` | Valid Docker image tags |
| `retry_count` | `int` | Current retry number |

**Example:**

```python
from dockai.core.agent_context import AgentContext

context = AgentContext(
    file_tree=["app.py", "requirements.txt"],
    file_contents="flask==2.0.0",
    analysis_result={"stack": "Python with Flask", "project_type": "service"},
    custom_instructions="Use alpine base images"
)
```

---

### `dockai.core.schemas`

#### `AnalysisResult`

Pydantic model for repository analysis output.

| Field | Type | Description |
|-------|------|-------------|
| `thought_process` | `str` | AI reasoning |
| `stack` | `str` | Detected technology stack |
| `project_type` | `Literal["service", "script"]` | Classification |
| `files_to_read` | `List[str]` | Critical files to examine |
| `build_command` | `Optional[str]` | Build command |
| `start_command` | `Optional[str]` | Start command |
| `suggested_base_image` | `str` | Recommended base image |
| `health_endpoint` | `Optional[HealthEndpoint]` | Detected health endpoint |
| `recommended_wait_time` | `int` | Estimated startup time (3-60s) |

---

#### `PlanningResult`

Pydantic model for strategic planning output.

| Field | Type | Description |
|-------|------|-------------|
| `thought_process` | `str` | Planning reasoning |
| `base_image_strategy` | `str` | Base image rationale |
| `build_strategy` | `str` | Build approach |
| `optimization_priorities` | `List[str]` | Ordered priorities |
| `potential_challenges` | `List[str]` | Anticipated issues |

---

#### `SecurityReviewResult`

Pydantic model for security review output.

| Field | Type | Description |
|-------|------|-------------|
| `thought_process` | `str` | Review reasoning |
| `is_secure` | `bool` | Whether Dockerfile is secure |
| `issues` | `List[SecurityIssue]` | List of issues found |
| `fixed_dockerfile` | `Optional[str]` | Corrected Dockerfile |
| `severity_summary` | `Dict[str, int]` | Count by severity |

---

#### `ReflectionResult`

Pydantic model for failure reflection output.

| Field | Type | Description |
|-------|------|-------------|
| `thought_process` | `str` | Analysis reasoning |
| `error_classification` | `str` | Error type |
| `root_cause` | `str` | Identified root cause |
| `recommended_strategy` | `str` | Next step |
| `specific_fixes` | `List[str]` | Fixes to apply |
| `lessons_learned` | `List[str]` | Knowledge gained |

---

#### `HealthEndpointDetectionResult`

Pydantic model for health endpoint detection.

| Field | Type | Description |
|-------|------|-------------|
| `detected` | `bool` | Whether endpoint found |
| `endpoint` | `Optional[HealthEndpoint]` | Endpoint details |
| `confidence` | `float` | Detection confidence |
| `evidence` | `List[str]` | Supporting evidence |

---

#### `ReadinessPatternResult`

Pydantic model for readiness pattern detection.

| Field | Type | Description |
|-------|------|-------------|
| `success_patterns` | `List[str]` | Patterns indicating success |
| `failure_patterns` | `List[str]` | Patterns indicating failure |
| `estimated_startup_time` | `int` | Expected startup seconds |

---

### `dockai.core.llm_providers`

#### `LLMProvider`

Enum for supported LLM providers.

```python
class LLMProvider(Enum):
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
```

#### `get_llm(agent_name, temperature)`

Gets the appropriate LLM for an agent.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `agent_name` | `str` | Name of the agent |
| `temperature` | `float` | Sampling temperature |

**Returns:** `BaseChatModel`

---

### `dockai.core.state`

#### `GraphState`

TypedDict for workflow state management.

```python
class GraphState(TypedDict):
    repo_path: str
    file_tree: List[str]
    analysis_result: Optional[AnalysisResult]
    file_contents: str
    health_result: Optional[HealthEndpointDetectionResult]
    readiness_result: Optional[ReadinessPatternResult]
    current_plan: Optional[PlanningResult]
    dockerfile_content: str
    thought_process: str
    review_result: Optional[SecurityReviewResult]
    validation_result: Optional[ValidationResult]
    retry_count: int
    retry_history: List[RetryAttempt]
    reflection: Optional[ReflectionResult]
    final_dockerfile: str
    token_usage: Dict[str, int]
```

---

## Utils Module

### `dockai.utils.scanner`

#### `get_file_tree(root_path)`

Scans a directory and returns a filtered file list.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `root_path` | `str` | Path to scan |

**Returns:** `List[str]`

**Features:**
- Respects `.gitignore` and `.dockerignore`
- Filters noise directories (`node_modules`, `venv`, `.git`)
- Returns relative paths

---

### `dockai.utils.file_utils`

#### `estimate_tokens(text)`

Estimates the number of tokens in a string.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `text` | `str` | Text to estimate tokens for |

**Returns:** `int` - Estimated token count (roughly text_length / 4)

---

#### `smart_truncate(content, filename, max_chars, max_lines)`

Truncates file content while preserving context.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `content` | `str` | File content to truncate |
| `filename` | `str` | Filename (for logging) |
| `max_chars` | `int` | Maximum characters to keep |
| `max_lines` | `int` | Maximum lines to keep |

**Returns:** `str` - Truncated content with head + tail preservation

---

#### `read_critical_files(path, files_to_read, truncation_enabled)`

Reads critical files with optional smart truncation.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `path` | `str` | Repository root path |
| `files_to_read` | `List[str]` | Relative paths to read |
| `truncation_enabled` | `bool \| None` | Enable truncation (None = use env var) |

**Returns:** `str` - Concatenated file contents

**Truncation Behavior:**
1. If `truncation_enabled` is explicitly set, use that value
2. Otherwise check `DOCKAI_TRUNCATION_ENABLED` env var
3. Default is `False` (no truncation)
4. Auto-enables if content exceeds `DOCKAI_TOKEN_LIMIT`

**Example:**

```python
from dockai.utils.file_utils import read_critical_files

# Default: no truncation unless content exceeds token limit
contents = read_critical_files(
    "/path/to/repo",
    ["app.py", "requirements.txt"]
)

# Explicitly enable truncation
contents = read_critical_files(
    "/path/to/repo",
    ["app.py", "requirements.txt"],
    truncation_enabled=True
)
```

---

### `dockai.utils.validator`

#### `validate_dockerfile(dockerfile_content, context_path, ...)`

Builds and tests a Dockerfile in a sandbox.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `dockerfile_content` | `str` | Dockerfile to validate |
| `context_path` | `str` | Build context path |
| `health_endpoint` | `Optional[HealthEndpoint]` | Health check config |
| `readiness_patterns` | `Optional[ReadinessPatternResult]` | Startup patterns |

**Returns:** `ValidationResult`

---

### `dockai.utils.prompts`

#### `PromptConfig`

Dataclass for custom prompt configuration.

```python
@dataclass
class PromptConfig:
    analyzer: Optional[str] = None
    analyzer_instructions: Optional[str] = None
    planner: Optional[str] = None
    planner_instructions: Optional[str] = None
    generator: Optional[str] = None
    generator_instructions: Optional[str] = None
    # ... more agents
```

#### `load_prompt_config(repo_path)`

Loads prompt configuration from environment and `.dockai` file.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `repo_path` | `str` | Repository path |

**Returns:** `PromptConfig`

---

### `dockai.utils.registry`

#### `verify_image_tag(image, tag)`

Verifies that a Docker image tag exists in a registry.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `image` | `str` | Image name |
| `tag` | `str` | Image tag |

**Returns:** `bool`

**Supported Registries:**
- Docker Hub
- Google Container Registry (GCR)
- Quay.io
- AWS ECR (limited)

---

### `dockai.utils.callbacks`

#### `TokenUsageCallback`

LangChain callback handler for tracking token usage.

```python
from dockai.utils.callbacks import TokenUsageCallback

callback = TokenUsageCallback()
# Use with LLM calls
usage = callback.get_usage()
print(usage)  # {"input_tokens": 1000, "output_tokens": 500}
```

---

### `dockai.utils.rate_limiter`

#### `RateLimiter`

Handles API rate limits with exponential backoff.

```python
from dockai.utils.rate_limiter import RateLimiter

limiter = RateLimiter(max_retries=3, base_delay=1.0)
result = limiter.execute(api_call_function)
```

---

## Workflow Module

### `dockai.workflow.graph`

#### `create_workflow()`

Creates the LangGraph workflow for Dockerfile generation.

**Returns:** `CompiledStateGraph`

**Example:**

```python
from dockai.workflow.graph import create_workflow

workflow = create_workflow()
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

#### `build(project_path, verbose, no_cache)`

Build command for generating Dockerfiles.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `project_path` | `str` | Path to project |
| `verbose` | `bool` | Enable debug logging |
| `no_cache` | `bool` | Disable Docker cache |

---

## Error Classes

### `dockai.core.errors`

```python
class DockAIError(Exception):
    """Base exception for DockAI errors."""

class AnalysisError(DockAIError):
    """Error during project analysis."""

class GenerationError(DockAIError):
    """Error during Dockerfile generation."""

class ValidationError(DockAIError):
    """Error during Dockerfile validation."""

class ConfigurationError(DockAIError):
    """Error in configuration."""
```

---

## Next Steps

- **[Architecture](./architecture.md)**: Understand the workflow
- **[Configuration](./configuration.md)**: All configuration options
- **[Customization](./customization.md)**: Tune for your stack

---

## 📚 References

- **[Architecture](./architecture.md)**: High-level design overview
- **[Configuration](./configuration.md)**: Environment variables and settings
- **[Customization](./customization.md)**: Tuning the agents

