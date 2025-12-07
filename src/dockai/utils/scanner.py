"""
DockAI File Scanner Module.

This module is responsible for traversing the user's project directory and building
a list of relevant files for analysis. It implements intelligent filtering to
ignore build artifacts, dependency directories (like node_modules, venv), and
version control files. This ensures the AI context window is not flooded with
irrelevant data, focusing only on source code and configuration files.
"""

import os
from typing import List, Set
import pathspec

# Core directories to ignore to prevent context explosion.
# We explicitly ignore these common build/cache/system folders across various
# technology stacks to ensure the AI focuses only on source code and configuration files.
# This list is technology-agnostic and covers common patterns.
DEFAULT_IGNORE_DIRS = {
    # Version control
    ".git",
    ".svn",
    ".hg",
    # Package manager directories (various ecosystems)
    "node_modules",
    "vendor",
    "packages",
    # Python virtual environments and caches
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "eggs",
    ".eggs",
    # Build output directories (various ecosystems)
    "dist",
    "build",
    "out",
    "target",
    "bin",
    "obj",
    "_build",
    # IDE and editor directories
    ".idea",
    ".vscode",
    ".vs",
    ".eclipse",
    # OS-specific
    "__MACOSX",
    ".DS_Store",
    # Test and coverage
    "coverage",
    ".coverage",
    "htmlcov",
    ".nyc_output",
    # Misc caches and generated
    ".cache",
    ".tmp",
    "tmp",
    ".gradle",
    ".cargo"
}


def load_ignore_spec(root_path: str, filename: str) -> pathspec.PathSpec:
    """
    Parses a .gitignore or .dockerignore file to create a PathSpec object.
    
    This allows the scanner to respect the user's existing ignore configurations,
    ensuring we don't scan files they have explicitly excluded.
    
    Args:
        root_path (str): The root directory of the repository.
        filename (str): The name of the ignore file (e.g., ".gitignore").
        
    Returns:
        pathspec.PathSpec: A PathSpec object used for matching file paths against the ignore patterns.
    """
    file_path = os.path.join(root_path, filename)
    patterns = []
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                patterns = f.readlines()
        except Exception:
            # Fail silently if we can't read the file, treating it as empty
            pass 
            
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def get_file_tree(root_path: str) -> List[str]:
    """
    Traverses the directory tree to build a flat list of relative file paths.
    
    This function applies a 'Filter & Select' strategy locally:
    1. It starts with a hardcoded list of noisy directories (DEFAULT_IGNORE_DIRS).
    2. It augments this with any .gitignore or .dockerignore patterns found in the root.
    3. It walks the tree, skipping any ignored directories to save processing time.
    
    This efficient scanning is crucial for performance on large repositories.
    
    Args:
        root_path (str): The root directory to scan.
        
    Returns:
        List[str]: A list of relative file paths that should be analyzed.
        
    Raises:
        PermissionError: If the directory cannot be accessed due to permissions.
    """
    import logging
    logger = logging.getLogger("dockai")
    
    # Validate root_path
    if not root_path:
        logger.error("Empty root_path provided to get_file_tree")
        return []
    
    if not os.path.exists(root_path):
        logger.error(f"Directory does not exist: {root_path}")
        raise FileNotFoundError(f"Directory not found: {root_path}")
    
    if not os.path.isdir(root_path):
        logger.error(f"Path is not a directory: {root_path}")
        raise NotADirectoryError(f"Not a directory: {root_path}")
    
    # Load ignore patterns from standard files
    gitignore_spec = load_ignore_spec(root_path, ".gitignore")
    dockerignore_spec = load_ignore_spec(root_path, ".dockerignore")
    
    file_list = []
    skipped_dirs = 0
    permission_errors = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Filter directories in-place to prevent os.walk from descending into them
            
            # 1. Filter by default ignore dirs (fastest check)
            original_count = len(dirnames)
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS]
            skipped_dirs += original_count - len(dirnames)
            
            # 2. Filter by gitignore/dockerignore specs (more complex check)
            # We need to check the relative path of the directory
            i = 0
            while i < len(dirnames):
                d = dirnames[i]
                abs_dir_path = os.path.join(dirpath, d)
                
                # Check if directory is accessible
                try:
                    os.access(abs_dir_path, os.R_OK)
                except OSError:
                    logger.warning(f"Cannot access directory (skipping): {abs_dir_path}")
                    dirnames.pop(i)
                    permission_errors += 1
                    continue
                
                rel_dir_path = os.path.relpath(abs_dir_path, root_path)
                
                # Add a trailing slash to indicate it's a directory for pathspec matching
                # This ensures patterns like "build/" match correctly
                if gitignore_spec.match_file(rel_dir_path + "/") or dockerignore_spec.match_file(rel_dir_path + "/"):
                    dirnames.pop(i)
                    skipped_dirs += 1
                else:
                    i += 1
            
            # Process files in the current directory
            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root_path)
                
                # Check if the file matches any ignore patterns
                if gitignore_spec.match_file(rel_path) or dockerignore_spec.match_file(rel_path):
                    continue
                
                # Check if file is readable
                if not os.access(abs_path, os.R_OK):
                    logger.debug(f"Skipping unreadable file: {rel_path}")
                    continue
                    
                file_list.append(rel_path)
    
    except PermissionError as e:
        logger.error(f"Permission denied while scanning directory: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error scanning directory: {e}")
        raise
    
    # Log summary for debugging
    if skipped_dirs > 0:
        logger.debug(f"Skipped {skipped_dirs} directories (ignored or inaccessible)")
    if permission_errors > 0:
        logger.warning(f"Encountered {permission_errors} permission errors while scanning")
    
    return file_list
