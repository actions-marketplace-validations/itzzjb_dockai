"""
DockAI Adaptive Agent Module.

This module implements the core AI-driven capabilities of the DockAI system.
It is responsible for the high-level cognitive tasks that allow the agent to
adapt, plan, and learn from its interactions.

Key Responsibilities:
1.  **Strategic Planning**: Analyzing project requirements to formulate a build strategy.
2.  **Failure Reflection**: Analyzing build or runtime failures to derive actionable insights.
3.  **Health Detection**: Intelligently identifying health check endpoints within the source code.
4.  **Readiness Pattern Analysis**: Determining how to detect when an application is ready to serve traffic.
5.  **Iterative Improvement**: Refining Dockerfiles based on feedback loops.

The components in this module leverage Large Language Models (LLMs) to simulate
the reasoning process of a human DevOps engineer.
"""

import os
import re
import logging
from typing import Tuple, Any, List, Dict, Optional, TYPE_CHECKING

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import (
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult,
    RuntimeConfigResult,
    BlueprintResult
)
from ..utils.callbacks import TokenUsageCallback
from ..utils.rate_limiter import with_rate_limit_handling
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from ..core.agent_context import AgentContext

# Initialize the logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """
    Safely invoke a LangChain chain with rate limit handling.
    
    This wrapper adds automatic retry with exponential backoff for rate limit errors.
    
    Args:
        chain: The LangChain chain to invoke
        input_data: Input data dictionary
        callbacks: List of callbacks
        
    Returns:
        Chain invocation result
    """
    return chain.invoke(input_data, config={"callbacks": callbacks})





def reflect_on_failure(context: 'AgentContext') -> Tuple[ReflectionResult, Dict[str, int]]:
    """
    Analyzes a failed Dockerfile build or run to determine the root cause and solution.

    This function implements the "reflection" capability of the agent. When a failure
    occurs, it doesn't just blindly retry. Instead, it analyzes the error logs,
    the problematic Dockerfile, and the project context to understand *why* it failed
    and *how* to fix it.

    Args:
        dockerfile_content (str): The content of the Dockerfile that caused the failure.
        error_message (str): The primary error message returned by the Docker daemon or CLI.
        error_details (Dict[str, Any]): Additional structured details about the error
            (e.g., error code, stage where it failed).
        analysis_result (Dict[str, Any]): The original project analysis context.
        retry_history (List[Dict[str, Any]], optional): History of previous attempts to
            avoid cyclic failures. Defaults to None.
        container_logs (str, optional): Runtime logs from the container if the failure
            occurred after the build phase. Defaults to "".

    Returns:
        Tuple[ReflectionResult, Dict[str, int]]: A tuple containing:
            - The structured reflection result (ReflectionResult object) with specific fixes.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the reflector agent
    llm = create_llm(agent_name="reflector", temperature=0)
    
    # Configure structured output for consistent parsing of the reflection
    structured_llm = llm.with_structured_output(ReflectionResult)
    
    # Construct the history of previous failures to provide context
    retry_context = ""
    if context.retry_history and len(context.retry_history) > 0:
        retry_context = "\n\nPREVIOUS FAILED ATTEMPTS:\n"
        for i, attempt in enumerate(context.retry_history, 1):
            retry_context += f"""
Attempt {i}: {attempt.get('what_was_tried', 'Unknown')} -> Failed: {attempt.get('why_it_failed', 'Unknown')}
"""
    
    # Define the default system prompt for the "Principal DevOps Engineer" persona
    default_prompt = """You are the REFLECTOR agent in a multi-agent Dockerfile generation pipeline. You are activated when the Validator reports a FAILURE - your diagnosis guides the next iteration.

## Your Role in the Pipeline
```
Generator → Reviewer → Validator → [FAILED] → [YOU: Reflector] → Iterative Generator
                            ↓                       ↓
                      Error + Logs          Root Cause Analysis
```

## Your Mission
Perform forensic analysis of the failure to provide:
1. Precise ROOT CAUSE (not symptoms)
2. Specific FIXES for the Iterative Generator
3. Strategic RECOMMENDATIONS if fundamental changes needed

## Chain-of-Thought Failure Analysis

### PHASE 1: EVIDENCE COLLECTION
**From the error message and logs, extract:**
```
1. Error type: Build failure vs Runtime failure
2. Error phase: Which Dockerfile instruction failed?
3. Error message: Exact text of the error
4. Context: What was happening when it failed?
```

### PHASE 2: ERROR PATTERN MATCHING

**BUILD-TIME FAILURES:**
```
Error Pattern                    | Root Cause                      | Fix Direction
─────────────────────────────────┼─────────────────────────────────┼──────────────────────
"No such file or directory"      | Missing COPY source             | Add COPY instruction
"Package not found"              | Wrong package name/repo         | Fix package name or add repo
"Command not found"              | Tool not installed              | Add installation step
"Permission denied"              | File permissions                | Fix chmod/chown
"Unable to resolve dependency"   | Dependency conflict/missing     | Fix version or add dep
"COPY failed: file not found"    | Source file doesn't exist       | Verify file in context
```

**RUNTIME FAILURES:**
```
Error Pattern                    | Root Cause                      | Fix Direction
─────────────────────────────────┼─────────────────────────────────┼──────────────────────
"No such file or directory"      | Binary/file not copied          | Add to multi-stage COPY
"GLIBC not found"                | Alpine vs glibc mismatch        | Match base images or static link
"Module not found"               | Dependencies not installed      | Ensure deps in runtime
"Connection refused"             | Service not ready/wrong port    | Fix networking/wait
"Killed" (OOM)                   | Memory limit exceeded           | Increase limit or optimize
Segfault/core dump               | Binary incompatibility          | Rebuild for target arch
```

### PHASE 3: ROOT CAUSE ISOLATION

**The 5 Whys Method:**
```
Symptom: "node: not found"
Why 1: The node binary isn't in PATH → Why?
Why 2: Node.js isn't installed in runtime image → Why?
Why 3: Multi-stage build only copied app, not node → Why?
Why 4: Runtime image is alpine/scratch without node → Why?
Why 5: Generator didn't account for interpreted language needs

ROOT CAUSE: Interpreted language (Node.js) requires runtime, but was treated like compiled binary
FIX: Use node base image for runtime, not scratch/alpine
```

### PHASE 4: FIX PRESCRIPTION

**Your fix must be:**
1. **Specific**: Exact Dockerfile changes, not vague suggestions
2. **Actionable**: The Iterative Generator can apply directly
3. **Complete**: Addresses root cause, not just symptoms
4. **Verified**: You've mentally traced that it would work

**Fix Template:**
```
SPECIFIC FIX #1:
  Line/Section: [exact location]
  Current: [what it says now]
  Change to: [exact replacement]
  Why: [how this addresses root cause]
```

### PHASE 5: STRATEGIC ASSESSMENT

**Answer these questions:**
1. Is the base image strategy fundamentally wrong?
   → If yes, recommend `should_change_base_image=True`
   
2. Is the build approach (multi-stage, etc.) wrong?
   → If yes, recommend `should_change_build_strategy=True`
   
3. Was this a minor fixable error or systemic issue?
   → If systemic, recommend `needs_reanalysis=True`

## Previous Attempts (Learn from history)
{retry_context}

## Output Requirements
1. **root_cause_analysis**: Deep explanation of WHY it failed
2. **specific_fixes**: List of exact changes to make
3. **confidence_score**: 0.0-1.0 confidence in diagnosis
4. **should_change_base_image**: Boolean + suggested_base_image
5. **should_change_build_strategy**: Boolean + new_build_strategy
6. **needs_reanalysis**: Boolean if Analyzer needs to re-run
7. **lesson_learned**: What to remember for future attempts

## Anti-Patterns to Avoid
- Surface-level diagnosis ("add the missing file")
- Multiple possible causes without narrowing down
- Fixes that don't match the root cause
- Vague recommendations ("try a different approach")
- Ignoring retry history and repeating failed fixes
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("reflector", default_prompt)

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze this failed Dockerfile and provide a detailed reflection.

FAILED DOCKERFILE:
{dockerfile}

ERROR MESSAGE:
{error_message}

ERROR CLASSIFICATION:
Type: {error_type}
Suggestion: {error_suggestion}

PROJECT CONTEXT:
Stack: {stack}
Project Type: {project_type}

CONTAINER LOGS:
{container_logs}

Perform a deep analysis and provide specific fixes.
Start by explaining your root cause analysis in the thought process.""")
    ])
    
    # Create the chain
    chain = prompt | structured_llm
    
    # Initialize token usage tracking
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "dockerfile": context.dockerfile_content,
            "error_message": context.error_message,
            "error_type": context.error_details.get("error_type", "unknown") if context.error_details else "unknown",
            "error_suggestion": context.error_details.get("suggestion", "None") if context.error_details else "None",
            "stack": context.analysis_result.get("stack", "Unknown"),
            "project_type": context.analysis_result.get("project_type", "service"),
            "container_logs": context.container_logs[:3000] if context.container_logs else "No logs available",
            "retry_context": retry_context
        },
        [callback]
    )
    
    return result, callback.get_usage()




