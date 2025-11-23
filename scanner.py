import os
from typing import List, Set

# Core directories to ignore to prevent context explosion.
# We explicitly ignore these system/heavy folders to ensure the LLM
# focuses only on source code and configuration files.
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
    Parses a .gitignore or .dockerignore file to extract user-defined ignore patterns.
    Returns a set of directory names to exclude from the scan.
    """
    file_path = os.path.join(root_path, filename)
    patterns = set()
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith("#"):
                        # Normalize by removing trailing slashes for directory matching
                        patterns.add(line.rstrip("/"))
        except Exception:
            pass 
            
    return patterns

def get_file_tree(root_path: str) -> List[str]:
    """
    Traverses the directory tree to build a flat list of relative file paths.
    
    This function applies a 'Filter & Select' strategy locally:
    1. It starts with a hardcoded list of noisy directories (DEFAULT_IGNORE_DIRS).
    2. It augments this with any .gitignore or .dockerignore patterns found in the root.
    3. It walks the tree, skipping any ignored directories to save processing time.
    """
    ignore_dirs = DEFAULT_IGNORE_DIRS.copy()
    
    ignore_dirs.update(load_ignore_file(root_path, ".gitignore"))
    ignore_dirs.update(load_ignore_file(root_path, ".dockerignore"))
    
    file_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # In-place modification of dirnames is required to prevent os.walk from
        # traversing into ignored directories (performance optimization).
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, root_path)
            file_list.append(rel_path)
            
    return file_list
