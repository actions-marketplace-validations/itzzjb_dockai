import os
from typing import List

def get_file_tree(root_path: str) -> List[str]:
    """
    Scans the directory tree rooted at root_path and returns a list of relative file paths.
    Ignores specific directories like .git, node_modules, etc.
    """
    ignore_dirs = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        "target",
        ".idea",
        ".vscode"
    }
    
    file_list = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Modify dirnames in-place to skip ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        
        for filename in filenames:
            # Create absolute path
            abs_path = os.path.join(dirpath, filename)
            # Convert to relative path from root_path
            rel_path = os.path.relpath(abs_path, root_path)
            file_list.append(rel_path)
            
    return file_list