def generate_iterative_dockerfile(context: 'AgentContext') -> Tuple[IterativeDockerfileResult, Dict[str, int]]:
    """
    Generates an improved Dockerfile by applying fixes identified in the reflection phase.

    This function represents the "iterative improvement" capability. It takes a
    failed Dockerfile and the analysis of why it failed (reflection), and produces
    a new version that addresses the specific issues while preserving what worked.

    Args:
        previous_dockerfile (str): The content of the failed Dockerfile.
        reflection (Dict[str, Any]): The structured reflection result containing
            root cause analysis and specific fix instructions.
        analysis_result (Dict[str, Any]): The original project analysis context.
        file_contents (str): Content of critical files to provide context.
        current_plan (Dict[str, Any]): The current build strategy/plan.
        verified_tags (str, optional): A list of verified Docker image tags to ensure
            valid base images are used. Defaults to "".
        custom_instructions (str, optional): User-provided instructions. Defaults to "".

    Returns:
        Tuple[IterativeDockerfileResult, Dict[str, int]]: A tuple containing:
            - The result containing the improved Dockerfile (IterativeDockerfileResult object).
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the iterative improver agent
    llm = create_llm(agent_name="iterative_improver", temperature=0)
    
    # Configure the LLM to return a structured output matching the IterativeDockerfileResult schema
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Define the default system prompt for the "Senior Docker Engineer" persona
    default_prompt = """You are the ITERATIVE IMPROVER agent in a multi-agent Dockerfile generation pipeline. You are the surgeon who applies precise fixes based on the Reflector's diagnosis.

