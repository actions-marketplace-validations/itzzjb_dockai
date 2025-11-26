# Platform Integration Guide

This guide covers how to embed DockAI into Platform Engineering platforms to enable zero-config deployments.

## Overview

DockAI is designed to be embedded into developer platforms, enabling:
- **Zero-config deployments** — Developers push code, containerization happens automatically
- **Consistent standards** — Platform enforces security and conventions
- **Any language support** — AI-based approach works with any technology stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZERO-CONFIG DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Developer        Platform               Cloud                  │
│   ─────────       ─────────              ─────                  │
│                                                                  │
│   git push ────► Webhook triggered                               │
│                       │                                          │
│                       ▼                                          │
│                 ┌─────────────┐                                  │
│                 │   DockAI    │ ◄── Platform customizations      │
│                 │ (embedded)  │                                  │
│                 └─────────────┘                                  │
│                       │                                          │
│                       ▼                                          │
│                 Dockerfile generated                             │
│                       │                                          │
│                       ▼                                          │
│                 Build & Push to Registry                         │
│                       │                                          │
│                       ▼                                          │
│   App is live! ◄── Deploy to K8s/Serverless                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits

| Traditional Approach | With DockAI Embedded |
|---------------------|----------------------|
| ❌ Require Dockerfile in repo | ✅ Auto-generate from code |
| ❌ Reject apps without Dockerfile | ✅ Accept any repo with code |
| ❌ Developers learn Docker | ✅ Developers focus on code |
| ❌ Inconsistent practices | ✅ Platform enforces standards |
| ❌ Security issues caught late | ✅ Security baked in |

## Integration Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PLATFORM ARCHITECTURE                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐     ┌─────────────────────────────────────────┐     │
│  │   GitHub    │     │         Platform Control Plane           │     │
│  │   GitLab    │────►│  ┌─────────────────────────────────┐    │     │
│  │   Bitbucket │     │  │      DockAI Service (API)       │    │     │
│  └─────────────┘     │  │  ┌─────────────────────────┐    │    │     │
│                      │  │  │ Platform Customizations │    │    │     │
│                      │  │  │ • Approved base images  │    │    │     │
│                      │  │  │ • Security policies     │    │    │     │
│                      │  │  │ • Naming conventions    │    │    │     │
│                      │  │  └─────────────────────────┘    │    │     │
│                      │  └─────────────────────────────────┘    │     │
│                      │                  │                       │     │
│                      │                  ▼                       │     │
│                      │  ┌─────────────────────────────────┐    │     │
│                      │  │       Container Registry         │    │     │
│                      │  │   (Harbor/GCR/ECR/ACR)          │    │     │
│                      │  └─────────────────────────────────┘    │     │
│                      │                  │                       │     │
│                      │                  ▼                       │     │
│                      │  ┌─────────────────────────────────┐    │     │
│                      │  │     Kubernetes / Serverless      │    │     │
│                      │  └─────────────────────────────────┘    │     │
│                      └─────────────────────────────────────────┘     │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Building a DockAI API Service

### FastAPI Example

