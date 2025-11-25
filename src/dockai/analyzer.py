"""
DockAI Analyzer Module

This module is responsible for the initial analysis of the repository.
It acts as the "Brain" of the operation, understanding the project structure,
identifying the technology stack, and determining the requirements.
"""

import os
import json
from typing import Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import AnalysisResult
from .callbacks import TokenUsageCallback

def analyze_repo_needs(file_list: list, custom_instructions: str = "") -> Tuple[AnalysisResult, Any]:
    """
    Stage 1: The Brain (Analysis).
    
    Uses LangChain and Pydantic to autonomously analyze the repository structure
    and determine the technology stack, requirements, and strategy.

    Args:
        file_list: List of all filenames in the repository.
        custom_instructions: Custom instructions from the user.

    Returns:
        Tuple of (AnalysisResult, usage_dict).
    """
    model_name = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    
    # Initialize Chat Model
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Define the structured output
    structured_llm = llm.with_structured_output(AnalysisResult)
    
    # Define Prompt
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

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Here is the file list: {file_list}

Analyze the project and provide a detailed thought process explaining your reasoning.""")
    ])
    
    # Create Chain
    chain = prompt | structured_llm
    
    # Execute with callback
    callback = TokenUsageCallback()
    file_list_str = json.dumps(file_list)
    
    result = chain.invoke(
        {
            "custom_instructions": custom_instructions, 
            "file_list": file_list_str
        },
        config={"callbacks": [callback]}
    )
    
    return result, callback.get_usage()