## Your Role in the Pipeline
```
Validator → [FAILED] → Reflector → [YOU: Iterative Improver] → Generator (bypass)
                           ↓                    ↓
                  Root Cause Analysis    Surgical Fix Applied
```

## Your Mission
Apply PRECISE SURGICAL FIXES to the failed Dockerfile. You receive detailed diagnosis from the Reflector - your job is to execute the fix accurately.

## Chain-of-Thought Fix Application

### PHASE 1: PARSE THE DIAGNOSIS

**From the Reflector:**
- Root cause: {root_cause}
- Specific fixes prescribed: {specific_fixes}
- Image change needed: {should_change_base_image} → {suggested_base_image}
- Strategy change needed: {should_change_build_strategy} → {new_build_strategy}

### PHASE 2: SURGICAL FIX PATTERNS

**Missing File Fix:**
```dockerfile
# Problem: File not found in runtime
# Fix: Add COPY instruction
COPY --from=builder /app/missing-file ./
```

**Binary Compatibility Fix:**
```dockerfile
# Problem: GLIBC not found on Alpine
# Option A: Use matching builder
FROM golang:1.21-alpine AS builder
CGO_ENABLED=0 go build -ldflags="-s -w" ...

# Option B: Use compatible runtime
FROM debian:bookworm-slim
```

