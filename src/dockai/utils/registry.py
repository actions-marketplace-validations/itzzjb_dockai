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
        List[str]: A list of verified, full image tags. Empty list if verification fails
                   (the generator will proceed with unverified tags).
    """
    tags = []
    
    try:
        # Dispatch to appropriate registry handler
        if ".dkr.ecr." in image_name and ".amazonaws.com" in image_name:
            logger.info(f"ECR image detected: {image_name}. Skipping tag verification (requires AWS credentials).")
            return []
            
        elif "gcr.io" in image_name:
            logger.debug(f"Fetching tags from GCR for: {image_name}")
            tags = _fetch_gcr_tags(image_name)
            
        elif "quay.io" in image_name:
            logger.debug(f"Fetching tags from Quay for: {image_name}")
            tags = _fetch_quay_tags(image_name)
            
        elif "ghcr.io" in image_name:
            logger.debug(f"Fetching tags from GHCR for: {image_name}")
            tags = _fetch_ghcr_tags(image_name)
            
        else:
            logger.debug(f"Fetching tags from Docker Hub for: {image_name}")
            tags = _fetch_docker_hub_tags(image_name)

        if not tags:
            logger.debug(f"No tags found for {image_name} - will use AI-suggested tags without verification")
            return []

        # Filter and sort tags
        processed = _process_tags(image_name, tags, limit)
        if processed:
            logger.debug(f"Found {len(processed)} verified tags for {image_name}")
        return processed
        
    except Exception as e:
        logger.warning(f"Failed to fetch tags for {image_name}: {e}")
        return []


def _fetch_docker_hub_tags(image_name: str) -> List[str]:
    """
    Fetch tags from Docker Hub using both v2 Registry API and Hub API.
    
    Docker Hub has two APIs:
    1. Registry API (registry-1.docker.io) - OCI standard, requires token
    2. Hub API (hub.docker.com) - Docker's proprietary API
    
    We try the Hub API first (simpler), then fall back to Registry API if needed.
    """
    # Handle official images (e.g., 'node' -> 'library/node')
    hub_image_name = image_name
    if "/" not in hub_image_name:
        hub_image_name = f"library/{hub_image_name}"
    elif hub_image_name.startswith("docker.io/"):
        hub_image_name = hub_image_name.replace("docker.io/", "")
    
    # Try Docker Hub API first (easier, no auth needed for public images)
    tags = _fetch_docker_hub_api(hub_image_name)
    if tags:
        return tags
    
    # Fallback to Registry v2 API with token auth
    logger.debug(f"Hub API failed for {hub_image_name}, trying Registry API...")
    return _fetch_docker_registry_v2_tags(hub_image_name)


def _fetch_docker_hub_api(hub_image_name: str) -> List[str]:
    """Fetch tags using Docker Hub's proprietary API."""
    url = f"https://hub.docker.com/v2/repositories/{hub_image_name}/tags"
    
    try:
        response = httpx.get(url, params={"page_size": 100}, timeout=10.0)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [r["name"] for r in results]
        elif response.status_code == 404:
            logger.debug(f"Docker Hub: Image '{hub_image_name}' not found (404)")
        elif response.status_code == 429:
            logger.warning(f"Docker Hub: Rate limited (429)")
        else:
            logger.debug(f"Docker Hub API returned {response.status_code} for {hub_image_name}")
    except httpx.TimeoutException:
        logger.debug(f"Docker Hub API timeout for {hub_image_name}")
    except Exception as e:
        logger.debug(f"Docker Hub API error for {hub_image_name}: {e}")
    
    return []


