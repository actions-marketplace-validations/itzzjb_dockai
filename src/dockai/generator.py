import os
from openai import OpenAI

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_dockerfile(stack_info: str, file_contents: str, custom_instructions: str = "", feedback_error: str = None) -> str:
    """
    Stage 2: The Architect (Generation).
    
    This function uses a high-intelligence LLM (GPT-4o) to synthesize the 
    gathered context into a production-ready Dockerfile. It applies best 
    practices like multi-stage builds, version pinning, and user permissions.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    system_prompt = """
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
    If an existing Dockerfile is provided in the input files, analyze it carefully. Use it to understand the project's specific build requirements, dependencies, and configurations. However, do not just copy it. Improve upon it by applying the best practices listed below (multi-stage, security, optimization).
    
    Requirements:
    1. Base Images: Use official, minimal base images (e.g., alpine, slim). PIN SPECIFIC VERSIONS (e.g., `node:18-alpine` NOT `node:latest`).
    2. Security: 
       - Run as a non-root user. Create a user if necessary.
       - Do not expose unnecessary ports.
    3. Optimization:
       - Use Multi-Stage builds to separate build dependencies from the runtime environment.
       - Optimize layer caching (e.g., COPY dependency files and install BEFORE copying source code).
       - Clean up cache/temporary files in the same RUN instruction to reduce image size.
    4. Configuration:
       - Set appropriate environment variables (e.g., `ENV NODE_ENV=production`, `ENV PYTHONDONTWRITEBYTECODE=1`).
       - Define the correct WORKDIR.
       - Expose the correct port (infer from code if possible, otherwise use standard ports like 3000, 8000, 8080).
    5. Entrypoint:
       - accurately determine the start command based on the provided files (e.g., `CMD ["python", "app.py"]`, `CMD ["npm", "start"]`).
    
    Output Format:
    - Return ONLY the raw content of the Dockerfile.
    - Do NOT use markdown code blocks (```).
    - Add helpful comments inside the Dockerfile explaining complex steps.
    """
    
    formatted_prompt = system_prompt.replace("{stack}", stack_info).replace("{file_contents}", file_contents).replace("{custom_instructions}", custom_instructions)
    
    if feedback_error:
        formatted_prompt += f"\n\nIMPORTANT: The previous Dockerfile you generated failed to build or run with the following error:\n{feedback_error}\n\nPlease analyze this error and fix the Dockerfile accordingly."

    response = client.chat.completions.create(
        model=os.getenv("MODEL_GENERATOR"),
        messages=[
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": "Generate the Dockerfile now."}
        ]
    )
    
    content = response.choices[0].message.content
    # Robust cleanup: Remove any markdown formatting the model might have added
    content = content.replace("```dockerfile", "").replace("```", "").strip()
    return content