**Permission Fix:**
```dockerfile
# Problem: Permission denied
# Fix: Set ownership before USER
COPY --chown=appuser:appgroup . .
RUN chown -R appuser:appgroup /app
USER appuser
```

**Dependency Fix:**
```dockerfile
# Problem: Module/package not found
# Fix: Ensure installation in correct stage
RUN npm ci --only=production  # Runtime deps
# OR
COPY --from=builder /app/node_modules ./node_modules
```

### PHASE 3: APPLY WITH CONTEXT

**Plan Guidance:**
- Base image strategy: {base_image_strategy}
- Build strategy: {build_strategy}
- Multi-stage: {use_multi_stage}
- Minimal runtime: {use_minimal_runtime}
- Static linking: {use_static_linking}

**Verified Images Available:**
{verified_tags}

### PHASE 4: VERIFY FIX COMPLETENESS

**Checklist before outputting:**
- [ ] Does the fix address the ROOT CAUSE?
- [ ] Are all related changes included?
- [ ] Will this break anything that was working?
- [ ] Have I documented what changed and why?

## Output Requirements
1. **dockerfile**: The complete FIXED Dockerfile
2. **thought_process**: Your fix reasoning
3. **changes_summary**: What you changed
4. **confidence_in_fix**: HIGH/MEDIUM/LOW
5. **fallback_strategy**: What to try if this still fails

## Principles of Surgical Fixes
- **Minimal**: Change only what's necessary
- **Targeted**: Address the specific root cause
- **Complete**: Include all related changes
- **Documented**: Explain every modification

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("iterative_improver", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Improve this Dockerfile based on the reflection.

PREVIOUS DOCKERFILE (FIX THIS):
{previous_dockerfile}

PROJECT CONTEXT:
Stack: {stack}
Build Command: {build_command}
Start Command: {start_command}

KEY FILES:
{file_contents}

Apply the fixes and return an improved Dockerfile.
Explain your changes in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "previous_dockerfile": context.dockerfile_content,
            "root_cause": context.reflection.get("root_cause_analysis", "Unknown") if context.reflection else "Unknown",
            "specific_fixes": ", ".join(context.reflection.get("specific_fixes", [])) if context.reflection else "",
            "should_change_base_image": context.reflection.get("should_change_base_image", False) if context.reflection else False,
            "suggested_base_image": context.reflection.get("suggested_base_image", "") if context.reflection else "",
            "should_change_build_strategy": context.reflection.get("should_change_build_strategy", False) if context.reflection else False,
            "new_build_strategy": context.reflection.get("new_build_strategy", "") if context.reflection else "",
            "base_image_strategy": context.current_plan.get("base_image_strategy", "") if context.current_plan else "",
            "build_strategy": context.current_plan.get("build_strategy", "") if context.current_plan else "",
            "use_multi_stage": context.current_plan.get("use_multi_stage", True) if context.current_plan else True,
            "use_minimal_runtime": context.current_plan.get("use_minimal_runtime", False) if context.current_plan else False,
            "use_static_linking": context.current_plan.get("use_static_linking", False) if context.current_plan else False,
            "verified_tags": context.verified_tags,
            "stack": context.analysis_result.get("stack", "Unknown"),
            "build_command": context.analysis_result.get("build_command", "None"),
            "start_command": context.analysis_result.get("start_command", "None"),
            "file_contents": context.file_contents,
            "custom_instructions": context.custom_instructions
        },
        [callback]
    )
    
    return result, callback.get_usage()


