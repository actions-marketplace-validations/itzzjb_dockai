# API Reference

This document provides detailed documentation for DockAI's modules and functions.

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

## Agents Module (`dockai.agents`)

### analyzer.py

#### `analyze_repo_needs(file_list, custom_instructions="")`

Performs AI-powered analysis of the repository to determine project requirements.

**Parameters:**
- `file_list` (list): List of file paths in the repository
- `custom_instructions` (str, optional): Additional instructions for the analyzer

**Returns:**
- `Tuple[AnalysisResult, Dict[str, int]]`: Analysis result and token usage

**Example:**
```python
from dockai.agents.analyzer import analyze_repo_needs

file_list = ["app.py", "requirements.txt", "README.md"]
result, usage = analyze_repo_needs(file_list, "Focus on Flask patterns")

print(result.stack)           # "Python with Flask"
print(result.project_type)    # "service"
print(result.suggested_base_image)  # "python:3.11-slim"
```

---

### generator.py

#### `generate_dockerfile(stack_info, file_contents, custom_instructions="", ...)`

Generates a Dockerfile based on analysis results and strategic plan.

**Parameters:**
- `stack_info` (str): Detected technology stack description
- `file_contents` (str): Content of critical files
- `custom_instructions` (str, optional): User instructions
- `feedback_error` (str, optional): Error from previous attempt
- `previous_dockerfile` (str, optional): Previous Dockerfile for iteration
- `retry_history` (List[Dict], optional): History of attempts
- `current_plan` (Dict, optional): Strategic plan
- `reflection` (Dict, optional): Reflection on failure

**Returns:**
- `Tuple[str, str, str, Any]`: (dockerfile_content, project_type, thought_process, usage)

**Example:**
```python
from dockai.agents.generator import generate_dockerfile

dockerfile, project_type, thoughts, usage = generate_dockerfile(
    stack_info="Python 3.11 with FastAPI",
    file_contents="fastapi==0.100.0\nuvicorn==0.23.0",
    custom_instructions="Use multi-stage build"
)
```

---

### reviewer.py

#### `review_dockerfile(dockerfile_content)`

Performs security review of a generated Dockerfile.

**Parameters:**
- `dockerfile_content` (str): The Dockerfile content to review

**Returns:**
- `Tuple[SecurityReviewResult, Any]`: Review result and token usage

**Example:**
```python
from dockai.agents.reviewer import review_dockerfile

result, usage = review_dockerfile("""
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
""")

print(result.is_secure)       # False (running as root)
print(result.issues)          # List of SecurityIssue objects
print(result.fixed_dockerfile)  # Corrected version
```

---

### agent_functions.py

#### `create_plan(analysis_result, file_contents, retry_history=None, custom_instructions="")`

Creates a strategic plan for Dockerfile generation.

**Parameters:**
- `analysis_result` (Dict): Results from project analysis
- `file_contents` (str): Critical file contents
- `retry_history` (List[Dict], optional): Previous attempt history
- `custom_instructions` (str, optional): Custom guidance

**Returns:**
- `Tuple[PlanningResult, Dict[str, int]]`: Plan and token usage

---

#### `reflect_on_failure(error_message, dockerfile_content, logs, retry_history, ...)`

Analyzes a failed attempt to learn and adapt.

**Parameters:**
- `error_message` (str): The error that occurred
- `dockerfile_content` (str): The Dockerfile that failed
- `logs` (str): Build/run logs
- `retry_history` (List[Dict]): Previous attempts
- Additional parameters for context

**Returns:**
- `Tuple[ReflectionResult, Dict[str, int]]`: Reflection and token usage

---

#### `detect_health_endpoints(file_contents, stack)`

Detects health check endpoints from source code.

**Parameters:**
- `file_contents` (str): Source code content
- `stack` (str): Detected technology stack

**Returns:**
- `Tuple[HealthEndpointDetectionResult, Dict[str, int]]`: Detection result and usage

---

#### `detect_readiness_patterns(file_contents, stack, analysis_result=None)`

Detects application startup patterns for readiness checks.

**Parameters:**
- `file_contents` (str): Source code content
- `stack` (str): Detected technology stack
- `analysis_result` (Dict, optional): Analysis context

**Returns:**
- `Tuple[ReadinessPatternResult, Dict[str, int]]`: Patterns and usage

---

## Core Module (`dockai.core`)

### schemas.py

#### `AnalysisResult`

Pydantic model for repository analysis output.

