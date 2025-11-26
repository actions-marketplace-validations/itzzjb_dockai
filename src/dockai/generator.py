"""
DockAI Generator Module.

This module is responsible for generating the Dockerfile.
It acts as the "Architect", using the analysis results and plan to create
a production-ready Dockerfile. It supports both fresh generation and
iterative improvement based on feedback.
"""

import os
from typing import Tuple, Any, Dict, List, Optional

# Third-party imports for LangChain and OpenAI integration
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas and callbacks
from .schemas import DockerfileResult, IterativeDockerfileResult
from .callbacks import TokenUsageCallback


def generate_dockerfile(
    stack_info: str, 
    file_contents: str, 
    custom_instructions: str = "", 
    feedback_error: str = None,
    previous_dockerfile: str = None,
    retry_history: List[Dict[str, Any]] = None,
    current_plan: Dict[str, Any] = None,
    reflection: Dict[str, Any] = None,
    **kwargs
) -> Tuple[str, str, str, Any]:
    """
    Orchestrates the Dockerfile generation process.

    This function serves as the main entry point for "Stage 2: The Architect".
    It decides whether to generate a fresh Dockerfile from scratch or to
    iteratively improve an existing one based on feedback and reflection.

    Args:
        stack_info (str): A summary of the detected technology stack.
        file_contents (str): The content of critical files to provide context.
        custom_instructions (str, optional): User-provided instructions. Defaults to "".
        feedback_error (str, optional): The error message from a previous failed attempt. Defaults to None.
        previous_dockerfile (str, optional): The content of the previous Dockerfile (for iteration). Defaults to None.
        retry_history (List[Dict[str, Any]], optional): A history of previous attempts and failures. Defaults to None.
        current_plan (Dict[str, Any], optional): The strategic plan for generation. Defaults to None.
        reflection (Dict[str, Any], optional): The analysis of why the previous attempt failed. Defaults to None.
        **kwargs: Additional arguments, such as 'model_name'.

    Returns:
        Tuple[str, str, str, Any]: A tuple containing:
            - The generated Dockerfile content.
            - The project type (e.g., 'service', 'script').
            - The AI's thought process/explanation.
            - Token usage statistics.
    """
    # Retrieve model name, defaulting to a high-capability model for code generation
    model_name = kwargs.get("model_name") or os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    # Initialize the ChatOpenAI client with temperature 0 for deterministic code generation
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Determine if we should perform iterative improvement or fresh generation
    is_iterative = previous_dockerfile and reflection and len(previous_dockerfile.strip()) > 0
    
    if is_iterative:
        return _generate_iterative_dockerfile(
            llm=llm,
            previous_dockerfile=previous_dockerfile,
            reflection=reflection,
            stack_info=stack_info,
            file_contents=file_contents,
            current_plan=current_plan,
            custom_instructions=custom_instructions,
            **kwargs
        )
    else:
        return _generate_fresh_dockerfile(
            llm=llm,
            stack_info=stack_info,
            file_contents=file_contents,
            custom_instructions=custom_instructions,
            feedback_error=feedback_error,
            retry_history=retry_history,
            current_plan=current_plan,
            **kwargs
        )


