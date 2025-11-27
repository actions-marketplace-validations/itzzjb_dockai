"""
DockAI Container Registry Integration.

This module provides functionality to interact with various container registries
(Docker Hub, GCR, Quay.io, ECR) to verify image existence and fetch valid tags.
This is critical for preventing the AI from hallucinating non-existent image tags.
"""

import httpx
import logging
from typing import List

from .rate_limiter import handle_registry_rate_limit

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


import re
from functools import lru_cache
from typing import List, Optional

@lru_cache(maxsize=128)
@handle_registry_rate_limit
def get_docker_tags(image_name: str, limit: int = 5) -> List[str]:
    """
    Fetches valid tags for a given Docker image from supported registries.
    
    This function queries the registry API to get a list of available tags for
    the specified image. It prioritizes 'alpine' and 'slim' tags to encourage
    smaller, more secure images. Results are cached in memory.
    
    Supported Registries:
    - Docker Hub (default)
    - Google Container Registry (gcr.io)
    - Quay.io
    - GitHub Container Registry (ghcr.io)
    - AWS ECR (limited support, skips verification)

    Args:
        image_name (str): The name of the image (e.g., 'node', 'gcr.io/my-project/my-image').
        limit (int, optional): The maximum number of fallback tags to return. Defaults to 5.

    Returns:
        List[str]: A list of verified, full image tags.
    """
    tags = []
    
    try:
        # Dispatch to appropriate registry handler
        if ".dkr.ecr." in image_name and ".amazonaws.com" in image_name:
            logger.info(f"ECR image detected: {image_name}. Skipping tag verification (requires AWS credentials).")
            return []
            
        elif "gcr.io" in image_name:
            tags = _fetch_gcr_tags(image_name)
            
        elif "quay.io" in image_name:
            tags = _fetch_quay_tags(image_name)
            
        elif "ghcr.io" in image_name:
            tags = _fetch_ghcr_tags(image_name)
            
        else:
            tags = _fetch_docker_hub_tags(image_name)

        if not tags:
            return []

        # Filter and sort tags
        return _process_tags(image_name, tags, limit)
        
    except Exception as e:
        logger.warning(f"Failed to fetch tags for {image_name}: {e}")
        return []


def _fetch_docker_hub_tags(image_name: str) -> List[str]:
    """Fetch tags from Docker Hub."""
    # Handle official images (e.g., 'node' -> 'library/node')
    hub_image_name = image_name
    if "/" not in hub_image_name:
        hub_image_name = f"library/{hub_image_name}"
    elif hub_image_name.startswith("docker.io/"):
        hub_image_name = hub_image_name.replace("docker.io/", "")
        
    url = f"https://hub.docker.com/v2/repositories/{hub_image_name}/tags"
    response = httpx.get(url, params={"page_size": 100}, timeout=5.0)
    
    if response.status_code == 200:
        results = response.json().get("results", [])
        return [r["name"] for r in results]
    return []


def _fetch_gcr_tags(image_name: str) -> List[str]:
    """Fetch tags from Google Container Registry."""
    # Format: gcr.io/project/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    domain = image_name.split("/")[0]
    url = f"https://{domain}/v2/{repo_path}/tags/list"
    
    response = httpx.get(url, timeout=5.0)
    if response.status_code == 200:
        return response.json().get("tags", [])
    return []


def _fetch_quay_tags(image_name: str) -> List[str]:
    """Fetch tags from Quay.io."""
    # Format: quay.io/namespace/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    url = f"https://quay.io/api/v1/repository/{repo_path}/tag"
    
    response = httpx.get(url, timeout=5.0)
    if response.status_code == 200:
        data = response.json().get("tags", [])
        return [t["name"] for t in data]
    return []


def _fetch_ghcr_tags(image_name: str) -> List[str]:
    """Fetch tags from GitHub Container Registry."""
    # GHCR requires a token even for public images usually, but we can try the anonymous endpoint
    # or the standard OCI distribution API if public.
    # Format: ghcr.io/owner/image
    # Note: GHCR often requires auth, so this might be limited for public packages.
    # We'll try the standard OCI tags/list endpoint.
    
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    url = f"https://ghcr.io/v2/{repo_path}/tags/list"
    
    # GHCR often returns 401 for unauthenticated requests even on public images
    # We can try to get a token first if needed, but for now we'll attempt a direct call
    # and fail gracefully if auth is required.
    response = httpx.get(url, timeout=5.0)
    
    if response.status_code == 200:
        return response.json().get("tags", [])
    elif response.status_code == 401:
        # Try to get an anonymous token? (Complex for GHCR)
        # For now, log and return empty
        logger.debug(f"GHCR requires auth for {image_name}, skipping verification")
        return []
    return []


