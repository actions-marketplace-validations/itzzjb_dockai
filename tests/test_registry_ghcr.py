"""Tests for GHCR and semantic sorting in registry module."""
import pytest
from unittest.mock import patch, MagicMock
from dockai.utils.registry import get_docker_tags, _get_image_prefix, _sort_tags_semantically

@pytest.fixture(autouse=True)
def clear_registry_cache():
    """Clear the lru_cache of get_docker_tags before each test."""
    get_docker_tags.cache_clear()

@patch("dockai.utils.registry.httpx.get")
def test_get_docker_tags_ghcr(mock_get):
    """Test fetching tags from GHCR with token auth"""
    # GHCR now requires two API calls: one for token, one for tags
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {"token": "test-token"}
    
    mock_tags_response = MagicMock()
    mock_tags_response.status_code = 200
    mock_tags_response.json.return_value = {
        "tags": ["v1.0.0", "v1.0.1", "latest"]
    }
    
    # First call is token, second call is tags
    mock_get.side_effect = [mock_token_response, mock_tags_response]
    
    tags = get_docker_tags("ghcr.io/owner/image")
    
    assert len(tags) > 0
    assert any("ghcr.io" in tag for tag in tags)
    assert any("v1.0.1" in tag for tag in tags)

def test_get_image_prefix_ghcr():
    """Test prefix generation for GHCR"""
    prefix = _get_image_prefix("ghcr.io/owner/image")
    assert prefix == "ghcr.io/owner/image:"

def test_semantic_sorting_logic():
    """Test the semantic sorting helper directly"""
    tags = ["1.0.0", "1.10.0", "1.2.0", "v2.0.0", "latest", "alpine"]
    sorted_tags = _sort_tags_semantically(tags)
    
    # Should be descending order of versions
    # v2.0.0 -> 1.10.0 -> 1.2.0 -> 1.0.0
    # 'latest' and 'alpine' don't match regex so they go to end (or start depending on implementation detail of 0,0,0)
    # Our implementation returns (0,0,0) for non-matches, so they should be at the end in descending sort
    
    assert sorted_tags[0] == "v2.0.0"
    assert sorted_tags[1] == "1.10.0"
    assert sorted_tags[2] == "1.2.0"
    assert sorted_tags[3] == "1.0.0"