def _generate_fresh_dockerfile(
    llm,
    stack_info: str,
    file_contents: str,
    custom_instructions: str = "",
    feedback_error: str = None,
    retry_history: List[Dict[str, Any]] = None,
    current_plan: Dict[str, Any] = None,
    **kwargs
) -> Tuple[str, str, str, Any]:
    """
    Generates a new Dockerfile from scratch.

    This internal function handles the initial generation logic, incorporating
    the strategic plan and any lessons learned from previous (failed) attempts
    if applicable.

    Args:
        llm: The initialized LangChain LLM object.
        stack_info (str): Detected stack information.
        file_contents (str): Content of critical files.
        custom_instructions (str, optional): User instructions. Defaults to "".
        feedback_error (str, optional): Error from previous run (if retrying without full reflection). Defaults to None.
        retry_history (List[Dict[str, Any]], optional): History of failures. Defaults to None.
        current_plan (Dict[str, Any], optional): Strategic plan. Defaults to None.
        **kwargs: Additional arguments.

    Returns:
        Tuple[str, str, str, Any]: Dockerfile content, project type, thought process, usage stats.
    """
    
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
    
    # Define the system prompt for the "Senior Docker Architect" persona
    system_template = """You are a Universal Docker Architect working as an autonomous AI agent.

Your Task:
Generate a highly optimized, production-ready Dockerfile for this application. You must work with ANY technology stack - past, present, or future.

Process:
1.  **REASON**: Explain your thought process. Why are you choosing this base image? Why this build strategy?
2.  **DRAFT**: Create the Dockerfile content based on best practices for the detected technology.

Requirements (Apply intelligently based on the detected technology):

1.  **Base Image Strategy (CRITICAL)**:
    -   **Standard Stacks**: Use official images (e.g., `python:3.11-slim`, `node:18-alpine`).
    -   **Unknown/Future Stacks**: If no official image exists, use a generic base (e.g., `ubuntu:latest`, `debian:bullseye`, `alpine:latest`) and INSTALL the necessary tools (compilers, interpreters) via package manager.
    -   **VERIFIED TAGS**: Use the provided list if applicable.

2.  **Architecture**: Use Multi-Stage builds when beneficial. Stage 1: Build/Compile with appropriate tools. Stage 2: Runtime with minimal dependencies.

3.  **CRITICAL - SOURCE FILE COPYING**:
    -   **YOU MUST COPY ALL APPLICATION SOURCE FILES** to the container.
    -   Analyze the project structure and ensure ALL necessary files are copied.
    -   Copy source files, templates, static assets, configuration files, and any runtime resources.
    -   For compiled languages: Source files must be copied BEFORE compilation.
    -   ALWAYS ensure either "COPY . ." or explicit copy of each required file/directory.
    -   Copying ONLY dependency manifest files is NOT ENOUGH.
    -   The runtime stage needs ALL files required to run the application.

4.  **Security**: Run as non-root user. Use proper user/group creation syntax appropriate for the base image's distribution.

5.  **Optimization**: Combine RUN commands where appropriate. Clean package caches after installation.

6.  **Configuration**: Set appropriate env vars, WORKDIR, and expose correct ports based on project analysis.

7.  **Commands**: Use the provided 'Build Command' and 'Start Command' if they are valid. If not, derive them from the code.

8.  **MULTI-STAGE BUILD PATTERNS**:
    -   For interpreted languages with package dependencies: Ensure dependencies installed in build stage are available in runtime stage.
    -   For compiled languages: Build in full image, copy only the binary/artifacts to minimal runtime image.
    -   Ensure binary compatibility between build and runtime stages (same OS family or static linking).

9.  **CRITICAL Binary/Runtime Compatibility**:
    -   Ensure compatibility between build and runtime environments.
    -   If using different base images, ensure dependencies and binaries are compatible.
    -   For native extensions or compiled code, match the build environment with runtime, or use static linking.

10. **GENERAL BEST PRACTICES**:
    -   Don't assume tools exist in minimal images - install explicitly if needed.
    -   User creation syntax may differ between distributions - use appropriate commands.
    -   Clean up package manager caches to reduce image size.

{plan_context}

{retry_context}

{error_context}
"""

    # Incorporate specific error context if available (e.g., from AI error analysis)
    error_context = ""
    if feedback_error:
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

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("user", """Stack: {stack}

Verified Base Images: {verified_tags}

Detected Build Command: {build_cmd}
Detected Start Command: {start_cmd}

File Contents:
{file_contents}

Custom Instructions: {custom_instructions}

Generate the Dockerfile and explain your reasoning in the thought process.""")
    ])
    
    # Create the execution chain
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Execute the chain
    result = chain.invoke(
        {
            "stack": stack_info,
            "verified_tags": kwargs.get("verified_tags", "None provided. Use your best judgement."),
            "build_cmd": kwargs.get("build_command", "None detected"),
            "start_cmd": kwargs.get("start_command", "None detected"),
            "file_contents": file_contents,
            "custom_instructions": custom_instructions,
            "error_context": error_context,
            "plan_context": plan_context,
            "retry_context": retry_context
        },
        config={"callbacks": [callback]}
    )
    
    return result.dockerfile, result.project_type, result.thought_process, callback.get_usage()


