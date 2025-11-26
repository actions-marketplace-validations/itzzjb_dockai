# Configuration Reference

This document covers all configuration options available in DockAI.

## Configuration Methods

DockAI supports configuration through:

1. **Environment Variables** — Global or CI/CD settings
2. **`.env` File** — Local development settings
3. **`.dockai` File** — Per-repository customization

Priority order (highest to lowest):
1. Environment variables
2. `.dockai` file
3. Built-in defaults

## Core Settings

### API Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes (if using OpenAI) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | - | Yes (if using Azure) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | - | Yes (if using Azure) |
| `GOOGLE_API_KEY` | Google Gemini API key | - | Yes (if using Gemini) |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | Yes (if using Anthropic) |

### LLM Provider Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_LLM_PROVIDER` | LLM provider (`openai`, `azure`, `gemini`, `anthropic`) | `openai` |
| `AZURE_OPENAI_API_VERSION` | Azure API version | `2024-02-15-preview` |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | - |

### Per-Agent Model Configuration

Each agent can use a different model for cost optimization:

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

### Workflow Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_RETRIES` | Maximum retry attempts | `3` |

## Validation Settings

### Security Scanning

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy vulnerability scan | `false` |
| `DOCKAI_STRICT_SECURITY` | Fail on any vulnerability | `false` |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Maximum image size (0 = disabled) | `500` |
| `DOCKAI_SKIP_HEALTH_CHECK` | Skip health endpoint checks | `false` |

### Resource Limits (Sandbox)

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKAI_VALIDATION_MEMORY` | Memory limit for validation | `512m` |
| `DOCKAI_VALIDATION_CPUS` | CPU limit for validation | `1.0` |
| `DOCKAI_VALIDATION_PIDS` | Process limit for validation | `100` |

## Custom Instructions

Instructions are **appended** to default prompts to guide AI reasoning:

| Variable | Description |
|----------|-------------|
| `DOCKAI_ANALYZER_INSTRUCTIONS` | Guide project analysis |
| `DOCKAI_PLANNER_INSTRUCTIONS` | Guide strategic planning |
| `DOCKAI_GENERATOR_INSTRUCTIONS` | Guide Dockerfile creation |
| `DOCKAI_GENERATOR_ITERATIVE_INSTRUCTIONS` | Guide iterative fixes |
| `DOCKAI_REVIEWER_INSTRUCTIONS` | Guide security review |
| `DOCKAI_REFLECTOR_INSTRUCTIONS` | Guide failure analysis |
| `DOCKAI_HEALTH_DETECTOR_INSTRUCTIONS` | Guide health detection |
| `DOCKAI_READINESS_DETECTOR_INSTRUCTIONS` | Guide readiness detection |
| `DOCKAI_ERROR_ANALYZER_INSTRUCTIONS` | Guide error classification |
| `DOCKAI_ITERATIVE_IMPROVER_INSTRUCTIONS` | Guide fix application |

## Custom Prompts (Advanced)

Prompts **completely replace** the default prompt for full control:

| Variable | Description |
|----------|-------------|
| `DOCKAI_PROMPT_ANALYZER` | Replace analyzer prompt |
| `DOCKAI_PROMPT_PLANNER` | Replace planner prompt |
| `DOCKAI_PROMPT_GENERATOR` | Replace generator prompt |
| `DOCKAI_PROMPT_GENERATOR_ITERATIVE` | Replace iterative generator prompt |
| `DOCKAI_PROMPT_REVIEWER` | Replace reviewer prompt |
| `DOCKAI_PROMPT_REFLECTOR` | Replace reflector prompt |
| `DOCKAI_PROMPT_HEALTH_DETECTOR` | Replace health detector prompt |
| `DOCKAI_PROMPT_READINESS_DETECTOR` | Replace readiness detector prompt |
| `DOCKAI_PROMPT_ERROR_ANALYZER` | Replace error analyzer prompt |
| `DOCKAI_PROMPT_ITERATIVE_IMPROVER` | Replace iterative improver prompt |

## `.dockai` File Format

Create a `.dockai` file in your project root for per-repository configuration:

```ini
# Instructions (appended to defaults)
[instructions_analyzer]
This is a Django application with Celery workers.
Dependencies are managed with Poetry.

[instructions_generator]
Use gunicorn as the WSGI server.
Run database migrations at container start.

[instructions_planner]
Use our approved base images from company-registry.io

[instructions_reviewer]
All containers must run as non-root (UID >= 10000).
Check for hardcoded API keys.

[instructions_reflector]
Common issue: missing libpq for psycopg2.

[instructions_health_detector]
Our health endpoint is at /api/v1/health/

[instructions_readiness_detector]
Look for "Application startup complete" in logs.

# Full prompt replacements (advanced)
[prompt_analyzer]
You are a specialized analyzer for Python web applications...

[prompt_reviewer]
You are a security expert focusing on container hardening...
```

### Legacy Format Support

The legacy `[analyzer]` and `[generator]` sections are still supported:

```ini
[analyzer]
Focus on microservices architecture.

[generator]
Use Alpine-based images where possible.
```

## Example Configurations

### Minimal Configuration

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
```

### Development Configuration

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
MAX_RETRIES=5
DOCKAI_SKIP_SECURITY_SCAN=true
```

### Production Configuration

```bash
# .env or CI/CD secrets
OPENAI_API_KEY=sk-your-key-here
DOCKAI_LLM_PROVIDER=openai
DOCKAI_MODEL_GENERATOR=gpt-4o
DOCKAI_MODEL_ANALYZER=gpt-4o-mini
MAX_RETRIES=3
DOCKAI_STRICT_SECURITY=true
DOCKAI_MAX_IMAGE_SIZE_MB=300
```

### Azure OpenAI Configuration

```bash
# .env
DOCKAI_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
DOCKAI_MODEL_ANALYZER=gpt-4o-mini
DOCKAI_MODEL_GENERATOR=gpt-4o
```

### Google Gemini Configuration

```bash
# .env
DOCKAI_LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-key
DOCKAI_MODEL_ANALYZER=gemini-1.5-flash
DOCKAI_MODEL_GENERATOR=gemini-1.5-pro
```

### Anthropic Configuration

```bash
# .env
DOCKAI_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-key
DOCKAI_MODEL_ANALYZER=claude-3-5-haiku-latest
DOCKAI_MODEL_GENERATOR=claude-sonnet-4-20250514
```

## Configuration Precedence

When the same setting is defined in multiple places:

1. **Environment Variable** — Highest priority
2. **`.dockai` file** — Repository-specific
3. **Default value** — Built-in fallback

Example: If `DOCKAI_ANALYZER_INSTRUCTIONS` is set as an environment variable AND in `.dockai`, the environment variable takes precedence.

## Next Steps

- **[Customization](./customization.md)** — Fine-tuning strategies
- **[GitHub Actions](./github-actions.md)** — CI/CD configuration
- **[API Reference](./api-reference.md)** — Programmatic usage