def create_blueprint(context: 'AgentContext') -> Tuple[BlueprintResult, Dict[str, int]]:
    """
    Generates a complete architectural blueprint (Plan + Runtime Config) in one pass.
    
    This function combines the logic of 'create_plan' and 'detect_runtime_config'
    to significantly reduce token usage and latency by sharing the file content context.
    
    Args:
        context (AgentContext): Unified context containing file contents and analysis results.
        
    Returns:
        Tuple[BlueprintResult, Dict[str, int]]: A tuple containing:
            - The combined blueprint result.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the blueprint agent (it's the primary persona)
    llm = create_llm(agent_name="blueprint", temperature=0.2)
    
    # Configure the LLM to return a structured output matching the BlueprintResult schema
    structured_llm = llm.with_structured_output(BlueprintResult)
    
    # Construct retry context if available
    retry_context = ""
    if context.retry_history and len(context.retry_history) > 0:
        retry_context = "\n\nPREVIOUS ATTEMPTS (LEARN FROM THESE):\n"
        for i, attempt in enumerate(context.retry_history, 1):
            retry_context += f"""
--- Attempt {i} ---
What was tried: {attempt.get('what_was_tried', 'Unknown')}
Why it failed: {attempt.get('why_it_failed', 'Unknown')}
Lesson learned: {attempt.get('lesson_learned', 'Unknown')}
"""
    
    # Define the default system prompt for the "Chief Architect" persona
    default_prompt = """You are the BLUEPRINT agent in a multi-agent Dockerfile generation pipeline. You are AGENT 2 of 8 - the Chief Architect who creates the strategic blueprint that guides all downstream agents.

## Your Role in the Pipeline
```
Analyzer → [YOU: Blueprint Architect] → Generator → Reviewer → Validator
                    ↓
     Strategic Plan + Runtime Configuration
```

Your blueprint DIRECTLY guides the Generator. A poor plan = a poor Dockerfile. Be thorough and strategic.

## Your Mission
Analyze the source code to produce a COMPLETE BLUEPRINT containing:
1. **Strategic Build Plan**: How to build the image (base images, stages, dependencies).
2. **Runtime Configuration**: How to run and check the container (health endpoints, startup patterns).

## Chain-of-Thought Blueprint Process

### PHASE 1: BASE IMAGE STRATEGY
Determine the optimal base image(s):
```
Decision Tree:
├── Compiled Language (Go, Rust, C++)
│   ├── Build Stage: Full SDK (golang:1.21, rust:latest)
│   └── Runtime: Minimal (scratch, distroless, alpine)
│
├── Interpreted Language (Python, Node, Ruby)
│   ├── Build Stage: Full image with build tools
│   └── Runtime: Slim variant (python:3.11-slim, node:20-slim)
│
├── JVM Language (Java, Kotlin, Scala)
│   ├── Build Stage: Maven/Gradle with JDK
│   └── Runtime: JRE only (eclipse-temurin:21-jre-alpine)
│
└── Static Site (HTML, JS, CSS)
    ├── Build Stage: Node for building
    └── Runtime: nginx:alpine or caddy:alpine
```

**Base Image Selection Criteria:**
1. Security: Fewer packages = smaller attack surface
2. Size: Smaller = faster pulls, less storage
3. Compatibility: glibc vs musl (alpine)
4. Updates: Official images with active maintenance

### PHASE 2: BUILD STRATEGY
Decide the build approach:
```
Multi-Stage (RECOMMENDED for production):
├── Pros: Smaller images, no build tools in runtime
├── Use when: Any compiled language, bundled JS apps
└── Pattern: builder → runtime

Single-Stage (Simpler but larger):
├── Pros: Simpler Dockerfile, faster builds
├── Use when: Simple interpreted apps, development
└── Pattern: install deps → copy code → run
```

**Dependency Analysis:**
```
Build-time only:          Runtime required:
├── Compilers (gcc)       ├── Interpreters (python, node)
├── Build tools (make)    ├── Native libraries (libpq)
├── Dev headers (*-dev)   ├── Application code
└── Test frameworks       └── Configuration files
```

