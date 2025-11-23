import os
from openai import OpenAI

def generate_dockerfile(stack_info: str, file_contents: str) -> str:
    """
    Stage 2: The Architect (Generation).
    
    This function uses a high-intelligence LLM (GPT-4o) to synthesize the 
    gathered context into a production-ready Dockerfile. It applies best 
    practices like multi-stage builds, version pinning, and user permissions.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    system_prompt = """
    You are an expert DevOps Researcher. 
    Context: We are building a {stack} application.
    Here are the contents of the critical configuration files:
    {file_contents}
    
    Task: Write a production-ready Multi-Stage Dockerfile.
    - Pin versions (Alpine/Slim).
    - Non-root user.
    - Optimize caching (COPY requirements first).
    
    Output ONLY the Dockerfile content. Do not include markdown formatting (```dockerfile ... ```). Just the raw content.
    """
    
    formatted_prompt = system_prompt.replace("{stack}", stack_info).replace("{file_contents}", file_contents)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using the most capable model for complex code generation
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": "Generate the Dockerfile now."}
            ]
        )
        
        content = response.choices[0].message.content
        # Robust cleanup: Remove any markdown formatting the model might have added
        content = content.replace("```dockerfile", "").replace("```", "").strip()
        return content
        
    except Exception as e:
        print(f"Error in generation stage: {e}")
        return "# Error generating Dockerfile"
