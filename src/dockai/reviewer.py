import os
from typing import Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import SecurityReviewResult
from .callbacks import TokenUsageCallback

def review_dockerfile(dockerfile_content: str) -> Tuple[SecurityReviewResult, Any]:
    """
    Stage 2.5: The Security Engineer (Review).
    
    Performs a static security analysis of the generated Dockerfile.
    
    NEW: Now provides structured fixes and can return a corrected Dockerfile
    when issues are found, enabling the generator to make targeted improvements.
    """
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini") # Use the faster model for review
    
    # Initialize Chat Model
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Define the structured output
    structured_llm = llm.with_structured_output(SecurityReviewResult)
    
    # Define Prompt
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
    
    # Create Chain
    chain = prompt | structured_llm
    
    # Execute with callback
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "dockerfile": dockerfile_content
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()
