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
    IterativeDockerfileResult
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


def create_plan(context: 'AgentContext') -> Tuple[PlanningResult, Dict[str, int]]:
    """
    Generates a strategic plan for Dockerfile creation using AI analysis.

    This function acts as the "architect" phase of the process. Before writing any code,
    it analyzes the project structure, requirements, and any previous failures to
    formulate a robust build strategy.

    Args:
        context (AgentContext): Unified context containing all project information,
            file tree, analysis results, retry history, and custom instructions.

    Returns:
        Tuple[PlanningResult, Dict[str, int]]: A tuple containing:
            - The structured planning result (PlanningResult object).
            - A dictionary tracking token usage for cost monitoring.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the planner agent
    llm = create_llm(agent_name="planner", temperature=0.2)
    
    # Configure the LLM to return a structured output matching the PlanningResult schema
    structured_llm = llm.with_structured_output(PlanningResult)
    
    # Construct the context from previous retry attempts to facilitate learning
    retry_context = ""
    if context.retry_history and len(context.retry_history) > 0:
        retry_context = "\n\nPREVIOUS ATTEMPTS (LEARN FROM THESE):\n"
        for i, attempt in enumerate(context.retry_history, 1):
            retry_context += f"""
--- Attempt {i} ---
What was tried: {attempt.get('what_was_tried', 'Unknown')}
Why it failed: {attempt.get('why_it_failed', 'Unknown')}
Lesson learned: {attempt.get('lesson_learned', 'Unknown')}
Error type: {attempt.get('error_type', 'Unknown')}
"""
        retry_context += "\nDO NOT repeat the same mistakes. Apply the lessons learned."
    
    # Define the default system prompt for the DevOps Architect persona
    default_prompt = """You are the PLANNER agent in a multi-agent Dockerfile generation pipeline. You are AGENT 2 of 10 - the strategic architect that guides all downstream generation.

## Your Role in the Pipeline
```
Analyzer → [YOU: Planner] → Generator → Reviewer → Validator → (Reflector if failed)
         ↑                         ↓
    Analysis Result          Strategic Plan (your output)
```

## Your Mission
Create a battle-tested strategic plan BEFORE any Dockerfile code is written. You are the chess grandmaster - think 5 moves ahead.

## Chain-of-Thought Strategic Planning

### PHASE 1: DIGEST UPSTREAM ANALYSIS
The Analyzer has provided:
- Stack: {stack}
- Project Type: {project_type}
- Build/Start Commands: Your execution blueprint

**Ask yourself:**
- Does this analysis make sense? Any red flags?
- What implicit requirements weren't stated?
- What could the Analyzer have missed?

### PHASE 2: ARCHITECTURE DECISION TREE

```
Is it COMPILED? (Go, Rust, C++, Java)
├─ YES → Multi-stage build essential
│       ├─ Builder stage: Full toolchain
│       └─ Runtime stage: Minimal (scratch, distroless, alpine)
│
└─ NO → Single or multi-stage based on complexity
        ├─ Node/Python/Ruby: Consider multi-stage for smaller images
        └─ Simple scripts: Single stage may suffice
```

```
Runtime linking strategy:
├─ Static binary (Go, Rust with musl) → Can use scratch/distroless
├─ Dynamic binary (C++, most compiled) → Match libc (glibc vs musl)
└─ Interpreted (Python, Node) → Include interpreter in runtime
```

### PHASE 3: BASE IMAGE STRATEGY

**Decision Matrix:**
| Requirement | Recommended Base |
|-------------|------------------|
| Smallest possible | scratch (static binaries only) |
| Minimal + shell | distroless or alpine |
| Compatibility | debian-slim, ubuntu |
| Specific runtime | Official language images (node:20-alpine) |
| Security scanning | Use official, tagged images |

**Anti-patterns:**
- `latest` tag (non-reproducible)
- Full OS images (ubuntu, debian) when slim/alpine works
- Alpine for glibc-dependent apps
- Mixing distro families between stages

### PHASE 4: ANTICIPATE FAILURE MODES

**Common failure patterns to plan against:**
```
1. Missing source files in runtime stage
   → Plan explicit COPY instructions
   
2. Binary compatibility (built on glibc, running on musl)
   → Plan matching base images or static linking
   
3. Missing native dependencies at runtime
   → Plan to identify runtime vs build-time deps
   
4. Permission issues (root vs non-root)
   → Plan USER instruction and directory ownership
   
5. Missing environment variables
   → Plan ENV or document required runtime vars
```

