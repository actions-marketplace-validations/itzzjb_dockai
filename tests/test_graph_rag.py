
import pytest
from unittest.mock import Mock, patch
from dockai.utils.indexer import ProjectIndex, FileChunk, FileAnalysis
from dockai.utils.context_retriever import ContextRetriever

class TestGraphRAG:
    """Tests for Graph-based RAG (Import Traversal) capabilities."""
    
    def setup_method(self):
        self.index = ProjectIndex(use_embeddings=False)
        self.retriever = ContextRetriever(self.index, {"stack": "Python"})

    def test_resolve_import_path_python_exact(self):
        """Test resolving exact Python file match."""
        project_files = {"app.py", "utils.py", "core/config.py"}
        
        # Simple import
        assert self.retriever._resolve_import_path("utils", project_files) == "utils.py"
        
        # Dotted import
        assert self.retriever._resolve_import_path("core.config", project_files) == "core/config.py"
        
        # Non-existent
        assert self.retriever._resolve_import_path("pandas", project_files) is None

    def test_resolve_import_path_python_init(self):
        """Test resolving Python package via __init__.py."""
        project_files = {"app.py", "core/__init__.py"}
        
        assert self.retriever._resolve_import_path("core", project_files) == "core/__init__.py"

    def test_resolve_import_path_js(self):
        """Test resolving JS imports."""
        project_files = {"index.js", "utils.js", "components/Button.ts"}
        
        # Standard JS
        assert self.retriever._resolve_import_path("utils", project_files) == "utils.js"
        
        # TS file
        assert self.retriever._resolve_import_path("components/Button", project_files) == "components/Button.ts"

    def test_get_imported_files_traversal(self):
        """Test that the retriever actually follows an import graph."""
        
        # Setup files: main.py imports utils
        self.index.chunks = [
            FileChunk("main.py", "import utils", 1, 1, "full"),
            FileChunk("utils.py", "def helper(): pass", 1, 1, "full"),
            FileChunk("ignored.py", "print('ignore me')", 1, 1, "full")
        ]
        
        # Setup analysis saying main.py is entry point and imports utils
        self.index.code_analysis = {
            "main.py": FileAnalysis(
                path="main.py", 
                language="python",
                entry_points=["main"],
                imports=["utils"]
            ),
            "utils.py": FileAnalysis(
                path="utils.py",
                language="python",
                imports=[]
            )
        }
        
        # Call the private method
        results = self.retriever._get_imported_files(seen_files=set())
        
        # Verification
        assert len(results) == 1
        assert results[0]["source"] == "utils.py"
        assert "def helper" in results[0]["content"]

    def test_get_imported_files_deduplication(self):
        """Test that already seen files are not returned."""
        self.index.chunks = [
            FileChunk("main.py", "import utils", 1, 1, "full"),
            FileChunk("utils.py", "code", 1, 1, "full")
        ]
        self.index.code_analysis = {
            "main.py": FileAnalysis("main.py", "python", imports=["utils"])
        }
        
        # utils.py is already seen
        seen = {"utils.py"}
        results = self.retriever._get_imported_files(seen_files=seen)
        
        # Should filter it out (note: the method itself returns candidates, 
        # filtering usually happens in main loop, but let's check the method behavior.
        # Looking at implementation: _get_imported_files CHECKS seen_files?
        # Yes: if resolved_path and resolved_path not in seen_files:
        assert len(results) == 0

    def test_integration_in_get_context(self):
        """Test that get_dockerfile_context includes imported files."""
        # Setup
        self.index.chunks = [
            FileChunk("main.py", "import settings", 1, 1, "full"),
            FileChunk("settings.py", "SECRET = 'xyz'", 1, 1, "full")
        ]
        self.index.code_analysis = {
            "main.py": FileAnalysis("main.py", "python", entry_points=["main"], imports=["settings"])
        }
        
        # Should find settings.py via graph traversal even if no query matches "settings"
        # provided we have semantic search disabled or non-matching queries.
        # But we want to confirm it appears in "Imported Files" section logic.
        
        context = self.retriever.get_dockerfile_context()
        
        assert "--- FILE: settings.py ---" in context
        assert "SECRET = 'xyz'" in context