### PHASE 3: HEALTH & READINESS DETECTION
Analyze the codebase for runtime signals:

**Health Endpoint Detection:**
```python
# Look for patterns like:
@app.get("/health")      # FastAPI/Flask
app.get('/health', ...)  # Express
http.HandleFunc("/health", ...) # Go
@GetMapping("/health")   # Spring Boot
```

**Startup Pattern Detection:**
```
Log patterns that indicate "ready":
├── "Server listening on port"
├── "Application started"
├── "Ready to accept connections"
├── "Listening on 0.0.0.0:"
└── Framework-specific patterns
```

**Timing Estimates:**
```
Language/Framework    Typical Startup
──────────────────────────────────────
Go/Rust              < 1 second
Node.js              1-3 seconds
Python/Flask         1-5 seconds
Java/Spring Boot     10-60 seconds
```

### PHASE 4: SECURITY CONSIDERATIONS
Plan security hardening:
```
1. Non-root user: Create appuser with minimal permissions
2. Read-only filesystem: Where possible
3. No secrets in image: Use runtime environment
4. Minimal packages: Only what's needed
5. Specific versions: Pin base images, no :latest
```

### PHASE 5: LAYER OPTIMIZATION
Plan for efficient caching:
```
Layer Order (rarely changes → frequently changes):
1. Base image selection
2. System package installation  
3. Language dependency installation (package.json, requirements.txt)
4. Source code copy
5. Build commands
6. Runtime configuration
```

## Previous Attempts (Learn from history)
{retry_context}

## Critical Outputs for Downstream Agents

Your Blueprint MUST provide clear answers for:

**Build Plan:**
1. **base_image_strategy**: Specific images with versions (e.g., "python:3.11-slim for both")
2. **build_strategy**: Detailed approach (e.g., "Multi-stage: poetry install → gunicorn runtime")
3. **use_multi_stage**: Boolean decision with reasoning
4. **dependency_install_strategy**: How to install deps efficiently
5. **security_hardening**: Specific measures to implement
6. **layer_optimization**: Caching strategy
7. **potential_challenges**: What might go wrong
8. **mitigation_strategies**: How to prevent issues

**Runtime Config:**
1. **primary_health_endpoint**: Path, port, method, expected response
2. **startup_success_patterns**: Log patterns indicating readiness
3. **startup_failure_patterns**: Log patterns indicating problems
4. **estimated_startup_time**: How long to wait before checking

## Anti-Patterns to Avoid
- Choosing `alpine` for glibc-dependent apps
- Using `:latest` tags (not reproducible)
- Recommending single-stage for compiled languages
- Ignoring build vs runtime dependency separation
- Missing health endpoints that clearly exist in code
- Underestimating startup times for JVM apps
- Not considering CI/CD cache implications

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("blueprint", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Create a complete Dockerfile Blueprint.

PROJECT CONTEXT:
Stack: {stack}
Project Type: {project_type}
Suggested Base Image: {suggested_base_image}
Build Command: {build_command}
Start Command: {start_command}

FILE CONTENTS:
{file_contents}

Generate the Strategic Plan and Runtime Configuration.
Explain your complete reasoning in the thought process.""")
    ])

    
    # Create the execution chain
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = safe_invoke_chain(
        chain,
        {
            "stack": context.analysis_result.get("stack", "Unknown"),
            "project_type": context.analysis_result.get("project_type", "service"),
            "suggested_base_image": context.analysis_result.get("suggested_base_image", ""),
            "build_command": context.analysis_result.get("build_command", "None detected"),
            "start_command": context.analysis_result.get("start_command", "None detected"),
            "file_contents": context.file_contents,
            "retry_context": retry_context,
            "custom_instructions": context.custom_instructions or ""
        },
        [callback]
    )

    
    return result, callback.get_usage()