def _process_tags(image_name: str, tags: List[str], limit: int) -> List[str]:
    """Filter, sort, and format the fetched tags."""
    # Filter out unstable tags
    version_tags = [t for t in tags if t not in ["latest", "stable", "edge", "nightly", "canary"]]
    
    if not version_tags:
        return []

    # Sort tags semantically to find the latest versions
    # We want to find the highest version number
    sorted_versions = _sort_tags_semantically(version_tags)
    
    if not sorted_versions:
        # Fallback to original list if sorting fails
        sorted_versions = version_tags

    # Get the latest version (first in the sorted list)
    latest_tag = sorted_versions[0]
    
    # Extract the version number part (e.g., "3.11" from "3.11-slim")
    # This regex looks for the first sequence of numbers and dots
    match = re.match(r"^v?(\d+(?:\.\d+)*)", latest_tag)
    latest_version_prefix = match.group(1) if match else None

    prefix = _get_image_prefix(image_name)

    if latest_version_prefix:
        logger.info(f"Detected latest version for {image_name}: {latest_version_prefix}")
        
        # Get all tags that start with this version prefix
        version_specific_tags = [t for t in tags if t.startswith(latest_version_prefix) or (t.startswith("v") and t[1:].startswith(latest_version_prefix))]
        
        # Sort: Alpine first, then Slim, then others
        def preference_sort(tag):
            score = 0
            if "alpine" in tag: score -= 2
            elif "slim" in tag: score -= 1
            if "window" in tag: score += 10 # Penalize windows images
            return score
            
        final_tags = sorted(version_specific_tags, key=preference_sort)
        return [f"{prefix}{t}" for t in final_tags]

    # Fallback Mix Strategy
    alpine_tags = [t for t in tags if "alpine" in t]
    slim_tags = [t for t in tags if "slim" in t]
    standard_tags = [t for t in tags if "alpine" not in t and "slim" not in t and "window" not in t]
    
    selected_tags = []
    selected_tags.extend(alpine_tags[:2])
    selected_tags.extend(slim_tags[:2])
    selected_tags.extend(standard_tags[:1])
    
    if len(selected_tags) >= 3:
        unique_tags = sorted(list(set(selected_tags)), reverse=True)
        return [f"{prefix}{t}" for t in unique_tags]
        
    return [f"{prefix}{t}" for t in tags[:limit]]


def _sort_tags_semantically(tags: List[str]) -> List[str]:
    """
    Sorts tags based on semantic versioning (highest first).
    Handles tags like '1.2.3', 'v1.2.3', '1.2.3-alpine'.
    """
    def version_key(tag):
        # Extract the version number part
        match = re.match(r"^v?(\d+(?:\.\d+)*)", tag)
        if not match:
            return (0, 0, 0) # Low priority for non-version tags
        
        version_str = match.group(1)
        try:
            # Convert "1.2.3" to (1, 2, 3)
            return tuple(map(int, version_str.split('.')))
        except ValueError:
            return (0, 0, 0)

    # Sort descending (highest version first)
    return sorted(tags, key=version_key, reverse=True)


def _get_image_prefix(image_name: str) -> str:
    """
    Determines the correct prefix for an image based on its registry.
    
    This ensures consistent tag formatting across all registries (e.g., keeping
    the full registry path for GCR/Quay, but simplifying for Docker Hub).

    Args:
        image_name (str): The raw image name.

    Returns:
        str: The formatted prefix (e.g., 'node:', 'gcr.io/my-project/my-image:').
    """
    # For registries with explicit domains, keep the full image name
    if any(registry in image_name for registry in ["gcr.io", "quay.io", "ghcr.io", ".dkr.ecr.", "azurecr.io"]):
        return f"{image_name}:"
    
    # For Docker Hub, normalize the name
    # Remove 'library/' prefix for official images to keep it clean and standard
    clean_name = image_name.replace("docker.io/", "").replace("library/", "")
    return f"{clean_name}:"
