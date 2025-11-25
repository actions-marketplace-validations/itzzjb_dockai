import os
from unittest.mock import patch, MagicMock
from dockai.generator import generate_dockerfile
from dockai.schemas import DockerfileResult

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_dockerfile_basic(mock_callback_class, mock_chat_openai):
    """Test basic Dockerfile generation"""
    dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]"""
    
    mock_result = DockerfileResult(
        thought_process="Using Python slim image for smaller size",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {
        "total_tokens": 800,
        "prompt_tokens": 500,
        "completion_tokens": 300
    }
    mock_callback_class.return_value = mock_callback
    
    result, project_type, thought_process, usage = generate_dockerfile(
        stack_info="Python/Flask",
        file_contents="--- FILE: requirements.txt ---\nflask==2.0.0\n"
    )
    
    assert "FROM python" in result
    assert "WORKDIR" in result
    assert "CMD" in result
    assert project_type == "service"
    assert "slim image" in thought_process
    assert usage["total_tokens"] == 800

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_dockerfile_with_custom_instructions(mock_callback_class, mock_chat_openai):
    """Test Dockerfile generation with custom instructions"""
    dockerfile_content = """FROM node:18-alpine
RUN adduser -D appuser
USER appuser
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 8080
CMD ["npm", "start"]"""
    
    mock_result = DockerfileResult(
        thought_process="Using Alpine for size, non-root user for security",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 900}
    mock_callback_class.return_value = mock_callback
    
    result, project_type, thought_process, usage = generate_dockerfile(
        stack_info="Node.js/Express",
        file_contents="--- FILE: package.json ---\n{\"name\": \"app\"}\n",
        custom_instructions="Use port 8080 and create non-root user"
    )
    
    assert "FROM node" in result
    assert "USER appuser" in result or "USER" in result
    assert "8080" in result
    assert project_type == "service"

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_dockerfile_with_feedback(mock_callback_class, mock_chat_openai):
    """Test Dockerfile generation with error feedback"""
    dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]"""
    
    mock_result = DockerfileResult(
        thought_process="Fixed missing dependency issue",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 1000}
    mock_callback_class.return_value = mock_callback
    
    error_msg = "Error: Cannot find module 'missing-package'"
    result, project_type, thought_process, usage = generate_dockerfile(
        stack_info="Node.js",
        file_contents="...",
        feedback_error=error_msg
    )
    
    # Verify the chain was invoked (error passed via prompt)
    assert mock_chain.invoke.called

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_dockerfile_script_type(mock_callback_class, mock_chat_openai):
    """Test Dockerfile generation for a script"""
    dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "cli.py"]"""
    
    mock_result = DockerfileResult(
        thought_process="This is a CLI script that runs once",
        dockerfile=dockerfile_content,
        project_type="script"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 700}
    mock_callback_class.return_value = mock_callback
    
    result, project_type, thought_process, usage = generate_dockerfile(
        stack_info="Python CLI",
        file_contents="--- FILE: cli.py ---\nprint('hello')\n"
    )
    
    assert "FROM python" in result
    assert project_type == "script"

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_dockerfile_with_verified_tags(mock_callback_class, mock_chat_openai):
    """Test that verified tags are passed to the generator"""
    dockerfile_content = "FROM node:20-alpine\nWORKDIR /app\nCMD [\"npm\", \"start\"]"
    
    mock_result = DockerfileResult(
        thought_process="Using verified tag node:20-alpine",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 600}
    mock_callback_class.return_value = mock_callback
    
    verified_tags = "node:20-alpine, node:20-slim, node:20"
    result, project_type, thought_process, usage = generate_dockerfile(
        stack_info="Node.js",
        file_contents="...",
        verified_tags=verified_tags
    )
    
    # Verify chain was invoked
    assert mock_chain.invoke.called

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
@patch("dockai.generator.os.getenv")
def test_generate_uses_model_from_kwargs(mock_getenv, mock_callback_class, mock_chat_openai):
    """Test that generator uses model_name from kwargs"""
    mock_getenv.side_effect = lambda key, default=None: {
        "OPENAI_API_KEY": "test-key"
    }.get(key, default)
    
    dockerfile_content = "FROM python:3.11"
    
    mock_result = DockerfileResult(
        thought_process="Test",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 100}
    mock_callback_class.return_value = mock_callback
    
    # Pass custom model via kwargs
    generate_dockerfile(
        stack_info="Python",
        file_contents="...",
        model_name="gpt-4o"
    )
    
    # Verify ChatOpenAI was initialized with the custom model
    mock_chat_openai.assert_called_once()
    call_kwargs = mock_chat_openai.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"

@patch("dockai.generator.ChatOpenAI")
@patch("dockai.generator.TokenUsageCallback")
def test_generate_with_build_and_start_commands(mock_callback_class, mock_chat_openai):
    """Test that build and start commands are passed to generator"""
    dockerfile_content = "FROM python:3.11\nRUN pip install -r requirements.txt\nCMD [\"python\", \"app.py\"]"
    
    mock_result = DockerfileResult(
        thought_process="Using detected build and start commands",
        dockerfile=dockerfile_content,
        project_type="service"
    )
    
    mock_llm = MagicMock()
    mock_chat_openai.return_value = mock_llm
    
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_result
    mock_structured_llm.__or__ = MagicMock(return_value=mock_chain)
    
    mock_callback = MagicMock()
    mock_callback.get_usage.return_value = {"total_tokens": 500}
    mock_callback_class.return_value = mock_callback
    
    generate_dockerfile(
        stack_info="Python",
        file_contents="...",
        build_command="pip install -r requirements.txt",
        start_command="python app.py"
    )
    
    # Verify chain was invoked
    assert mock_chain.invoke.called