```python
# dockai_platform_service.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os

app = FastAPI(title="DockAI Platform Service")


class ContainerizeRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    team: str
    platform_config: dict = {}


class ContainerizeResponse(BaseModel):
    dockerfile: str
    image_tag: str
    build_status: str
    security_scan: dict


@app.post("/containerize", response_model=ContainerizeResponse)
async def containerize_repo(
    request: ContainerizeRequest, 
    background_tasks: BackgroundTasks
):
    """
    Auto-containerize any repository.
    
    1. Clone the repo
    2. Run DockAI with platform-specific customizations
    3. Build and push to registry
    4. Return results
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone repo
        result = subprocess.run(
            ["git", "clone", "--depth=1", "-b", request.branch, 
             request.repo_url, tmpdir],
            capture_output=True
        )
        if result.returncode != 0:
            raise HTTPException(400, "Failed to clone repository")
        
        # Write platform-specific .dockai config
        dockai_config = generate_platform_config(
            request.team, 
            request.platform_config
        )
        config_path = os.path.join(tmpdir, ".dockai")
        with open(config_path, "w") as f:
            f.write(dockai_config)
        
        # Run DockAI
        env = {
            **os.environ,
            "OPENAI_API_KEY": os.getenv("PLATFORM_OPENAI_KEY"),
            "DOCKAI_STRICT_SECURITY": "true",
            "DOCKAI_MAX_IMAGE_SIZE_MB": "500",
        }
        
        result = subprocess.run(
            ["dockai", "build", tmpdir],
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            raise HTTPException(500, f"DockAI failed: {result.stderr}")
        
        # Read generated Dockerfile
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path) as f:
            dockerfile_content = f.read()
        
        # Build and push (background task)
        image_tag = f"platform-registry.io/{request.team}/app:{request.branch}"
        background_tasks.add_task(build_and_push, tmpdir, image_tag)
        
        return ContainerizeResponse(
            dockerfile=dockerfile_content,
            image_tag=image_tag,
            build_status="building",
            security_scan={}
        )


def generate_platform_config(team: str, overrides: dict) -> str:
    """Generate .dockai config with platform defaults."""
    return f"""
[instructions_planner]
PLATFORM REQUIREMENTS:
- Base images MUST be from platform-registry.io/approved/
- All images must include platform telemetry agent
- Maximum final image size: 500MB

[instructions_generator]
REQUIRED LABELS:
- LABEL platform.team="{team}"
- LABEL platform.managed-by="dockai"
- LABEL platform.version="${{GIT_SHA}}"

REQUIRED ENV:
- ENV PLATFORM_TELEMETRY_ENABLED=true
- ENV SERVICE_NAME="${{SERVICE_NAME}}"

[instructions_reviewer]
SECURITY (enforced by platform):
- Non-root user with UID >= 10000
- No secrets in Dockerfile
- No privileged operations
- HEALTHCHECK instruction required

{overrides.get('custom_instructions', '')}
"""


async def build_and_push(tmpdir: str, image_tag: str):
    """Build Docker image and push to registry."""
    # Build
    subprocess.run(
        ["docker", "build", "-t", image_tag, tmpdir],
        check=True
    )
    # Push
    subprocess.run(
        ["docker", "push", image_tag],
        check=True
    )
```

## Platform-Specific Integrations

### WSO2 Choreo

