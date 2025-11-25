import os
from typing import Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import DockerfileResult
from .callbacks import TokenUsageCallback

def generate_dockerfile(stack_info: str, file_contents: str, custom_instructions: str = "", feedback_error: str = None, **kwargs) -> Tuple[str, str, str, Any]:
    """
    Stage 2: The Architect (Generation).
    
    Uses LangChain and Pydantic to generate a structured Dockerfile.
    """
    model_name = kwargs.get("model_name") or os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    # Initialize Chat Model
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Define the structured output
    structured_llm = llm.with_structured_output(DockerfileResult)
    
    # Define Prompt
    system_template = """You are a Senior Docker Architect.

Your Task:
Generate a highly optimized, production-ready Multi-Stage Dockerfile for this application.

Process:
1. REASON: Explain your thought process. Why are you choosing this base image? Why this build strategy?
2. DRAFT: Create the Dockerfile content based on best practices.

Requirements:
1. Base Images: Use the provided VERIFIED TAGS. Prefer 'alpine' for size, but use 'slim' or 'standard' if compatibility requires it (e.g., Python wheels, C deps).
2. Architecture: MANDATORY: Use Multi-Stage builds. Stage 1: Build/Compile. Stage 2: Runtime (copy only artifacts).
3. Security: Run as non-root user. Drop all capabilities.
4. Optimization: Combine RUN commands. Clean package caches (apt-get clean, npm cache clean).
5. Configuration: Set env vars, WORKDIR, expose correct ports.
6. Commands: Use the provided 'Build Command' and 'Start Command' if they are valid.

{error_context}
"""

    error_context = ""
    if feedback_error:
        error_context = f"""
CRITICAL: The previous Dockerfile failed validation with this error:
"{feedback_error}"

You MUST analyze this error and fix it in the new Dockerfile.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", "Stack: {stack}\n\nVerified Base Images: {verified_tags}\n\nDetected Build Command: {build_cmd}\nDetected Start Command: {start_cmd}\n\nFile Contents:\n{file_contents}\n\nCustom Instructions: {custom_instructions}")
    ])
    
    # Create Chain
    chain = prompt | structured_llm
    
    # Execute with callback
    callback = TokenUsageCallback()
    
    result = chain.invoke(
        {
            "stack": stack_info,
            "verified_tags": kwargs.get("verified_tags", "None provided. Use your best judgement."),
            "build_cmd": kwargs.get("build_command", "None detected"),
            "start_cmd": kwargs.get("start_command", "None detected"),
            "file_contents": file_contents,
            "custom_instructions": custom_instructions,
            "error_context": error_context
        },
        config={"callbacks": [callback]}
    )
    
    return result.dockerfile, result.project_type, result.thought_process, callback.get_usage()
