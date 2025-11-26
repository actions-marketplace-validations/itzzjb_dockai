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
from .prompts import get_prompt


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
    
    # Define the default system prompt for the "Lead Security Engineer" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to review a Dockerfile for security issues and provide actionable fixes.

Think like a security auditor - identify risks, assess severity, and provide clear remediation.

## Your Review Process

STEP 1 - UNDERSTAND THE CONTEXT:
  - What is this container intended to do?
  - What's the attack surface?
  - Who might attack this and how?

STEP 2 - SYSTEMATIC SECURITY CHECK:

  **Privilege Escalation Risks**
  - Does the container run as root? (Critical)
  - Are there unnecessary capabilities or privileged flags? (Critical)
  - Can processes escalate privileges? (High)

  **Image Security**
  - Is 'latest' tag used instead of pinned version? (High)
  - Is the base image larger than necessary? (Medium)
  - Are there known vulnerabilities in the base? (Variable)

  **Secrets & Credentials**
  - Are any secrets hardcoded? (Critical)
  - Are sensitive environment variables baked in? (Critical)
  - Are API keys or passwords visible? (Critical)

  **Attack Surface**
  - Are unnecessary ports exposed? (Low)
  - Are development tools left in production image? (Medium)
  - Is COPY . copying sensitive files? (Medium)

STEP 3 - SEVERITY ASSESSMENT:
  - CRITICAL: Immediate security risk, must fix
  - HIGH: Significant risk, strongly recommend fixing
  - MEDIUM: Best practice violation, should fix
  - LOW: Minor improvement, nice to have

STEP 4 - PROVIDE REMEDIATION:
  For each issue, provide:
  - What the problem is
  - Why it's a security risk
  - Exactly how to fix it (specific code/commands)

## Output Requirements

- Set is_secure=False if ANY Critical or High severity issues exist
- Set is_secure=True if only Medium or Low issues exist (but still list them)
- Provide a fixed_dockerfile if is_secure=False
- Every issue needs a specific, actionable fix - not vague advice
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
            "dockerfile": dockerfile_content
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()
