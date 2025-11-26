"""
DockAI Security Reviewer Module.

This module acts as the "Security Engineer" in the DockAI workflow.
It performs a static analysis of the generated Dockerfile to identify
security vulnerabilities and best practice violations. It provides
structured feedback and, critically, can return a corrected Dockerfile
to automatically fix identified issues.
"""

import os
from typing import Tuple, Any

# Third-party imports for LangChain and OpenAI integration
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas and callbacks
from .schemas import SecurityReviewResult
from .callbacks import TokenUsageCallback


def review_dockerfile(dockerfile_content: str) -> Tuple[SecurityReviewResult, Any]:
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
        dockerfile_content (str): The content of the Dockerfile to review.

    Returns:
        Tuple[SecurityReviewResult, Any]: A tuple containing:
            - The structured security review result.
            - Token usage statistics.
    """
    # Use the faster/cheaper model for review as it's a classification/analysis task
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    # Initialize the ChatOpenAI client with temperature 0 for deterministic analysis
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Configure the LLM to return a structured output matching the SecurityReviewResult schema
    structured_llm = llm.with_structured_output(SecurityReviewResult)
    
    # Define the system prompt for the "Lead Security Engineer" persona
    system_template = """You are a Lead Security Engineer working as an autonomous AI agent, specializing in Container Security.

Your Goal: Review the provided Dockerfile for security vulnerabilities and best practice violations.
If issues are found, you MUST provide specific, actionable fixes.

You must work with ANY programming language, framework, or technology stack.

SECURITY CHECKLIST:
1. ROOT USER: Does the container run as root? (Critical)
   - Fix: Add USER directive with non-root user
   
2. BASE IMAGE: Is it using 'latest' tag? (High) Is it using an unnecessarily large image? (Medium)
   - Fix: Specify exact version tags, use minimal images appropriate for the technology
   
3. SECRETS: Are there any hardcoded secrets or sensitive env vars? (Critical)
   - Fix: Use build args or runtime env vars, never hardcode
   
4. PACKAGES: Are there unnecessary package installations? (Low)
   - Fix: Only install required packages, clean caches
   
5. PORTS: Are unnecessary ports exposed? (Low)
   - Fix: Only expose required ports

6. PRIVILEGE ESCALATION: Does it use --privileged or dangerous capabilities? (Critical)
   - Fix: Remove privileged flags, use minimal capabilities

7. COPY SCOPE: Does COPY . include sensitive files? (Medium)
   - Fix: Use .dockerignore or specific COPY commands

OUTPUT REQUIREMENTS:
- If you find CRITICAL or HIGH severity issues, set is_secure=False
- If you find only MEDIUM or LOW issues, set is_secure=True (but list them)
- For EVERY issue, provide a clear suggestion AND add it to dockerfile_fixes
- If is_secure=False, provide a fixed_dockerfile with all issues corrected

Your fixes must be SPECIFIC and ACTIONABLE - not vague recommendations.
"""

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
    
    # Create the execution chain
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = chain.invoke(
        {
            "dockerfile": dockerfile_content
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()
