from unittest.mock import patch, MagicMock
from dockai.generator import generate_dockerfile

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_basic(mock_openai):
    """Test basic Dockerfile generation"""
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]"""
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function
    result = generate_dockerfile(
        stack_info="Python/Flask",
        file_contents="--- FILE: requirements.txt ---\nflask==2.0.0\n"
    )
    
    # Assertions
    assert "FROM python" in result
    assert "WORKDIR" in result
    assert "CMD" in result
    mock_client.chat.completions.create.assert_called_once()

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_with_custom_instructions(mock_openai):
    """Test Dockerfile generation with custom instructions"""
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """FROM node:18-alpine
RUN adduser -D appuser
USER appuser
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 8080
CMD ["npm", "start"]"""
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function with custom instructions
    result = generate_dockerfile(
        stack_info="Node.js/Express",
        file_contents="--- FILE: package.json ---\n{\"name\": \"app\"}\n",
        custom_instructions="Use port 8080 and create non-root user"
    )
    
    # Assertions
    assert "FROM node" in result
    assert "USER appuser" in result or "USER" in result
    assert "8080" in result
    mock_client.chat.completions.create.assert_called_once()

@patch("dockai.generator.OpenAI")
def test_generate_dockerfile_strips_markdown(mock_openai):
    """Test that markdown code blocks are stripped from response"""
    # Setup mock response with markdown
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """```dockerfile
FROM python:3.11-slim
WORKDIR /app
CMD ["python", "app.py"]
```"""
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function
    result = generate_dockerfile(
        stack_info="Python",
        file_contents="--- FILE: app.py ---\nprint('hello')\n"
    )
    
    # Assertions - should strip markdown
    assert "```" not in result
    assert "FROM python" in result
    assert result.startswith("FROM")
