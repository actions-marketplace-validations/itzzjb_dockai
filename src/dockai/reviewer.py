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
    system_template = """You are a Lead Security Engineer specializing in Container Security.

Your Goal: Review the provided Dockerfile for security vulnerabilities and best practice violations.

Checklist:
1. ROOT USER: Does the container run as root? (Critical)
2. BASE IMAGE: Is it using 'latest' tag? (High) Is it a full OS instead of slim/alpine? (Medium)
3. SECRETS: Are there any hardcoded secrets or sensitive env vars? (Critical)
4. PACKAGES: Are there unnecessary package installations? (Low)
5. PORTS: Are unnecessary ports exposed? (Low)

Output:
- If you find CRITICAL or HIGH severity issues, set is_secure=False.
- If you find only MEDIUM or LOW issues, set is_secure=True (but list them).
- Provide clear suggestions for fixes.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", "Review this Dockerfile:\n\n{dockerfile}")
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
