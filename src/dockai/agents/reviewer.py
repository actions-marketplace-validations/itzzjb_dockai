"""
DockAI Security Reviewer Module.

This module acts as the "Security Engineer" in the DockAI workflow.
It performs a static analysis of the generated Dockerfile to identify
security vulnerabilities and best practice violations. It provides
structured feedback and, critically, can return a corrected Dockerfile
to automatically fix identified issues.
"""

import os
from typing import Tuple, Any, TYPE_CHECKING

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import SecurityReviewResult
from ..utils.callbacks import TokenUsageCallback
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from ..core.agent_context import AgentContext


def review_dockerfile(context: 'AgentContext') -> Tuple[SecurityReviewResult, Any]:
    """
    Stage 2.5: The Security Engineer (Review).
    
    Performs a static security analysis of the generated Dockerfile using an LLM.
    
    This function:
    1. Checks for critical security issues (e.g., running as root, hardcoded secrets).
    2. Checks for best practices (e.g., specific tags, minimal images).
    3. Returns a structured result containing identified issues, severity levels,
       and specific fixes.
    4. If critical issues are found, it generates a corrected Dockerfile.

    Args:
        context (AgentContext): Unified context containing dockerfile_content and other info.

    Returns:
        Tuple[SecurityReviewResult, Any]: A tuple containing:
            - The structured security review result.
            - Token usage statistics.
    """
    from ..core.agent_context import AgentContext
    # Create LLM using the provider factory for the reviewer agent
    llm = create_llm(agent_name="reviewer", temperature=0)
    
    # Configure the LLM to return a structured output matching the SecurityReviewResult schema
    structured_llm = llm.with_structured_output(SecurityReviewResult)
    
    # Define the default system prompt for the "Lead Security Engineer" persona
    default_prompt = """You are the REVIEWER agent in a multi-agent Dockerfile generation pipeline. You are AGENT 4 of 10 - the security gatekeeper that must approve or reject Dockerfiles.

## Your Role in the Pipeline
```
Analyzer → Planner → Generator → [YOU: Reviewer] → Validator
                          ↓              ↓
                     Dockerfile    Pass/Fail + Fixed Version
```

## Your Mission
Perform a comprehensive security audit and provide:
1. PASS (is_secure=True) if no Critical/High issues
2. FAIL (is_secure=False) with a FIXED Dockerfile if Critical/High issues exist

## Chain-of-Thought Security Analysis

### PHASE 1: THREAT MODEL
**Who might attack this container?**
- External attackers (network exposure)
- Malicious dependencies (supply chain)
- Container escape attempts
- Privilege escalation attempts

### PHASE 2: SYSTEMATIC SECURITY CHECKLIST

**CRITICAL SEVERITY (Must Fix - Blocks Deployment)**
```
Issue                          | Detection Pattern
───────────────────────────────┼─────────────────────────────────
Hardcoded secrets              | API_KEY=, PASSWORD=, SECRET= in ENV
Running as root explicitly     | USER root (not acceptable)
Embedded credentials           | COPY .env, --build-arg with secrets
Privileged container hints     | --privileged, --cap-add in comments
Private key in image           | COPY id_rsa, COPY *.pem
```

**HIGH SEVERITY (Should Fix - Security Risk)**
```
Issue                          | Detection Pattern
───────────────────────────────┼─────────────────────────────────
Running as root implicitly     | No USER instruction = root
Using 'latest' tag             | FROM image:latest or FROM image (no tag)
No explicit non-root user      | Missing USER + adduser pattern
Overly permissive permissions  | chmod 777, chmod -R 777
COPY . without .dockerignore   | COPY . . (may include secrets)
Build secrets in final image   | Multi-stage not cleaning build args
```

**MEDIUM SEVERITY (Best Practice - Recommend Fix)**
```
Issue                          | Detection Pattern
───────────────────────────────┼─────────────────────────────────
Unnecessary packages           | Dev tools in production image
No health check                | Missing HEALTHCHECK instruction
Unnecessary ports exposed      | Multiple EXPOSE without justification
Package cache not cleaned      | Missing rm -rf /var/lib/apt/lists/*
Using sudo/su in scripts       | sudo, su - in RUN commands
```

**LOW SEVERITY (Nice to Have)**
```
Issue                          | Detection Pattern
───────────────────────────────┼─────────────────────────────────
No LABEL metadata              | Missing LABEL instructions
Suboptimal layer ordering      | Source before dependencies
Missing .dockerignore mention  | No evidence of exclusions
```

### PHASE 3: REMEDIATION PATTERNS

**Root User Fix:**
```dockerfile
# BEFORE (insecure):
FROM node:20-alpine
WORKDIR /app
COPY . .
CMD ["node", "server.js"]

# AFTER (secure):
FROM node:20-alpine
RUN addgroup -g 1001 -S appgroup && adduser -u 1001 -S appuser -G appgroup
WORKDIR /app
COPY --chown=appuser:appgroup . .
USER appuser
CMD ["node", "server.js"]
```

**Latest Tag Fix:**
```dockerfile
# BEFORE: FROM python:latest
# AFTER:  FROM python:3.12-slim
```

**Secrets Fix:**
```dockerfile
# BEFORE (insecure):
ENV DATABASE_URL=postgresql://user:password@host/db

# AFTER (secure):
# Pass at runtime: docker run -e DATABASE_URL=... image
# Or use Docker secrets / external secret management
```

### PHASE 4: OUTPUT DECISION MATRIX

```
Issues Found              → Action
──────────────────────────────────────────
Any CRITICAL              → is_secure=False + fixed_dockerfile
Any HIGH                  → is_secure=False + fixed_dockerfile  
Only MEDIUM/LOW           → is_secure=True + list issues as warnings
No issues                 → is_secure=True
```

## Output Requirements
1. **is_secure**: Boolean - False if ANY Critical or High issues
2. **issues**: List of all issues found with severity and fix
3. **fixed_dockerfile**: Complete fixed Dockerfile (if is_secure=False)
4. **security_score**: Optional 0-100 rating

## Important Notes
- ALWAYS provide specific line numbers when possible
- ALWAYS provide the exact fix, not vague suggestions
- If generating fixed_dockerfile, ensure ALL issues are addressed
- Don't flag false positives (e.g., USER 1001 is valid)
"""

    # Get custom prompt if configured, otherwise use default
    system_template = get_prompt("reviewer", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", """Review this Dockerfile for security issues.

DOCKERFILE:
{dockerfile}

Analyze for security vulnerabilities and provide:
1. List of issues with severity
2. Specific fixes for each issue
3. A corrected Dockerfile if critical/high issues are found""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = chain.invoke(
        {
            "dockerfile": context.dockerfile_content
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()
