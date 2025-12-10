# API Reference

This document provides code-level documentation for DockAI's main modules and functions.

## Table of Contents

- [Workflow Module](#workflow-module)
- [Agents Module](#agents-module)
- [Utils Module](#utils-module)
- [Core Module](#core-module)
- [CLI Module](#cli-module)

## Workflow Module

### `src/dockai/workflow/graph.py`

Main workflow orchestration using LangGraph.

#### `build_app_graph(config: dict) -> CompiledGraph`

Builds and compiles the LangGraph state graph for the DockAI workflow.

**Parameters:**
- `config` (dict): Configuration dictionary with all settings

**Returns:**
- `CompiledGraph`: Compiled LangGraph state graph

**Graph Structure:**
```
START → scan → analyze → read_files → blueprint → generate 
→ [conditional: review] → validate → [conditional: retry/reanalyze/end]
```

**Example:**
```python
from dockai.workflow.graph import build_app_graph

config = {"path": "/path/to/project", "max_retries": 3}
graph = build_app_graph(config)
result = graph.invoke({"path": "/path/to/project", "config": config})
```

### `src/dockai/workflow/nodes.py`

Workflow node implementations.

#### `scan_node(state: DockAIState) -> DockAIState`

Scans the project directory to build a file tree.

**Returns:**
- Updated state with `file_tree` populated

#### `analyze_node(state: DockAIState) -> DockAIState`

Performs AI-powered project analysis.

**Returns:**
- Updated state with `analysis_result` and `usage_stats`

#### `read_files_node(state: DockAIState) -> DockAIState`

Reads project files using RAG-based context retrieval.

**Returns:**
- Updated state with `file_contents` and optionally `code_intelligence`

#### `blueprint_node(state: DockAIState) -> DockAIState`

Creates architectural blueprint and runtime configuration.

**Returns:**
- Updated state with `current_plan`, `detected_health_endpoint`, `readiness_patterns`

#### `generate_node(state: DockAIState) -> DockAIState`

Generates the Dockerfile.

**Returns:**
- Updated state with `dockerfile_content`

#### `review_node(state: DockAIState) -> DockAIState`

Performs AI-powered security review.

**Returns:**
- Updated state with potential security issues or approved Dockerfile

#### `validate_node(state: DockAIState) -> DockAIState`

Validates the Dockerfile with Docker, Hadolint, and Trivy.

**Returns:**
- Updated state with `validation_result`, `error`, `error_details`

#### `reflect_node(state: DockAIState) -> DockAIState`

Analyzes failures and determines next steps.

**Returns:**
- Updated state with `reflection`, `needs_reanalysis`, `retry_history`

### `src/dockai/workflow/routing.py`

Conditional routing logic for the workflow.

#### `should_review(state: DockAIState) -> str`

Determines if security review is needed.

**Returns:**
- `"review"` or `"validate"`

#### `should_retry(state: DockAIState) -> str`

Determines if retry is needed after validation.

**Returns:**
- `"reflect"` (on failure), `"end"` (on success), or `"increment_retry"` (max retries)

#### `route_after_reflection(state: DockAIState) -> str`

Routes after reflection based on the decision.

**Returns:**
- `"analyze"` (reanalyze), `"generate"` (retry), or `"end"` (give up)

## Agents Module

### `src/dockai/agents/analyzer.py`

#### `analyze_project(file_tree: List[str], config: dict, model: str) -> dict`

Analyzes a project to determine its type, stack, and configuration.

**Parameters:**
- `file_tree`: List of relative file paths
- `config`: Configuration dictionary
- `model`: LLM model name

**Returns:**
- `dict`: Analysis result with keys:
  - `project_type`: Type of project (e.g., "web_app", "cli", "library")
  - `primary_language`: Primary programming language
  - `frameworks`: List of detected frameworks
  - `build_commands`: List of build commands
  - `start_command`: Command to start the application
  - `entry_points`: List of entry point files
  - `dependencies`: Dependency files and package managers

**Example:**
```python
from dockai.agents.analyzer import analyze_project

result = analyze_project(
    file_tree=["app.js", "package.json", "src/server.js"],
    config={"path": "/path/to/project"},
    model="gpt-4o-mini"
)
# Result: {"project_type": "web_app", "primary_language": "javascript", ...}
```

### `src/dockai/agents/generator.py`

#### `create_dockerfile(analysis: dict, context: str, config: dict, model: str) -> str`

Generates a Dockerfile from scratch.

**Parameters:**
- `analysis`: Analysis result from analyzer
- `context`: File contents (RAG-retrieved)
- `config`: Configuration dictionary
- `model`: LLM model name

**Returns:**
- `str`: Generated Dockerfile content

#### `create_blueprint(analysis: dict, context: str, config: dict, model: str) -> dict`

Creates an architectural blueprint for the Dockerfile.

**Parameters:**
- Same as `create_dockerfile`

**Returns:**
- `dict`: Blueprint with keys:
  - `base_image`: Recommended base image
  - `build_strategy`: "multi-stage" or "single-stage"
  - `port`: Application port
  - `health_endpoint`: Health check endpoint
  - `env_vars`: Required environment variables

#### `generate_iterative_dockerfile(current_dockerfile: str, error_details: str, reflection: str, config: dict, model: str) -> str`

Improves an existing Dockerfile based on error feedback.

**Parameters:**
- `current_dockerfile`: Current Dockerfile content
- `error_details`: Error logs from validation
- `reflection`: AI reflection on the failure
- `config`: Configuration dictionary
- `model`: LLM model name

**Returns:**
- `str`: Improved Dockerfile content

### `src/dockai/agents/reviewer.py`

#### `review_dockerfile(dockerfile: str, analysis: dict, config: dict, model: str) -> dict`

Performs AI-powered security review of a Dockerfile.

**Parameters:**
- `dockerfile`: Dockerfile content
- `analysis`: Project analysis
- `config`: Configuration dictionary
- `model`: LLM model name

**Returns:**
- `dict`: Review result with keys:
  - `approved`: Boolean
  - `issues`: List of security issues
  - `suggestions`: List of improvement suggestions

### `src/dockai/agents/agent_functions.py`

#### `reflect_on_failure(error: str, error_details: str, dockerfile: str, analysis: dict, history: List[dict], config: dict, model: str) -> dict`

Analyzes a failure and determines the next step.

**Returns:**
- `dict`: Reflection result with keys:
  - `explanation`: What went wrong
  - `root_cause`: Identified root cause
  - `next_step`: "retry", "reanalyze", or "give_up"
  - `strategy`: Specific strategy to try

#### `classify_build_error(error_output: str, config: dict, model: str) -> dict`

Classifies the type of Docker build error.

**Returns:**
- `dict`: Error classification

## Utils Module

### `src/dockai/utils/indexer.py`

RAG indexing and retrieval.

#### `class ProjectIndex`

##### `__init__(use_embeddings: bool = True)`

Initializes the project index.

##### `index_project(root_path: str, file_tree: List[str], chunk_size: int = 400, chunk_overlap: int = 50)`

Indexes all files in the project for semantic search.

**Parameters:**
- `root_path`: Absolute path to project root
- `file_tree`: List of relative file paths
- `chunk_size`: Lines per chunk (default: 400)
- `chunk_overlap`: Overlap between chunks (default: 50)

##### `search(query: str, top_k: int = 10) -> List[FileChunk]`

Searches for the most relevant file chunks.

**Parameters:**
- `query`: Search query (usually the analysis result summary)
- `top_k`: Number of chunks to return

**Returns:**
- List of `FileChunk` objects ranked by relevance

##### `get_stats() -> dict`

Returns indexing statistics.

**Returns:**
- `dict`: Stats with `total_files`, `total_chunks`, `indexed_at`

### `src/dockai/utils/scanner.py`

#### `get_file_tree(path: str) -> List[str]`

Scans a directory and returns a list of relative file paths.

**Parameters:**
- `path`: Absolute path to scan

**Returns:**
- `List[str]`: List of relative paths

**Respects:**
- `.gitignore`
- `.dockerignore`
- Common ignore patterns (node_modules, __pycache__, etc.)

### `src/dockai/utils/validator.py`

#### `validate_dockerfile(path: str, analysis: dict, config: dict) -> dict`

Validates a Dockerfile by building and testing the container.

**Parameters:**
- `path`: Project path
- `analysis`: Analysis result
- `config`: Configuration dictionary

**Returns:**
- `dict`: Validation result with:
  - `success`: Boolean
  - `error`: Error message (if failed)
  - `error_details`: Detailed logs
  - `image_size`: Built image size in bytes
  - `hadolint_issues`: List of Hadolint issues
  - `trivy_vulnerabilities`: List of vulnerabilities

**Steps:**
1. Docker build
2. Hadolint linting
3. Trivy security scan
4. Container startup test
5. Health check (if configured)

### `src/dockai/utils/code_intelligence.py`

#### `analyze_file(file_path: str, content: str) -> Optional[FileAnalysis]`

Performs AST analysis on a code file.

**Parameters:**
- `file_path`: Relative file path (used to determine language)
- `content`: File content

**Returns:**
- `FileAnalysis` object with:
  - `entry_points`: List of entry point functions
  - `ports`: Detected port numbers
  - `env_vars`: Environment variable references
  - `frameworks`: Detected frameworks
  - `imports`: Import statements

**Supported Languages:**
- Python (via `ast`)
- JavaScript/TypeScript (via regex)
- Go (via regex)

### `src/dockai/utils/file_utils.py`

#### `read_critical_files(path: str, file_tree: List[str], max_chars: int, max_lines: int) -> str`

Reads critical files (dependencies, configs, entry points) from a project.

**Parameters:**
- `path`: Project root path
- `file_tree`: List of file paths
- `max_chars`: Max characters per file
- `max_lines`: Max lines per file

**Returns:**
- `str`: Concatenated file contents

#### `smart_truncate(content: str, max_lines: int) -> str`

Intelligently truncates file content while preserving structure.

**Strategy:**
- Keep imports
- Keep class/function signatures
- Keep docstrings
- Truncate function bodies

## Core Module

### `src/dockai/core/llm_providers.py`

#### `get_model_for_agent(agent_name: str, config: dict) -> ChatModel`

Returns the configured LLM model for a given agent.

**Parameters:**
- `agent_name`: Name of the agent (e.g., "analyzer", "generator")
- `config`: Configuration dictionary

**Returns:**
- Configured LangChain `ChatModel` instance

**Supported Providers:**
- OpenAI (ChatOpenAI)
- Google Gemini (ChatGoogleGenerativeAI)
- Anthropic Claude (ChatAnthropic)
- Azure OpenAI (AzureChatOpenAI)
- Ollama (ChatOllama)

**Example:**
```python
from dockai.core.llm_providers import get_model_for_agent

config = {"llm_provider": "openai", "model_analyzer": "gpt-4o-mini"}
model = get_model_for_agent("analyzer", config)
response = model.invoke("Analyze this project...")
```

### `src/dockai/core/schemas.py`

#### `class DockAIState(TypedDict)`

LangGraph state schema.

**Fields:**
- `path` (str): Project path
- `config` (dict): Configuration
- `file_tree` (List[str]): File tree
- `analysis_result` (dict): Analysis result
- `file_contents` (str): RAG-retrieved context
- `current_plan` (str): Architectural blueprint
- `dockerfile_content` (str): Generated Dockerfile
- `error` (str): Error message
- `error_details` (str): Detailed error logs
- `reflection` (str): Reflection on failure
- `retry_count` (int): Current retry count
- `needs_reanalysis` (bool): Whether to reanalyze
- `usage_stats` (dict): Token usage statistics

### `src/dockai/core/errors.py`

Custom exception classes for error handling.

## CLI Module

### `src/dockai/cli/main.py`

#### `build(path: str, verbose: bool, no_cache: bool)`

Main CLI command for building Dockerfiles.

**Parameters:**
- `path`: Path to the project (default: current directory)
- `verbose`: Enable verbose logging (default: False)
- `no_cache`: Disable Docker cache (not fully implemented)

**Example:**
```bash
dockai build /path/to/project --verbose
```

**Programmatic Usage:**
```python
from dockai.cli.main import build

build(path="/path/to/project", verbose=True, no_cache=False)
```

### `src/dockai/cli/ui.py`

#### `setup_logging(verbose: bool = False) -> logging.Logger`

Configures logging with Rich formatting.

**Parameters:**
- `verbose`: Enable DEBUG level logs

**Returns:**
- Configured logger instance

## State Schema Reference

Complete `DockAIState` fields:

```python
{
    # Input
    "path": str,                          # Project path
    "config": dict,                       # Configuration
    
    # Scanning
    "file_tree": List[str],               # List of relative paths
    
    # Analysis
    "analysis_result": {
        "project_type": str,
        "primary_language": str,
        "frameworks": List[str],
        "build_commands": List[str],
        "start_command": str,
        "entry_points": List[str],
        "dependencies": dict
    },
    
    # Context
    "file_contents": str,                 # RAG-retrieved context
    "code_intelligence": dict,            # AST analysis results
    
    # Planning
    "current_plan": str,                  # Architectural blueprint
    "detected_health_endpoint": str,      # Health check endpoint
    "readiness_patterns": List[str],      # Readiness probe patterns
    
    # Generation
    "dockerfile_content": str,            # Generated Dockerfile
    
    # Validation
    "validation_result": {
        "success": bool,
        "error": str,
        "image_size": int,
        "hadolint_issues": List[dict],
        "trivy_vulnerabilities": List[dict]
    },
    
    # Error Handling
    "error": str,                         # Short error message
    "error_details": str,                 # Full error logs
    "reflection": str,                    # AI reflection
    "retry_count": int,                   # Current attempt number
    "retry_history": List[dict],          # History of attempts
    "needs_reanalysis": bool,             # Reanalyze flag
    
    # Observability
    "usage_stats": {
        "analyzer": {"input_tokens": int, "output_tokens": int},
        "blueprint": {"input_tokens": int, "output_tokens": int},
        "generator": {"input_tokens": int, "output_tokens": int},
        # ... other agents
    }
}
```

## Configuration Schema

Complete configuration dictionary structure:

```python
{
    # Core
    "path": str,
    "llm_provider": str,  # "openai", "gemini", "anthropic", "azure", "ollama"
    
    # Model Selection
    "model_analyzer": str,
    "model_blueprint": str,
    "model_generator": str,
    "model_generator_iterative": str,
    "model_reviewer": str,
    "model_reflector": str,
    "model_error_analyzer": str,
    "model_iterative_improver": str,
    
    # Validation
    "skip_hadolint": bool,
    "skip_security_scan": bool,
    "strict_security": bool,
    "max_image_size_mb": int,
    "skip_health_check": bool,
    "skip_security_review": bool,
    "validation_memory": str,
    "validation_cpus": str,
    "validation_pids": int,
    
    # File Reading
    "max_file_chars": int,
    "max_file_lines": int,
    "truncation_enabled": bool,
    "token_limit": int,
    
    # RAG
    "use_rag": bool,
    "embedding_model": str,
    "read_all_files": bool,
    
    # Retry
    "max_retries": int,
    
    # Custom Instructions
    "analyzer_instructions": str,
    "generator_instructions": str,
    # ... (all agents)
    
    # Custom Prompts
    "prompt_analyzer": str,
    "prompt_generator": str,
    # ... (all agents)
    
    # Observability
    "enable_tracing": bool,
    "tracing_exporter": str,
    "langchain_tracing_v2": bool,
    
    # Caching
    "llm_caching": bool
}
```

---

## Example: Complete Programmatic Usage

```python
from dockai.workflow.graph import build_app_graph
from dockai.core.schemas import DockAIState

# Configuration
config = {
    "path": "/path/to/project",
    "llm_provider": "openai",
    "model_analyzer": "gpt-4o-mini",
    "model_generator": "gpt-4o",
    "max_retries": 3,
    "skip_hadolint": False,
    "use_rag": True
}

# Build graph
graph = build_app_graph(config)

# Initial state
initial_state: DockAIState = {
    "path": config["path"],
    "config": config
}

# Run workflow
result = graph.invoke(initial_state)

# Access results
print("Dockerfile:", result["dockerfile_content"])
print("Usage:", result["usage_stats"])

if result.get("error"):
    print("Error:", result["error"])
    print("Details:", result["error_details"])
```

---

**For more details, see the source code in `src/dockai/`.**
