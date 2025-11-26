# Customization Guide

DockAI's power comes from its ability to be customized for your specific technology stack, organizational standards, and security requirements.

---

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

---

## Instructions vs. Prompts

### Instructions (Recommended)

Instructions are **appended** to the default prompt:

- ✅ Preserve DockAI's base intelligence
- ✅ Add organization-specific context
- ✅ Handle common edge cases
- ✅ Easy to maintain

```ini
[instructions_generator]
Our standard practices:
- Always use /app as working directory
- Include LABEL maintainer="platform-team@company.io"
- Set ENV SERVICE_NAME to the repository name
```

### Prompts (Advanced)

Prompts **completely replace** the default:

- ⚠️ Full control over agent behavior
- ⚠️ Must handle all edge cases yourself
- ⚠️ May break with DockAI updates
- ⚠️ Higher maintenance burden

```ini
[prompt_reviewer]
You are a security specialist for financial services applications.

Focus on:
1. PCI-DSS compliance requirements
2. Data encryption at rest and in transit
3. Audit logging requirements
...
```

---

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

---

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

---

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

---

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

---

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

---

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

---

### Readiness Detector Agent

**Purpose**: Startup pattern analysis

**Good customizations**:
- Startup log patterns
- Typical startup times
- Framework-specific signals

```ini
[instructions_readiness_detector]
Our startup patterns:
- Django: "Starting development server" or "Booting worker"
- FastAPI: "Uvicorn running on"
- Node.js: "Server listening on port"

Typical startup times:
- Simple services: 3-5 seconds
- Services with DB: 10-15 seconds
- Services with heavy init: 30+ seconds
```

---

## Real-World Examples

### Python Web Service (Django)

```ini
[instructions_analyzer]
This is a Django application with:
- Celery for background tasks
- PostgreSQL database
- Redis for caching and Celery broker
- Poetry for dependency management

[instructions_generator]
- Use gunicorn with uvicorn workers
- Run database migrations in entrypoint
- Use multi-stage build with poetry export
- Include celery worker command as alternative

[instructions_reviewer]
- Ensure DATABASE_URL is not hardcoded
- Check for DJANGO_SECRET_KEY handling
- Verify static files are collected
```

---

### Node.js Microservice

```ini
[instructions_analyzer]
Express.js microservice with:
- TypeScript compilation
- Prisma ORM for PostgreSQL
- pnpm package manager

[instructions_generator]
- Use node:20-alpine for final image
- Multi-stage: build TypeScript, copy dist
- Run prisma generate in build stage
- Do NOT include devDependencies in final

[instructions_reflector]
Common issues:
- "prisma not found": Run npx prisma generate
- "esbuild binary not found": Need platform-specific binary
```

---

### Go Service

```ini
[instructions_analyzer]
Go service with:
- Go modules
- CGO disabled (pure Go)
- gRPC and HTTP endpoints

[instructions_generator]
- Build with CGO_ENABLED=0 for static binary
- Use scratch or distroless as final base
- Include CA certificates for HTTPS calls
- Copy only the binary, nothing else

[instructions_planner]
- Always use multi-stage build
- Final image should be under 50MB
- No shell needed in production
```

---

## Customization Progression

### Day 1: Basic Setup

```ini
[instructions_generator]
Use our approved base images from company-registry.io
```

### Week 1: Add Common Fixes

```ini
[instructions_reflector]
If you see "pg_config not found", install libpq-dev
If you see "node-gyp" errors, install build-essential
```

### Month 1: Repository-Specific

Create `.dockai` files in each repository with project-specific guidance.

### Ongoing: Continuous Refinement

- Add new patterns as you discover them
- Document lessons learned from failures
- Share customizations across teams

---

## Sharing Customizations

### Version Control

Always commit `.dockai` files to version control:

```bash
git add .dockai
git commit -m "Add DockAI configuration for Django service"
```

### Organization Templates

Create template `.dockai` files for common project types:

```
templates/
├── python-django.dockai
├── python-fastapi.dockai
├── node-express.dockai
├── node-nextjs.dockai
└── go-service.dockai
```

### CI/CD Secrets

Store organization-wide settings as GitHub secrets:

```yaml
env:
  DOCKAI_PLANNER_INSTRUCTIONS: ${{ secrets.DOCKAI_PLANNER_INSTRUCTIONS }}
  DOCKAI_REVIEWER_INSTRUCTIONS: ${{ secrets.DOCKAI_REVIEWER_INSTRUCTIONS }}
```

---

## Measuring Effectiveness

| Metric | Before Customization | After Customization |
|--------|---------------------|---------------------|
| First-attempt success rate | ~60% | ~85%+ |
| Average retries | 1.5 | 0.3 |
| Token usage | High | Reduced 30-50% |
| Manual fixes needed | Often | Rarely |

---

## Next Steps

- **[Configuration](./configuration.md)**: All configuration options
- **[GitHub Actions](./github-actions.md)**: CI/CD integration
- **[Platform Integration](./platform-integration.md)**: Embedding DockAI
