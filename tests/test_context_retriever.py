"""
Tests for the Context Retriever module.

These tests verify that the context retriever correctly:
- Retrieves must-have files
- Generates AST summaries
- Combines multiple retrieval strategies
- Respects token limits
"""

import pytest
from unittest.mock import Mock, MagicMock

from dockai.utils.context_retriever import ContextRetriever, RetrievedContext
from dockai.utils.indexer import ProjectIndex, FileChunk
from dockai.utils.code_intelligence import FileAnalysis


class TestRetrievedContext:
    """Tests for RetrievedContext dataclass."""
    
    def test_basic_creation(self):
        """Test basic context creation."""
        ctx = RetrievedContext(
            content="def main(): pass",
            source="app.py",
            relevance_score=0.9,
            context_type="entry_point"
        )
        
        assert ctx.source == "app.py"
        assert ctx.relevance_score == 0.9
        assert ctx.context_type == "entry_point"


class TestContextRetriever:
    """Tests for ContextRetriever class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.index = ProjectIndex(use_embeddings=False)
        self.retriever = ContextRetriever(self.index)
    
    def test_format_chunk_full(self):
        """Test formatting of full file chunks."""
        chunk = FileChunk(
            file_path="app.py",
            content="def main(): pass",
            start_line=1,
            end_line=1,
            chunk_type="full"
        )
        
        formatted = self.retriever._format_chunk(chunk)
        
        assert "--- FILE: app.py ---" in formatted
        assert "def main(): pass" in formatted
    
    def test_format_chunk_partial(self):
        """Test formatting of partial chunks."""
        chunk = FileChunk(
            file_path="large.py",
            content="some code",
            start_line=100,
            end_line=200,
            chunk_type="chunk"
        )
        
        formatted = self.retriever._format_chunk(chunk)
        
        assert "lines 100-200" in formatted
        assert "large.py" in formatted
    
    def test_generate_ast_summary_empty(self):
        """Test AST summary with no analysis."""
        summary = self.retriever._generate_ast_summary()
        
        assert summary == ""
    
    def test_generate_ast_summary_with_data(self):
        """Test AST summary with analysis data."""
        self.index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:main()"],
                env_vars=["PORT", "DEBUG"],
                exposed_ports=[8000],
                framework_hints=["FastAPI"]
            )
        }
        
        summary = self.retriever._generate_ast_summary()
        
        assert "CODE INTELLIGENCE SUMMARY" in summary
        assert "Entry Points" in summary
        assert "app.py:main()" in summary
        assert "Environment Variables" in summary
        assert "PORT" in summary
        assert "Ports Detected" in summary
        assert "8000" in summary
        assert "Frameworks Detected" in summary
        assert "FastAPI" in summary
    
    def test_must_have_files_included(self):
        """Test that must-have files are always included."""
        # Add various file types
        self.index.chunks = [
            FileChunk("package.json", '{"name": "test"}', 1, 1, "full", metadata={}),
            FileChunk("random.py", "code", 1, 1, "full", metadata={}),
            FileChunk("requirements.txt", "flask==2.0", 1, 1, "full", metadata={}),
        ]
        
        context = self.retriever.get_dockerfile_context(max_tokens=10000)
        
        # Must-have files should be included
        assert "package.json" in context
        assert "requirements.txt" in context
    
    def test_token_limit_respected(self):
        """Test that context respects token limits."""
        # Create large chunks
        large_content = "x" * 10000  # 10000 chars ≈ 2500 tokens
        self.index.chunks = [
            FileChunk(f"file{i}.py", large_content, 1, 100, "full", metadata={})
            for i in range(10)
        ]
        
        # Set a small token limit
        context = self.retriever.get_dockerfile_context(max_tokens=5000)  # ~20000 chars
        
        # Context should be truncated
        assert len(context) < 100000  # Much less than total content
    
    def test_get_entry_point_code(self):
        """Test entry point code extraction."""
        self.index.chunks = [
            FileChunk("app.py", "def main():\n    print('Hello')", 1, 2, "full", metadata={}),
            FileChunk("utils.py", "def helper(): pass", 1, 1, "full", metadata={}),
        ]
        self.index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:main()"]
            )
        }
        
        entry_code = self.retriever._get_entry_point_code()
        
        assert len(entry_code) == 1
        assert entry_code[0]["source"] == "app.py"
        assert "ENTRY POINT FILE" in entry_code[0]["content"]
    
    def test_get_quick_summary(self):
        """Test quick summary generation."""
        self.index.chunks = [FileChunk("a.py", "code", 1, 1, "full", metadata={})] * 3
        self.index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:main()"],
                env_vars=["PORT"],
                exposed_ports=[8000],
                framework_hints=["Flask"]
            )
        }
        
        summary = self.retriever.get_quick_summary()
        
        assert summary["files_indexed"] == 3
        assert summary["files_analyzed"] == 1
        assert "app.py:main()" in summary["entry_points"]
        assert "PORT" in summary["env_vars"]
        assert 8000 in summary["ports"]
        assert "Flask" in summary["frameworks"]
    
    def test_dockerfile_context_integration(self):
        """Test full dockerfile context retrieval."""
        # Setup a realistic project structure
        self.index.chunks = [
            FileChunk("Dockerfile", "FROM python:3.9\nCMD python app.py", 1, 2, "full", metadata={"is_dockerfile": True}),
            FileChunk("requirements.txt", "flask==2.0\ngunicorn==20.0", 1, 2, "full", metadata={"is_dependency": True}),
            FileChunk("app.py", "from flask import Flask\napp = Flask(__name__)", 1, 2, "full", metadata={}),
        ]
        self.index.code_analysis = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:__main__"],
                framework_hints=["Flask"]
            )
        }
        
        context = self.retriever.get_dockerfile_context(max_tokens=10000)
        
        # Should include all relevant content
        assert "requirements.txt" in context
        assert "flask" in context.lower()
    
    def test_semantic_search_integration(self):
        """Test that semantic search results are included."""
        self.index.chunks = [
            FileChunk("app.py", "def main(): pass", 1, 1, "full", metadata={}),
            FileChunk("server.py", "def start_server(): listen(8080)", 1, 1, "full", metadata={}),
        ]
        
        # Mock the search method to return predictable results
        original_search = self.index.search
        self.index.search = Mock(return_value=[self.index.chunks[1]])
        
        context = self.retriever.get_dockerfile_context(max_tokens=10000)
        
        # Restore
        self.index.search = original_search
        
        # Should include search results
        assert "server.py" in context


class TestContextRetrieverEdgeCases:
    """Edge case tests for ContextRetriever."""
    
    def test_empty_index(self):
        """Test with completely empty index."""
        index = ProjectIndex(use_embeddings=False)
        retriever = ContextRetriever(index)
        
        context = retriever.get_dockerfile_context()
        
        # Should not crash, return empty or minimal context
        assert isinstance(context, str)
    
    def test_very_small_token_limit(self):
        """Test with extremely small token limit."""
        index = ProjectIndex(use_embeddings=False)
        index.chunks = [
            FileChunk("large.py", "x" * 10000, 1, 100, "full", metadata={})
        ]
        retriever = ContextRetriever(index)
        
        context = retriever.get_dockerfile_context(max_tokens=100)  # ~400 chars
        
        # Should truncate appropriately
        assert len(context) <= 1000  # Some buffer for formatting
    
    def test_duplicate_file_handling(self):
        """Test that duplicate files are not included twice."""
        index = ProjectIndex(use_embeddings=False)
        # Same file appearing in multiple queries
        index.chunks = [
            FileChunk("package.json", '{"name": "test"}', 1, 1, "full", metadata={}),
        ]
        index.search = Mock(return_value=[index.chunks[0]])  # Would return same file
        
        retriever = ContextRetriever(index)
        context = retriever.get_dockerfile_context()
        
        # package.json should appear only once
        count = context.count("--- FILE: package.json ---")
        assert count <= 1