### PHASE 5: LEARNING FROM HISTORY
{retry_context}

**If retrying, you MUST:**
1. Acknowledge what failed before
2. Explain WHY that approach was wrong
3. Describe how your new plan avoids that mistake
4. Consider if a fundamentally different approach is needed

## Output Contract for Generator Agent

Your plan MUST clearly specify:
1. **base_image_strategy**: Exact image:tag recommendations with rationale
2. **build_strategy**: Step-by-step build approach
3. **use_multi_stage**: true/false with justification
4. **use_minimal_runtime**: true/false based on requirements
5. **use_static_linking**: true/false for compiled languages
6. **potential_challenges**: What could go wrong
7. **mitigation_strategies**: How to prevent/handle each challenge
8. **thought_process**: Your complete reasoning chain

## Strategic Principles
- **Separation of Concerns**: Build tools ≠ Runtime tools
- **Minimal Attack Surface**: Every extra binary is a potential CVE
- **Reproducibility**: Pinned versions, locked dependencies
- **Fail Fast**: Catch issues in build, not production
- **Security by Default**: Non-root, no secrets baked in

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("planner", default_prompt)

    # Create the chat prompt template combining system instructions and user input
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Create a strategic plan for generating a Dockerfile.

PROJECT ANALYSIS:
Stack: {stack}
Project Type: {project_type}
Suggested Base Image: {suggested_base_image}
Build Command: {build_command}
Start Command: {start_command}

KEY FILE CONTENTS:
{file_contents}

Generate a comprehensive plan that will guide the Dockerfile generation.
Start by explaining your thought process in detail.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain with the provided context (with rate limit handling)
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
            "custom_instructions": context.custom_instructions
        },
        [callback]
    )
    
    return result, callback.get_usage()



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


def detect_health_endpoints(context: 'AgentContext') -> Tuple[HealthEndpointDetectionResult, Dict[str, int]]:
    """
    Scans source code to identify potential health check endpoints and port configurations.

    This function uses AI to "read" the code, looking for common patterns that indicate
    where the application exposes its health status (e.g., /health, /ready). It also
    looks for port configurations to ensure the Dockerfile exposes the correct port.

    Args:
        file_contents (str): The raw content of the source files to be analyzed.
        analysis_result (Dict[str, Any]): The results from the initial project analysis.

    Returns:
        Tuple[HealthEndpointDetectionResult, Dict[str, int]]: A tuple containing:
            - The detection result (HealthEndpointDetectionResult object) with found endpoints.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the health detector agent
    llm = create_llm(agent_name="health_detector", temperature=0)
    
    # Configure the LLM to return a structured output matching the HealthEndpointDetectionResult schema
    structured_llm = llm.with_structured_output(HealthEndpointDetectionResult)
    
    # Define the default system prompt for the "Code Analyst" persona
    default_prompt = """You are the HEALTH DETECTOR agent in a multi-agent Dockerfile generation pipeline. Your analysis enables proper HEALTHCHECK instructions.

## Your Role in the Pipeline
```
Analyzer → [YOU: Health Detector] → Planner → Generator
                   ↓
         Health endpoint info for HEALTHCHECK instruction
```

