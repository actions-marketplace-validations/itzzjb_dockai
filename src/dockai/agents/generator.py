"""
DockAI Generator Module.

This module is responsible for generating the Dockerfile.
It acts as the "Architect", using the analysis results and plan to create
a production-ready Dockerfile. It supports both fresh generation and
iterative improvement based on feedback.
"""

import os
from typing import Tuple, Any, Dict, List, Optional, TYPE_CHECKING

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import DockerfileResult, IterativeDockerfileResult
from ..utils.callbacks import TokenUsageCallback
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from ..core.agent_context import AgentContext


def generate_dockerfile(context: 'AgentContext') -> Tuple[str, str, str, Any]:
    """
    Orchestrates the Dockerfile generation process.

    This function serves as the main entry point for "Stage 2: The Architect".
    It decides whether to generate a fresh Dockerfile from scratch or to
    iteratively improve an existing one based on feedback and reflection.

    Args:
        context (AgentContext): Unified context containing all project information,
            file tree, analysis results, retry history, plan, reflection, and custom instructions.

    Returns:
        Tuple[str, str, str, Any]: A tuple containing:
            - The generated Dockerfile content.
            - The project type (e.g., 'service', 'script').
            - The AI's thought process/explanation.
            - Token usage statistics.
    """
    from ..core.agent_context import AgentContext
    
    # Determine if we should perform iterative improvement or fresh generation
    previous_dockerfile = context.dockerfile_content
    reflection = context.reflection
    is_iterative = previous_dockerfile and reflection and len(previous_dockerfile.strip()) > 0
    
    # Create LLM using the provider factory - use different agents for fresh vs iterative
    agent_name = "generator_iterative" if is_iterative else "generator"
    llm = create_llm(agent_name=agent_name, temperature=0)
    
    if is_iterative:
        return _generate_iterative_dockerfile(
            llm=llm,
            context=context
        )
    else:
        return _generate_fresh_dockerfile(
            llm=llm,
            context=context
        )


