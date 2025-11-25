import os
from typing import Tuple
from openai import OpenAI

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_dockerfile(stack_info: str, file_contents: str, custom_instructions: str = "", feedback_error: str = None) -> Tuple[str, object]:
    """
    Stage 2: The Architect (Generation).
    
    This function uses a high-intelligence LLM (GPT-4o) to synthesize the 
    gathered context into a production-ready Dockerfile. It applies best 
    practices like multi-stage builds, version pinning, and user permissions.
    
    Args:
        stack_info (str): Description of the technology stack.
        file_contents (str): The contents of the critical files.
        custom_instructions (str): Optional custom instructions from the user.
        feedback_error (str): Optional error message from a previous validation attempt.
        
    Returns:
        Tuple: A tuple containing:
            - str: The generated Dockerfile content.
            - str: The detected project type ('service' or 'script').
            - object: The usage statistics from the API call.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    system_prompt = r"""
    You are a Senior DevOps Engineer and Containerization Expert.
    
    Context:
    We are containerizing a {stack} application.
    
    Input:
    Below are the contents of the critical configuration and source files from the repository:
    {file_contents}
    
    User Custom Instructions:
    {custom_instructions}
    
    Your Task:
    Generate a highly optimized, production-ready Multi-Stage Dockerfile for this application.

    IMPORTANT:
    If an existing Dockerfile is provided in the input files, analyze it carefully. Use it to understand the project's specific build requirements, dependencies, and configurations. However, do not just copy it. Improve upon it by applying the best practices listed below.
    
    Requirements:
    1. Base Images: 
       - Use official, minimal base images appropriate for the stack
       - PIN SPECIFIC VERSIONS (never use 'latest' tag)
       - Choose the smallest viable variant (alpine, slim, distroless when appropriate)
       
    2. Security: 
       - Run as a non-root user (create dedicated user if needed)
       - Minimize exposed ports (only what's necessary)
       - Follow principle of least privilege
       
    3. Optimization:
       - Use Multi-Stage builds to separate build and runtime dependencies
       - Optimize layer caching (install dependencies before copying source code)
       - Clean up caches and temporary files in the same RUN instruction
       - Minimize final image size
       
    4. Configuration:
       - Set appropriate environment variables for production
       - Avoid inline comments in multi-line instructions
       - Define proper WORKDIR
       - Expose correct port(s) based on the application
       
    5. Entrypoint:
       - Determine the correct start command from the provided files
       - Use exec form (JSON array) for CMD/ENTRYPOINT
       - Ensure the command is appropriate for the project type
    
    Output Format:
    - Return a JSON object with two keys:
      1. "dockerfile": The raw content of the Dockerfile (string)
      2. "project_type": "service" (if it listens on a port/runs indefinitely) or "script" (if it runs once and exits)
    - Do NOT use markdown code blocks.
    """
    
    formatted_prompt = system_prompt.replace("{stack}", stack_info).replace("{file_contents}", file_contents).replace("{custom_instructions}", custom_instructions)
    
    
    if feedback_error:
        formatted_prompt += f"""

CRITICAL - DOCKERFILE VALIDATION FAILED:
The previous Dockerfile you generated failed validation with the following error:

{feedback_error}

Your Task:
1. Carefully analyze the error message to identify the root cause
2. Determine what went wrong (missing dependencies, wrong paths, incorrect commands, permission issues, etc.)
3. Generate an improved Dockerfile that fixes the specific issue
4. Ensure you don't introduce new problems while fixing this one
5. Apply your expertise to understand and resolve the underlying problem

Generate a corrected Dockerfile that addresses the error above.
"""

    response = client.chat.completions.create(
        model=os.getenv("MODEL_GENERATOR"),
        messages=[
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": "Generate the Dockerfile now."}
        ],
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    usage = response.usage
    
    import json
    try:
        data = json.loads(content)
        dockerfile_content = data.get("dockerfile", "")
        project_type = data.get("project_type", "service")
        
        # Robust cleanup
        dockerfile_content = dockerfile_content.replace("```dockerfile", "").replace("```", "").strip()
        
        return dockerfile_content, project_type, usage
    except Exception:
        # Fallback if JSON parsing fails (unlikely with json_object mode but possible)
        # Assume content is just the Dockerfile
        return content.strip(), "service", usage