## Your Mission
Analyze source code to discover:
1. Health check endpoints (URLs the container can hit to verify it's healthy)
2. Port configurations (what port the app listens on)
3. Protocol information (HTTP, TCP, gRPC)

## Chain-of-Thought Discovery Process

### PHASE 1: IDENTIFY APPLICATION TYPE

```
Type              | Health Check Approach
──────────────────┼─────────────────────────────────────
Web Server/API    | HTTP endpoint (GET /health, /healthz, /ready)
gRPC Service      | gRPC health check protocol
TCP Service       | TCP port check
Worker/Consumer   | Custom health file or no health check
CLI/Script        | No health check needed (exit code)
```

### PHASE 2: FRAMEWORK-SPECIFIC PATTERNS

**Node.js / Express:**
```javascript
// Look for patterns like:
app.get('/health', (req, res) => res.send('OK'))
app.get('/api/health', healthController.check)
router.get('/healthz', ...)
// Port patterns:
app.listen(3000)
const PORT = process.env.PORT || 3000
```

**Python / Flask / Django / FastAPI:**
```python
# Flask:
@app.route('/health')
# Django:
path('health/', health_check_view)
# FastAPI:
@app.get("/health")
# Port patterns:
app.run(port=8000)
uvicorn.run(app, port=8000)
```

**Go:**
```go
// Look for patterns like:
http.HandleFunc("/health", healthHandler)
http.HandleFunc("/healthz", ...)
mux.HandleFunc("/ready", ...)
// Port patterns:
http.ListenAndServe(":8080", ...)
```

**Java / Spring:**
```java
// Spring Boot Actuator:
@GetMapping("/actuator/health")
// Custom:
@GetMapping("/health")
// Port: server.port=8080
```

### PHASE 3: COMMON HEALTH ENDPOINT NAMES

**Priority order (most to least common):**
```
1. /health         - Most universal
2. /healthz        - Kubernetes convention
3. /ready          - Readiness check
4. /readiness      - Alternative readiness
5. /live           - Liveness check
6. /liveness       - Alternative liveness
7. /ping           - Simple availability
8. /status         - Status endpoint
9. /api/health     - API-prefixed
10. /actuator/health - Spring Boot
```

### PHASE 4: PORT DETECTION

**Search patterns by framework:**
```
Environment Variables:
  PORT, APP_PORT, SERVER_PORT, HTTP_PORT

Config Files:
  - package.json: "start": "... --port 3000"
  - config.json/yaml: port: 8080
  - .env: PORT=3000
  
Code Patterns:
  - .listen(3000)
  - :8080
  - port=8000
  - server.port=
```

### PHASE 5: CONFIDENCE ASSESSMENT

```
Confidence Level | Evidence Required
─────────────────┼────────────────────────────────────
HIGH             | Explicit health endpoint in code
MEDIUM           | Framework default or config file
LOW              | Inferred from framework conventions
NONE             | No evidence found
```

## Output Requirements
1. **health_endpoint**: The URL path (e.g., "/health")
2. **port**: The port number (e.g., 8080)
3. **protocol**: HTTP, TCP, or gRPC
4. **confidence**: HIGH, MEDIUM, LOW, NONE
5. **thought_process**: How you found this information

## Anti-Patterns to Avoid
- Guessing standard ports without evidence
- Assuming /health exists without seeing it in code
- Missing framework-specific conventions
- Ignoring environment variable port configurations
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("health_detector", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze these files to detect health check endpoints.

STACK: {stack}

FILE CONTENTS:
{file_contents}

Find any health check endpoints and their port configurations.
Explain your reasoning in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "stack": context.analysis_result.get("stack", "Unknown"),
            "file_contents": context.file_contents
        },
        [callback]
    )
    
    return result, callback.get_usage()


