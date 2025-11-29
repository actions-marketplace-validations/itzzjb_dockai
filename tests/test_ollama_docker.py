"""Tests for Ollama Docker support."""
import pytest
from unittest.mock import patch, MagicMock

from dockai.utils.ollama_docker import (
    is_ollama_available,
    is_ollama_installed,
    is_docker_available,
    get_ollama_url,
    OLLAMA_DOCKER_IMAGE,
    OLLAMA_CONTAINER_NAME,
)


class TestOllamaAvailability:
    """Tests for Ollama availability checks."""
    
    @patch("dockai.utils.ollama_docker.httpx.get")
    def test_ollama_available_success(self, mock_get):
        """Test that is_ollama_available returns True when API responds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        assert is_ollama_available("http://localhost:11434") is True
        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5.0)
    
    @patch("dockai.utils.ollama_docker.httpx.get")
    def test_ollama_available_failure(self, mock_get):
        """Test that is_ollama_available returns False on connection error."""
        mock_get.side_effect = Exception("Connection refused")
        
        assert is_ollama_available("http://localhost:11434") is False
    
    @patch("dockai.utils.ollama_docker.httpx.get")
    def test_ollama_available_bad_status(self, mock_get):
        """Test that is_ollama_available returns False on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        assert is_ollama_available("http://localhost:11434") is False


class TestOllamaInstalled:
    """Tests for Ollama installation check."""
    
    @patch("dockai.utils.ollama_docker.subprocess.run")
    def test_ollama_installed_yes(self, mock_run):
        """Test detection of installed Ollama."""
        mock_run.return_value = MagicMock(returncode=0)
        
        assert is_ollama_installed() is True
        mock_run.assert_called_once()
    
    @patch("dockai.utils.ollama_docker.subprocess.run")
    def test_ollama_installed_no(self, mock_run):
        """Test detection when Ollama is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        assert is_ollama_installed() is False


class TestDockerAvailable:
    """Tests for Docker availability check."""
    
    @patch("dockai.utils.ollama_docker.subprocess.run")
    def test_docker_available_yes(self, mock_run):
        """Test detection of running Docker."""
        mock_run.return_value = MagicMock(returncode=0)
        
        assert is_docker_available() is True
    
    @patch("dockai.utils.ollama_docker.subprocess.run")
    def test_docker_available_no(self, mock_run):
        """Test detection when Docker is not available."""
        mock_run.side_effect = FileNotFoundError()
        
        assert is_docker_available() is False


class TestGetOllamaUrl:
    """Tests for get_ollama_url function."""
    
    @patch("dockai.utils.ollama_docker.is_ollama_available")
    def test_returns_preferred_url_when_available(self, mock_available):
        """Test that preferred URL is returned when Ollama is available."""
        mock_available.return_value = True
        
        url = get_ollama_url(preferred_url="http://localhost:11434")
        
        assert url == "http://localhost:11434"
        mock_available.assert_called_with("http://localhost:11434")
    
    @patch("dockai.utils.ollama_docker.start_ollama_container")
    @patch("dockai.utils.ollama_docker.is_ollama_installed")
    @patch("dockai.utils.ollama_docker.is_ollama_available")
    def test_starts_docker_when_not_available(self, mock_available, mock_installed, mock_start):
        """Test that Docker container is started when Ollama not available."""
        mock_available.return_value = False
        mock_installed.return_value = False
        mock_start.return_value = "http://localhost:11435"
        
        url = get_ollama_url(model_name="llama3", preferred_url="http://localhost:11434")
        
        assert url == "http://localhost:11435"
        mock_start.assert_called_once_with("llama3")


class TestOllamaDockerConstants:
    """Tests for module constants."""
    
    def test_docker_image_defined(self):
        """Test that Docker image is properly defined."""
        assert OLLAMA_DOCKER_IMAGE == "ollama/ollama:latest"
    
    def test_container_name_defined(self):
        """Test that container name is properly defined."""
        assert OLLAMA_CONTAINER_NAME == "dockai-ollama"
