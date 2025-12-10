"""
Tests for the Project Indexer module.

These tests verify that the indexer correctly:
- Chunks files for embedding
- Builds the search index
- Performs semantic and keyword search
- Integrates with code intelligence
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from dockai.utils.indexer import ProjectIndex, FileChunk


class TestFileChunk:
    """Tests for FileChunk dataclass."""
    
    def test_basic_creation(self):
        """Test basic chunk creation."""
        chunk = FileChunk(
            file_path="app.py",
            content="def main(): pass",
            start_line=1,
            end_line=1,
            chunk_type="full"
        )
        
        assert chunk.file_path == "app.py"
        assert chunk.content == "def main(): pass"
        assert chunk.chunk_type == "full"
    
    def test_metadata(self):
        """Test chunk metadata."""
        chunk = FileChunk(
            file_path="package.json",
            content='{"name": "test"}',
            start_line=1,
            end_line=1,
            chunk_type="full",
            metadata={"is_dependency": True}
        )
        
        assert chunk.metadata["is_dependency"] is True


class TestProjectIndex:
    """Tests for ProjectIndex class."""
    
    def test_init_without_embeddings(self):
        """Test initialization without embeddings."""
        index = ProjectIndex(use_embeddings=False)
        
        assert index.use_embeddings is False
        assert index.embedder is None
        assert index.chunks == []
    

    def test_chunking_small_file(self):
        """Test that small files become single chunks."""
        index = ProjectIndex(use_embeddings=False)
        
        content = "line1\nline2\nline3"
        index._chunk_file("test.py", content, chunk_size=100, chunk_overlap=10)
        
        assert len(index.chunks) == 1
        assert index.chunks[0].chunk_type == "full"
        assert index.chunks[0].start_line == 1
        assert index.chunks[0].end_line == 3
    
    def test_chunking_large_file(self):
        """Test that large files are split into chunks."""
        index = ProjectIndex(use_embeddings=False)
        
        # Create a file with 500 lines
        lines = [f"line {i}" for i in range(500)]
        content = "\n".join(lines)
        
        index._chunk_file("large.py", content, chunk_size=100, chunk_overlap=20)
        
        # Should have multiple chunks
        assert len(index.chunks) > 1
        
        # All chunks should be of type "chunk" (not "full")
        for chunk in index.chunks:
            assert chunk.chunk_type == "chunk"
    
    def test_is_config_file(self):
        """Test config file detection."""
        index = ProjectIndex(use_embeddings=False)
        
        assert index._is_config_file("config.py") is True
        assert index._is_config_file("settings.json") is True
        assert index._is_config_file(".env.example") is True
        assert index._is_config_file("app.py") is False
    
    def test_is_dependency_file(self):
        """Test dependency file detection."""
        index = ProjectIndex(use_embeddings=False)
        
        assert index._is_dependency_file("package.json") is True
        assert index._is_dependency_file("requirements.txt") is True
        assert index._is_dependency_file("go.mod") is True
        assert index._is_dependency_file("app.py") is False
    
    def test_keyword_search(self):
        """Test keyword-based search."""
        index = ProjectIndex(use_embeddings=False)
        
        # Add some test chunks with metadata
        index.chunks = [
            FileChunk("app.py", "def start server application", 1, 1, "full", metadata={}),
            FileChunk("db.py", "def connect database postgres", 1, 1, "full", metadata={}),
            FileChunk("utils.py", "def helper utility function", 1, 1, "full", metadata={}),
        ]
        
        results = index._keyword_search("server application", top_k=2)
        
        # Should find at least one result
        assert len(results) >= 1
        assert len(results) <= 2
        # The app.py chunk should be most relevant (contains both "server" and "application")
        assert results[0].file_path == "app.py"
    
    def test_keyword_search_with_boost(self):
        """Test that dependency files get boosted in search."""
        index = ProjectIndex(use_embeddings=False)
        
        index.chunks = [
            FileChunk("app.py", "dependencies list", 1, 1, "full", metadata={"is_dependency": False}),
            FileChunk("package.json", "dependencies list", 1, 1, "full", metadata={"is_dependency": True}),
        ]
        
        results = index._keyword_search("dependencies", top_k=2)
        
        # package.json should be boosted
        assert results[0].file_path == "package.json"
    
    def test_index_project_with_temp_files(self):
        """Test indexing a project with temporary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            app_py = os.path.join(tmpdir, "app.py")
            with open(app_py, "w") as f:
                f.write("def main():\n    print('Hello')\n")
            
            pkg_json = os.path.join(tmpdir, "package.json")
            with open(pkg_json, "w") as f:
                f.write('{"name": "test", "version": "1.0.0"}')
            
            index = ProjectIndex(use_embeddings=False)
            index.index_project(tmpdir, ["app.py", "package.json"])
            
            assert len(index.chunks) == 2
            assert len(index.code_analysis) == 2  # Python AND package.json now analyzed
    
    def test_get_entry_points(self):
        """Test entry point extraction."""
        index = ProjectIndex(use_embeddings=False)
        
        # Mock code analysis with entry points
        from dockai.utils.code_intelligence import FileAnalysis
        index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:main()"]
            ),
            "server.py": FileAnalysis(
                path="server.py",
                language="python",
                entry_points=["server.py:__main__"]
            ),
        }
        
        entry_points = index.get_entry_points()
        
        assert "app.py:main()" in entry_points
        assert "server.py:__main__" in entry_points
    
    def test_get_all_env_vars(self):
        """Test environment variable aggregation."""
        index = ProjectIndex(use_embeddings=False)
        
        from dockai.utils.code_intelligence import FileAnalysis
        index.code_analysis = {
            "config.py": FileAnalysis(
                path="config.py",
                language="python",
                env_vars=["DATABASE_URL", "PORT"]
            ),
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                env_vars=["PORT", "DEBUG"]
            ),
        }
        
        env_vars = index.get_all_env_vars()
        
        assert "DATABASE_URL" in env_vars
        assert "PORT" in env_vars
        assert "DEBUG" in env_vars
    
    def test_get_all_ports(self):
        """Test port aggregation."""
        index = ProjectIndex(use_embeddings=False)
        
        from dockai.utils.code_intelligence import FileAnalysis
        index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                exposed_ports=[8000]
            ),
            "server.py": FileAnalysis(
                path="server.py",
                language="python",
                exposed_ports=[3000, 8000]  # Duplicate 8000
            ),
        }
        
        ports = index.get_all_ports()
        
        assert 8000 in ports
        assert 3000 in ports
        # Should be deduplicated
        assert len(ports) == 2
    
    def test_get_frameworks(self):
        """Test framework aggregation."""
        index = ProjectIndex(use_embeddings=False)
        
        from dockai.utils.code_intelligence import FileAnalysis
        index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                framework_hints=["FastAPI", "SQLAlchemy"]
            ),
            "server.py": FileAnalysis(
                path="server.py",
                language="python",
                framework_hints=["FastAPI"]  # Duplicate
            ),
        }
        
        frameworks = index.get_frameworks()
        
        assert "FastAPI" in frameworks
        assert "SQLAlchemy" in frameworks
    
    def test_get_stats(self):
        """Test stats generation."""
        index = ProjectIndex(use_embeddings=False)
        
        index.chunks = [FileChunk("a.py", "code", 1, 1, "full", metadata={})] * 5
        
        # Create a proper mock with the required attributes
        from dockai.utils.code_intelligence import FileAnalysis
        index.code_analysis = {
            "a.py": FileAnalysis(
                path="a.py",
                language="python",
                entry_points=[],
                env_vars=[],
                exposed_ports=[],
                framework_hints=[]
            )
        }
        
        stats = index.get_stats()
        
        assert stats["total_chunks"] == 5
        assert stats["total_files_analyzed"] == 1
        assert stats["embeddings_available"] is False
    
    def test_search_empty_index(self):
        """Test search on empty index."""
        index = ProjectIndex(use_embeddings=False)
        
        results = index.search("anything")
        
        assert results == []


