import pytest
from unittest.mock import patch, MagicMock
from dockai.utils.registry import get_docker_tags, _get_image_prefix

@pytest.fixture(autouse=True)
def clear_registry_cache():
    """Clear the lru_cache of get_docker_tags before each test."""
    get_docker_tags.cache_clear()

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_docker_hub(mock_get):
    """Test fetching tags from Docker Hub"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "20-alpine"},
            {"name": "20-slim"},
            {"name": "20"},
            {"name": "18-alpine"},
            {"name": "latest"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("node")
    
    assert len(tags) > 0
    assert any("20-alpine" in tag for tag in tags)
    # Should prioritize alpine tags
    assert tags[0].endswith("alpine") or "alpine" in tags[0]

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_gcr(mock_get):
    """Test fetching tags from GCR"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tags": ["v1.0-alpine", "v1.0", "latest"]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("gcr.io/my-project/my-image")
    
    assert len(tags) > 0
    assert any("gcr.io" in tag for tag in tags)
    assert any("alpine" in tag for tag in tags)

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_quay(mock_get):
    """Test fetching tags from Quay.io"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tags": [
            {"name": "v2.0-alpine"},
            {"name": "v2.0"},
            {"name": "latest"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("quay.io/namespace/image")
    
    assert len(tags) > 0
    assert any("quay.io" in tag for tag in tags)

def test_get_docker_tags_ecr():
    """Test ECR detection (should skip tag fetching)"""
    tags = get_docker_tags("123456789.dkr.ecr.us-east-1.amazonaws.com/my-repo")
    
    # Should return empty list for ECR (requires AWS credentials)
    assert tags == []

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_network_error(mock_get):
    """Test handling of network errors"""
    mock_get.side_effect = Exception("Network error")
    
    tags = get_docker_tags("node")
    
    # Should return empty list on error
    assert tags == []

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_version_detection(mock_get):
    """Test that it detects and uses latest version"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "21-alpine"},
            {"name": "21-slim"},
            {"name": "21"},
            {"name": "20-alpine"},
            {"name": "20-slim"},
            {"name": "18-alpine"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("node")
    
    # Should prioritize version 21 (latest)
    assert any("21" in tag for tag in tags)
    # Should have alpine variants first
    if len(tags) > 0:
        assert "alpine" in tags[0] or "21" in tags[0]

def test_get_image_prefix_docker_hub():
    """Test prefix generation for Docker Hub"""
    prefix = _get_image_prefix("node")
    assert prefix == "node:"
    
    prefix = _get_image_prefix("library/node")
    assert prefix == "node:"  # Should strip library/

def test_get_image_prefix_gcr():
    """Test prefix generation for GCR"""
    prefix = _get_image_prefix("gcr.io/project/image")
    assert prefix == "gcr.io/project/image:"

def test_get_image_prefix_quay():
    """Test prefix generation for Quay.io"""
    prefix = _get_image_prefix("quay.io/namespace/image")
    assert prefix == "quay.io/namespace/image:"

def test_get_image_prefix_ecr():
    """Test prefix generation for ECR"""
    prefix = _get_image_prefix("123456789.dkr.ecr.us-east-1.amazonaws.com/repo")
    assert prefix == "123456789.dkr.ecr.us-east-1.amazonaws.com/repo:"

def test_get_image_prefix_acr():
    """Test prefix generation for Azure Container Registry"""
    prefix = _get_image_prefix("myregistry.azurecr.io/image")
    assert prefix == "myregistry.azurecr.io/image:"

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_alpine_priority(mock_get):
    """Test that alpine tags are prioritized"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "20"},
            {"name": "20-slim"},
            {"name": "20-alpine"},
            {"name": "20-bullseye"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("node")
    
    # Alpine should come first
    assert len(tags) > 0
    alpine_tags = [t for t in tags if "alpine" in t]
    assert len(alpine_tags) > 0
    # First tag should be alpine
    assert "alpine" in tags[0]
