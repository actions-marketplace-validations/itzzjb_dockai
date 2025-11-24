from unittest.mock import patch, MagicMock
from dockai.generator import generate_dockerfile

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_basic(mock_openai):
    """Test basic Dockerfile generation"""
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """{
        "dockerfile": "FROM python:3.11-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install -r requirements.txt\\nCOPY . .\\nCMD [\\"python\\", \\"app.py\\"]",
        "project_type": "service"
    }"""
    mock_response.usage = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function
    result, project_type, usage = generate_dockerfile(
        stack_info="Python/Flask",
        file_contents="--- FILE: requirements.txt ---\nflask==2.0.0\n"
    )
    
    # Assertions
    assert "FROM python" in result
    assert "WORKDIR" in result
    assert "CMD" in result
    assert project_type == "service"
    assert usage is not None
    mock_client.chat.completions.create.assert_called_once()

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_with_custom_instructions(mock_openai):
    """Test Dockerfile generation with custom instructions"""
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """{
        "dockerfile": "FROM node:18-alpine\\nRUN adduser -D appuser\\nUSER appuser\\nWORKDIR /app\\nCOPY package*.json ./\\nRUN npm ci --production\\nCOPY . .\\nEXPOSE 8080\\nCMD [\\"npm\\", \\"start\\"]",
        "project_type": "service"
    }"""
    mock_response.usage = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function with custom instructions
    result, project_type, usage = generate_dockerfile(
        stack_info="Node.js/Express",
        file_contents="--- FILE: package.json ---\n{\"name\": \"app\"}\n",
        custom_instructions="Use port 8080 and create non-root user"
    )
    
    # Assertions
    assert "FROM node" in result
    assert "USER appuser" in result or "USER" in result
    assert "8080" in result
    assert project_type == "service"
    assert usage is not None
    mock_client.chat.completions.create.assert_called_once()

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_strips_markdown(mock_openai):
    """Test that markdown code blocks are stripped from response"""
    # Setup mock response with markdown
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """{
        "dockerfile": "```dockerfile\\nFROM python:3.11-slim\\nWORKDIR /app\\nCMD [\\"python\\", \\"app.py\\"]\\n```",
        "project_type": "script"
    }"""
    mock_response.usage = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function
    result, project_type, usage = generate_dockerfile(
        stack_info="Python",
        file_contents="--- FILE: app.py ---\nprint('hello')\n"
    )
    
    # Assertions - should strip markdown
    assert "```" not in result
    assert "FROM python" in result
    assert result.startswith("FROM")
    assert project_type == "script"
    assert usage is not None

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_with_feedback(mock_openai):
    """Test Dockerfile generation with error feedback"""
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """{
        "dockerfile": "FROM python:3.11-slim",
        "project_type": "service"
    }"""
    mock_response.usage = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function with feedback
    error_msg = "Error: Cannot find module 'missing.js'"
    generate_dockerfile(
        stack_info="Node.js",
        file_contents="...",
        feedback_error=error_msg
    )
    
    # Verify the prompt contains the error message
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args[1]['messages']
    system_prompt = messages[0]['content']
    
    assert "IMPORTANT: The previous Dockerfile you generated failed" in system_prompt
    assert error_msg in system_prompt
