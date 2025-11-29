# GitHub Actions Integration

This guide provides comprehensive documentation for using DockAI in CI/CD pipelines with GitHub Actions. Learn how to automate Dockerfile generation, customize behavior for your organization, and integrate with your deployment workflows.

---

## 📋 Table of Contents

1. [Why Use DockAI in CI/CD?](#why-use-dockai-in-cicd)
2. [Quick Start](#quick-start)
3. [Action Reference](#action-reference)
4. [Usage Examples](#usage-examples)
5. [Complete Workflow Examples](#complete-workflow-examples)
6. [Organization-Level Configuration](#organization-level-configuration)
7. [Committing Generated Dockerfile](#committing-generated-dockerfile)
8. [Advanced Patterns](#advanced-patterns)
9. [Troubleshooting](#troubleshooting)

---

## Why Use DockAI in CI/CD?

### Benefits of Automated Dockerfile Generation

| Benefit | Description |
|---------|-------------|
| **Consistency** | Every build uses the same generation process |
| **Up-to-date** | Dockerfiles are regenerated when dependencies change |
| **Security** | Automatic scanning catches vulnerabilities early |
| **Compliance** | Organization standards are enforced automatically |
| **Documentation** | Generated Dockerfiles can be committed for review |

### When to Use GitHub Actions

- **Pull Requests**: Validate that a Dockerfile can be generated
- **Main Branch**: Generate production Dockerfiles
- **Scheduled**: Weekly regeneration to pick up security fixes
- **Manual**: On-demand generation for specific projects

---

## Quick Start

### Minimal Setup

Create `.github/workflows/dockai.yml`:

```yaml
name: Generate Dockerfile with DockAI

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### What This Does

1. Checks out your repository
2. Runs DockAI with default settings
3. Generates `Dockerfile` in your repository root
4. Validates the Dockerfile by building it
5. Runs security scanning

The Dockerfile is generated at runtime but not committed by default. See [Committing Generated Dockerfile](#committing-generated-dockerfile) to save it.

---

## Action Reference

### Basic Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `project_path` | Path to project root relative to repository | No | `.` |
| `llm_provider` | LLM provider to use | No | `openai` |

### API Key Inputs

You need to provide the API key for your chosen provider:

| Input | Provider | When Required |
|-------|----------|---------------|
| `openai_api_key` | OpenAI | If `llm_provider=openai` |
| `azure_openai_api_key` | Azure OpenAI | If `llm_provider=azure` |
| `azure_openai_endpoint` | Azure OpenAI | If `llm_provider=azure` |
| `azure_openai_api_version` | Azure OpenAI | Optional, has default |
| `google_api_key` | Google Gemini | If `llm_provider=gemini` |
| `anthropic_api_key` | Anthropic | If `llm_provider=anthropic` |

**Ollama Note**: Ollama doesn't require an API key but needs Docker (available on GitHub runners) or a local installation.

### Model Configuration

Assign different models to different agents for cost optimization:

| Input | Agent | Default |
|-------|-------|---------|
| `model_analyzer` | Project analyzer | Provider default (fast) |
| `model_planner` | Strategic planner | Provider default (fast) |
| `model_generator` | Dockerfile generator | Provider default (powerful) |
| `model_generator_iterative` | Iterative fixes | Provider default (powerful) |
| `model_reviewer` | Security reviewer | Provider default (fast) |
| `model_reflector` | Failure analyzer | Provider default (powerful) |
| `model_health_detector` | Health endpoint finder | Provider default (fast) |
| `model_readiness_detector` | Startup pattern finder | Provider default (fast) |
| `model_error_analyzer` | Error classifier | Provider default (fast) |
| `model_iterative_improver` | Fix applier | Provider default (powerful) |

### Workflow Settings

| Input | Description | Default |
|-------|-------------|---------|
| `max_retries` | Maximum retry attempts on failure | `3` |

### Validation Settings

| Input | Description | Default |
|-------|-------------|---------|
| `skip_hadolint` | Skip Hadolint Dockerfile linting | `false` |
| `skip_security_scan` | Skip Trivy vulnerability scanning | `false` |
| `strict_security` | Fail on ANY vulnerability | `false` |
| `max_image_size_mb` | Maximum allowed image size (0=disabled) | `500` |
| `skip_health_check` | Skip health endpoint verification | `false` |
| `validation_memory` | Memory limit for validation container | `512m` |
| `validation_cpus` | CPU limit for validation container | `1.0` |
| `validation_pids` | Process limit for validation container | `100` |
| `max_file_chars` | Max characters per file to read | `200000` |
| `max_file_lines` | Max lines per file to read | `5000` |

### Observability Settings

| Input | Description | Default |
|-------|-------------|---------|
| `enable_tracing` | Enable OpenTelemetry tracing | `false` |
| `tracing_exporter` | Exporter type (`console` or `otlp`) | `console` |
| `otlp_endpoint` | OTLP endpoint for trace export | `http://localhost:4317` |

### Custom Instructions

Add guidance for specific agents (appended to default prompts):

| Input | Agent |
|-------|-------|
| `analyzer_instructions` | Guide project analysis |
| `planner_instructions` | Guide build strategy |
| `generator_instructions` | Guide Dockerfile creation |
| `generator_iterative_instructions` | Guide iterative fixes |
| `reviewer_instructions` | Guide security review |
| `reflector_instructions` | Guide failure analysis |
| `health_detector_instructions` | Guide health detection |
| `readiness_detector_instructions` | Guide readiness detection |
| `error_analyzer_instructions` | Guide error classification |
| `iterative_improver_instructions` | Guide fix application |

### Custom Prompts (Advanced)

Completely replace default prompts (use with caution):

| Input | Agent |
|-------|-------|
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
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Google Gemini (Free Tier Available)

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: gemini
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
```

### Anthropic Claude

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: anthropic
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Azure OpenAI (Enterprise)

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: azure
    azure_openai_api_key: ${{ secrets.AZURE_OPENAI_API_KEY }}
    azure_openai_endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
    azure_openai_api_version: '2024-02-15-preview'
```

### Ollama (Local, Free)

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: ollama
    # No API key needed - uses Docker-based Ollama
```

### Cost-Optimized Configuration

Use cheaper/faster models for simple tasks:

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    # Fast models for simple tasks
    model_analyzer: gpt-4o-mini
    model_planner: gpt-4o-mini
    model_reviewer: gpt-4o-mini
    model_health_detector: gpt-4o-mini
    model_readiness_detector: gpt-4o-mini
    model_error_analyzer: gpt-4o-mini
    # Powerful models where it matters
    model_generator: gpt-4o
    model_generator_iterative: gpt-4o
    model_reflector: gpt-4o
    model_iterative_improver: gpt-4o
```

### Strict Security Mode

Fail on any security vulnerability:

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: 'true'
    max_image_size_mb: '300'  # Also enforce size limits
```

### With Custom Instructions

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    generator_instructions: |
      REQUIREMENTS:
      - Use multi-stage builds for all projects
      - Final image must use non-root user with UID 10000
      - Always include HEALTHCHECK instruction
      - Use only approved base images from company-registry.io
    reviewer_instructions: |
      SECURITY POLICY:
      - Fail if running as root
      - Fail if any hardcoded secrets detected
      - Warn on :latest tags
```

### High Retry Count for Complex Projects

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_retries: '5'
    validation_memory: '1g'  # More memory for large builds
    validation_cpus: '2.0'   # More CPU for faster builds
```

### With OpenTelemetry Tracing

For debugging and observability:

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    enable_tracing: 'true'
    tracing_exporter: 'console'  # Prints to logs
```

For production (export to Jaeger/Tempo/etc.):

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    enable_tracing: 'true'
    tracing_exporter: 'otlp'
    otlp_endpoint: 'http://jaeger:4317'
```

---

## Complete Workflow Examples

### Basic CI/CD Pipeline

Generate Dockerfile and build image on every push:

```yaml
name: Docker Build

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  generate-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false  # Just build, don't push
          tags: myapp:${{ github.sha }}
```

### Build and Push to Container Registry

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write  # For GHCR
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          strict_security: 'true'  # Fail on vulnerabilities
      
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
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            api:
              - 'services/api/**'
            worker:
              - 'services/worker/**'
            frontend:
              - 'services/frontend/**'

  build:
    needs: detect-changes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile for ${{ matrix.service }}
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: services/${{ matrix.service }}
      
      - name: Build ${{ matrix.service }}
        run: |
          docker build -t myapp-${{ matrix.service }}:${{ github.sha }} services/${{ matrix.service }}
```

### Scheduled Weekly Updates

Regenerate Dockerfiles weekly to pick up security fixes:

```yaml
name: Weekly Dockerfile Update

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at midnight
  workflow_dispatch:  # Allow manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Regenerate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          strict_security: 'true'
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'chore: regenerate Dockerfile with DockAI'
          title: 'chore: Weekly Dockerfile Update'
          body: |
            ## Automated Dockerfile Update
            
            This PR regenerates the Dockerfile using the latest DockAI version.
            
            Changes may include:
            - Updated base image versions
            - Security improvements
            - Dependency updates
            
            Please review before merging.
          branch: dockerfile-update
          delete-branch: true
```

### PR Validation Only

Check that a Dockerfile CAN be generated without committing:

```yaml
name: Validate Dockerfile Generation

on:
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Dockerfile Can Be Generated
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Dockerfile generated and validated successfully!'
            })
```

---

## Organization-Level Configuration

### Reusable Workflow

Create a shared workflow in your organization's `.github` repository:

```yaml
# .github/.github/workflows/dockai-template.yml
name: DockAI Template

on:
  workflow_call:
    inputs:
      project_path:
        required: false
        type: string
        default: '.'
      strict_security:
        required: false
        type: boolean
        default: true
    secrets:
      OPENAI_API_KEY:
        required: true

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: ${{ inputs.project_path }}
          strict_security: ${{ inputs.strict_security }}
          # Organization-wide standards
          generator_instructions: |
            ORGANIZATION REQUIREMENTS:
            - Use only approved base images from company-registry.io
            - All containers must run as non-root (UID 10000)
            - Include standard labels for tracking
          reviewer_instructions: |
            SECURITY POLICY:
            - Fail on any CRITICAL vulnerability
            - Fail if running as root
            - Fail if secrets detected
```

Use in individual repositories:

```yaml
# In your repository's workflow
name: Build

on: [push]

jobs:
  dockai:
    uses: your-org/.github/.github/workflows/dockai-template.yml@main
    secrets:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Organization Secrets

Set these at the organization level for all repositories:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (or your provider's key) |
| `DOCKAI_GENERATOR_INSTRUCTIONS` | Organization-wide generator guidance |
| `DOCKAI_REVIEWER_INSTRUCTIONS` | Organization-wide security requirements |

---

## Committing Generated Dockerfile

By default, DockAI generates the Dockerfile at **runtime only**. If you want to save it to your repository, add a commit step.

### Why Commit the Dockerfile?

| Reason | Benefit |
|--------|---------|
| **Version Control** | Track Dockerfile changes over time |
| **Code Review** | Review changes in pull requests |
| **Transparency** | See exactly what's being used |
| **Offline Builds** | Build without running DockAI |
| **Manual Edits** | Make adjustments to generated file |

### Basic Commit Step

```yaml
name: Generate and Commit Dockerfile

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  dockai:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Required for pushing
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Commit and Push
        run: |
          # Configure git
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          
          # Add generated files
          git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
          
          # Commit only if there are changes
          git diff --staged --quiet || git commit -m "chore: update Dockerfile with DockAI"
          
          # Push
          git push
```

### Understanding the Commit Step

```bash
# 1. Configure git with bot identity
git config --local user.email "github-actions[bot]@users.noreply.github.com"
git config --local user.name "github-actions[bot]"

# 2. Stage generated files (handle missing .dockerignore gracefully)
git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile

# 3. Only commit if there are actual changes
git diff --staged --quiet || git commit -m "chore: update Dockerfile with DockAI"

# 4. Push to current branch
git push
```

### Conditional Commit (Skip on PRs)

```yaml
- name: Commit and Push
  if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
    git diff --staged --quiet || git commit -m "chore: update Dockerfile with DockAI"
    git push
```

This ensures:
- ✅ Commits on push to main/develop
- ✅ Commits on manual workflow dispatch
- ❌ No commits on pull requests (avoids polluting PRs)

### Create PR Instead of Direct Commit

```yaml
- name: Create Pull Request
  uses: peter-evans/create-pull-request@v5
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    commit-message: 'chore: update Dockerfile with DockAI'
    title: 'chore: Update Dockerfile'
    body: |
      ## Automated Update
      
      This PR updates the Dockerfile using DockAI.
      Please review before merging.
    branch: dockerfile-update
    delete-branch: true
```

---

## Advanced Patterns

### Matrix Build with Different Providers

Test with multiple LLM providers:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        provider: [openai, gemini, anthropic]
        include:
          - provider: openai
            api_key_secret: OPENAI_API_KEY
          - provider: gemini
            api_key_secret: GOOGLE_API_KEY
          - provider: anthropic
            api_key_secret: ANTHROPIC_API_KEY
    steps:
      - uses: actions/checkout@v4
      - uses: itzzjb/dockai@v3
        with:
          llm_provider: ${{ matrix.provider }}
          openai_api_key: ${{ matrix.provider == 'openai' && secrets[matrix.api_key_secret] || '' }}
          google_api_key: ${{ matrix.provider == 'gemini' && secrets[matrix.api_key_secret] || '' }}
          anthropic_api_key: ${{ matrix.provider == 'anthropic' && secrets[matrix.api_key_secret] || '' }}
```

### Conditional Security Strictness

Be strict on main, lenient on feature branches:

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: ${{ github.ref == 'refs/heads/main' && 'true' || 'false' }}
```

### Environment-Specific Configuration

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      - uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          generator_instructions: ${{ vars.DOCKAI_GENERATOR_INSTRUCTIONS }}
```

---

## Troubleshooting

### "API key not found"

**Solution**: Ensure secrets are configured:

1. Go to Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY` (or your provider's key)
4. Value: Your API key
5. Reference as `${{ secrets.OPENAI_API_KEY }}`

### "Build failed after max retries"

**Solutions**:

```yaml
# 1. Increase retries
max_retries: '5'

# 2. Increase resources
validation_memory: '1g'
validation_cpus: '2.0'

# 3. Add custom instructions
generator_instructions: |
  This project has specific requirements:
  - Needs build-essential for native modules
  - Uses port 3000
```

### "Docker build timeout"

GitHub runners have limited resources. Solutions:

1. **Use self-hosted runners** for large images
2. **Skip security scanning** to speed up: `skip_security_scan: 'true'`
3. **Add optimization instructions**

### "Permission denied" when committing

**Solution**: Add write permissions:

```yaml
permissions:
  contents: write
```

### "Trivy scan taking too long"

**Solutions**:

```yaml
# Skip Trivy (not recommended for production)
skip_security_scan: 'true'

# Or use offline mode (faster but less up-to-date)
# (configure in Trivy-specific ways)
```

### Debugging Failed Runs

1. **Enable verbose tracing**:
```yaml
enable_tracing: 'true'
tracing_exporter: 'console'
```

2. **Check action logs** for detailed error messages

3. **Test locally first**:
```bash
export OPENAI_API_KEY=sk-your-key
dockai build . --verbose
```

---

## Next Steps

- **[Configuration Reference](./configuration.md)**: All configuration options
- **[Customization Guide](./customization.md)**: Fine-tune for your stack
- **[MCP Server](./mcp-server.md)**: AI assistant integration
- **[FAQ](./faq.md)**: Common questions and answers