**Fields:**
- `thought_process` (str): AI reasoning
- `stack` (str): Detected technology stack
- `project_type` (Literal["service", "script"]): Project classification
- `files_to_read` (List[str]): Critical files to examine
- `build_command` (Optional[str]): Build command
- `start_command` (Optional[str]): Start command
- `suggested_base_image` (str): Recommended Docker base image
- `health_endpoint` (Optional[HealthEndpoint]): Detected health endpoint
- `recommended_wait_time` (int): Estimated startup time (3-60 seconds)

---

#### `PlanningResult`

Pydantic model for strategic planning output.

**Fields:**
- `thought_process` (str): Planning reasoning
- `base_image_strategy` (str): Base image selection rationale
- `build_strategy` (str): Build approach description
- `optimization_priorities` (List[str]): Ordered priorities
- `potential_challenges` (List[str]): Anticipated issues
- `mitigation_strategies` (List[str]): Solutions for challenges
- `use_multi_stage` (bool): Multi-stage build decision
- `use_minimal_runtime` (bool): Minimal image decision
- `use_static_linking` (bool): Static linking decision
- `estimated_image_size` (str): Size estimate

---

#### `SecurityReviewResult`

Pydantic model for security review output.

**Fields:**
- `is_secure` (bool): Pass/fail security check
- `issues` (List[SecurityIssue]): Detected issues
- `thought_process` (str): Review reasoning
- `dockerfile_fixes` (List[str]): Specific fixes
- `fixed_dockerfile` (Optional[str]): Corrected Dockerfile

---

#### `ReflectionResult`

Pydantic model for failure reflection output.

**Fields:**
- `thought_process` (str): Analysis reasoning
- `root_cause_analysis` (str): Root cause description
- `what_was_tried` (str): Previous approach summary
- `why_it_failed` (str): Failure explanation
- `lesson_learned` (str): Key takeaway
- `should_change_base_image` (bool): Image change needed
- `suggested_base_image` (Optional[str]): New image suggestion
- `should_change_build_strategy` (bool): Strategy change needed
- `specific_fixes` (List[str]): Actionable fixes
- `needs_reanalysis` (bool): Re-analyze flag
- `confidence_in_fix` (Literal["high", "medium", "low"]): Fix confidence

---

### llm_providers.py

#### `create_llm(agent_name, temperature=0.0)`

Creates an LLM instance for the specified agent.

**Parameters:**
- `agent_name` (str): Agent identifier
- `temperature` (float): LLM temperature (0.0-1.0)

**Returns:**
- LangChain LLM instance

---

#### `LLMConfig`

Configuration dataclass for LLM settings.

**Fields:**
- `provider` (LLMProvider): Provider enum
- `models` (dict): Per-agent model mapping
- `temperature` (float): Default temperature
- `azure_endpoint` (Optional[str]): Azure endpoint
- `azure_api_version` (str): Azure API version
- `google_project` (Optional[str]): Google Cloud project

---

### errors.py

#### `classify_error(error_output, logs="", stack="")`

Classifies an error for intelligent handling.

**Parameters:**
- `error_output` (str): Error message/output
- `logs` (str, optional): Full logs
- `stack` (str, optional): Technology stack

**Returns:**
- `ClassifiedError`: Classified error with suggestions

---

#### `ErrorType`

Enum of error classifications.

**Values:**
- `PROJECT_ERROR`: User's code/config issue (no retry)
- `DOCKERFILE_ERROR`: Generated Dockerfile issue (can retry)
- `ENVIRONMENT_ERROR`: Local system issue (no retry)
- `UNKNOWN_ERROR`: Unclassified (attempt retry)

---

### state.py

#### `DockAIState`

TypedDict defining the workflow state.

