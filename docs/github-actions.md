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
  workflow_dispatch:

jobs:
  dockai:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Required if committing Dockerfile
    steps:
      - uses: actions/checkout@v4
      
      - name: Run DockAI
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      # Optional: Commit the generated Dockerfile to your repository
      - name: Commit and push Dockerfile
        if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
          git diff --staged --quiet || git commit -m "chore: auto-generate Dockerfile with DockAI"
          git push
```

> 💡 **Note**: The commit step is optional. Remove it if you only want to generate the Dockerfile at runtime without saving it to your repository. See [Committing Generated Dockerfile](#committing-generated-dockerfile) for more details.

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
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### Google Gemini

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

### Azure OpenAI

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: azure
    azure_openai_api_key: ${{ secrets.AZURE_OPENAI_API_KEY }}
    azure_openai_endpoint: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
```

### Cost-Optimized Configuration

Use faster models for simple tasks:

```yaml
- uses: itzzjb/dockai@v3
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
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: 'true'
    max_image_size_mb: '300'
```

### Custom Instructions

```yaml
- uses: itzzjb/dockai@v3
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
- uses: itzzjb/dockai@v3
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
        uses: itzzjb/dockai@v3
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
    permissions:
      packages: write  # Required for GHCR push
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
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
        uses: itzzjb/dockai@v3
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
        uses: itzzjb/dockai@v3
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
      
      - uses: itzzjb/dockai@v3
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

## Committing Generated Dockerfile

By default, DockAI generates the Dockerfile at **runtime only** - it's not automatically committed to your repository. This is useful for:
- **Runtime builds**: Building Docker images in CI/CD without cluttering your repo
- **Testing**: Trying different configurations without committing changes
- **Dynamic generation**: Generating Dockerfiles on-demand for different environments

However, if you want to **save the Dockerfile to your repository**, you can add a commit step to your workflow.

---

### Why Commit the Dockerfile?

Committing the generated Dockerfile has several benefits:

✅ **Version Control**: Track changes to your Dockerfile over time  
✅ **Code Review**: Review Dockerfile changes in pull requests  
✅ **Transparency**: See exactly what Docker configuration is being used  
✅ **Offline Builds**: Build images without re-running DockAI  
✅ **Manual Edits**: Make manual adjustments to the AI-generated Dockerfile

---

### How to Commit the Dockerfile

Add a commit step **after** the DockAI action in your workflow:

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
      contents: write  # Required for pushing commits
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Commit and push Dockerfile
        if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
          git diff --staged --quiet || git commit -m "chore: auto-generate Dockerfile with DockAI"
          git push
```

---

### Explanation of the Commit Step

Let's break down what this step does:

1. **Conditional Execution**: Only runs on `push` or `workflow_dispatch` events
   ```yaml
   if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
   ```

2. **Git Configuration**: Sets up git with the GitHub Actions bot identity
   ```bash
   git config --local user.email "github-actions[bot]@users.noreply.github.com"
   git config --local user.name "github-actions[bot]"
   ```

3. **Stage Files**: Adds the generated files (handles missing `.dockerignore` gracefully)
   ```bash
   git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
   ```

4. **Commit Only if Changed**: Only creates a commit if there are actual changes
   ```bash
   git diff --staged --quiet || git commit -m "chore: auto-generate Dockerfile with DockAI"
   ```

5. **Push to Repository**: Pushes the commit to the current branch
   ```bash
   git push
   ```

---

### Avoiding Commits on Pull Requests

The `if` condition prevents committing on pull requests, which is usually desired:

```yaml
if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
```

This means:
- ✅ **Commits on push to main/develop**: Dockerfile is saved to the branch
- ✅ **Commits on manual trigger**: Dockerfile is saved when you manually run the workflow
- ❌ **No commits on PRs**: Avoids polluting PR branches with automated commits

If you **do** want to commit on PRs, remove the `if` condition or adjust it:

```yaml
# Commit on all events
- name: Commit and push Dockerfile
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
    git diff --staged --quiet || git commit -m "chore: auto-generate Dockerfile with DockAI"
    git push
```

---

### Custom Commit Messages

You can customize the commit message to include more context:

```yaml
- name: Commit and push Dockerfile
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
    git diff --staged --quiet || git commit -m "chore: update Dockerfile for ${{ github.ref_name }} @ ${{ github.sha }}"
    git push
```

Or use environment variables for more dynamic messages:

```yaml
- name: Commit and push Dockerfile
  env:
    COMMIT_MSG: "feat: regenerate Dockerfile with DockAI v3"
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add Dockerfile .dockerignore 2>/dev/null || git add Dockerfile
    git diff --staged --quiet || git commit -m "$COMMIT_MSG"
    git push
```

---

### Creating a Pull Request Instead

Instead of committing directly, you can create a pull request with the changes:

```yaml
name: Generate Dockerfile PR

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: 'chore: Update Dockerfile with DockAI'
          commit-message: 'chore: Regenerate Dockerfile with DockAI'
          branch: dockerfile-update
          body: |
            ## Automated Dockerfile Update
            
            This PR updates the Dockerfile using DockAI.
            
            Please review the changes before merging.
```

---

### Required Permissions

Ensure your workflow has write permissions to commit and push:

```yaml
permissions:
  contents: write
```

This is usually enabled by default, but some organizations may restrict it. If you get a permission error, check your repository or organization settings.

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
- **[MCP Server](./mcp-server.md)**: AI Agent integration guide