def _generate_iterative_dockerfile(
    llm,
    previous_dockerfile: str,
    reflection: Dict[str, Any],
    stack_info: str,
    file_contents: str,
    current_plan: Dict[str, Any] = None,
    custom_instructions: str = "",
    **kwargs
) -> Tuple[str, str, str, Any]:
    """
    Generates an improved Dockerfile by iterating on a previous attempt.

    This internal function handles the iterative improvement logic. It uses the
    reflection data (root cause, specific fixes) to modify the previous Dockerfile
    surgically, rather than rewriting it from scratch.

    Args:
        llm: The initialized LangChain LLM object.
        previous_dockerfile (str): The content of the failed Dockerfile.
        reflection (Dict[str, Any]): Analysis of the failure.
        stack_info (str): Detected stack information.
        file_contents (str): Content of critical files.
        current_plan (Dict[str, Any], optional): Strategic plan. Defaults to None.
        custom_instructions (str, optional): User instructions. Defaults to "".
        **kwargs: Additional arguments.

    Returns:
        Tuple[str, str, str, Any]: Improved Dockerfile content, project type, thought process, usage stats.
    """
    
    # Configure the LLM for iterative output
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Build reflection context string
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
    
    # Define the system prompt for the "Iterative Improver" persona
    system_template = """You are a Senior Docker Engineer ITERATING on a failed Dockerfile.

CRITICAL: You are NOT starting from scratch. You are IMPROVING an existing Dockerfile
based on specific feedback about what went wrong.

ITERATION RULES:
1.  **PRESERVE** what was working - don't change things that weren't causing issues.
2.  **APPLY** specific fixes from the reflection - these are targeted solutions.
3.  **MAKE MINIMAL CHANGES** - surgical fixes, not rewrites.
4.  **LEARN** from the failure - understand WHY it failed to ensure the fix is correct.

COMMON ISSUES TO CHECK (Apply intelligently based on the technology):
-   **Missing source files**: Ensure ALL application source files are COPIED (not just dependency/manifest files).
-   **Verify all source code files** required for the detected technology are properly copied.
-   **Multi-stage builds**: If copying from builder, ensure builder stage has ALL files to copy.
-   **Dependency artifacts**: Ensure package manager outputs are available in runtime stage.
-   **Binary compatibility**: Ensure build and runtime environments are compatible.

REFLECTION ANALYSIS:
Root Cause: {root_cause}
Why It Failed: {why_it_failed}
Lesson Learned: {lesson_learned}

SPECIFIC FIXES TO APPLY:
{specific_fixes}

{image_change_guidance}

{strategy_change_guidance}

{plan_guidance}

VERIFIED BASE IMAGES: {verified_tags}

{custom_instructions}
"""

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

KEY FILE CONTENTS:
{file_contents}

Apply the specific fixes and return an improved Dockerfile.
Explain what you changed and why in the thought process.""")
    ])
    
    # Create the execution chain
    chain = prompt | structured_llm
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
            "verified_tags": kwargs.get("verified_tags", "None provided"),
            "stack": stack_info,
            "build_cmd": kwargs.get("build_command", "None detected"),
            "start_cmd": kwargs.get("start_command", "None detected"),
            "file_contents": file_contents[:6000],
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
