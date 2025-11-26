"""Tests for the analyzer module."""
import pytest
from unittest.mock import patch, MagicMock
from dockai.analyzer import analyze_repo_needs
from dockai.schemas import AnalysisResult, HealthEndpoint


class TestAnalyzeRepoNeeds:
    """Test analyze_repo_needs function."""
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_python_project(self, mock_chat, mock_invoke):
        """Test analyzing a Python project."""
        health_endpoint = HealthEndpoint(path="/health", port=8080)
        mock_result = AnalysisResult(
            thought_process="Found Python project with Flask",
            stack="Python with Flask",
            project_type="service",
            files_to_read=["requirements.txt", "app.py"],
            build_command="pip install -r requirements.txt",
            start_command="python app.py",
            suggested_base_image="python:3.11-slim",
            health_endpoint=health_endpoint,
            recommended_wait_time=5
        )
        
        mock_invoke.return_value = mock_result
        
        file_tree = ["app.py", "requirements.txt", "README.md"]
        result, usage = analyze_repo_needs(file_tree)
        
        assert isinstance(result, AnalysisResult)
        assert result.stack == "Python with Flask"
        assert result.project_type == "service"
        assert "requirements.txt" in result.files_to_read
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_node_project(self, mock_chat, mock_invoke):
        """Test analyzing a Node.js project."""
        mock_result = AnalysisResult(
            thought_process="Found Node.js project with Express",
            stack="Node.js with Express",
            project_type="service",
            files_to_read=["package.json", "index.js"],
            build_command="npm install",
            start_command="npm start",
            suggested_base_image="node:20-alpine",
            recommended_wait_time=10
        )
        
        mock_invoke.return_value = mock_result
        
        file_tree = ["package.json", "index.js", "src/"]
        result, usage = analyze_repo_needs(file_tree)
        
        assert result.stack == "Node.js with Express"
        assert result.suggested_base_image == "node:20-alpine"
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_go_project(self, mock_chat, mock_invoke):
        """Test analyzing a Go project."""
        mock_result = AnalysisResult(
            thought_process="Found Go project",
            stack="Go",
            project_type="service",
            files_to_read=["go.mod", "main.go"],
            build_command="go build -o app",
            start_command="./app",
            suggested_base_image="golang:1.21-alpine",
            recommended_wait_time=3
        )
        
        mock_invoke.return_value = mock_result
        
        file_tree = ["go.mod", "go.sum", "main.go"]
        result, usage = analyze_repo_needs(file_tree)
        
        assert result.stack == "Go"
        assert "go.mod" in result.files_to_read
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_script_project(self, mock_chat, mock_invoke):
        """Test analyzing a script-type project."""
        mock_result = AnalysisResult(
            thought_process="Found Python script",
            stack="Python",
            project_type="script",
            files_to_read=["script.py"],
            build_command=None,
            start_command="python script.py",
            suggested_base_image="python:3.11-slim",
            recommended_wait_time=3
        )
        
        mock_invoke.return_value = mock_result
        
        file_tree = ["script.py"]
        result, usage = analyze_repo_needs(file_tree)
        
        assert result.project_type == "script"
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_with_custom_instructions(self, mock_chat, mock_invoke):
        """Test analyzer with custom instructions."""
        mock_result = AnalysisResult(
            thought_process="Applied custom alpine preference",
            stack="Python",
            project_type="service",
            files_to_read=["app.py"],
            build_command=None,
            start_command="python app.py",
            suggested_base_image="python:3.11-alpine",
            recommended_wait_time=5
        )
        
        mock_invoke.return_value = mock_result
        
        file_tree = ["app.py"]
        result, usage = analyze_repo_needs(
            file_tree,
            custom_instructions="Always use alpine images"
        )
        
        assert "alpine" in result.suggested_base_image
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_returns_usage_stats(self, mock_chat, mock_invoke):
        """Test that analyzer returns usage statistics."""
        mock_result = AnalysisResult(
            thought_process="Analysis complete",
            stack="Python",
            project_type="service",
            files_to_read=["app.py"],
            build_command=None,
            start_command="python app.py",
            suggested_base_image="python:3.11",
            recommended_wait_time=5
        )
        
        mock_invoke.return_value = mock_result
        
        result, usage = analyze_repo_needs(["app.py"])
        
        assert isinstance(usage, dict)
        assert "total_tokens" in usage
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
    
    @patch("dockai.analyzer.safe_invoke_chain")
    @patch("dockai.analyzer.ChatOpenAI")
    def test_analyze_no_health_endpoint(self, mock_chat, mock_invoke):
        """Test analysis result with no health endpoint."""
        mock_result = AnalysisResult(
            thought_process="No explicit health endpoint found",
            stack="Python",
            project_type="service",
            files_to_read=["app.py"],
            build_command=None,
            start_command="python app.py",
            suggested_base_image="python:3.11",
            health_endpoint=None,
            recommended_wait_time=5
        )
        
        mock_invoke.return_value = mock_result
        
        result, usage = analyze_repo_needs(["app.py"])
        
        assert result.health_endpoint is None
