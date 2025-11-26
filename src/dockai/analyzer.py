"""
DockAI Analyzer Module.

This module is responsible for the initial analysis of the repository.
It acts as the "Brain" of the operation, understanding the project structure,
identifying the technology stack, and determining the requirements.
"""

import os
import json
from typing import Tuple, Any, Dict, List

# Third-party imports for LangChain and OpenAI integration
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas and callbacks
from .schemas import AnalysisResult
from .callbacks import TokenUsageCallback
from .rate_limiter import with_rate_limit_handling


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """Safely invoke a LangChain chain with rate limit handling."""
    return chain.invoke(input_data, config={"callbacks": callbacks})


def analyze_repo_needs(file_list: list, custom_instructions: str = "") -> Tuple[AnalysisResult, Dict[str, int]]:
    """
    Performs the initial analysis of the repository to determine project requirements.

    This function corresponds to "Stage 1: The Brain" of the DockAI process. It uses
    an LLM to analyze the list of files in the repository and deduce the technology
    stack, project type (service vs. script), and necessary build/start commands.

    Args:
        file_list (list): A list of all filenames in the repository to be analyzed.
        custom_instructions (str, optional): Specific instructions provided by the user
            to guide the analysis (e.g., "This is a Django app"). Defaults to "".

    Returns:
        Tuple[AnalysisResult, Dict[str, int]]: A tuple containing:
            - The structured analysis result (AnalysisResult object).
            - A dictionary tracking token usage for cost monitoring.
    """
    # Retrieve the model name from environment variables, defaulting to a cost-effective model
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    # Initialize the ChatOpenAI client with temperature 0 for deterministic analysis
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Configure the LLM to return a structured output matching the AnalysisResult schema
    structured_llm = llm.with_structured_output(AnalysisResult)
    
    # Define the system prompt to establish the agent's persona as a Build Engineer
    system_prompt = """You are a Universal Build Engineer and DevOps Architect working as an autonomous AI agent.
You will receive a list of ALL filenames in a repository.

Your Goal: Autonomously analyze the project structure to determine how to build and run it, regardless of the language or era.

You must be able to handle:
1.  **Standard Stacks**: Node.js, Python, Go, Rust, Java, etc.
2.  **Legacy Systems**: C/C++, Perl, PHP, etc.
3.  **Future/Unknown Languages**: If you see a file extension you don't recognize, use your reasoning capabilities to deduce how it might be run (e.g., looking for a 'build' script, a 'Makefile', or a binary).

Your Tasks (Apply intelligent reasoning for ANY technology):
1.  **REASON**: Think step-by-step. If you don't recognize the stack immediately, look for generic build signals (Makefiles, shell scripts, Dockerfiles, configure scripts).
2.  **FILTER**: Exclude irrelevant directories (node_modules, venv, target, .git, .idea).
3.  **IDENTIFY STACK**: Determine the technology. If unknown, describe the *type* of environment needed (e.g., "Requires a C compiler", "Needs a JVM", "Needs a specific interpreter").
4.  **CLASSIFY TYPE**: 'service' (daemon/server) vs 'script' (batch/cli).
5.  **SELECT FILES**: Identify critical files. For unknown stacks, prioritize `README`, `Makefile`, `build.sh`, and files with unique extensions.
6.  **EXTRACT COMMANDS**: Deduce build/start commands. If unknown, look for a `Makefile` target or a script named `start` or `run`.
7.  **IDENTIFY IMAGE**: Choose a base image.
    -   Standard: `python:3.11`, `node:18`
    -   Unknown/Generic: `ubuntu:latest`, `debian:bullseye`, or `alpine:latest` (and plan to install tools).
8.  **DETECT HEALTH ENDPOINT**: Only if explicit.
9.  **ESTIMATE WAIT TIME**: 3-60s.

IMPORTANT: You are replacing a human engineer. If a human can figure out how to run this by looking at the files, YOU must be able to do it too.
 
User Custom Instructions:
{custom_instructions}
"""

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
    file_list_str = json.dumps(file_list)
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "custom_instructions": custom_instructions, 
            "file_list": file_list_str
        },
        [callback]
    )
    
    return result, callback.get_usage()