def _generate_fresh_dockerfile(
    llm,
    context: 'AgentContext'
) -> Tuple[str, str, str, Any]:
    """
    Generates a new Dockerfile from scratch.

    This internal function handles the initial generation logic, incorporating
    the strategic plan and any lessons learned from previous (failed) attempts
    if applicable.

    Args:
        llm: The initialized LangChain LLM object.
        context (AgentContext): Unified context containing all project information.

    Returns:
        Tuple[str, str, str, Any]: Dockerfile content, project type, thought process, usage stats.
    """
    from ..core.agent_context import AgentContext
    
    # Extract values from context
    stack_info = context.analysis_result.get("stack", "Unknown")
    file_contents = context.file_contents
    custom_instructions = context.custom_instructions
    feedback_error = context.error_message
    retry_history = context.retry_history
    current_plan = context.current_plan
    file_tree = context.file_tree
    error_details = context.error_details
    verified_tags = context.verified_tags
    build_command = context.analysis_result.get("build_command", "None detected")
    start_command = context.analysis_result.get("start_command", "None detected")
    
    # Configure the LLM to return a structured output matching the DockerfileResult schema
    structured_llm = llm.with_structured_output(DockerfileResult)
    
    # Construct the retry context to prevent repeating mistakes
    retry_context = ""
    if retry_history and len(retry_history) > 0:
        retry_context = "\n\nLEARN FROM PREVIOUS ATTEMPTS:\n"
        for i, attempt in enumerate(retry_history, 1):
            retry_context += f"""
Attempt {i}:
- Tried: {attempt.get('what_was_tried', 'Unknown approach')}
- Failed because: {attempt.get('why_it_failed', 'Unknown reason')}
- Lesson: {attempt.get('lesson_learned', 'No lesson recorded')}
"""
        retry_context += "\nAPPLY THESE LESSONS - do NOT repeat the same mistakes!\n"
    
    # Construct the plan context to guide the generation strategy
    plan_context = ""
    if current_plan:
        plan_context = f"""
STRATEGIC PLAN (Follow this guidance):
- Base Image Strategy: {current_plan.get('base_image_strategy', 'Use appropriate images')}
- Build Strategy: {current_plan.get('build_strategy', 'Multi-stage build')}
- Use Multi-Stage: {current_plan.get('use_multi_stage', True)}
- Use Minimal Runtime: {current_plan.get('use_minimal_runtime', False)}
- Use Static Linking: {current_plan.get('use_static_linking', False)}
- Potential Challenges: {', '.join(current_plan.get('potential_challenges', []))}
- Mitigation Strategies: {', '.join(current_plan.get('mitigation_strategies', []))}
"""

    # EXPERT KNOWLEDGE INJECTION
    expert_guidance = _get_expert_guidance(stack_info)
    expert_context = ""
    if expert_guidance:
        expert_context = f"""
### PHASE 0: EXPERT STACK GUIDANCE (CRITICAL)
Use these PRODUCTION-READY patterns for {stack_info}:
{expert_guidance}
"""
    
    # Define the default system prompt for the "Senior Docker Architect" persona
    default_prompt = """You are the GENERATOR agent in a multi-agent Dockerfile generation pipeline. You are AGENT 3 of 8 - the craftsman who transforms plans into working Dockerfiles.

## Your Role in the Pipeline
```
Analyzer → Blueprint → [YOU: Generator] → Reviewer → Validator
                ↓                            ↓
         Strategic Plan               Your Dockerfile
```

## Your Mission
Generate a production-ready Dockerfile that:
1. Follows the Blueprint's strategic guidance
2. Builds successfully on first attempt
3. Passes security review
4. Runs the application correctly

## Chain-of-Thought Generation Process

{expert_context}

### PHASE 1: INTERNALIZE THE PLAN
The Blueprint Architect has provided strategic guidance:
{plan_context}

**Checklist before writing ANY code:**
- [ ] Do I understand the base image strategy?
- [ ] Do I know if this needs multi-stage?
- [ ] Do I understand build vs runtime dependencies?
- [ ] Have I identified all source files to copy?

### PHASE 2: STRUCTURE THE DOCKERFILE

**For Multi-Stage Builds:**
```dockerfile
# Stage 1: Builder
FROM <build-image> AS builder
# Install build dependencies
# Copy source files
# Run build commands
# Output: compiled artifacts

# Stage 2: Runtime  
FROM <runtime-image>
# Copy ONLY what's needed from builder
# Set up non-root user
# Configure runtime
# Define entrypoint
```

**For Single-Stage Builds:**
```dockerfile
FROM <image>
# Install dependencies
# Copy application
# Configure runtime
# Define entrypoint
```

### PHASE 3: THE CRITICAL COPY CHECKLIST

**#1 CAUSE OF DOCKERFILE FAILURES: Missing files**

```
MUST COPY (always):
├── Source code files (.py, .js, .go, etc.)
├── Package manifests (package.json, requirements.txt)
├── Lock files (package-lock.json, yarn.lock)
├── Configuration files (config/, .env.example)
├── Templates and static assets
└── Any file referenced in start command

SHOULD NOT COPY:
├── .git/
├── node_modules/, __pycache__/, venv/
├── .env (secrets!)
├── Test files (unless needed)
└── IDE configs (.vscode/, .idea/)
```

**Multi-Stage Copy Pattern:**
```dockerfile
# In builder stage:
COPY package*.json ./
RUN npm ci
COPY . .        # ← Copy ALL source AFTER deps
RUN npm run build

# In runtime stage:
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules  # ← Don't forget!
COPY --from=builder /app/package.json ./              # ← May be needed!
```

### PHASE 4: SECURITY HARDENING

```dockerfile
# Create non-root user (REQUIRED for production)
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set ownership before switching user
RUN chown -R appuser:appgroup /app

# Switch to non-root
USER appuser

# Never do this:
# USER root  ← Security violation
# COPY .env  ← Secrets in image
```

### PHASE 5: OPTIMIZATION LAYERS

**Layer Caching Strategy:**
```dockerfile
# 1. System deps (changes rarely)
RUN apt-get update && apt-get install -y --no-install-recommends \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Language deps (changes sometimes)
COPY package*.json ./
RUN npm ci --only=production

# 3. Source code (changes often)
COPY . .
```

## Learning from Previous Attempts
{retry_context}

## Error Context to Address
{error_context}

## Verified Base Images
Use ONLY these verified images when available: {verified_tags}
If no verified tags, use official images with specific version tags (never `latest`).

## Output Requirements
1. **dockerfile**: Complete, valid Dockerfile
2. **project_type**: "service" or "script"
3. **thought_process**: Your complete reasoning chain

## Existing Dockerfile Reference - IMPORTANT!
If there is an existing Dockerfile in the file contents, USE IT AS YOUR FOUNDATION:
1. **START from the existing Dockerfile** - don't create from scratch
2. **PRESERVE what works** - keep project-specific knowledge (env vars, ports, build steps, etc.)
3. **IMPROVE what's problematic** - fix outdated patterns, security issues, optimization opportunities
4. **LEARN from it** - the existing Dockerfile may contain domain knowledge you don't have

The existing Dockerfile was created by someone who understands the project. Your job is to:
- Apply modern best practices (multi-stage builds, non-root user, minimal images)
- Fix any issues the original authors may have missed
- Keep the essence of what makes it work for this specific project

## Anti-Patterns to Avoid
- Ignoring an existing Dockerfile and starting from scratch
- `COPY . .` without considering what's being copied
- Running as root in production
- Forgetting to copy lock files
- Installing dev dependencies in production
- Leaving build tools in runtime image
- Using `latest` tag
- Forgetting to copy compiled output in multi-stage

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_template = get_prompt("generator", default_prompt)

    # Incorporate specific error context if available (e.g., from AI error analysis)
    error_context = ""
    if feedback_error:
        dockerfile_fix = error_details.get("dockerfile_fix", "") if error_details else ""
        image_suggestion = error_details.get("image_suggestion", "") if error_details else ""
        
        error_context = f"""
