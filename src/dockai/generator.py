"""
DockAI Generator Module

This module is responsible for generating the Dockerfile.
It acts as the "Architect", using the analysis results and plan to create
a production-ready Dockerfile. It supports both fresh generation and
iterative improvement based on feedback.
"""

import os
from typing import Tuple, Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

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
    Stage 2: The Architect (Generation).
    
    Uses LangChain and Pydantic to generate a structured Dockerfile.
    
    Supports iterative improvement when previous_dockerfile and reflection are provided.
    The AI will make targeted fixes instead of regenerating from scratch.

    Args:
        stack_info: Information about the technology stack.
        file_contents: Content of critical files.
        custom_instructions: Custom instructions from the user.
        feedback_error: Error message from previous attempt (if any).
        previous_dockerfile: Previous Dockerfile content (for iteration).
        retry_history: History of previous retries.
        current_plan: Current generation plan.
        reflection: Reflection on previous failure.
        **kwargs: Additional arguments (model_name, etc.).

    Returns:
        Tuple of (dockerfile_content, project_type, thought_process, usage_stats).
    """
    model_name = kwargs.get("model_name") or os.getenv("MODEL_GENERATOR", "gpt-4o")
    
    # Initialize Chat Model
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Check if this is an iterative improvement (has previous dockerfile and reflection)
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
    """Generate a new Dockerfile from scratch (first attempt or no previous context)."""
    
    # Define the structured output
    structured_llm = llm.with_structured_output(DockerfileResult)
    
    # Build retry history context
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
    
    # Build plan context
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
    
    # Define Prompt
    system_template = """You are a Senior Docker Architect working as an autonomous AI agent.

Your Task:
Generate a highly optimized, production-ready Dockerfile for this application. You must work with ANY technology stack.

Process:
1.  **REASON**: Explain your thought process. Why are you choosing this base image? Why this build strategy?
2.  **DRAFT**: Create the Dockerfile content based on best practices for the detected technology.

Requirements (Apply intelligently based on the detected technology):

1.  **Base Image Strategy (CRITICAL)**:
    -   **BUILD STAGE**: Use appropriate images with compilers, build tools, and system packages needed for building.
        -   Choose images that include the necessary development dependencies for the detected technology.
    -   **RUNTIME STAGE**: Use minimal/slim/distroless images appropriate for the technology for security and smaller size.
    -   Use **VERIFIED TAGS** from the provided list - prefer specific version tags over 'latest'.

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

7.  **Commands**: Use the provided 'Build Command' and 'Start Command' if they are valid.

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
        ("user", """Stack: {stack}

Verified Base Images: {verified_tags}

Detected Build Command: {build_cmd}
Detected Start Command: {start_cmd}

File Contents:
{file_contents}

Custom Instructions: {custom_instructions}

Generate the Dockerfile and explain your reasoning in the thought process.""")
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
    """Generate an improved Dockerfile by iterating on the previous attempt."""
    
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Build reflection context
    specific_fixes = reflection.get("specific_fixes", [])
    fixes_str = "\n".join([f"  - {fix}" for fix in specific_fixes]) if specific_fixes else "No specific fixes provided"
    
    # Build plan context
    plan_guidance = ""
    if current_plan:
        plan_guidance = f"""
UPDATED PLAN BASED ON LESSONS LEARNED:
- Base Image Strategy: {current_plan.get('base_image_strategy', 'Default')}
- Build Strategy: {current_plan.get('build_strategy', 'Multi-stage')}
- Use Static Linking: {current_plan.get('use_static_linking', False)}
- Use Alpine Runtime: {current_plan.get('use_alpine_runtime', False)}
"""
    
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

    # Build image change guidance
    image_change_guidance = ""
    if reflection.get("should_change_base_image"):
        suggested = reflection.get("suggested_base_image", "")
        image_change_guidance = f"""
IMAGE CHANGE REQUIRED:
The reflection suggests changing the base image to: {suggested}
Apply this change to fix compatibility issues.
"""
    
    # Build strategy change guidance  
    strategy_change_guidance = ""
    if reflection.get("should_change_build_strategy"):
        new_strategy = reflection.get("new_build_strategy", "")
        strategy_change_guidance = f"""
BUILD STRATEGY CHANGE REQUIRED:
New strategy: {new_strategy}
Apply this strategic change to the Dockerfile.
"""

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
    
    chain = prompt | structured_llm
    callback = TokenUsageCallback()
    
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
    
    # Build thought process from iterative result
    thought_process = f"""ITERATIVE IMPROVEMENT:
Previous Issues Addressed: {', '.join(result.previous_issues_addressed)}
Changes Made: {', '.join(result.changes_summary)}
Confidence: {result.confidence_in_fix}
Fallback Strategy: {result.fallback_strategy or 'None'}

{result.thought_process}"""
    
    return result.dockerfile, result.project_type, thought_process, callback.get_usage()
