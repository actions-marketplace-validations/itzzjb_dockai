# Configuration Reference

Complete reference for all DockAI configuration options.

---

## Configuration Methods

DockAI supports three configuration methods (in priority order):

| Priority | Method | Use Case |
|----------|--------|----------|
| 1 (Highest) | Environment Variables | Runtime overrides, CI/CD |
| 2 | `.dockai` File | Repository-specific settings |
| 3 (Lowest) | Built-in Defaults | Intelligent fallbacks |

---

## API Configuration

### Provider API Keys

| Variable | Provider | Required |
|----------|----------|----------|
| `OPENAI_API_KEY` | OpenAI | If using OpenAI |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | If using Azure |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | If using Azure |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | Default: `2024-02-15-preview` |
| `GOOGLE_API_KEY` | Google Gemini | If using Gemini |
| `ANTHROPIC_API_KEY` | Anthropic | If using Anthropic |
| `OLLAMA_BASE_URL` | Ollama | Default: `http://localhost:11434` |

### LLM Provider Selection

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_LLM_PROVIDER` | Provider selection | `openai` |

**Valid values**: `openai`, `azure`, `gemini`, `anthropic`, `ollama`

---

## Per-Agent Model Configuration

Assign different models to different agents for cost optimization:

| Variable | Agent | Default (OpenAI) |
|----------|-------|------------------|
| `DOCKAI_MODEL_ANALYZER` | Project analyzer | `gpt-4o-mini` |
| `DOCKAI_MODEL_PLANNER` | Strategic planner | `gpt-4o-mini` |
| `DOCKAI_MODEL_GENERATOR` | Dockerfile generator | `gpt-4o` |
| `DOCKAI_MODEL_GENERATOR_ITERATIVE` | Iterative generator | `gpt-4o` |
| `DOCKAI_MODEL_REVIEWER` | Security reviewer | `gpt-4o-mini` |
| `DOCKAI_MODEL_REFLECTOR` | Failure reflector | `gpt-4o` |
| `DOCKAI_MODEL_HEALTH_DETECTOR` | Health detector | `gpt-4o-mini` |
| `DOCKAI_MODEL_READINESS_DETECTOR` | Readiness detector | `gpt-4o-mini` |
| `DOCKAI_MODEL_ERROR_ANALYZER` | Error analyzer | `gpt-4o-mini` |
| `DOCKAI_MODEL_ITERATIVE_IMPROVER` | Iterative improver | `gpt-4o` |

### Default Models by Provider

| Provider | Fast Model | Powerful Model |
|----------|------------|----------------|
| OpenAI | `gpt-4o-mini` | `gpt-4o` |
| Azure | `gpt-4o-mini` | `gpt-4o` |
| Gemini | `gemini-1.5-flash` | `gemini-1.5-pro` |
| Anthropic | `claude-3-5-haiku-latest` | `claude-sonnet-4-20250514` |
| Ollama | `llama3` | `llama3` |

### Mixed Provider Configuration

You can use different providers for different agents by prefixing the model name with `provider/`. This is useful for balancing cost, privacy, and performance.

**Example**: Use local Ollama for everything, but OpenAI for the initial analysis.

```bash
# Default provider for all agents
DOCKAI_LLM_PROVIDER=ollama

# Override specifically for the analyzer agent
DOCKAI_MODEL_ANALYZER=openai/gpt-4o-mini
```

**Supported Prefixes**:
- `openai/`
- `azure/`
- `gemini/`
- `anthropic/`
- `ollama/`

---

## Workflow Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_RETRIES` | Maximum retry attempts | `3` |

---

## Security & Validation Settings

### Linting & Security Scanning

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_SKIP_HADOLINT` | Skip Hadolint Dockerfile linting | `false` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy vulnerability scan | `false` |
| `DOCKAI_STRICT_SECURITY` | Fail on any vulnerability | `false` |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Maximum image size (0 = disabled) | `500` |
| `DOCKAI_SKIP_HEALTH_CHECK` | Skip health endpoint checks | `false` |

### Validation Resource Limits

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_VALIDATION_MEMORY` | Memory limit for validation | `512m` |
| `DOCKAI_VALIDATION_CPUS` | CPU limit for validation | `1.0` |
| `DOCKAI_VALIDATION_PIDS` | Process limit for validation | `100` |