CRITICAL: The previous Dockerfile failed validation with this error:
"{feedback_error}"

You MUST analyze this error and fix it in the new Dockerfile.
"""
        if dockerfile_fix:
            error_context += f"""
AI-SUGGESTED FIX: {dockerfile_fix}
Apply this fix to the new Dockerfile.
"""
        if image_suggestion:
            error_context += f"""
AI-SUGGESTED IMAGE: {image_suggestion}
Consider using this image strategy.
"""

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", """Stack: {stack}

Verified Base Images: {verified_tags}

Detected Build Command: {build_cmd}
Detected Start Command: {start_cmd}

Project Files (ONLY copy files that actually exist in this list):
{file_tree}

RAG-RETRIEVED CONTEXT (Most Relevant Chunks):
{file_contents}

Custom Instructions: {custom_instructions}

Generate the Dockerfile and explain your reasoning in the thought process.""")
    ])
    
    # Create the execution chain
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    file_tree_str = "\n".join(file_tree) if file_tree else "No file tree available"
    result = chain.invoke(
        {
            "stack": stack_info,
            "verified_tags": verified_tags or "None provided.  Use your best judgement.",
            "build_cmd": build_command,
            "start_cmd": start_command,
            "file_tree": file_tree_str,
            "file_contents": file_contents,
            "custom_instructions": custom_instructions,
            "error_context": error_context,
            "plan_context": plan_context,
            "retry_context": retry_context,
            "expert_context": expert_context
        },
        config={"callbacks": [callback]}
    )
    
    return result.dockerfile, result.project_type, result.thought_process, callback.get_usage()


def _generate_iterative_dockerfile(
    llm,
    context: 'AgentContext'
) -> Tuple[str, str, str, Any]:
    """
    Generates an improved Dockerfile by iterating on a previous attempt.

    This internal function handles the iterative improvement logic. It uses the
    reflection data (root cause, specific fixes) to modify the previous Dockerfile
    surgically, rather than rewriting it from scratch.

    Args:
        llm: The initialized LangChain LLM object.
        context (AgentContext): Unified context containing all project information.

    Returns:
        Tuple[str, str, str, Any]: Improved Dockerfile content, project type, thought process, usage stats.
    """
    from ..core.agent_context import AgentContext
    
    # Extract values from context
    previous_dockerfile = context.dockerfile_content
    reflection = context.reflection or {}
    stack_info = context.analysis_result.get("stack", "Unknown")
    file_contents = context.file_contents
    current_plan = context.current_plan
    custom_instructions = context.custom_instructions
    verified_tags = context.verified_tags
    build_command = context.analysis_result.get("build_command", "None detected")
    start_command = context.analysis_result.get("start_command", "None detected")
    
    # Configure the LLM to return a structured output matching the IterativeDockerfileResult schema
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Build reflection context string from the specific fixes identified
    specific_fixes = reflection.get("specific_fixes", [])
    fixes_str = "\n".join([f"  - {fix}" for fix in specific_fixes]) if specific_fixes else "No specific fixes provided"
    
    # Build updated plan guidance
    plan_guidance = ""
    if current_plan:
        plan_guidance = f"""
