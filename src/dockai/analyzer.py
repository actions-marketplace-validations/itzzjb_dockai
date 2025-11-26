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
    system_prompt = """You are an expert Build Engineer and DevOps Architect working as an autonomous AI agent.
You will receive a list of ALL filenames in a repository.

Your Goal: Autonomously analyze the project structure to determine the technology stack, identify critical files, and prepare for Dockerfile generation. You must work with ANY programming language, framework, or technology.

Your Tasks (Apply intelligent reasoning for ANY technology):
1.  **REASON**: Think step-by-step about what the file structure implies about the technology stack and architecture.
2.  **FILTER**: Exclude irrelevant directories and files (build artifacts, caches, IDE configs, etc.).
3.  **IDENTIFY STACK**: Determine the primary technology, frameworks, and build tools by analyzing file patterns, extensions, and project structure.
4.  **CLASSIFY TYPE**: Determine if the project is a "service" (long-running process like a web server, API, daemon) or a "script" (runs once and exits).
5.  **SELECT FILES**: Identify critical files needed to understand dependencies, entrypoints, configuration, and build requirements.
6.  **EXTRACT COMMANDS**: Determine the 'build_command' and 'start_command' by understanding the detected technology's conventions.
7.  **IDENTIFY IMAGE**: Determine the most appropriate Docker Hub base image for the detected technology stack.
8.  **DETECT HEALTH ENDPOINT (OPTIONAL)**: 
    -   Only set health_endpoint if you find EXPLICIT health check implementations in the file structure.
    -   If NO health endpoint is clearly indicated, set health_endpoint to null.
    -   Do NOT guess - only provide if you're confident based on actual file patterns.
9.  **ESTIMATE WAIT TIME**: Estimate container initialization time based on the detected technology (3-60s).

IMPORTANT: Work with ANY technology stack - do not limit yourself to specific languages or frameworks. Use your knowledge to analyze and understand any project structure.

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
    
    # Execute the chain
    result = chain.invoke(
        {
            "custom_instructions": custom_instructions, 
            "file_list": file_list_str
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()