[Choreo](https://wso2.com/choreo/) integration example:

```python
class ChoreoBuildService:
    def __init__(self):
        self.dockai_config = {
            "planner_instructions": """
                CHOREO PLATFORM STANDARDS:
                - Use Choreo-approved base images from gcr.io/choreo-images/
                - All services must expose metrics on /metrics
                - Health check required at /healthz
                - Max image size: 500MB
            """,
            "reviewer_instructions": """
                CHOREO SECURITY REQUIREMENTS:
                - Non-root user mandatory (UID 10001)
                - No shell access in production images
                - All secrets via Choreo secret management
                - HTTPS only - no HTTP endpoints
            """,
            "generator_instructions": """
                CHOREO CONVENTIONS:
                - LABEL choreo.component.type="${component_type}"
                - LABEL choreo.project.id="${project_id}"
                - ENV CHOREO_ENVIRONMENT=production
                - Expose port 8080 for HTTP services
            """
        }
    
    def containerize_component(self, repo_url: str, component_type: str):
        """Auto-containerize a Choreo component from source."""
        pass
```

### SkyU Platform

[SkyU](https://skyu.io/) configuration example:

```yaml
# skyu_dockai_config.yaml
skyu_dockai_config:
  base_images:
    python: "skyu-registry.io/base/python:3.11-slim"
    node: "skyu-registry.io/base/node:20-alpine"
    go: "skyu-registry.io/base/golang:1.21-alpine"
  
  security:
    enforce_non_root: true
    max_image_size_mb: 400
    required_labels:
      - "skyu.io/managed-by=dockai"
      - "skyu.io/team=${team_name}"
  
  kubernetes:
    generate_resource_limits: true
    default_replicas: 2
    auto_scaling: true
```

### Backstage Integration

[Backstage](https://backstage.io/) Software Template:

```yaml
# backstage-template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: deploy-any-service
  title: Deploy Any Service (No Dockerfile Needed)
spec:
  parameters:
    - title: Source Repository
      properties:
        repoUrl:
          type: string
          title: Repository URL
  
  steps:
    - id: fetch-repo
      name: Fetch Source Code
      action: fetch:plain
      input:
        url: ${{ parameters.repoUrl }}
    
    - id: containerize
      name: Auto-Generate Dockerfile
      action: dockai:generate
      input:
        sourcePath: ${{ steps.fetch-repo.output.path }}
        platformConfig: |
          [instructions_planner]
          Use company-approved images from harbor.internal/
          
          [instructions_reviewer]
          Enforce SOC2 compliance requirements
    
    - id: deploy
      name: Deploy to Kubernetes
      action: kubernetes:deploy
      input:
        dockerfile: ${{ steps.containerize.output.dockerfile }}
```

## Multi-Tenant Configuration

For platforms serving multiple teams:

```python
class MultiTenantDockAI:
    def __init__(self):
        self.platform_defaults = {
            "security": {
                "non_root": True,
                "max_image_size_mb": 500,
            }
        }
    
    def get_team_config(self, team_id: str) -> dict:
        """Get team-specific configuration."""
        team_config = self.load_team_config(team_id)
        return {
            **self.platform_defaults,
            **team_config,
        }
    
    def generate_dockai_config(self, team_id: str, repo_config: dict) -> str:
        """Generate .dockai file with layered configuration."""
        team_config = self.get_team_config(team_id)
        
        return f"""
[instructions_planner]
# Platform defaults
{self.platform_defaults.get('planner_instructions', '')}

# Team overrides
{team_config.get('planner_instructions', '')}

# Repository-specific
{repo_config.get('planner_instructions', '')}

[instructions_reviewer]
# Platform security (mandatory)
- Non-root user: {team_config['security']['non_root']}
- Max image size: {team_config['security']['max_image_size_mb']}MB

# Team security
{team_config.get('reviewer_instructions', '')}
"""
```

## Webhook Integration

Example webhook handler for git events:

```python
from fastapi import FastAPI, Request
import hmac
import hashlib

app = FastAPI()

@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Handle GitHub push webhook."""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    
    if not verify_signature(body, signature):
        return {"error": "Invalid signature"}
    
    payload = await request.json()
    
    # Only process push to main
    if payload.get("ref") != "refs/heads/main":
        return {"status": "ignored"}
    
    repo_url = payload["repository"]["clone_url"]
    
    # Trigger containerization
    result = await containerize_repo(ContainerizeRequest(
        repo_url=repo_url,
        branch="main",
        team=extract_team(payload),
    ))
    
    return {"status": "triggered", "image_tag": result.image_tag}


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET").encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Developer Experience

### Before (Traditional)

```bash
# Developer workflow
1. Write code
2. Learn Docker basics
3. Write Dockerfile (trial and error)
4. Debug build failures
5. Fix security issues from review
6. Finally deploy
# Time: Hours to days
```

### After (With DockAI Platform)

```bash
# Developer workflow
1. Write code
2. git push
3. ☕ Get coffee
4. App is deployed
# Time: Minutes
```

## Best Practices

### 1. Layered Configuration

```
Platform Defaults
    └── Team Overrides
        └── Repository Config
            └── Build-time Overrides
```

### 2. Security at Every Layer

- Platform enforces minimum security requirements
- Teams can add stricter requirements
- Repositories cannot weaken security

### 3. Observability

- Log all containerization attempts
- Track success/failure rates
- Monitor image sizes and build times

### 4. Caching

- Cache base images in platform registry
- Reuse build layers across builds
- Store successful configurations

### 5. Gradual Rollout

1. Start with opt-in projects
2. Gather feedback and improve customization
3. Expand to more teams
4. Make it the default for new projects

## Next Steps

- **[Configuration](./configuration.md)** — All configuration options
- **[Customization](./customization.md)** — Fine-tuning strategies
- **[API Reference](./api-reference.md)** — Programmatic usage