UPDATED PLAN BASED ON LESSONS LEARNED:
- Base Image Strategy: {current_plan.get('base_image_strategy', 'Default')}
- Build Strategy: {current_plan.get('build_strategy', 'Multi-stage')}
- Use Static Linking: {current_plan.get('use_static_linking', False)}
- Use Alpine Runtime: {current_plan.get('use_alpine_runtime', False)}
"""
    
    # Define the default system prompt for the "Iterative Improver" persona
    default_prompt = """You are the ITERATIVE GENERATOR agent in a multi-agent Dockerfile generation pipeline. You are activated when a previous Dockerfile FAILED and needs surgical fixes.

## Your Role in the Pipeline
```
Generator → Reviewer → Validator → [FAILED] → Reflector → [YOU: Iterative Generator]
                                                   ↓
                                         Root Cause Analysis
```

## Your Mission
Apply SURGICAL FIXES to the failed Dockerfile based on the Reflector's diagnosis. You are NOT rewriting from scratch - you are making targeted corrections.

## Chain-of-Thought Debugging Process

### PHASE 1: UNDERSTAND THE FAILURE
The Reflector has diagnosed:
- **Root Cause**: {root_cause}
- **Why It Failed**: {why_it_failed}
- **Lesson Learned**: {lesson_learned}

**Specific Fixes Prescribed:**
{specific_fixes}

### PHASE 2: LOCATE THE PROBLEM

**Map the error to Dockerfile line(s):**
```
Error Type → Likely Location
─────────────────────────────
"file not found"      → COPY instruction(s)
"command not found"   → RUN or ENTRYPOINT
"permission denied"   → USER/chmod/chown issue
"package not found"   → apt-get/apk/pip install
"binary won't run"    → Base image compatibility
"port already in use" → EXPOSE or app config
"connection refused"  → Network/service config
```

### PHASE 3: APPLY SURGICAL CHANGES

**Rules of Surgical Fixes:**
1. **Minimal Changes**: Touch only what's broken
2. **Preserve Working Code**: If it wasn't failing, don't change it
3. **One Fix at a Time**: Don't introduce new changes alongside fixes
4. **Verify the Fix**: Mentally trace execution to confirm

**Change Documentation Template:**
```
BEFORE: <original line>
AFTER:  <fixed line>
REASON: <why this fixes the root cause>
```

### PHASE 4: SPECIAL FIX PATTERNS

**Missing Files Fix:**
```dockerfile
# BEFORE (broken):
COPY --from=builder /app/dist ./dist

# AFTER (fixed) - copy all needed files:
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
```

**Binary Compatibility Fix:**
```dockerfile
# BEFORE (broken) - glibc binary on musl:
FROM golang:1.21 AS builder
# ... build ...
FROM alpine

# AFTER (fixed) - match libc:
FROM golang:1.21-alpine AS builder
RUN apk add --no-cache musl-dev
# ... build with CGO_ENABLED=0 or matching musl ...
FROM alpine
```

**Permission Fix:**
```dockerfile
# BEFORE (broken):
USER appuser
WORKDIR /app
COPY . .

# AFTER (fixed):
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser
```

## Strategic Guidance Updates
{image_change_guidance}
{strategy_change_guidance}
{plan_guidance}

## Available Verified Images
{verified_tags}

