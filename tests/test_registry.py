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


@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_with_target_version_filter(mock_get):
    """Test Docker Hub name= filter when target_version is specified"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "18-alpine"},
            {"name": "18-slim"},
            {"name": "18.20.8-alpine"},
            {"name": "18.20.8"},
            {"name": "18"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("node", target_version="18")
    
    # Should return filtered tags matching version 18
    assert len(tags) > 0
    assert all("18" in tag for tag in tags)
    # Alpine should be prioritized
    assert "alpine" in tags[0]
    
    # Verify the API was called with the name filter
    call_args = mock_get.call_args
    assert call_args is not None
    # Check params include name filter
    params = call_args.kwargs.get("params", {}) if call_args.kwargs else call_args[1].get("params", {})
    assert params.get("name") == "18"


@patch("dockai.utils.registry._fetch_docker_registry_v2_tags")
@patch("dockai.utils.registry._fetch_docker_hub_api")
def test_get_docker_tags_fallback_to_registry_v2(mock_hub_api, mock_registry_v2):
    """Test fallback to Registry v2 when Hub API filter returns no results"""
    # Hub API returns empty (AI suggested wrong version)
    mock_hub_api.return_value = []
    
    # Registry v2 returns all tags
    mock_registry_v2.return_value = [
        "20-alpine", "20-slim", "20", "19-alpine", "18-alpine", "latest"
    ]
    
    tags = get_docker_tags("node", target_version="99")  # Non-existent version
    
    # Should fall back to Registry v2 and return results
    assert len(tags) > 0
    # Hub API should have been called first
    mock_hub_api.assert_called_once()
    # Registry v2 should have been called as fallback
    mock_registry_v2.assert_called_once()


@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_quay_pagination(mock_get):
    """Test Quay.io pagination through multiple pages"""
    # Create mock responses for multiple pages
    page1_response = MagicMock()
    page1_response.status_code = 200
    page1_response.json.return_value = {
        "tags": [{"name": f"v1.{i}"} for i in range(50)],
        "has_additional": True,
        "page": 1
    }
    
    page2_response = MagicMock()
    page2_response.status_code = 200
    page2_response.json.return_value = {
        "tags": [{"name": f"v2.{i}"} for i in range(50)],
        "has_additional": True,
        "page": 2
    }
    
    page3_response = MagicMock()
    page3_response.status_code = 200
    page3_response.json.return_value = {
        "tags": [{"name": f"v3.{i}"} for i in range(25)],
        "has_additional": False,  # Last page
        "page": 3
    }
    
    mock_get.side_effect = [page1_response, page2_response, page3_response]
    
    tags = get_docker_tags("quay.io/namespace/image")
    
    # Should have fetched all pages (50 + 50 + 25 = 125 tags)
    # But we process and filter them
    assert len(tags) > 0
    # Should have made 3 API calls
    assert mock_get.call_count == 3


@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_hub_api_with_filter_success(mock_get):
    """Test that Hub API with filter returns correctly when tags found"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "3.11-alpine"},
            {"name": "3.11-slim"},
            {"name": "3.11.5-alpine"},
            {"name": "3.11"}
        ]
    }
    mock_get.return_value = mock_response
    
    tags = get_docker_tags("python", target_version="3.11")
    
    # Should return filtered Python 3.11 tags
    assert len(tags) > 0
    assert all("3.11" in tag for tag in tags)
    # Alpine should be first
    assert "alpine" in tags[0]


@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_extracts_version_from_image_tag(mock_get):
    """Test that version is extracted from image:tag format"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"name": "20-alpine"},
            {"name": "20-slim"},
            {"name": "20.10.0-alpine"}
        ]
    }
    mock_get.return_value = mock_response
    
    # Pass image with tag - should extract version "20"
    tags = get_docker_tags("node:20-alpine")
    
    # Should work with version extracted from tag
    assert len(tags) > 0


@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_empty_image_name(mock_get):
    """Test handling of empty/invalid image names"""
    tags = get_docker_tags("")
    assert tags == []
    
    tags = get_docker_tags("   ")
    assert tags == []
    
    # httpx.get should not have been called
    mock_get.assert_not_called()
