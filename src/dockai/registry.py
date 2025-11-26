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


@handle_registry_rate_limit
def get_docker_tags(image_name: str, limit: int = 5) -> List[str]:
    """
    Fetches valid tags for a given Docker image from supported registries.
    
    This function queries the registry API to get a list of available tags for
    the specified image. It prioritizes 'alpine' and 'slim' tags to encourage
    smaller, more secure images.
    
    Supported Registries:
    - Docker Hub (default)
    - Google Container Registry (gcr.io)
    - Quay.io
    - AWS ECR (limited support, skips verification to avoid auth dependency)

    Args:
        image_name (str): The name of the image (e.g., 'node', 'gcr.io/my-project/my-image').
        limit (int, optional): The maximum number of fallback tags to return if smart filtering fails. Defaults to 5.

    Returns:
        List[str]: A list of verified, full image tags (e.g., ['node:20-alpine', 'node:20-slim']).
    """
    tags = []
    
    try:
        # 1. AWS ECR (Elastic Container Registry)
        if ".dkr.ecr." in image_name and ".amazonaws.com" in image_name:
            # Format: <account-id>.dkr.ecr.<region>.amazonaws.com/<repository>
            # ECR requires AWS CLI or boto3 authentication, which we don't want as a hard dependency.
            # For now, we'll skip tag fetching for ECR and let the AI use its knowledge/suggestions as-is.
            logger.info(f"ECR image detected: {image_name}. Skipping tag verification (requires AWS credentials).")
            return []  # AI will use suggested_base_image as-is

        # 2. GCR (Google Container Registry)
        elif "gcr.io" in image_name:
            # Format: gcr.io/project/image
            # API: https://gcr.io/v2/project/image/tags/list
            repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
            domain = image_name.split("/")[0]  # gcr.io, us.gcr.io, etc.
            url = f"https://{domain}/v2/{repo_path}/tags/list"
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                tags = response.json().get("tags", [])

        # 3. Quay.io
        elif "quay.io" in image_name:
            # Format: quay.io/namespace/image
            # API: https://quay.io/api/v1/repository/namespace/image/tag
            repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
            url = f"https://quay.io/api/v1/repository/{repo_path}/tag"
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json().get("tags", [])
                tags = [t["name"] for t in data]

        # 4. Docker Hub (Default)
        else:
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
                tags = [r["name"] for r in results]

        if not tags:
            return []

        # Filter out 'latest', 'stable', etc. to find specific version numbers
        # This helps in pinning versions for reproducibility
        version_tags = [t for t in tags if t not in ["latest", "stable", "edge", "nightly"]]
        
        # Try to extract the major version from the first valid tag
        # Docker Hub usually sorts by last_updated, so the first few tags are likely the newest versions
        # But to be safe, let's look at the top 20 tags and find the highest version number
        
        latest_version = None
        for tag in version_tags[:20]:
            # Simple heuristic: look for the first number in the tag
            # e.g. "20-alpine" -> "20", "3.11-slim" -> "3.11"
            parts = tag.split('-')[0].split('.')
            if parts[0].isdigit():
                current_version = parts[0]
                # If we haven't found a version yet, or this one is higher (lexicographically for now)
                if latest_version is None or (current_version.isdigit() and latest_version.isdigit() and int(current_version) > int(latest_version)):
                    latest_version = current_version
        
        # Determine prefix based on registry type for correct image formatting
        prefix = _get_image_prefix(image_name)
        
        # If we found a version, filter tags to only include that version
        if latest_version:
            logger.info(f"Detected latest version for {image_name}: {latest_version}")
            # Return ALL tags for this version, sorted to put alpine/slim first
            version_specific_tags = [t for t in tags if t.startswith(latest_version)]
            
            # Sort: Alpine first, then Slim, then others
            def sort_key(tag):
                if "alpine" in tag: return 0
                if "slim" in tag: return 1
                return 2
                
            sorted_tags = sorted(version_specific_tags, key=sort_key)
            return [f"{prefix}{t}" for t in sorted_tags]
        
        # Fallback: If no version detected, use the mix strategy
        # Categorize tags to provide a good variety to the AI
        alpine_tags = [t for t in tags if "alpine" in t]
        slim_tags = [t for t in tags if "slim" in t]
        standard_tags = [t for t in tags if "alpine" not in t and "slim" not in t and "window" not in t]
        
        # Select a mix: 2 Alpine, 2 Slim, 1 Standard
        selected_tags = []
        selected_tags.extend(alpine_tags[:2])
        selected_tags.extend(slim_tags[:2])
        selected_tags.extend(standard_tags[:1])
        
        # If we have selected tags, return them
        if len(selected_tags) >= 3:
            # Remove duplicates and format
            unique_tags = sorted(list(set(selected_tags)), reverse=True)
            return [f"{prefix}{t}" for t in unique_tags]
            
        # Fallback: If we didn't find enough categorized tags, just return the top N tags
        return [f"{prefix}{t}" for t in tags[:limit]]
        
    except Exception as e:
        logger.warning(f"Failed to fetch tags for {image_name}: {e}")
        return []


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
    if any(registry in image_name for registry in ["gcr.io", "quay.io", ".dkr.ecr.", "azurecr.io"]):
        return f"{image_name}:"
    
    # For Docker Hub, normalize the name
    # Remove 'library/' prefix for official images to keep it clean and standard
    clean_name = image_name.replace("docker.io/", "").replace("library/", "")
    return f"{clean_name}:"