**Fields:** See [Architecture](./architecture.md#state-management) for full field list.

---

## Utils Module (`dockai.utils`)

### scanner.py

#### `get_file_tree(root_path)`

Scans directory and returns filtered file list.

**Parameters:**
- `root_path` (str): Directory to scan

**Returns:**
- `List[str]`: Relative file paths

---

### validator.py

#### `validate_docker_build_and_run(directory, project_type="service", ...)`

Builds and validates a Dockerfile.

**Parameters:**
- `directory` (str): Directory with Dockerfile
- `project_type` (str): "service" or "script"
- `stack` (str): Technology stack
- `health_endpoint` (Optional[Tuple]): (path, port) tuple
- `recommended_wait_time` (int): Startup wait time
- `readiness_patterns` (List[str]): Success log patterns
- `failure_patterns` (List[str]): Failure log patterns

**Returns:**
- `Tuple[bool, str, int, Optional[ClassifiedError]]`: (success, message, image_size, error)

---

### prompts.py

#### `get_prompt(agent_name, default_prompt)`

Gets the prompt for an agent, checking custom configuration.

**Parameters:**
- `agent_name` (str): Agent identifier
- `default_prompt` (str): Fallback prompt

**Returns:**
- `str`: Final prompt (custom or default with instructions)

---

#### `load_prompts(path)`

Loads prompts from environment and `.dockai` file.

**Parameters:**
- `path` (str): Project directory path

**Returns:**
- `PromptConfig`: Loaded configuration

---

### callbacks.py

#### `TokenUsageCallback`

LangChain callback for tracking token usage.

**Methods:**
- `on_llm_end(response)`: Called after LLM completion
- `get_usage()`: Returns usage dictionary

**Example:**
```python
from dockai.utils.callbacks import TokenUsageCallback

callback = TokenUsageCallback()
# ... use with LangChain chain ...
usage = callback.get_usage()
print(f"Total tokens: {usage['total_tokens']}")
```

---

### rate_limiter.py

#### `@with_rate_limit_handling(max_retries=5, base_delay=1.0, max_delay=60.0)`

Decorator for rate limit handling with exponential backoff.

**Parameters:**
- `max_retries` (int): Maximum retry attempts
- `base_delay` (float): Initial delay in seconds
- `max_delay` (float): Maximum delay in seconds

**Example:**
```python
from dockai.utils.rate_limiter import with_rate_limit_handling

@with_rate_limit_handling(max_retries=3)
def call_api():
    # API call that might hit rate limits
    pass
```

---

### registry.py

#### `get_docker_tags(image_name, limit=5)`

Fetches valid tags from container registry.

**Parameters:**
- `image_name` (str): Image name (e.g., "node", "gcr.io/project/image")
- `limit` (int): Maximum fallback tags

**Returns:**
- `List[str]`: Valid image tags

**Supported Registries:**
- Docker Hub
- Google Container Registry (GCR)
- Quay.io
- AWS ECR (limited)

---

## Workflow Module (`dockai.workflow`)

### graph.py

#### `create_graph()`

Creates and compiles the LangGraph workflow.

**Returns:**
- `CompiledGraph`: Executable workflow

---

### nodes.py

Node functions for each workflow step. See [Architecture](./architecture.md) for details on each node.

**Available Nodes:**
- `scan_node` - File discovery
- `analyze_node` - Project analysis
- `read_files_node` - File content extraction
- `detect_health_node` - Health endpoint detection
- `detect_readiness_node` - Readiness pattern detection
- `plan_node` - Strategic planning
- `generate_node` - Dockerfile generation
- `review_node` - Security review
- `validate_node` - Build validation
- `reflect_node` - Failure reflection
- `increment_retry` - Retry counter

---

## CLI Module (`dockai.cli`)

### main.py

#### `run(path, verbose=False)`

Main CLI entry point.

**Parameters:**
- `path` (str): Project directory to analyze
- `verbose` (bool): Enable debug logging

---

### ui.py

#### `print_welcome()`
Prints the welcome banner.

#### `print_error(title, message, details=None)`
Prints formatted error message.

#### `print_success(message)`
Prints formatted success message.

#### `print_warning(message)`
Prints formatted warning message.

#### `display_summary(final_state, output_path)`
Displays execution summary with usage statistics.

#### `display_failure(final_state)`
Displays failure details with troubleshooting info.

---

## Usage Examples

### Complete Workflow

```python
from dockai.workflow.graph import create_graph

# Create the workflow graph
graph = create_graph()

# Initialize state
initial_state = {
    "path": "/path/to/project",
    "max_retries": 3,
    "config": {},
    # ... other required fields
}

# Run the workflow
final_state = graph.invoke(initial_state)

# Check results
if final_state["validation_result"]["success"]:
    print("Dockerfile generated successfully!")
    print(final_state["dockerfile_content"])
else:
    print("Failed:", final_state["error"])
```

### Individual Agent Usage

```python
from dockai.agents.analyzer import analyze_repo_needs
from dockai.agents.generator import generate_dockerfile
from dockai.utils.scanner import get_file_tree

# Scan project
files = get_file_tree("/path/to/project")

# Analyze
analysis, _ = analyze_repo_needs(files)

# Generate
dockerfile, project_type, _, _ = generate_dockerfile(
    stack_info=analysis.stack,
    file_contents="...",
)

print(dockerfile)
```
