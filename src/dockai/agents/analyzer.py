"""
DockAI Analyzer Module.

This module is responsible for the initial analysis of the repository.
It acts as the "Brain" of the operation, understanding the project structure,
identifying the technology stack, and determining the requirements.
"""

import os
import json
from typing import Tuple, Any, Dict, List

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import AnalysisResult
from ..utils.callbacks import TokenUsageCallback
from ..utils.rate_limiter import with_rate_limit_handling
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """Safely invoke a LangChain chain with rate limit handling."""
    return chain.invoke(input_data, config={"callbacks": callbacks})


def analyze_repo_needs(context: 'AgentContext') -> Tuple[AnalysisResult, Dict[str, int]]:
    """
    Performs the initial analysis of the repository to determine project requirements.

    This function corresponds to "Stage 1: The Brain" of the DockAI process. It uses
    an LLM to analyze the list of files in the repository and deduce the technology
    stack, project type (service vs. script), and necessary build/start commands.

    Args:
        context (AgentContext): Unified context containing file_tree and custom_instructions.

    Returns:
        Tuple[AnalysisResult, Dict[str, int]]: A tuple containing:
            - The structured analysis result (AnalysisResult object).
            - A dictionary tracking token usage for cost monitoring.
    """
    from ..core.agent_context import AgentContext
    # Create LLM using the provider factory for the analyzer agent
    llm = create_llm(agent_name="analyzer", temperature=0)
    
    # Configure the LLM to return a structured output matching the AnalysisResult schema
    structured_llm = llm.with_structured_output(AnalysisResult)
    
    # Default system prompt for the Build Engineer persona
    default_prompt = """You are an autonomous AI reasoning agent. Your task is to analyze a software project and understand how it works.

Think like a human engineer encountering this project for the first time. You have no assumptions about what technology is used - you must DISCOVER and DEDUCE everything from first principles.

## Your Cognitive Process

STEP 1 - OBSERVE: What files do you see? What patterns emerge from their names and extensions?

STEP 2 - HYPOTHESIZE: Based on your observations, what type of project could this be? Consider:
  - File extensions you recognize vs ones that are unfamiliar
  - Configuration files that hint at build systems or frameworks
  - Directory structures that suggest architectural patterns

STEP 3 - REASON: How would a human figure out how to run this?
  - Look for README files, Makefiles, build scripts, or configuration
  - Examine manifest files that declare dependencies
  - Identify entry points (main files, index files, executables)

STEP 4 - DEDUCE: What runtime environment does this need?
  - What interpreter, compiler, or runtime is required?
  - What dependencies must be available?
  - What system resources or services does it need?

STEP 5 - CONCLUDE: Formulate your analysis with confidence levels
  - What are you certain about vs what are educated guesses?
  - What additional information would help confirm your analysis?

## Key Questions to Answer

1. **What is this?** - Technology stack, framework, purpose
2. **What does it need?** - Runtime, dependencies, environment
3. **How does it build?** - Compilation, packaging, asset processing
4. **How does it run?** - Entry command, required arguments, ports
5. **Is it a service or script?** - Long-running daemon vs one-time execution

## Important Principles

- Unfamiliar technology is NOT a blocker - reason from what you observe
- Generic build indicators (Makefile, configure, build.sh) are universal
- When uncertain, propose a base environment and specify what needs to be installed
- Think about what a human would do to get this running

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("analyzer", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Here is the file list: {file_list}

Analyze the project and provide a detailed thought process explaining your reasoning.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Convert file list to JSON string for better formatting in the prompt
    file_list_str = json.dumps(context.file_tree)
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "custom_instructions": context.custom_instructions, 
            "file_list": file_list_str
        },
        [callback]
    )
    
    return result, callback.get_usage()