### File Analysis Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_TRUNCATION_ENABLED` | Enable smart file truncation | `false` |
| `DOCKAI_TOKEN_LIMIT` | Token limit that triggers auto-truncation | `100000` |
| `DOCKAI_MAX_FILE_CHARS` | Max characters per file (when truncating) | `200000` |
| `DOCKAI_MAX_FILE_LINES` | Max lines per file (when truncating) | `5000` |

**Truncation Behavior**:
- **Default**: Truncation is OFF - files are read in full
- **Env Var**: Set `DOCKAI_TRUNCATION_ENABLED=true` to always truncate large files
- **Auto-truncation**: If total content exceeds `DOCKAI_TOKEN_LIMIT`, truncation auto-enables
- **Token Estimation**: ~1 token ≈ 4 characters

---

## Observability & Tracing

DockAI supports **OpenTelemetry** for distributed tracing, providing visibility into each step of the Dockerfile generation workflow.

### Tracing Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` |
| `DOCKAI_TRACING_EXPORTER` | Exporter type (`console`, `otlp`) | `console` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL (for `otlp` exporter) | `http://localhost:4317` |
| `OTEL_SERVICE_NAME` | Service name for traces | `dockai` |

### Traced Operations

When tracing is enabled, spans are created for:
- **Workflow execution**: Overall `dockai.workflow` span
- **Node execution**: Individual spans for each node (`node.scan`, `node.analyze`, `node.plan`, `node.generate`, `node.review`, `node.validate`, `node.reflect`)
- **LLM calls**: Token usage, model selection, and timing

### Example: Console Tracing

```bash
# Enable console tracing for debugging
DOCKAI_ENABLE_TRACING=true
DOCKAI_TRACING_EXPORTER=console
```

### Example: OTLP Export (Jaeger, Grafana Tempo, Datadog)

```bash
# Enable OTLP tracing for production observability
DOCKAI_ENABLE_TRACING=true
DOCKAI_TRACING_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
```

### Span Attributes

Each node span includes relevant attributes:
- `node.scan`: `files_found`, `path`
- `node.analyze`: `stack`, `project_type`
- `node.plan`: `retry_count`
- `node.generate`: `retry_count`, `project_type`
- `node.review`: `is_secure`, `issues_count`
- `node.validate`: `success`, `error`, `image_size_mb`
- `node.reflect`: `root_cause`, `confidence`, `needs_reanalysis`

---

## Custom Instructions

Instructions are **appended** to default prompts to guide AI reasoning:

| Variable | Agent | Description |
|----------|-------|-------------|
| `DOCKAI_ANALYZER_INSTRUCTIONS` | Analyzer | Guide project analysis |
| `DOCKAI_PLANNER_INSTRUCTIONS` | Planner | Guide strategic planning |
| `DOCKAI_GENERATOR_INSTRUCTIONS` | Generator | Guide Dockerfile creation |
| `DOCKAI_GENERATOR_ITERATIVE_INSTRUCTIONS` | Generator (Iterative) | Guide iterative fixes |
| `DOCKAI_REVIEWER_INSTRUCTIONS` | Reviewer | Guide security review |
| `DOCKAI_REFLECTOR_INSTRUCTIONS` | Reflector | Guide failure analysis |
| `DOCKAI_HEALTH_DETECTOR_INSTRUCTIONS` | Health Detector | Guide health detection |
| `DOCKAI_READINESS_DETECTOR_INSTRUCTIONS` | Readiness Detector | Guide readiness detection |
| `DOCKAI_ERROR_ANALYZER_INSTRUCTIONS` | Error Analyzer | Guide error classification |
| `DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS` | Iterative Improver | Guide fix application |

---

## Custom Prompts (Advanced)

Prompts **completely replace** the default prompt for full control:

| Variable | Agent |
|----------|-------|
| `DOCKAI_PROMPT_ANALYZER` | Replace analyzer prompt |
| `DOCKAI_PROMPT_PLANNER` | Replace planner prompt |
| `DOCKAI_PROMPT_GENERATOR` | Replace generator prompt |
| `DOCKAI_PROMPT_GENERATOR_ITERATIVE` | Replace iterative generator |
| `DOCKAI_PROMPT_REVIEWER` | Replace reviewer prompt |
| `DOCKAI_PROMPT_REFLECTOR` | Replace reflector prompt |
| `DOCKAI_PROMPT_HEALTH_DETECTOR` | Replace health detector |
| `DOCKAI_PROMPT_READINESS_DETECTOR` | Replace readiness detector |
| `DOCKAI_PROMPT_ERROR_ANALYZER` | Replace error analyzer |
| `DOCKAI_PROMPT_ITERATIVE_IMPROVER` | Replace iterative improver |

> ⚠️ **Warning**: Custom prompts completely override defaults. Use instructions instead unless you need full control.

---

## `.dockai` File Format

Create a `.dockai` file in your project root for repository-specific configuration.

### Basic Structure

```ini
# Instructions (appended to defaults)
[instructions_analyzer]
Your instructions here...

[instructions_generator]
Your instructions here...

# Full prompt replacements (advanced)
[prompt_analyzer]
Complete prompt replacement...
```

### Complete Example

```ini
# Project context for the analyzer
[instructions_analyzer]
This is a Django application with Celery workers.
Dependencies are managed with Poetry.
Uses PostgreSQL for the database.

# Dockerfile generation guidance
[instructions_generator]
Use gunicorn as the WSGI server.
Run database migrations at container start.
Use /app as WORKDIR.
Create non-root user with UID 10000.

# Strategic planning constraints
[instructions_planner]
Use approved base images from company-registry.io only.
Prefer multi-stage builds for all compiled languages.

# Security requirements
[instructions_reviewer]
All containers MUST run as non-root (UID >= 10000).
Check for hardcoded API keys or secrets.
Fail on any CRITICAL or HIGH vulnerabilities.

# Known issues and fixes
[instructions_reflector]
Common issue: "pg_config not found"
Solution: Install postgresql-dev (Alpine) or libpq-dev (Debian)

Common issue: "GLIBC not found" on Alpine
Solution: Use Debian-based image or install gcompat

# Health endpoint location
[instructions_health_detector]
Our health endpoint is at /api/v1/health/
Port is always 8080 for HTTP services.

# Startup pattern
[instructions_readiness_detector]
Look for "Application startup complete" in logs.
Typical startup time is 5-10 seconds.
```

---

## Environment File (`.env`)

### Minimal Configuration

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### Full Configuration Example

```bash
# LLM Provider
DOCKAI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here

# Per-agent model optimization
DOCKAI_MODEL_ANALYZER=gpt-4o-mini
DOCKAI_MODEL_PLANNER=gpt-4o-mini
DOCKAI_MODEL_GENERATOR=gpt-4o
DOCKAI_MODEL_REVIEWER=gpt-4o-mini
DOCKAI_MODEL_REFLECTOR=gpt-4o

# Workflow settings
MAX_RETRIES=5

# Security settings
DOCKAI_SKIP_SECURITY_SCAN=false
DOCKAI_STRICT_SECURITY=true
DOCKAI_MAX_IMAGE_SIZE_MB=300

# Validation resource limits
DOCKAI_VALIDATION_MEMORY=1g
DOCKAI_VALIDATION_CPUS=2.0
DOCKAI_VALIDATION_PIDS=200

# Custom instructions
DOCKAI_GENERATOR_INSTRUCTIONS="Always use multi-stage builds"
```

---

## Configuration Precedence

When the same setting is configured in multiple places:

```
Environment Variable (highest priority)
        ↓
   .dockai file
        ↓
  Built-in Default (lowest priority)
```

### Example

```bash
# .dockai file
[instructions_generator]
Use Alpine base images

# Environment variable
export DOCKAI_GENERATOR_INSTRUCTIONS="Use Debian base images"

# Result: "Use Debian base images" is used (env var wins)
```

---

## Next Steps

- **[Customization](./customization.md)**: Strategies for effective customization
- **[GitHub Actions](./github-actions.md)**: CI/CD configuration
- **[MCP Server](./mcp-server.md)**: AI Agent integration guide

