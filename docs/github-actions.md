# GitHub Actions Integration

Complete guide for using DockAI in CI/CD pipelines with GitHub Actions.

---

## Quick Start

Create `.github/workflows/dockai.yml`:

```yaml
name: Auto-Dockerize with DockAI

on:
  push:
    branches: [main]

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run DockAI
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

---

## Action Reference

### Basic Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `project_path` | Path to project root | No | `.` |
| `llm_provider` | LLM provider | No | `openai` |

### API Key Inputs

| Input | Provider | Required |
|-------|----------|----------|
| `openai_api_key` | OpenAI | If using OpenAI |
| `azure_openai_api_key` | Azure | If using Azure |
| `azure_openai_endpoint` | Azure | If using Azure |
| `azure_openai_api_version` | Azure | No |
| `google_api_key` | Gemini | If using Gemini |
| `anthropic_api_key` | Anthropic | If using Anthropic |

### Model Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `model_analyzer` | Model for analyzer | Provider default |
| `model_planner` | Model for planner | Provider default |
| `model_generator` | Model for generator | Provider default |
| `model_generator_iterative` | Model for iterative generator | Provider default |
| `model_reviewer` | Model for reviewer | Provider default |
| `model_reflector` | Model for reflector | Provider default |
| `model_health_detector` | Model for health detector | Provider default |
| `model_readiness_detector` | Model for readiness detector | Provider default |
| `model_error_analyzer` | Model for error analyzer | Provider default |
| `model_iterative_improver` | Model for iterative improver | Provider default |

### Workflow Settings

| Input | Description | Default |
|-------|-------------|---------|
| `max_retries` | Maximum retry attempts | `3` |

### Validation Settings

| Input | Description | Default |
|-------|-------------|---------|
| `skip_security_scan` | Skip Trivy scanning | `false` |
| `strict_security` | Fail on any vulnerability | `false` |
| `max_image_size_mb` | Max image size (0 = disabled) | `500` |
| `skip_health_check` | Skip health endpoint checks | `false` |
| `validation_memory` | Memory limit for validation | `512m` |
| `validation_cpus` | CPU limit for validation | `1.0` |
| `validation_pids` | Process limit for validation | `100` |
| `max_file_chars` | Max characters per file | `200000` |
| `max_file_lines` | Max lines per file | `5000` |

### Custom Instructions

| Input | Description |
|-------|-------------|
| `analyzer_instructions` | Guide project analysis |
| `planner_instructions` | Guide strategic planning |
| `generator_instructions` | Guide Dockerfile creation |
| `generator_iterative_instructions` | Guide iterative generation |
| `reviewer_instructions` | Guide security review |
| `reflector_instructions` | Guide failure analysis |
| `health_detector_instructions` | Guide health detection |
| `readiness_detector_instructions` | Guide readiness detection |
| `error_analyzer_instructions` | Guide error classification |
| `iterative_improver_instructions` | Guide fix application |

### Custom Prompts (Advanced)

| Input | Description |
|-------|-------------|
| `prompt_analyzer` | Replace analyzer prompt |
| `prompt_planner` | Replace planner prompt |
| `prompt_generator` | Replace generator prompt |
| `prompt_generator_iterative` | Replace iterative generator |
| `prompt_reviewer` | Replace reviewer prompt |
| `prompt_reflector` | Replace reflector prompt |
| `prompt_health_detector` | Replace health detector |
| `prompt_readiness_detector` | Replace readiness detector |
| `prompt_error_analyzer` | Replace error analyzer |
| `prompt_iterative_improver` | Replace iterative improver |

---

## Usage Examples

### Basic OpenAI

```yaml
- uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Google Gemini

```yaml
- uses: itzzjb/dockai@v2
  with:
    llm_provider: gemini
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
```

### Anthropic Claude

```yaml
- uses: itzzjb/dockai@v2
  with:
    llm_provider: anthropic
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Azure OpenAI

```yaml
- uses: itzzjb/dockai@v2
  with:
    llm_provider: azure
    azure_openai_api_key: ${{ secrets.AZURE_OPENAI_API_KEY }}
    azure_openai_endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
```

### Cost-Optimized Configuration

Use faster models for simple tasks:

```yaml
- uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    model_analyzer: gpt-4o-mini
    model_planner: gpt-4o-mini
    model_generator: gpt-4o
    model_reviewer: gpt-4o-mini
    model_reflector: gpt-4o
```

### Strict Security

Fail on any security vulnerability:

```yaml
- uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: 'true'
    max_image_size_mb: '300'
```

### Custom Instructions

```yaml
- uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    generator_instructions: |
      Use multi-stage builds for all projects.
      Final image must use non-root user with UID 10000.
      Always include HEALTHCHECK instruction.
    reviewer_instructions: |
      Fail if running as root.
      Check for hardcoded secrets.
```

### High Retry Count

For complex projects that may need multiple attempts:

```yaml
- uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_retries: '5'
    validation_memory: '1g'
    validation_cpus: '2.0'
```

---

## Complete Workflow Examples

### Basic CI/CD

```yaml
name: Docker Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name == 'push' }}
          tags: myregistry/myapp:${{ github.sha }}
```

### With Container Registry

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          strict_security: 'true'
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### Monorepo with Multiple Services

```yaml
name: Build Services

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, worker, frontend]
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile for ${{ matrix.service }}
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: services/${{ matrix.service }}
```

### Scheduled Dockerfile Updates

```yaml
name: Weekly Dockerfile Update

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Regenerate Dockerfile
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          strict_security: 'true'
      
      - name: Create PR if changed
        uses: peter-evans/create-pull-request@v5
        with:
          title: 'chore: Update Dockerfile'
          commit-message: 'chore: Regenerate Dockerfile with DockAI'
          branch: dockerfile-update
```

---

## Organization-Level Configuration

### Reusable Workflow

Create `.github/workflows/dockai-template.yml` in your org's `.github` repo:

```yaml
name: DockAI Template

on:
  workflow_call:
    inputs:
      project_path:
        required: false
        type: string
        default: '.'
    secrets:
      OPENAI_API_KEY:
        required: true

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: ${{ inputs.project_path }}
          # Organization defaults
          strict_security: 'true'
          generator_instructions: |
            Use only approved base images from company-registry.io
            All containers must run as non-root
```

Use in your repos:

```yaml
name: Build

on: [push]

jobs:
  dockai:
    uses: your-org/.github/.github/workflows/dockai-template.yml@main
    secrets:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Organization Secrets

Set these at the organization level:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `DOCKAI_GENERATOR_INSTRUCTIONS` | Default generator instructions |
| `DOCKAI_REVIEWER_INSTRUCTIONS` | Default reviewer instructions |

---

## Troubleshooting

### "API key not found"

Ensure your secret is set correctly:

1. Go to Repository Settings → Secrets → Actions
2. Add `OPENAI_API_KEY` (or your provider's key)
3. Reference as `${{ secrets.OPENAI_API_KEY }}`

### "Build failed after max retries"

Increase retries and resources:

```yaml
max_retries: '5'
validation_memory: '1g'
validation_cpus: '2.0'
```

### "Docker build timeout"

The GitHub-hosted runner has limited resources. Consider:

1. Using self-hosted runners for large images
2. Enabling `skip_security_scan` to skip Trivy
3. Adding custom instructions for optimization

### "Permission denied"

Ensure the workflow has write permissions:

```yaml
permissions:
  contents: write
```

---

## Next Steps

- **[Configuration](./configuration.md)**: All configuration options
- **[Customization](./customization.md)**: Fine-tune for your stack
- **[Platform Integration](./platform-integration.md)**: Embedding DockAI
