import os
from typing import List, Set

# Core directories to ignore to prevent context explosion.
# We explicitly ignore these system/heavy folders to ensure the LLM
# focuses only on source code and configuration files.
import pathspec

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

def load_ignore_spec(root_path: str, filename: str) -> pathspec.PathSpec:
    """
    Parses a .gitignore or .dockerignore file to create a PathSpec object.
    """
    file_path = os.path.join(root_path, filename)
    patterns = []
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                patterns = f.readlines()
        except Exception:
            pass 
            
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

def get_file_tree(root_path: str) -> List[str]:
    """
    Traverses the directory tree to build a flat list of relative file paths.
    
    This function applies a 'Filter & Select' strategy locally:
    1. It starts with a hardcoded list of noisy directories (DEFAULT_IGNORE_DIRS).
    2. It augments this with any .gitignore or .dockerignore patterns found in the root.
    3. It walks the tree, skipping any ignored directories to save processing time.
    """
    gitignore_spec = load_ignore_spec(root_path, ".gitignore")
    dockerignore_spec = load_ignore_spec(root_path, ".dockerignore")
    
    file_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter directories in-place
        # We first filter by default ignore dirs
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS]
        
        # Then we filter by gitignore/dockerignore specs
        # We need to check the relative path of the directory
        i = 0
        while i < len(dirnames):
            d = dirnames[i]
            abs_dir_path = os.path.join(dirpath, d)
            rel_dir_path = os.path.relpath(abs_dir_path, root_path)
            # Add a trailing slash to indicate it's a directory for pathspec
            if gitignore_spec.match_file(rel_dir_path + "/") or dockerignore_spec.match_file(rel_dir_path + "/"):
                dirnames.pop(i)
            else:
                i += 1
        
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, root_path)
            
            if gitignore_spec.match_file(rel_path) or dockerignore_spec.match_file(rel_path):
                continue
                
            file_list.append(rel_path)
            
    return file_list
