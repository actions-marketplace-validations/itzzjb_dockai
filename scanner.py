import os
from typing import List, Set

# Default directories to ignore to reduce noise
# Default directories to ignore to prevent context explosion
# We only ignore the massive/system folders that would crash the LLM context window.
# Everything else (dist, build, .idea, etc.) is passed to the AI to decide.
DEFAULT_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    "__MACOSX",
    "coverage"
}

def load_ignore_file(root_path: str, filename: str) -> Set[str]:
    """
    Reads a specific ignore file (like .gitignore or .dockerignore) in the root_path 
    if it exists and returns a set of patterns.
    """
    file_path = os.path.join(root_path, filename)
    patterns = set()
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Basic handling: remove trailing slashes for directory matching
                        patterns.add(line.rstrip("/"))
        except Exception:
            pass 
            
    return patterns

def get_file_tree(root_path: str) -> List[str]:
    """
    Scans the directory tree rooted at root_path and returns a list of relative file paths.
    Ignores directories specified in DEFAULT_IGNORE_DIRS, .gitignore, and .dockerignore.
    """
    # Start with defaults
    ignore_dirs = DEFAULT_IGNORE_DIRS.copy()
    
    # Add patterns from .gitignore and .dockerignore
    ignore_dirs.update(load_ignore_file(root_path, ".gitignore"))
    ignore_dirs.update(load_ignore_file(root_path, ".dockerignore"))
    
    file_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Modify dirnames in-place to skip ignored directories
        # We check if the directory name is in our ignore list
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        
        for filename in filenames:
            # Create absolute path
            abs_path = os.path.join(dirpath, filename)
            # Convert to relative path from root_path
            rel_path = os.path.relpath(abs_path, root_path)
            file_list.append(rel_path)
            
    return file_list
