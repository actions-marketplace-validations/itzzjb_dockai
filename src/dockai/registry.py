import httpx
import logging
from typing import List

logger = logging.getLogger("dockai")

def get_docker_tags(image_name: str, limit: int = 5) -> List[str]:
    """
    Fetches valid tags for a given Docker image from Docker Hub, GCR, or Quay.io.
    Prioritizes 'alpine' and 'slim' tags for optimization.
    """
    tags = []
    
    try:
        # 1. GCR (Google Container Registry)
        if "gcr.io" in image_name:
            # Format: gcr.io/project/image
            # API: https://gcr.io/v2/project/image/tags/list
            repo_path = image_name.split("/", 1)[1]
            domain = image_name.split("/")[0] # gcr.io, us.gcr.io, etc.
            url = f"https://{domain}/v2/{repo_path}/tags/list"
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                tags = response.json().get("tags", [])

        # 2. Quay.io
        elif "quay.io" in image_name:
            # Format: quay.io/namespace/image
            # API: https://quay.io/api/v1/repository/namespace/image/tag
            repo_path = image_name.split("/", 1)[1]
            url = f"https://quay.io/api/v1/repository/{repo_path}/tag"
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json().get("tags", [])
                tags = [t["name"] for t in data]

        # 3. Docker Hub (Default)
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

        # Filter out 'latest', 'stable', etc. to find version numbers
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
            # Ensure we keep the registry prefix if it existed
            prefix = ""
            if "gcr.io" in image_name or "quay.io" in image_name:
                prefix = f"{image_name}:"
            else:
                # For Docker Hub, we standardized on library/image, but we want to return just image:tag or library/image:tag
                # Let's return exactly what was passed or the standard form
                prefix = f"{image_name.replace('library/', '')}:"

            return [f"{prefix}{t}" for t in sorted_tags]
        
        # Fallback: If no version detected, use the mix strategy
        # Categorize tags
        alpine_tags = [t for t in tags if "alpine" in t]
        slim_tags = [t for t in tags if "slim" in t]
        standard_tags = [t for t in tags if "alpine" not in t and "slim" not in t and "window" not in t]
        
        # Select a mix: 2 Alpine, 2 Slim, 1 Standard
        selected_tags = []
        selected_tags.extend(alpine_tags[:2])
        selected_tags.extend(slim_tags[:2])
        selected_tags.extend(standard_tags[:1])
        
        # Prefix handling for return
        prefix = ""
        if "gcr.io" in image_name or "quay.io" in image_name:
            prefix = f"{image_name}:"
        else:
            prefix = f"{image_name.replace('library/', '')}:"

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
