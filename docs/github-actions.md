# GitHub Actions Integration

This guide covers how to use DockAI in your CI/CD pipelines with GitHub Actions.

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

## Action Inputs

### Required Inputs

| Input | Description |
|-------|-------------|
| `openai_api_key` | Your OpenAI API key (store as a secret) |

### Optional Inputs

#### Project Settings

| Input | Description | Default |
|-------|-------------|---------|
| `project_path` | Path to project root | `.` |

#### Model Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `model_generator` | Model for generation/reflection | `gpt-4o` |
| `model_analyzer` | Model for analysis/planning | `gpt-4o-mini` |

#### Workflow Settings

| Input | Description | Default |
|-------|-------------|---------|
| `max_retries` | Maximum retry attempts | `3` |

#### Validation Settings

| Input | Description | Default |
|-------|-------------|---------|
| `skip_security_scan` | Skip Trivy scanning | `false` |
| `strict_security` | Fail on any vulnerability | `false` |
| `max_image_size_mb` | Maximum image size (0 = disabled) | `500` |
| `skip_health_check` | Skip health endpoint checks | `false` |

#### Resource Limits

| Input | Description | Default |
|-------|-------------|---------|
| `validation_memory` | Memory limit for validation | `512m` |
| `validation_cpus` | CPU limit for validation | `1.0` |
| `validation_pids` | Process limit for validation | `100` |

#### Custom Instructions

| Input | Description |
|-------|-------------|
| `analyzer_instructions` | Guide project analysis |
| `planner_instructions` | Guide strategic planning |
| `generator_instructions` | Guide Dockerfile creation |
| `reviewer_instructions` | Guide security review |
| `reflector_instructions` | Guide failure analysis |
| `health_detector_instructions` | Guide health detection |
| `readiness_detector_instructions` | Guide readiness detection |
| `error_analyzer_instructions` | Guide error classification |
| `iterative_improver_instructions` | Guide fix application |
| `generator_iterative_instructions` | Guide iterative generation |

#### Custom Prompts (Advanced)

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

## Usage Examples

### Basic Usage

```yaml
- name: Run DockAI
  uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### With Model Configuration

```yaml
- name: Run DockAI
  uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    model_generator: 'gpt-4o'
    model_analyzer: 'gpt-4o-mini'
    max_retries: '5'
```

### With Security Settings

```yaml
- name: Run DockAI
  uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: 'true'
    max_image_size_mb: '300'
```

### With Custom Instructions

```yaml
- name: Run DockAI
  uses: itzzjb/dockai@v2
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    analyzer_instructions: 'This is a Django app with Celery'
    generator_instructions: |
      Use gunicorn as WSGI server.
      Include database migrations.
    reviewer_instructions: |
      All containers must run as non-root.
      Fail if any secrets are detected.
```

### Full Configuration Example

```yaml
name: Auto-Dockerize with DockAI

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
      
      - name: Run DockAI
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          
          # Model configuration
          model_generator: 'gpt-4o'
          model_analyzer: 'gpt-4o-mini'
          
          # Workflow settings
          max_retries: '5'
          
          # Validation settings
          skip_security_scan: 'false'
          strict_security: 'true'
          max_image_size_mb: '300'
          
          # Resource limits
          validation_memory: '1g'
          validation_cpus: '2.0'
          
          # Custom instructions
          analyzer_instructions: 'Focus on microservices architecture'
          generator_instructions: 'Use Alpine-based images'
          planner_instructions: |
            Approved base images:
            - python:3.11-slim
            - node:20-alpine
          reviewer_instructions: |
            Security requirements:
            - Non-root user mandatory
            - No hardcoded secrets
      
      - name: Upload Dockerfile
        uses: actions/upload-artifact@v4
        with:
          name: dockerfile
          path: Dockerfile
```

## Workflow Patterns

### On Push to Main

```yaml
on:
  push:
    branches: [main]
```

### On Pull Request

```yaml
on:
  pull_request:
    branches: [main]
```

### Manual Trigger

```yaml
on:
  workflow_dispatch:
    inputs:
      path:
        description: 'Project path'
        required: false
        default: '.'
```

### Scheduled Run

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
```

## Multi-Project Monorepo

For monorepos with multiple services:

```yaml
name: Dockerize All Services

on:
  push:
    branches: [main]

jobs:
  discover:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.find.outputs.services }}
    steps:
      - uses: actions/checkout@v4
      - id: find
        run: |
          services=$(ls -d services/*/ | jq -R -s -c 'split("\n")[:-1]')
          echo "services=$services" >> $GITHUB_OUTPUT
  
  dockerize:
    needs: discover
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: ${{ fromJson(needs.discover.outputs.services) }}
    steps:
      - uses: actions/checkout@v4
      - name: Run DockAI
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          project_path: ${{ matrix.service }}
```

## Build and Push Pattern

Combine DockAI with Docker build and push:

```yaml
name: Build and Push

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Dockerfile
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

## Secrets Management

### Setting Up Secrets

1. Go to your repository settings
2. Navigate to Secrets and Variables → Actions
3. Click "New repository secret"
4. Add `OPENAI_API_KEY` with your API key

### Organization Secrets

For organization-wide settings, use organization secrets:

1. Go to organization settings
2. Navigate to Secrets and Variables → Actions
3. Add secrets accessible to multiple repositories

## Troubleshooting

### Action Fails Immediately

Check that:
- `OPENAI_API_KEY` secret is set
- Secret name matches exactly (case-sensitive)

### Rate Limit Errors

If you see rate limit errors:
- DockAI automatically retries with backoff
- Consider reducing `max_retries` to limit API calls
- Upgrade your OpenAI API tier for higher limits

### Docker Build Fails

Check the action logs for:
- Specific error messages
- Whether it's a project issue or Dockerfile issue
- Resource limit problems

### Security Scan Fails

If strict security is enabled and the scan fails:
- Review the vulnerability report
- Either fix the vulnerabilities or adjust `strict_security`

## Best Practices

### 1. Use Secrets for API Keys

Never hardcode API keys in workflow files:
```yaml
# ✅ Good
openai_api_key: ${{ secrets.OPENAI_API_KEY }}

# ❌ Bad
openai_api_key: 'sk-actual-key-here'
```

### 2. Pin Action Version

Use specific versions for reproducibility:
```yaml
# ✅ Good - pinned version
uses: itzzjb/dockai@v2

# ⚠️ Less stable - latest
uses: itzzjb/dockai@main
```

### 3. Cache Dependencies

Speed up workflows by caching:
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### 4. Use Conditional Runs

Only run DockAI when relevant files change:
```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'requirements.txt'
      - 'package.json'
```

## Next Steps

- **[Configuration](./configuration.md)** — All configuration options
- **[Customization](./customization.md)** — Fine-tuning strategies
- **[Platform Integration](./platform-integration.md)** — Embedding in platforms