def _fetch_docker_registry_v2_tags(image_name: str) -> List[str]:
    """
    Fetch tags using Docker Registry v2 API with anonymous token.
    
    This is the OCI-standard way to access Docker Hub programmatically.
    Requires getting an anonymous token first.
    """
    try:
        # Step 1: Get anonymous auth token
        token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image_name}:pull"
        token_response = httpx.get(token_url, timeout=10.0)
        
        if token_response.status_code != 200:
            logger.debug(f"Failed to get Docker token: {token_response.status_code}")
            return []
        
        token = token_response.json().get("token")
        if not token:
            logger.debug("No token in Docker auth response")
            return []
        
        # Step 2: Fetch tags with the token
        tags_url = f"https://registry-1.docker.io/v2/{image_name}/tags/list"
        headers = {"Authorization": f"Bearer {token}"}
        tags_response = httpx.get(tags_url, headers=headers, timeout=10.0)
        
        if tags_response.status_code == 200:
            return tags_response.json().get("tags", [])
        elif tags_response.status_code == 404:
            logger.debug(f"Registry v2: Image '{image_name}' not found (404)")
        else:
            logger.debug(f"Registry v2 API returned {tags_response.status_code} for {image_name}")
            
    except httpx.TimeoutException:
        logger.debug(f"Registry v2 API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"Registry v2 API error for {image_name}: {e}")
    
    return []


def _fetch_gcr_tags(image_name: str) -> List[str]:
    """Fetch tags from Google Container Registry."""
    # Format: gcr.io/project/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    domain = image_name.split("/")[0]
    url = f"https://{domain}/v2/{repo_path}/tags/list"
    
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json().get("tags", [])
        elif response.status_code == 404:
            logger.debug(f"GCR: Image '{image_name}' not found (404)")
        elif response.status_code == 401:
            logger.debug(f"GCR: Authentication required for '{image_name}' (401)")
        else:
            logger.debug(f"GCR API returned {response.status_code} for {image_name}")
    except httpx.TimeoutException:
        logger.debug(f"GCR API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"GCR API error for {image_name}: {e}")
    
    return []


def _fetch_quay_tags(image_name: str) -> List[str]:
    """Fetch tags from Quay.io."""
    # Format: quay.io/namespace/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    url = f"https://quay.io/api/v1/repository/{repo_path}/tag"
    
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            data = response.json().get("tags", [])
            return [t["name"] for t in data]
        elif response.status_code == 404:
            logger.debug(f"Quay: Image '{image_name}' not found (404)")
        elif response.status_code == 401:
            logger.debug(f"Quay: Authentication required for '{image_name}' (401)")
        else:
            logger.debug(f"Quay API returned {response.status_code} for {image_name}")
    except httpx.TimeoutException:
        logger.debug(f"Quay API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"Quay API error for {image_name}: {e}")
    
    return []


def _fetch_ghcr_tags(image_name: str) -> List[str]:
    """
    Fetch tags from GitHub Container Registry.
    
    GHCR requires authentication even for public images in most cases.
    We try anonymous access first, then attempt to get an anonymous token.
    """
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    
    # Try with anonymous token first (GHCR's OCI-compliant approach)
    try:
        # Get anonymous token
        token_url = f"https://ghcr.io/token?scope=repository:{repo_path}:pull"
        token_response = httpx.get(token_url, timeout=10.0)
        
        if token_response.status_code == 200:
            token = token_response.json().get("token")
            if token:
                # Fetch tags with token
                tags_url = f"https://ghcr.io/v2/{repo_path}/tags/list"
                headers = {"Authorization": f"Bearer {token}"}
                tags_response = httpx.get(tags_url, headers=headers, timeout=10.0)
                
                if tags_response.status_code == 200:
                    return tags_response.json().get("tags", [])
                elif tags_response.status_code == 404:
                    logger.debug(f"GHCR: Image '{image_name}' not found (404)")
                elif tags_response.status_code == 401:
                    logger.debug(f"GHCR: Authentication required for '{image_name}' - package may be private")
                else:
                    logger.debug(f"GHCR API returned {tags_response.status_code} for {image_name}")
        else:
            logger.debug(f"GHCR token request returned {token_response.status_code}")
            
    except httpx.TimeoutException:
        logger.debug(f"GHCR API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"GHCR API error for {image_name}: {e}")
    
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
