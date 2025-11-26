# Customization Guide

DockAI's power comes from its ability to be customized for your specific technology stack, organizational standards, and security requirements. This guide covers strategies for effective customization.

## Customization Philosophy

DockAI uses a **progressive refinement** approach:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: Per-Run Overrides                       │
│         (CLI flags, environment variables at runtime)               │
├─────────────────────────────────────────────────────────────────────┤
│                  LAYER 2: Repository Configuration                  │
│            (.dockai file in the repository root)                    │
├─────────────────────────────────────────────────────────────────────┤
│                  LAYER 1: Organization Defaults                     │
│          (Environment variables, CI/CD secrets)                     │
├─────────────────────────────────────────────────────────────────────┤
│                     LAYER 0: Built-in Defaults                      │
│              (DockAI's intelligent base behavior)                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Instructions vs. Prompts

### Instructions (Recommended)

Instructions are **appended** to the default prompt. Use them to:
- Guide the AI's reasoning while keeping its base intelligence
- Add organization-specific context
- Handle common edge cases

```ini
[instructions_generator]
Our standard practices:
- Always use /app as working directory
- Include LABEL maintainer="platform-team@company.io"
- Set ENV SERVICE_NAME to the repository name
```

### Prompts (Advanced)

Prompts **completely replace** the default prompt. Use them when:
- You need full control over agent behavior
- The default approach doesn't fit your needs
- You're building a specialized variant of DockAI

```ini
[prompt_reviewer]
You are a security specialist for financial services applications.

Focus on:
1. PCI-DSS compliance requirements
2. Data encryption at rest and in transit
3. Audit logging requirements
...
```

## Customization by Agent

### Analyzer Agent

**Purpose**: Project discovery and stack detection

**Good customizations**:
- Internal framework detection
- Custom project conventions
- Legacy system patterns

```ini
[instructions_analyzer]
Our organization uses:
- "CompanyFramework" which requires Python 3.11+ and uvloop
- Configuration in /etc/company/config/
- Internal package registry at packages.company.io

Project types we have:
- "microservice" - Long-running HTTP services
- "worker" - Background job processors
- "cron" - Scheduled tasks
```

### Planner Agent

**Purpose**: Strategic build planning

**Good customizations**:
- Approved base images
- Build strategy preferences
- Size/security tradeoffs

```ini
[instructions_planner]
APPROVED BASE IMAGES (use only these):
- company-registry.io/python:3.11-slim
- company-registry.io/node:20-alpine
- company-registry.io/golang:1.21-alpine

BUILD REQUIREMENTS:
- Always use multi-stage builds for compiled languages
- Final images must be under 500MB
- Use distroless where possible for security
```

### Generator Agent

**Purpose**: Dockerfile creation

**Good customizations**:
- Standard labels and metadata
- Required environment variables
- Organizational conventions

```ini
[instructions_generator]
REQUIRED LABELS (always include):
- LABEL org.company.team="${TEAM}"
- LABEL org.company.version="${VERSION}"
- LABEL org.company.managed-by="dockai"

REQUIRED ENV:
- ENV SERVICE_NAME required
- ENV ENVIRONMENT=production

CONVENTIONS:
- Use /app as WORKDIR
- Create non-root user with UID 10000
- Include our standard healthcheck wrapper
```

### Reviewer Agent

**Purpose**: Security audit

**Good customizations**:
- Compliance requirements
- Approved/blocked packages
- Security policies

```ini
[instructions_reviewer]
SECURITY REQUIREMENTS (enforce strictly):
- All containers MUST run as non-root (UID >= 10000)
- No secrets or credentials in Dockerfile
- Base images must use SHA256 digest pinning
- No shell access in production images

COMPLIANCE (SOC 2 / HIPAA):
- Fail if any CRITICAL CVE detected
- All packages must be from approved sources
- Audit all RUN commands for data handling
```

### Reflector Agent

**Purpose**: Failure analysis and learning

**Good customizations**:
- Common issues in your stack
- Known workarounds
- Debug patterns

```ini
[instructions_reflector]
KNOWN ISSUES IN OUR STACK:

1. "pg_config not found"
   Solution: Install postgresql-dev (Alpine) or libpq-dev (Debian)
   
2. "Failed to build cryptography"
   Solution: Need gcc, musl-dev, libffi-dev, openssl-dev
   
3. "GLIBC not found" (Alpine)
   Solution: Use Debian-based image or install gcompat

4. Permission denied on /app
   Solution: Ensure WORKDIR ownership matches USER
```

### Health Detector Agent

**Purpose**: Health endpoint discovery

**Good customizations**:
- Standard health endpoint paths
- Port conventions
- Framework-specific patterns

```ini
[instructions_health_detector]
Our health endpoint conventions:
- Path: /api/v1/health or /health
- Port: 8080 for HTTP services, 9090 for gRPC
- Response: {"status": "healthy", "version": "..."} 

Framework patterns:
- Django: /api/health/ with DRF
- FastAPI: /health with automatic docs
- Express: /health or /ping
```

### Readiness Detector Agent

**Purpose**: Startup pattern analysis

**Good customizations**:
- Standard log formats
- Startup indicators
- Timeout expectations

```ini
[instructions_readiness_detector]
Our applications log startup as:
- Django: "Starting development server at" or "Booting worker"
- FastAPI: "Application startup complete"
- Node.js: "Server listening on port"

Expected startup times:
- Simple services: 3-5 seconds
- Services with DB migrations: 15-30 seconds
- Services loading ML models: 60-120 seconds
```

## Enterprise Patterns

### Pattern 1: Organization-Wide Defaults

Set via CI/CD environment variables:

```yaml
# Organization GitHub Actions template
env:
  DOCKAI_PLANNER_INSTRUCTIONS: |
    APPROVED BASE IMAGES:
    - ghcr.io/company/python:3.11-slim
    - ghcr.io/company/node:20-alpine
    
  DOCKAI_REVIEWER_INSTRUCTIONS: |
    SECURITY (mandatory):
    - Non-root user (UID 10000)
    - No hardcoded secrets
```

### Pattern 2: Stack-Specific Templates

Create reusable `.dockai` templates:

**Django Template** (`.dockai.django`):
```ini
[instructions_analyzer]
This is a Django application.
Settings in DJANGO_SETTINGS_MODULE.
Dependencies in requirements.txt or pyproject.toml.

[instructions_generator]
Django practices:
- Use gunicorn with uvicorn workers
- Run collectstatic during build
- Migrations at container start (entrypoint)
```

**Express Template** (`.dockai.express`):
```ini
[instructions_analyzer]
Node.js Express application.
Entry point in package.json "main" or "start" script.

[instructions_generator]
Express practices:
- Use node:20-alpine
- npm ci --only=production
- NODE_ENV=production
- Run as node user
```

### Pattern 3: Monorepo Configuration

Place `.dockai` in each service directory:

```
monorepo/
├── services/
│   ├── api/
│   │   ├── .dockai          # API-specific
│   │   └── src/
│   ├── worker/
│   │   ├── .dockai          # Worker-specific
│   │   └── src/
│   └── frontend/
│       ├── .dockai          # Frontend-specific
│       └── src/
```

### Pattern 4: Learning from Failures

Document failures in your customization:

```ini
[instructions_error_analyzer]
HISTORICAL ISSUES:

Issue: "ModuleNotFoundError: No module named 'pkg_resources'"
Cause: Missing setuptools in slim images
Fix: Add "pip install setuptools" or use full image

Issue: "Error loading shared library libssl.so.1.1"
Cause: OpenSSL version mismatch
Fix: Use Debian-based image or install openssl-compat

Issue: Container exits immediately
Cause: Foreground process not configured
Fix: Ensure CMD runs in foreground (no daemonization)
```

## Progressive Refinement Workflow

### Week 1: Observe

Run DockAI with defaults and note:
- What works well
- What fails consistently
- What needs manual adjustment

### Week 2: Add Basic Instructions

```ini
[instructions_planner]
Prefer python:3.11-slim over python:3.11

[instructions_generator]
Include our standard metadata labels
```

### Week 3: Expand Coverage

```ini
[instructions_analyzer]
We use Poetry for dependency management.
Look for pyproject.toml before requirements.txt.

[instructions_reflector]
Alpine issues: switch to Debian for native extensions
```

### Week 4+: Repository-Specific

Create `.dockai` files for repositories with unique requirements.

## Measuring Success

Track these metrics:

| Metric | Before | Target |
|--------|--------|--------|
| First-attempt success | ~60% | 85%+ |
| Average retries | 2-3 | < 1 |
| Security failures | ~40% | < 10% |
| Manual edits | Common | Rare |

## Best Practices

### Do

- ✅ Start simple and iterate
- ✅ Document the "why" in your instructions
- ✅ Version control your `.dockai` files
- ✅ Share learnings across teams
- ✅ Test customizations on sample projects

### Don't

- ❌ Over-customize too early
- ❌ Replace prompts unless absolutely necessary
- ❌ Duplicate information already in defaults
- ❌ Add instructions that contradict defaults
- ❌ Forget to update customizations when your stack changes

## Next Steps

- **[Configuration](./configuration.md)** — All configuration options
- **[Platform Integration](./platform-integration.md)** — Embedding DockAI
- **[GitHub Actions](./github-actions.md)** — CI/CD setup
