# Configuration Reference

This document provides a complete reference for all DockAI configuration options, explaining not just what each option does, but **when and why** you would use it.

---

## 📋 Table of Contents

1. [Configuration Methods](#configuration-methods)
2. [API Configuration](#api-configuration)
3. [Per-Agent Model Configuration](#per-agent-model-configuration)
4. [Workflow Settings](#workflow-settings)
5. [Security & Validation Settings](#security--validation-settings)
6. [Observability & Tracing](#observability--tracing)
7. [Custom Instructions](#custom-instructions)
8. [Custom Prompts (Advanced)](#custom-prompts-advanced)
9. [The .dockai File](#the-dockai-file)
10. [Configuration Precedence](#configuration-precedence)
11. [Complete Examples](#complete-examples)

---

## Configuration Methods

DockAI supports three configuration methods. Understanding their priority helps you structure your configuration effectively.

### Priority Order (Highest to Lowest)

| Priority | Method | Best For |
|----------|--------|----------|
| 1 (Highest) | **Environment Variables** | Runtime overrides, CI/CD secrets, temporary changes |
| 2 | **`.dockai` File** | Repository-specific settings, version-controlled config |
| 3 (Lowest) | **Built-in Defaults** | Intelligent fallbacks when nothing is configured |

### How Priority Works

When DockAI needs a configuration value:

1. **Check environment variable** → If set, use it
2. **Check `.dockai` file** → If present and has the value, use it
3. **Use built-in default** → Always has a sensible fallback

**Example**: Generator instructions

```bash
# .dockai file says:
[instructions_generator]
Use Alpine base images

# Environment variable says:
export DOCKAI_GENERATOR_INSTRUCTIONS="Use Debian base images"

# Result: "Use Debian base images" is used (env var wins)
```

### When to Use Each Method

| Method | Use When |
|--------|----------|
| **Environment Variables** | CI/CD secrets, per-run overrides, sensitive data (API keys) |
| **`.dockai` File** | Project-specific settings that should be version controlled |
| **Defaults** | Standard projects that don't need special handling |

---

## API Configuration

### Provider API Keys

Each LLM provider requires its own API key:

| Variable | Provider | How to Get |
|----------|----------|------------|
| `OPENAI_API_KEY` | OpenAI | [platform.openai.com](https://platform.openai.com) → API Keys |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | Azure Portal → Your OpenAI resource → Keys |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | Azure Portal → Your OpenAI resource → Endpoint |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | Default: `2024-02-15-preview` |
| `GOOGLE_API_KEY` | Google Gemini | [ai.google.dev](https://ai.google.dev) → Get API Key |
| `ANTHROPIC_API_KEY` | Anthropic | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `OLLAMA_BASE_URL` | Ollama | Default: `http://localhost:11434` |

### LLM Provider Selection

```bash
# Choose your provider
DOCKAI_LLM_PROVIDER=openai  # Default
```

**Valid values**: `openai`, `azure`, `gemini`, `anthropic`, `ollama`

### Provider Comparison

| Provider | Pros | Cons | Best For |
|----------|------|------|----------|
| **OpenAI** | Best quality, fast | Pay per token | Most users, production |
| **Azure OpenAI** | Enterprise compliance, data privacy | Requires Azure subscription | Enterprise environments |
| **Gemini** | Free tier available, good quality | Rate limits on free tier | Cost-conscious users |
| **Anthropic** | Excellent reasoning, large context | Pay per token | Complex projects |
| **Ollama** | Free, private, offline | Requires local compute | Privacy-focused, offline |

### Ollama Docker Fallback

A unique feature: If you select Ollama but don't have it installed, DockAI automatically uses Docker to run Ollama:

```bash
# This works even without Ollama installed locally
DOCKAI_LLM_PROVIDER=ollama
dockai build .

# DockAI will:
# 1. Check if Ollama is running locally
# 2. If not, pull ollama/ollama Docker image
# 3. Start a container named 'dockai-ollama'
# 4. Pull the required model inside the container
# 5. Use a persistent volume for model caching
```

**Why this exists**: We want privacy-focused users to be able to use local LLMs without complex setup. If Docker is available, Ollama works automatically.

---

## Per-Agent Model Configuration

DockAI has 10 specialized agents. You can assign different models to each for cost optimization.

### The Model Variables

| Variable | Agent | Default (OpenAI) | Purpose |
|----------|-------|------------------|---------|
| `DOCKAI_MODEL_ANALYZER` | Analyzer | `gpt-4o-mini` | Detect technology stack |
| `DOCKAI_MODEL_PLANNER` | Planner | `gpt-4o-mini` | Create build strategy |
| `DOCKAI_MODEL_GENERATOR` | Generator | `gpt-4o` | Write Dockerfile |
| `DOCKAI_MODEL_GENERATOR_ITERATIVE` | Iterative Generator | `gpt-4o` | Fix failed Dockerfile |
| `DOCKAI_MODEL_REVIEWER` | Reviewer | `gpt-4o-mini` | Security audit |
| `DOCKAI_MODEL_REFLECTOR` | Reflector | `gpt-4o` | Analyze failures |
| `DOCKAI_MODEL_HEALTH_DETECTOR` | Health Detector | `gpt-4o-mini` | Find health endpoints |
| `DOCKAI_MODEL_READINESS_DETECTOR` | Readiness Detector | `gpt-4o-mini` | Find startup patterns |
| `DOCKAI_MODEL_ERROR_ANALYZER` | Error Analyzer | `gpt-4o-mini` | Classify errors |
| `DOCKAI_MODEL_ITERATIVE_IMPROVER` | Iterative Improver | `gpt-4o` | Apply specific fixes |

### Why Different Models?

Not all tasks require the most powerful model:

- **Fast models** (`gpt-4o-mini`, `gemini-1.5-flash`, `claude-3-5-haiku`): Good for pattern matching, classification, simple analysis
- **Powerful models** (`gpt-4o`, `gemini-1.5-pro`, `claude-sonnet-4`): Required for complex reasoning, code generation, root cause analysis

### Default Models by Provider

| Provider | Fast Model | Powerful Model |
|----------|------------|----------------|
| OpenAI | `gpt-4o-mini` | `gpt-4o` |
| Azure | `gpt-4o-mini` | `gpt-4o` |
| Gemini | `gemini-1.5-flash` | `gemini-1.5-pro` |
| Anthropic | `claude-3-5-haiku-latest` | `claude-sonnet-4-20250514` |
| Ollama | `llama3` | `llama3` |

### Cost Optimization Strategy

Use powerful models only where needed:

```bash
# Recommended cost-optimized configuration
DOCKAI_MODEL_ANALYZER=gpt-4o-mini        # Pattern matching
DOCKAI_MODEL_PLANNER=gpt-4o-mini         # Quick planning
DOCKAI_MODEL_GENERATOR=gpt-4o            # Complex code gen (worth it)
DOCKAI_MODEL_GENERATOR_ITERATIVE=gpt-4o  # Debugging (worth it)
DOCKAI_MODEL_REVIEWER=gpt-4o-mini        # Rule checking
DOCKAI_MODEL_REFLECTOR=gpt-4o            # Root cause analysis (worth it)
DOCKAI_MODEL_HEALTH_DETECTOR=gpt-4o-mini # Pattern matching
DOCKAI_MODEL_READINESS_DETECTOR=gpt-4o-mini
DOCKAI_MODEL_ERROR_ANALYZER=gpt-4o-mini
DOCKAI_MODEL_ITERATIVE_IMPROVER=gpt-4o   # Code modification (worth it)
```

### Mixed Provider Configuration

**Powerful feature**: Use different providers for different agents. Prefix the model name with `provider/`:

```bash
# Default provider for all agents
DOCKAI_LLM_PROVIDER=ollama

# But use OpenAI for the analyzer (needs internet access anyway)
DOCKAI_MODEL_ANALYZER=openai/gpt-4o-mini

# And Anthropic for complex reflection
DOCKAI_MODEL_REFLECTOR=anthropic/claude-sonnet-4-20250514
```

**Supported prefixes**:
- `openai/`
- `azure/`
- `gemini/`
- `anthropic/`
- `ollama/`

**Use cases**:
- Use local Ollama for most tasks, cloud for complex reasoning
- Use organization's Azure OpenAI for compliance, OpenAI for better models
- Use free Gemini tier for simple tasks, paid OpenAI for generation

---

## Workflow Settings

### Retry Configuration

| Variable | Description | Default | Recommendation |
|----------|-------------|---------|----------------|
| `MAX_RETRIES` | Maximum validation retry attempts | `3` | Increase for complex projects |

**Why retries matter**: Most projects don't work on the first try. The retry mechanism is a key differentiator—DockAI learns from failures.

```bash
# For simple projects
MAX_RETRIES=2

# For complex projects with unusual requirements
MAX_RETRIES=5

# For debugging (see what happens without retries)
MAX_RETRIES=1
```

---

## Security & Validation Settings

### Linting & Security Scanning

| Variable | Description | Default | When to Change |
|----------|-------------|---------|----------------|
| `DOCKAI_SKIP_HADOLINT` | Skip Hadolint Dockerfile linting | `false` | When Hadolint not available |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy vulnerability scan | `false` | For faster iteration, non-production |
| `DOCKAI_STRICT_SECURITY` | Fail on ANY vulnerability | `false` | Production environments |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Maximum allowed image size | `500` | Enforce size limits |
| `DOCKAI_SKIP_HEALTH_CHECK` | Skip health endpoint verification | `false` | For scripts, not services |

### Why These Matter

**Hadolint**: Catches Dockerfile anti-patterns like:
- Using `latest` tag
- Missing `--no-cache` flags
- Inefficient layer ordering

**Trivy**: Scans the built image for:
- Known CVEs in base image
- Vulnerable packages
- Exposed secrets

**Strict Security**: In production, you probably want to fail if vulnerabilities are found rather than just warning.

### Validation Resource Limits

| Variable | Description | Default | When to Change |
|----------|-------------|---------|----------------|
| `DOCKAI_VALIDATION_MEMORY` | Memory limit for test container | `512m` | Large apps need more |
| `DOCKAI_VALIDATION_CPUS` | CPU limit for test container | `1.0` | Heavy computation |
| `DOCKAI_VALIDATION_PIDS` | Process limit for test container | `100` | Fork-heavy apps |

**Why resource limits?** Validation runs untrusted containers (the generated Dockerfile could do anything). Limits prevent:
- Runaway memory usage
- CPU hogging
- Fork bombs

```bash
# For Java/JVM applications (need more memory)
DOCKAI_VALIDATION_MEMORY=1g

# For build-heavy projects
DOCKAI_VALIDATION_CPUS=2.0
```

### File Analysis Settings

| Variable | Description | Default | When to Change |
|----------|-------------|---------|----------------|
| `DOCKAI_TRUNCATION_ENABLED` | Always truncate large files | `false` | Large monorepos |
| `DOCKAI_TOKEN_LIMIT` | Token limit triggering auto-truncation | `100000` | Adjust for model context |
| `DOCKAI_MAX_FILE_CHARS` | Max characters per file when truncating | `200000` | Fine-tune truncation |
| `DOCKAI_MAX_FILE_LINES` | Max lines per file when truncating | `5000` | Fine-tune truncation |

**How truncation works**:
1. By default, files are read in full
2. If total content exceeds `DOCKAI_TOKEN_LIMIT`, truncation auto-enables
3. Truncation keeps the beginning and end of files (most important parts)

**Token estimation**: Approximately 1 token ≈ 4 characters

```bash
# For large monorepos
DOCKAI_TRUNCATION_ENABLED=true
DOCKAI_MAX_FILE_CHARS=50000

# For projects with large generated files
DOCKAI_MAX_FILE_LINES=1000
```

---

## Observability & Tracing

DockAI supports **OpenTelemetry** for distributed tracing. This is invaluable for:
- Debugging slow runs
- Understanding token usage patterns
- Integrating with observability platforms

### Tracing Configuration

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `DOCKAI_ENABLE_TRACING` | Enable OpenTelemetry tracing | `false` | `true`/`false` |
| `DOCKAI_TRACING_EXPORTER` | Where to send traces | `console` | `console`, `otlp` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL | `http://localhost:4317` | Your collector |
| `OTEL_SERVICE_NAME` | Service name in traces | `dockai` | Custom name |

### What Gets Traced

When tracing is enabled, spans are created for:

| Span | Attributes | Purpose |
|------|------------|---------|
| `dockai.workflow` | Total duration, success/failure | Overall workflow |
| `node.scan` | `files_found`, `path` | File discovery |
| `node.analyze` | `stack`, `project_type` | Stack detection |
| `node.plan` | `retry_count` | Strategy planning |
| `node.generate` | `retry_count`, `project_type` | Dockerfile generation |
| `node.review` | `is_secure`, `issues_count` | Security review |
| `node.validate` | `success`, `error`, `image_size_mb` | Validation |
| `node.reflect` | `root_cause`, `confidence` | Failure analysis |

### Console Tracing (Debugging)

For local debugging, console tracing prints spans to stdout:

```bash
DOCKAI_ENABLE_TRACING=true
DOCKAI_TRACING_EXPORTER=console
dockai build .
```

### OTLP Export (Production)

For production observability, export to your collector:

```bash
# Jaeger
DOCKAI_ENABLE_TRACING=true
DOCKAI_TRACING_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Grafana Tempo
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317

# Datadog (with OTLP collector)
OTEL_EXPORTER_OTLP_ENDPOINT=http://datadog-agent:4317
```

---

## Custom Instructions

Instructions are **appended** to default prompts. This is the recommended way to customize agent behavior.

### Why Instructions (Not Prompts)?

- ✅ **Preserve base intelligence**: DockAI's prompts are carefully crafted
- ✅ **Additive**: Add your context without removing existing guidance
- ✅ **Maintainable**: Survives DockAI updates
- ✅ **Safe**: Can't accidentally break core functionality

### Instruction Variables

| Variable | Agent | What to Include |
|----------|-------|-----------------|
| `DOCKAI_ANALYZER_INSTRUCTIONS` | Analyzer | Internal frameworks, project conventions |
| `DOCKAI_PLANNER_INSTRUCTIONS` | Planner | Approved base images, build strategies |
| `DOCKAI_GENERATOR_INSTRUCTIONS` | Generator | Required labels, ENV vars, conventions |
| `DOCKAI_GENERATOR_ITERATIVE_INSTRUCTIONS` | Iterative Generator | Debug strategies |
| `DOCKAI_REVIEWER_INSTRUCTIONS` | Reviewer | Compliance requirements, policies |
| `DOCKAI_REFLECTOR_INSTRUCTIONS` | Reflector | Known issues and fixes |
| `DOCKAI_HEALTH_DETECTOR_INSTRUCTIONS` | Health Detector | Health endpoint conventions |
| `DOCKAI_READINESS_DETECTOR_INSTRUCTIONS` | Readiness Detector | Startup patterns |
| `DOCKAI_ERROR_ANALYZER_INSTRUCTIONS` | Error Analyzer | Common error patterns |
| `DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS` | Iterative Improver | Fix strategies |

### Example Instructions

```bash
# Organization standards for generator
DOCKAI_GENERATOR_INSTRUCTIONS="
REQUIRED LABELS (always include):
- LABEL org.company.team=\${TEAM}
- LABEL org.company.version=\${VERSION}

CONVENTIONS:
- Use /app as WORKDIR
- Create non-root user with UID 10000
- Always use multi-stage builds
"

# Known issues for reflector
DOCKAI_REFLECTOR_INSTRUCTIONS="
KNOWN ISSUES IN OUR STACK:
- 'pg_config not found': Install postgresql-dev (Alpine) or libpq-dev (Debian)
- 'GLIBC not found' on Alpine: Use Debian-based image or install gcompat
"
```

---

## Custom Prompts (Advanced)

Prompts **completely replace** the default prompt. Use only when you need full control.

### ⚠️ Warning

Custom prompts:
- Override all default behavior
- Must handle all edge cases yourself
- May break with DockAI updates
- Require deep understanding of the agent's role

### Prompt Variables

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

### When Custom Prompts Make Sense

- Industry-specific compliance (PCI-DSS, HIPAA)
- Highly specialized internal frameworks
- Complete organizational override of behavior
- Research and experimentation

---

## The .dockai File

The `.dockai` file provides repository-specific configuration that can be version controlled.

### File Location

Create `.dockai` in your project root:

```
my-project/
├── .dockai           ← Configuration file
├── app.py
├── requirements.txt
└── ...
```

### Basic Structure

```ini
# Instructions are appended to defaults
[instructions_analyzer]
Your instructions here...

[instructions_generator]
Your instructions here...

# Prompts replace defaults entirely (advanced)
[prompt_analyzer]
Complete prompt replacement...
```

### Complete Example

```ini
# ============================================================
# DockAI Configuration for Django Microservice
# ============================================================

# Help the analyzer understand our stack
[instructions_analyzer]
This is a Django application with:
- Celery for background tasks (uses Redis broker)
- PostgreSQL database (requires psycopg2)
- Poetry for dependency management
- Gunicorn as the WSGI server

Project structure:
- /src contains the Django app
- /scripts contains entrypoint scripts
- /config contains configuration files

# Guide the strategic planning
[instructions_planner]
REQUIREMENTS:
- Use our approved base image: company-registry.io/python:3.11-slim
- Multi-stage build is mandatory for production
- Final image should be under 500MB

BUILD CONSIDERATIONS:
- Poetry export to requirements.txt for pip install
- Collect static files during build
- Do NOT include dev dependencies in final image

# Dockerfile generation guidance
[instructions_generator]
REQUIRED ELEMENTS:
- LABEL maintainer="platform-team@company.io"
- ENV DJANGO_SETTINGS_MODULE=config.settings.production
- Run migrations in entrypoint, not Dockerfile
- Include our standard entrypoint from /scripts/docker-entrypoint.sh

CONVENTIONS:
- WORKDIR /app
- Non-root user: appuser with UID 10000
- EXPOSE 8000 for HTTP

# Security requirements (we're SOC 2 compliant)
[instructions_reviewer]
MANDATORY SECURITY CHECKS:
- Container MUST run as non-root (UID >= 10000)
- No secrets, passwords, or API keys in Dockerfile
- No curl/wget in final image (attack surface)
- Base image must be pinned to SHA256 digest

COMPLIANCE:
- Fail on any CRITICAL or HIGH CVE
- All packages from approved sources only

# Common issues we've encountered
[instructions_reflector]
KNOWN ISSUES AND SOLUTIONS:

1. "pg_config executable not found"
   Cause: psycopg2 needs PostgreSQL headers to compile
   Solution: Install libpq-dev in build stage, use psycopg2-binary for simpler builds

2. "Error: static files not found"
   Cause: collectstatic not run during build
   Solution: Run python manage.py collectstatic --noinput

3. "Permission denied: /app/logs"
   Cause: Log directory not writable by non-root user
   Solution: Create /app/logs and chown to appuser

4. "Database connection refused"
   Cause: Migration running before DB is ready
   Solution: Use wait-for-it.sh or similar in entrypoint

# Our health endpoint convention
[instructions_health_detector]
Our services expose:
- Health: /api/health/ (GET, returns 200 with {"status": "healthy"})
- Readiness: /api/ready/ (GET, returns 200 when DB connected)
- Port: Always 8000 for HTTP

Django health check uses django-health-check package.

# Startup patterns for our Django apps
[instructions_readiness_detector]
Gunicorn startup patterns:
- Success: "Booting worker with pid" or "Listening at: http://0.0.0.0:8000"
- Failure: "Error:" or "ModuleNotFoundError"

Typical startup time: 10-15 seconds (includes migration check)
```

---

## Configuration Precedence

Understanding precedence helps avoid confusion when settings seem to not apply.

### Full Precedence Chain

```
┌─────────────────────────────────────────────────────────────────┐
│ Priority 1: Environment Variables                                │
│ (Set in shell, CI/CD, or .env file)                             │
│                                                                  │
│ DOCKAI_GENERATOR_INSTRUCTIONS="Use Debian"                      │
├─────────────────────────────────────────────────────────────────┤
│ Priority 2: .dockai File                                         │
│ (In repository root)                                             │
│                                                                  │
│ [instructions_generator]                                         │
│ Use Alpine base images                                           │
├─────────────────────────────────────────────────────────────────┤
│ Priority 3: Built-in Defaults                                    │
│ (In DockAI source code)                                          │
│                                                                  │
│ Default prompt templates                                         │
└─────────────────────────────────────────────────────────────────┘

Result: "Use Debian" is used (env var has highest priority)
```

### Combining Instructions

Instructions from different sources are combined:

```bash
# Environment variable
export DOCKAI_GENERATOR_INSTRUCTIONS="Use multi-stage builds"

# .dockai file
[instructions_generator]
Use non-root user
```

Both instructions are sent to the agent—they don't override each other.

---

## Complete Examples

### Minimal Configuration

For quick testing:

```bash
# .env
OPENAI_API_KEY=sk-your-api-key-here
```

### Cost-Optimized Configuration

For production with cost management:

```bash
# .env
DOCKAI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key

# Use fast models for simple tasks
DOCKAI_MODEL_ANALYZER=gpt-4o-mini
DOCKAI_MODEL_PLANNER=gpt-4o-mini
DOCKAI_MODEL_REVIEWER=gpt-4o-mini
DOCKAI_MODEL_HEALTH_DETECTOR=gpt-4o-mini
DOCKAI_MODEL_READINESS_DETECTOR=gpt-4o-mini
DOCKAI_MODEL_ERROR_ANALYZER=gpt-4o-mini

# Use powerful models where it matters
DOCKAI_MODEL_GENERATOR=gpt-4o
DOCKAI_MODEL_GENERATOR_ITERATIVE=gpt-4o
DOCKAI_MODEL_REFLECTOR=gpt-4o
DOCKAI_MODEL_ITERATIVE_IMPROVER=gpt-4o
```

### Security-Focused Configuration

For production environments:

```bash
# .env
DOCKAI_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Strict security
DOCKAI_STRICT_SECURITY=true
DOCKAI_MAX_IMAGE_SIZE_MB=300

# Don't skip any scans
DOCKAI_SKIP_HADOLINT=false
DOCKAI_SKIP_SECURITY_SCAN=false

# More retries for complex compliance requirements
MAX_RETRIES=5
```

### Privacy-Focused Configuration

For sensitive codebases:

```bash
# .env
DOCKAI_LLM_PROVIDER=ollama

# Local model
DOCKAI_MODEL_GENERATOR=llama3
DOCKAI_MODEL_REFLECTOR=llama3

# Skip external registry validation (may need local images)
# (not currently a setting, but could add custom instructions)
```

### CI/CD Configuration (GitHub Actions)

```yaml
# .github/workflows/dockai.yml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    
    # Cost optimization
    model_analyzer: gpt-4o-mini
    model_generator: gpt-4o
    
    # Security
    strict_security: 'true'
    max_image_size_mb: '400'
    
    # Custom instructions from secrets
    generator_instructions: ${{ secrets.DOCKAI_GENERATOR_INSTRUCTIONS }}
```

---

## Next Steps

- **[Customization Guide](./customization.md)**: Strategies for effective customization
- **[GitHub Actions](./github-actions.md)**: CI/CD integration with full examples
- **[MCP Server](./mcp-server.md)**: AI assistant integration
- **[Architecture](./architecture.md)**: Understand why these options exist
