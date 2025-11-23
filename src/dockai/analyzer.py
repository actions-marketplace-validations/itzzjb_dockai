import json
import os
from openai import OpenAI

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_repo_needs(file_list: list, custom_instructions: str = "") -> dict:
    """
    Stage 1: The Brain (Analysis).
    
    This function sends the raw file structure to a lightweight LLM (GPT-4o-mini).
    The goal is to identify the technology stack and filter the list down to 
    only the critical files needed for context (e.g., package.json, requirements.txt).
    
    Returns:
        dict: containing 'stack' (str) and 'files_to_read' (List[str]).
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    file_list_json = json.dumps(file_list)
    
    system_prompt = """
    You are an expert Build Engineer and DevOps Architect. 
    You will receive a JSON list of ALL filenames in a repository.
    
    Your Goal: Analyze the project structure to determine the technology stack and identify the MINIMUM set of critical files required to generate a production-ready Dockerfile.

    Your Tasks:
    1. FILTER: Exclude irrelevant directories and files (e.g., .git, .idea, .vscode, node_modules, venv, __pycache__, dist, build, test coverage reports, images, markdown docs).
    2. IDENTIFY STACK: Determine the primary programming language, framework, and package manager (e.g., "Python/Django with Poetry", "Node.js/Next.js with npm", "Go/Gin").
    3. SELECT FILES: Identify the specific files needed to:
       - Resolve dependencies (e.g., package.json, package-lock.json, yarn.lock, requirements.txt, pyproject.toml, poetry.lock, go.mod, go.sum, Gemfile, Gemfile.lock, pom.xml, build.gradle).
       - Determine the entrypoint (e.g., main.py, app.py, index.js, server.js, main.go, wsgi.py, manage.py).
       - Understand build configuration (e.g., next.config.js, webpack.config.js, angular.json, vite.config.js).
       - See existing container config (e.g., Dockerfile, docker-compose.yml).

    User Custom Instructions:
    {custom_instructions}

    Return a JSON object ONLY with the following structure:
    { 
        "stack": "Detailed description of the tech stack", 
        "files_to_read": ["path/to/file1", "path/to/file2"] 
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
    
    # Robust cleanup: Remove any markdown formatting
    content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # This will be caught by tenacity and retried
        raise ValueError(f"Failed to parse JSON response from Analyzer: {e}. Content: {content}")
