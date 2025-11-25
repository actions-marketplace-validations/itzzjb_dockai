import os
import json
from typing import Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import AnalysisResult
from .callbacks import TokenUsageCallback

def analyze_repo_needs(file_list: list, custom_instructions: str = "") -> Tuple[AnalysisResult, Any]:
    """
    Stage 1: The Brain (Analysis).
    
    Uses LangChain and Pydantic for structured analysis of the repository.
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
    system_prompt = """You are an expert Build Engineer and DevOps Architect working as an AI agent.
You will receive a list of ALL filenames in a repository.

Your Goal: Analyze the project structure to determine the technology stack, identify critical files, and prepare for Dockerfile generation.

Your Tasks:
1. REASON: First, think step-by-step about what the file structure implies.
2. FILTER: Exclude irrelevant directories and files.
3. IDENTIFY STACK: Determine the primary programming language, framework, and package manager.
4. CLASSIFY TYPE: Determine if the project is a "service" (long-running) or a "script" (runs once).
5. SELECT FILES: Identify specific files needed to understand dependencies, entrypoints, and build config.
6. EXTRACT COMMANDS: Predict the 'build_command' and 'start_command' based on standard conventions.
7. IDENTIFY IMAGE: Predict the 'suggested_base_image' (official Docker Hub repo name) for this stack.
8. DETECT HEALTH ENDPOINT (OPTIONAL): 
   - Only set health_endpoint if you find EXPLICIT health check routes in the file list (e.g., health.ts, health.py, routes/health.js)
   - Common patterns: /health, /api/health, /healthz, /ready, /ping
   - If NO health endpoint file is clearly present, set health_endpoint to null
   - Do NOT guess - only provide if you're confident
9. ESTIMATE WAIT TIME: Estimate initialization time (3-30s).

User Custom Instructions:
{custom_instructions}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Here is the file list: {file_list}")
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
