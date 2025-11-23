import json
import os
from openai import OpenAI

def analyze_repo_needs(file_list: list) -> dict:
    """
    Stage 1: The Brain.
    Asks the AI which files are critical to read based on the file structure.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Convert list to JSON string for the prompt
    file_list_json = json.dumps(file_list)
    
    system_prompt = """
    You are a Build Engineer. You will receive a JSON list of ALL filenames in a repository.
    
    Your Task:
    1. FILTER: Ignore irrelevant files (e.g., .idea, .vscode, dist, build, images, markdown docs).
    2. ANALYZE: Identify the technology stack (e.g., Python/Flask, Node/Express).
    3. SELECT: Pick the SPECIFIC configuration and source files needed to understand the build (e.g., package.json, requirements.txt, main.py, Dockerfile).
    
    Return a JSON object ONLY: 
    { 
        "stack": "Name of the tech stack", 
        "files_to_read": ["path/to/critical_file1", "path/to/critical_file2"] 
    }
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using mini for speed as requested
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the file list: {file_list_json}"}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        # Fallback or error handling
        print(f"Error in analysis stage: {e}")
        return {"stack": "unknown", "files_to_read": []}
