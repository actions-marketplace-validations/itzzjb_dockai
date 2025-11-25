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
    system_template = """You are a Senior Docker Architect working as an AI agent.

Your Task:
Generate a highly optimized, production-ready Multi-Stage Dockerfile for this application.

Process:
1. REASON: Explain your thought process. Why are you choosing this base image? Why this build strategy?
2. DRAFT: Create the Dockerfile content based on best practices.

Requirements:
1. Base Image Strategy (CRITICAL):
   - BUILD STAGE: Use STANDARD/FULL images (e.g., python:3.11-bookworm, node:20-bookworm, golang:1.21, rust:1.70)
     - These have compilers, build tools, and system packages needed for building
     - NEVER use slim/alpine for build stage unless you are 100% certain no compilation is needed
   - RUNTIME STAGE: Use SLIM/ALPINE images (e.g., python:3.11-slim, node:20-alpine, alpine:3.18)
     - These are minimal for security and smaller size
   - Use VERIFIED TAGS from the provided list - prefer specific version tags (e.g., node:20.10.0-bookworm not node:latest)

2. Architecture: MANDATORY: Use Multi-Stage builds. Stage 1: Build/Compile with full image. Stage 2: Runtime with slim/alpine (copy only artifacts).

3. Security: Run as non-root user. Use proper user/group creation syntax for the distro (adduser/addgroup differ between Debian and Alpine).

4. Optimization: Combine RUN commands. Clean package caches (apt-get clean, npm cache clean).

5. Configuration: Set env vars, WORKDIR, expose correct ports.

6. Commands: Use the provided 'Build Command' and 'Start Command' if they are valid.

7. CRITICAL Binary Compatibility Rules:
   - GLIBC vs MUSL: Binaries compiled on Debian/Ubuntu (glibc) CANNOT run on Alpine (musl) without static linking
   - This causes "./app: not found" or "No such file or directory" errors even though the file exists
   
   FOR GO APPLICATIONS (MANDATORY):
   - OPTION A (PREFERRED): Build static binary with: CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o app
     Then you can use any Alpine image for runtime
   - OPTION B: Use same distro family - build on alpine, run on alpine (golang:X-alpine → alpine:X)
   - NEVER: Build on bookworm/bullseye and run on alpine without CGO_ENABLED=0
   
   FOR RUST APPLICATIONS:
   - OPTION A: Cross-compile for musl: rustup target add x86_64-unknown-linux-musl && cargo build --release --target x86_64-unknown-linux-musl
   - OPTION B: Use same distro family (rust:X-bookworm → debian:X-slim)
   
   FOR NODE.JS: Build on bookworm → run on bookworm-slim (NOT alpine unless using alpine for build too)
   
   OTHER PITFALLS:
   - Don't use setcap on Alpine without installing libcap
   - Don't use adduser --system on Alpine (use adduser -D instead)
   - Don't assume curl/wget exist in slim images

{error_context}
"""

    error_context = ""
    if feedback_error:
        # Check if feedback_error contains structured suggestions (from AI error analysis)
        dockerfile_fix = kwargs.get("dockerfile_fix", "")
        image_suggestion = kwargs.get("image_suggestion", "")
        
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