class TestProjectIndexWithEmbeddings:
    """Tests for ProjectIndex with embeddings (mocked)."""
    
    def test_semantic_search_with_numpy(self):
        """Test semantic search with in-memory numpy embeddings."""
        import numpy as np
        
        index = ProjectIndex(use_embeddings=False)  # Init without embedder
        index.use_embeddings = True
        
        # Manually setup embedder and embeddings
        index.embedder = Mock()
        
        # Create test chunks  
        index.chunks = [
            FileChunk("app.py", "start server application", 1, 10, "full", {}),
            FileChunk("db.py", "database connection", 1, 20, "full", {})
        ]
        
        # Mock chunk embeddings (2 chunks, 3D embeddings, normalized)
        index.chunk_embeddings = np.array([
            [0.6, 0.0, 0.8],  # app.py
            [0.0, 1.0, 0.0]   # db.py
        ])
        
        # Mock query embedding (normalized)
        query_embedding = np.array([[0.6, 0.0, 0.8]])  # Similar to app.py
        mock_result = MagicMock()
        mock_result.__getitem__ = lambda self, idx: query_embedding
        index.embedder.encode = Mock(return_value=query_embedding)
        
        results = index._semantic_search("start server", top_k=2)
        
        # Should return chunks sorted by similarity
        assert len(results) >= 1
        # app.py should be most similar
        assert results[0].file_path == "app.py"