def detect_readiness_patterns(context: 'AgentContext') -> Tuple[ReadinessPatternResult, Dict[str, int]]:
    """
    Analyzes application logs and code to determine how to detect when the app is ready.

    Instead of relying on arbitrary sleep times, this function identifies the specific
    log messages or output patterns that signify a successful startup (e.g., "Server
    running on port 8080"). It also identifies failure patterns to fail fast.

    Args:
        file_contents (str): The content of the source files.
        analysis_result (Dict[str, Any]): The results from the initial project analysis.

    Returns:
        Tuple[ReadinessPatternResult, Dict[str, int]]: A tuple containing:
            - The readiness pattern result (ReadinessPatternResult object) with regex patterns.
            - A dictionary tracking token usage.
    """
    from ..core.agent_context import AgentContext
    
    # Create LLM using the provider factory for the readiness detector agent
    llm = create_llm(agent_name="readiness_detector", temperature=0)
    
    # Configure the LLM to return a structured output matching the ReadinessPatternResult schema
    structured_llm = llm.with_structured_output(ReadinessPatternResult)
    
    # Define the default system prompt for the "Startup Pattern Expert" persona
    default_prompt = """You are the READINESS DETECTOR agent in a multi-agent Dockerfile generation pipeline. Your patterns enable the Validator to know when the app is ready.

## Your Role in the Pipeline
```
Analyzer → [YOU: Readiness Detector] → Validator
                    ↓
         Log patterns to detect "app is ready" vs "app failed"
```

## Your Mission
Analyze source code to discover:
1. **Success patterns**: Log messages that mean "application started successfully"
2. **Failure patterns**: Log messages that mean "startup failed"
3. **Timing estimates**: How long startup typically takes

## Chain-of-Thought Pattern Discovery

### PHASE 1: UNDERSTAND STARTUP SEQUENCE

**What happens when this app starts?**
```
1. Load configuration
2. Initialize dependencies (DB connections, caches)
3. Start server/bind to port
4. Log "ready" message
```

### PHASE 2: FRAMEWORK-SPECIFIC SUCCESS PATTERNS

**Node.js / Express:**
```javascript
// Common success patterns:
console.log('Server listening on port 3000')
console.log('App started successfully')
app.listen(PORT, () => console.log(`Running on ${{PORT}}`))
// Regex: /listening on port \\d+/i, /server (started|running)/i
```

**Python / Flask / Django / FastAPI:**
```python
# Flask:
print(" * Running on http://127.0.0.1:5000")
# Django:
"Starting development server at http://..."
# FastAPI/Uvicorn:
"Uvicorn running on http://0.0.0.0:8000"
"Application startup complete"
# Regex: /running on|started at|startup complete/i
```

**Go:**
```go
// Common patterns:
log.Println("Server started on :8080")
fmt.Println("Listening on port 8080")
// Regex: /listening|started|ready/i
```

**Java / Spring:**
```java
// Spring Boot:
"Started Application in X.XXX seconds"
"Tomcat started on port(s): 8080"
// Regex: /Started .* in \\d+.*seconds|Tomcat started/i
```

### PHASE 3: COMMON FAILURE PATTERNS

```
Pattern Type          | Regex Pattern
──────────────────────┼────────────────────────────────────
Fatal errors          | /fatal|panic|exception|error:/i
Connection failures   | /connection refused|cannot connect|ECONNREFUSED/i
Missing dependencies  | /module not found|import error|no such file/i
Port conflicts        | /address already in use|EADDRINUSE/i
Permission issues     | /permission denied|EACCES/i
Configuration errors  | /invalid config|missing required/i
```

### PHASE 4: TIMING ESTIMATION

```
Application Type      | Typical Startup Time
──────────────────────┼─────────────────────
Simple Node.js        | 1-3 seconds
Python Flask/FastAPI  | 1-3 seconds
Java/Spring Boot      | 10-30 seconds
Go application        | <1 second
Apps with DB init     | 5-15 seconds
Apps with migrations  | 15-60 seconds
```

**Factors that increase startup time:**
- Database connections/migrations
- Cache warming
- Large dependency initialization
- External service health checks
- JIT compilation (Java, .NET)

### PHASE 5: REGEX PATTERN CONSTRUCTION

**Good regex patterns are:**
1. **Specific enough** to avoid false positives
2. **Flexible enough** to handle variations
3. **Case insensitive** when appropriate

**Examples:**
```regex
# Success (good)
/listening on (port )?\\d+/i
/server (is )?(started|running|ready)/i
/application startup complete/i

# Success (too generic - avoid)
/started/i  # Too many false positives

# Failure (good)
/error:|fatal:|panic:|exception/i
/ECONNREFUSED|EADDRINUSE|EACCES/i

# Failure (too generic - avoid)
/error/i  # Would match "error handling code"
```

## Output Requirements
1. **success_patterns**: List of regex patterns for "app ready"
2. **failure_patterns**: List of regex patterns for "startup failed"
3. **estimated_startup_time**: Seconds to wait before checking
4. **confidence**: HIGH, MEDIUM, LOW
5. **thought_process**: How you derived these patterns

## Anti-Patterns to Avoid
- Overly generic patterns (just "started")
- Forgetting case sensitivity issues
- Missing framework-specific patterns
- Underestimating startup time for complex apps
- Regex that would match normal log lines
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("readiness_detector", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analyze these files to determine startup patterns.

STACK: {stack}
PROJECT TYPE: {project_type}

FILE CONTENTS:
{file_contents}

Identify log patterns that indicate successful startup or failure.
Explain your reasoning in the thought process.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "stack": context.analysis_result.get("stack", "Unknown"),
            "project_type": context.analysis_result.get("project_type", "service"),
            "file_contents": context.file_contents
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



