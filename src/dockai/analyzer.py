import json
import os
from typing import Tuple, Dict, List, Any
from openai import OpenAI

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_repo_needs(file_list: list, custom_instructions: str = "") -> Tuple[dict, object]:
    """
    Stage 1: The Brain (Analysis).
    
    This function sends the raw file structure to a lightweight LLM (GPT-4o-mini).
    The goal is to identify the technology stack and filter the list down to 
    only the critical files needed for context (e.g., package.json, requirements.txt).
    
    Args:
        file_list (list): A list of all file paths in the repository.
        custom_instructions (str): Optional custom instructions from the user.
        
    Returns:
        Tuple[Dict, object]: A tuple containing:
            - Dict: A dictionary containing:
                - 'stack' (str): Description of the technology stack.
                - 'files_to_read' (List[str]): List of critical files to read for context.
            - object: The usage statistics from the API call.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    file_list_json = json.dumps(file_list)
    
    system_prompt = r"""
    You are an expert Build Engineer and DevOps Architect. 
    You will receive a JSON list of ALL filenames in a repository.
    
    Your Goal: Analyze the project structure to determine the technology stack, identify critical files, detect health endpoints, and estimate appropriate validation wait times.

    Your Tasks:
    1. FILTER: Exclude irrelevant directories and files (IDE configs, dependency caches, build outputs, test coverage, media files, documentation).
    
    2. IDENTIFY STACK: Determine the primary programming language, framework, and package manager with specific versions when possible.
    
    3. CLASSIFY TYPE: Determine if the project is a "service" (long-running process that listens on a port) or a "script" (runs once and exits). Consider the actual behavior, not just the presence of certain files.
    
    4. SELECT FILES: Identify the specific files needed to understand:
       - Dependencies and their versions (lock files, manifests, module definitions)
       - Application entrypoint(s) and main source files
       - Build and bundler configurations
       - Existing container configurations if present
       
    5. DETECT HEALTH ENDPOINT: Analyze the file structure to predict if there's a health check endpoint:
       - Look for routing files, API handlers, controller definitions
       - Infer common health check patterns based on the framework
       - Determine the likely port based on framework conventions or configuration files
       - Return null if no health endpoint can be inferred
       
    6. ESTIMATE WAIT TIME: Based on the stack characteristics, estimate initialization time in seconds:
       - Consider: compilation needs, JVM/runtime startup, database connections, model loading, framework bootstrapping
       - Provide a realistic estimate based on the complexity you observe
       - Range: 3-30 seconds depending on stack complexity

    User Custom Instructions:
    {custom_instructions}

    Return a JSON object ONLY with the following structure:
    { 
        "stack": "Detailed description of the tech stack",
        "project_type": "service" or "script",
        "files_to_read": ["path/to/file1", "path/to/file2"],
        "health_endpoint": {"path": "/health", "port": 8080} or null,
        "recommended_wait_time": 5
    }
    """
    
    formatted_prompt = system_prompt.replace("{custom_instructions}", custom_instructions)

    response = client.chat.completions.create(
        model=os.getenv("MODEL_ANALYZER"),
        messages=[
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": f"Here is the file list: {file_list_json}"}
        ],
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    usage = response.usage
    
    # Robust cleanup: Remove any markdown formatting
    content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(content), usage
    except json.JSONDecodeError as e:
        # This will be caught by tenacity and retried
        raise ValueError(f"Failed to parse JSON response from Analyzer: {e}. Content: {content}")
