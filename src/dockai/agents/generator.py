"""
DockAI Generator Module.

This module is responsible for generating the Dockerfile.
It acts as the "Architect", using the analysis results and plan to create
a production-ready Dockerfile. It supports both fresh generation and
iterative improvement based on feedback.
"""

import os
from typing import Tuple, Any, Dict, List, Optional

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import DockerfileResult, IterativeDockerfileResult
from ..utils.callbacks import TokenUsageCallback
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm


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
    # Determine if we should perform iterative improvement or fresh generation
    is_iterative = previous_dockerfile and reflection and len(previous_dockerfile.strip()) > 0
    
    # Create LLM using the provider factory - use different agents for fresh vs iterative
    agent_name = "generator_iterative" if is_iterative else "generator"
    llm = create_llm(agent_name=agent_name, temperature=0)
    
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
    
    # Define the default system prompt for the "Senior Docker Architect" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to create a Dockerfile that successfully builds and runs the application.

Think like an experienced engineer - understand the WHY behind each decision, not just the WHAT.

## Your Generation Process

STEP 1 - UNDERSTAND THE REQUIREMENTS:
  - What does this application need to run?
  - What must be built or compiled?
  - What files need to be present in the final image?
  - What environment does the application expect?

STEP 2 - DESIGN THE STRUCTURE:
  - Do I need separate build and runtime environments?
  - What base image provides the right foundation?
  - In what order should instructions be arranged for caching?
  - What can be parallelized or combined?

STEP 3 - REASON ABOUT EACH INSTRUCTION:
  - Why this base image?
  - Why copy these files in this order?
  - Why these specific commands?
  - What could break and how do I prevent it?

STEP 4 - VERIFY COMPLETENESS:
  - Are ALL source files copied? (Not just manifests/configs)
  - Are ALL dependencies available at runtime?
  - Is the entry command correct?
  - Will the application have permission to run?

## Essential Principles

**SOURCE FILES**: The most common failure is forgetting to copy application code. You MUST:
  - Copy ALL source files the application needs (not just package.json, requirements.txt, etc.)
  - Include templates, static files, configuration, and any runtime resources
  - For multi-stage builds, ensure files built in stage 1 are properly copied to stage 2

**SECURITY**: Production containers should:
  - Run as a non-root user
  - Not contain unnecessary tools or shells
  - Not embed secrets or credentials
  - Use specific version tags, not 'latest'

**OPTIMIZATION**: Efficient images:
  - Install dependencies before copying source (for caching)
  - Clean up package manager caches
  - Combine related RUN commands
  - Use multi-stage builds to separate build-time from runtime

**COMPATIBILITY**: When using multi-stage builds:
  - Ensure binaries compiled in stage 1 can run in stage 2
  - Same OS family, compatible architectures
  - Consider static vs dynamic linking

## Context from Planning

{plan_context}

## Lessons from Previous Attempts

{retry_context}

## Error to Address

{error_context}
"""

    # Get custom prompt if configured, otherwise use default
    system_template = get_prompt("generator", default_prompt)

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
    
    # Configure the LLM to return a structured output matching the IterativeDockerfileResult schema
    structured_llm = llm.with_structured_output(IterativeDockerfileResult)
    
    # Build reflection context string from the specific fixes identified
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
    
    # Define the default system prompt for the "Iterative Improver" persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to fix a Dockerfile that failed based on specific feedback.

Think like a debugger - understand exactly what went wrong and make the minimal change to fix it.

## Your Debugging Process

STEP 1 - UNDERSTAND THE FAILURE:
  - What error occurred?
  - What line or instruction caused it?
  - What was the expected behavior vs actual?

STEP 2 - ANALYZE THE ROOT CAUSE:
  - Root cause: {root_cause}
  - Why it failed: {why_it_failed}
  - Lesson learned: {lesson_learned}

STEP 3 - REVIEW THE PRESCRIBED FIXES:
{specific_fixes}

STEP 4 - APPLY CHANGES CAREFULLY:
  - Make targeted changes to address the root cause
  - Preserve everything that was working correctly
  - Don't introduce new problems while fixing old ones

## Important Guidance

{image_change_guidance}

{strategy_change_guidance}

{plan_guidance}

## Key Principles

**PRESERVE WHAT WORKS**: This is not a rewrite - it's a surgical fix. Only change what's broken.

**VERIFY SOURCE FILES**: The most common issue is missing files. Ensure:
  - All application source code is copied (not just configs/manifests)
  - Multi-stage builds copy everything needed from builder stage
  - Runtime stage has all files required to execute

**CHECK COMPATIBILITY**: If changing base images:
  - Binaries built in one environment must run in another
  - Consider static linking for maximum portability
  - Match OS families when dynamic linking is required

**EXPLAIN YOUR CHANGES**: Be explicit about:
  - What you changed
  - Why you changed it
  - How it addresses the root cause

Verified base images: {verified_tags}

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_template = get_prompt("generator_iterative", default_prompt)

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
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
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