## Output Requirements
1. **dockerfile**: The FIXED Dockerfile
2. **changes_summary**: List of specific changes made
3. **previous_issues_addressed**: What problems were fixed
4. **confidence_in_fix**: high/medium/low
5. **fallback_strategy**: What to try if this still fails
6. **thought_process**: Your debugging reasoning

## Reference Existing Dockerfiles
If there are other Dockerfile variants in the project (Dockerfile.dev, Dockerfile.prod, etc.):
- Check if they have working solutions for similar problems
- They may contain project-specific fixes or workarounds
- Learn from their patterns but don't blindly copy - understand WHY they work

## Anti-Patterns for Iterative Fixes
- Rewriting the entire Dockerfile (that's not a fix)
- Adding workarounds without understanding root cause
- Changing working lines "just in case"
- Ignoring the Reflector's diagnosis
- Making multiple unrelated changes at once

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_template = get_prompt("generator_iterative", default_prompt)

    # Build image change guidance if recommended by reflection
    image_change_guidance = ""
    if reflection.get("should_change_base_image"):
        suggested = reflection.get("suggested_base_image", "")
        image_change_guidance = f"""
IMAGE CHANGE REQUIRED:
The reflection suggests changing the base image to: {suggested}
Apply this change to fix compatibility issues.
"""
    
    # Build strategy change guidance if recommended by reflection
    strategy_change_guidance = ""
    if reflection.get("should_change_build_strategy"):
        new_strategy = reflection.get("new_build_strategy", "")
        strategy_change_guidance = f"""
BUILD STRATEGY CHANGE REQUIRED:
New strategy: {new_strategy}
Apply this strategic change to the Dockerfile.
"""

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", """PREVIOUS DOCKERFILE (IMPROVE THIS):
{previous_dockerfile}

PROJECT CONTEXT:
Stack: {stack}
Build Command: {build_cmd}
Start Command: {start_cmd}

RAG-RETRIEVED CONTEXT (Most Relevant Chunks):
{file_contents}

Apply the specific fixes and return an improved Dockerfile.
Explain what you changed and why in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = chain.invoke(
        {
            "previous_dockerfile": previous_dockerfile,
            "root_cause": reflection.get("root_cause_analysis", "Unknown"),
            "why_it_failed": reflection.get("why_it_failed", "Unknown"),
            "lesson_learned": reflection.get("lesson_learned", "No lesson"),
            "specific_fixes": fixes_str,
            "image_change_guidance": image_change_guidance,
            "strategy_change_guidance": strategy_change_guidance,
            "plan_guidance": plan_guidance,
            "verified_tags": verified_tags or "None provided",
            "stack": stack_info,
            "build_cmd": build_command,
            "start_cmd": start_command,
            "file_contents": file_contents,
            "custom_instructions": custom_instructions
        },
        config={"callbacks": [callback]}
    )
    
    # Format the thought process for display
    thought_process = f"""ITERATIVE IMPROVEMENT:
Previous Issues Addressed: {', '.join(result.previous_issues_addressed)}
Changes Made: {', '.join(result.changes_summary)}
Confidence: {result.confidence_in_fix}
Fallback Strategy: {result.fallback_strategy or 'None'}

{result.thought_process}"""
    
    return result.dockerfile, result.project_type, thought_process, callback.get_usage()



def _get_expert_guidance(stack: str) -> str:
    """
    Returns curated expert patterns for specific stacks.
    This helps the LLM avoid common hallucinations and adhere to best practices.
    Covers all 15+ supported languages in DockAI v4.0 architecture.
    """
    stack_lower = stack.lower()
    
    # Python Ecosystem
    if "python" in stack_lower:
        return """
**PYTHON PRODUCTION PATTERNS:**
- **Env Vars**: Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` immediately after FROM.
- **Dependencies**: COPY `requirements.txt` / `pyproject.toml` / `Pipfile` separately before `COPY . .` to leverage caching.
- **Package Manager**: Use `pip install --no-cache-dir` for smaller images. For Poetry: `poetry install --no-dev --no-root`.
- **User**: Create non-root user `appuser`. Ensure `chown -R appuser:appgroup /app` is done *before* switching USER.
- **Path**: Ensure `/home/appuser/.local/bin` is in PATH if installing with `--user` flag.
- **Django**: Run `python manage.py collectstatic --noinput` and `python manage.py migrate` at runtime, NOT in build.
- **FastAPI/ASGI**: Use `uvicorn app.main:app --host 0.0.0.0 --port 8000` or `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`.
- **Flask/WSGI**: Use `gunicorn -w 4 -b 0.0.0.0:8000 app:app` for production.
- **Virtual Env**: Don't create venv in Docker - install globally in the container.
        """
    
    # Node.js/JavaScript/TypeScript Ecosystem
    if "node" in stack_lower or "javascript" in stack_lower or "typescript" in stack_lower or "next" in stack_lower or "react" in stack_lower or "vue" in stack_lower or "angular" in stack_lower:
        return """
**NODE.JS/JAVASCRIPT/TYPESCRIPT PRODUCTION PATTERNS:**
- **Node Environment**: Set `ENV NODE_ENV=production` to disable dev dependencies and enable optimizations.
- **Dependencies**: COPY `package.json` AND `package-lock.json` (or `yarn.lock`, `pnpm-lock.yaml`). Run `npm ci` (clean install), NOT `npm install`.
- **User**: Use the built-in `node` user (uid 1000). Avoid running as root: `USER node`.
- **Permissions**: If you need to write to directories: `RUN chown -R node:node /app` before switching user.
- **Next.js**: Multi-stage build: build with `npm run build`, runtime needs `.next/`, `public/`, `node_modules/`, `package.json`.
- **TypeScript**: Compile in builder stage with `npm run build` or `tsc`, copy `dist/` to runtime.
- **PM2**: If using PM2, install globally and use `pm2-runtime start ecosystem.config.js` for proper signal handling.
- **Tini**: Use `tini` as init process for proper signal handling: `ENTRYPOINT ["/sbin/tini", "--", "node", "server.js"]`.
- **Pruning**: Use `npm prune --production` after build to remove dev dependencies before copying to runtime.
        """
    
    # Go Ecosystem
    if "go" in stack_lower or "golang" in stack_lower:
        return """
**GO PRODUCTION PATTERNS:**
- **Multi-Stage**: ALWAYS use multi-stage: `golang:*-alpine` for build, `alpine` or `gcr.io/distroless/static-debian12` for runtime.
- **Static Build**: `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o /app/main .` for static binary.
- **Modules**: COPY `go.mod` and `go.sum` first, run `go mod download`, then COPY source for layer caching.
- **Security**: NEVER run as root. Use `USER nonroot:nonroot` (distroless) or create user with `adduser --disabled-password --gecos "" appuser`.
- **Certificates**: If using scratch/minimal, copy CA certs: `COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/`.
- **Timezone**: If needed: `COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo`.
- **Binary Location**: Place binary at `/app/main` or `/usr/local/bin/app` for easy execution.
        """
    
    # Rust Ecosystem
    if "rust" in stack_lower or "cargo" in stack_lower:
        return """
**RUST PRODUCTION PATTERNS:**
- **Multi-Stage**: `rust:*-alpine` or `rust:*-slim` for build, `alpine`, `debian:bookworm-slim`, or `scratch` for runtime.
- **Static Build**: For musl static: `rustup target add x86_64-unknown-linux-musl` then `cargo build --release --target x86_64-unknown-linux-musl`.
- **Dependencies**: COPY `Cargo.toml` and `Cargo.lock` first, create dummy `src/main.rs`, build deps, then copy real source.
- **Size Optimization**: Use `strip` to reduce binary size: `RUN strip /app/target/release/myapp`.
- **User**: Create non-root user. In Alpine: `RUN adduser -D -u 1000 appuser`.
- **Certificates**: Copy CA certs for HTTPS: `COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/`.
- **Actix/Rocket/Axum**: Bind to `0.0.0.0:8080`, not `localhost`, to accept external connections.
        """
    
    # Ruby Ecosystem
    if "ruby" in stack_lower or "rails" in stack_lower:
        return """
**RUBY PRODUCTION PATTERNS:**
- **Bundler**: COPY `Gemfile` and `Gemfile.lock` first, run `bundle install --without development test`, then COPY source.
- **Rails**: Run `rails assets:precompile` in builder stage. Set `RAILS_ENV=production` and `RACK_ENV=production`.
- **User**: Create non-root user and use it. `RUN useradd -m -u 1000 appuser`.
- **Puma**: Use Puma server for Rails: `bundle exec puma -C config/puma.rb`.
- **Database**: Don't run migrations in Dockerfile. Run `rails db:migrate` as a separate container/job.
- **Secrets**: Use ENV vars for `SECRET_KEY_BASE` and database credentials, never hardcode.
        """
    
    # PHP Ecosystem
    if "php" in stack_lower or "laravel" in stack_lower or "symfony" in stack_lower:
        return """
**PHP PRODUCTION PATTERNS:**
- **Image**: Use official `php:*-fpm-alpine` for FPM or `php:*-cli-alpine` for CLI apps.
- **Composer**: COPY `composer.json` and `composer.lock` first, run `composer install --no-dev --optimize-autoloader`, then COPY source.
- **Laravel**: Run `php artisan config:cache`, `php artisan route:cache`, `php artisan view:cache` in build for optimization.
- **Nginx**: For web apps, use multi-container setup or include nginx in the same image with supervisord.
- **Permissions**: Set ownership: `chown -R www-data:www-data /var/www/html` and run as `USER www-data`.
- **Extensions**: Install needed extensions: `RUN docker-php-ext-install pdo pdo_mysql opcache`.
- **OPcache**: Enable OPcache for production performance.
        """
    
    # Java Ecosystem
    if "java" in stack_lower or "spring" in stack_lower or "maven" in stack_lower or "gradle" in stack_lower:
        return """
**JAVA PRODUCTION PATTERNS:**
- **Multi-Stage**: Use `maven:*` or `gradle:*-jdk17` for build, `eclipse-temurin:17-jre` or `openjdk:17-jre-slim` for runtime.
- **Maven**: COPY `pom.xml` first, run `mvn dependency:go-offline`, then COPY `src/` and build.
- **Gradle**: COPY `build.gradle*` and `settings.gradle*` first, run `gradle dependencies --no-daemon`, then copy source.
- **Spring Boot**: Build with `mvn clean package -DskipTests`, JAR will be in `target/*.jar`. Copy to runtime as `app.jar`.
- **JVM Flags**: Set appropriate heap: `ENV JAVA_OPTS="-Xmx512m -Xms256m"` and use in ENTRYPOINT.
- **User**: Create non-root user and run as that user. Don't run Java as root.
- **Health**: Spring Boot Actuator provides `/actuator/health` - use for HEALTHCHECK.
        """
    
    # C# / .NET Ecosystem
    if "c#" in stack_lower or ".net" in stack_lower or "dotnet" in stack_lower or "aspnet" in stack_lower:
        return """
**.NET PRODUCTION PATTERNS:**
- **Multi-Stage**: Use `mcr.microsoft.com/dotnet/sdk:7.0` for build, `mcr.microsoft.com/dotnet/aspnet:7.0` for runtime.
- **Restore**: COPY `*.csproj` and `*.sln` first, run `dotnet restore`, then COPY source and `dotnet publish`.
- **Publish**: Use `dotnet publish -c Release -o /app/publish` to create optimized build.
- **User**: Use non-root user. .NET images include `app` user: `USER app`.
- **Environment**: Set `ASPNETCORE_ENVIRONMENT=Production` for production config.
- **Ports**: ASP.NET Core default port is 80/443. Expose and bind correctly: `ASPNETCORE_URLS=http://+:80`.
- **Globalization**: If you need globalization: `ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=false`.
        """
    
    # Kotlin Ecosystem
    if "kotlin" in stack_lower or "ktor" in stack_lower:
        return """
**KOTLIN PRODUCTION PATTERNS:**
- **Jvm**: Follow Java patterns for Kotlin/JVM projects (use Gradle/Maven multi-stage builds).
- **Ktor**: Build fat JAR with `gradle shadowJar` or `./gradlew build`, copy JAR to runtime.
- **Native**: For Kotlin/Native, compile to native binary and use minimal runtime image.
- **Spring Boot (Kotlin)**: Same as Java Spring Boot patterns.
- **Dependencies**: COPY build files first, fetch deps, then copy source for caching.
        """
    
    # Scala Ecosystem
    if "scala" in stack_lower or "play" in stack_lower or "akka" in stack_lower:
        return """
**SCALA PRODUCTION PATTERNS:**
- **SBT**: Use `sbt:*` for build, `eclipse-temurin:17-jre` for runtime. Build with `sbt assembly` or `sbt stage`.
- **Play Framework**: Use `sbt stage` to package, creates a startup script in `target/universal/stage/bin/`.
- **Akka HTTP**: Build fat JAR with `sbt assembly`, copy to runtime as `app.jar`.
- **JVM Settings**: Set heap appropriately for Scala apps: `-Xmx1g -Xms512m`.
- **User**: Run as non-root user.
        """
    
    # Elixir Ecosystem
    if "elixir" in stack_lower or "phoenix" in stack_lower:
        return """
**ELIXIR PRODUCTION PATTERNS:**
- **Release**: Use `mix release` for production deployment (creates self-contained release).
- **Multi-Stage**: Build in `elixir:*-alpine`, run in `alpine` with only ERTS (Erlang runtime).
- **Phoenix**: Run `mix assets.deploy` in build to compile frontend assets.
- **Env**: Set `MIX_ENV=prod` for production. Never use `mix phx.server` in prod - use releases.
- **Migrations**: Run `bin/myapp eval "MyApp.Release.migrate"` at container startup, not in Dockerfile.
- **User**: Create non-root user and run release as that user.
        """
    
    # Haskell Ecosystem
    if "haskell" in stack_lower or "ghc" in stack_lower or "stack" in stack_lower:
        return """
**HASKELL PRODUCTION PATTERNS:**
- **Stack**: Use `haskell:*` for build, compile with `stack build --copy-bins`, copy binary to minimal runtime.
- **Static**: Compile static binary for smallest image: `stack build --ghc-options='-optl-static'`.
- **Cabal**: Use cabal-install for dependency resolution and building.
- **Runtime**: Use `debian:bookworm-slim` or `alpine` with required system libs.
- **Libraries**: GHC binaries may need glibc, gmp, libffi - ensure they're in runtime image.
        """
    
    # Dart Ecosystem
    if "dart" in stack_lower or "flutter" in stack_lower:
        return """
**DART PRODUCTION PATTERNS:**
- **Server**: For Dart server apps, build with `dart compile exe bin/server.dart -o server`, copy binary to runtime.
- **Flutter Web**: Build with `flutter build web`, copy `build/web/` to nginx image and serve.
- **Flutter Mobile**: Docker isn't typical for mobile apps, but can use for CI/CD builds.
- **Dependencies**: Run `dart pub get` or `flutter pub get` before building.
        """
    
    # Swift Ecosystem
    if "swift" in stack_lower or "vapor" in stack_lower:
        return """
**SWIFT PRODUCTION PATTERNS:**
- **Vapor**: Use `swift:*` for build, compile with `swift build -c release`, copy `.build/release/App` to runtime.
- **Runtime**: Use `swift:*-slim` or Ubuntu slim with Swift runtime libraries.
- **Static Build**: For smallest image, compile release mode and use minimal runtime image.
- **Dependencies**: SPM (Swift Package Manager) resolves dependencies from `Package.swift`.
        """
    
    # Default/Generic guidance
    return """
**UNIVERSAL PRODUCTION PATTERNS:**
- **Least Privilege**: ALWAYS create and use a non-root user for security.
- **Layer Caching**: Copy dependency manifests first, install dependencies, THEN copy source code.
- **Multi-Stage Builds**: Separate build and runtime stages to ship only what's needed, not build tools.
- **.dockerignore**: Use `.dockerignore` to exclude `.git/`, tests, dev dependencies, and IDE configs.
- **Health Checks**: Implement HTTP health endpoint (`/health` or `/healthz`) and add HEALTHCHECK instruction.
- **Graceful Shutdown**: Handle SIGTERM properly for zero-downtime deployments.
    """

