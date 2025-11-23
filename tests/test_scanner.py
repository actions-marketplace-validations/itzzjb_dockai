import os
import tempfile
import shutil
from dockai.scanner import get_file_tree

def test_get_file_tree_ignores_git():
    # Create a temp dir
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create .git dir
        os.makedirs(os.path.join(tmpdirname, ".git"))
        # Create a normal file
        with open(os.path.join(tmpdirname, "main.py"), "w") as f:
            f.write("print('hello')")
            
        files = get_file_tree(tmpdirname)
        assert "main.py" in files
        assert ".git" not in files

def test_get_file_tree_respects_gitignore():
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create .gitignore
        with open(os.path.join(tmpdirname, ".gitignore"), "w") as f:
            f.write("secret.txt\n")
            
        # Create secret file
        with open(os.path.join(tmpdirname, "secret.txt"), "w") as f:
            f.write("shh")
            
        # Create normal file
        with open(os.path.join(tmpdirname, "app.py"), "w") as f:
            f.write("print('app')")
            
        files = get_file_tree(tmpdirname)
        assert "app.py" in files
        assert "secret.txt" not in files
