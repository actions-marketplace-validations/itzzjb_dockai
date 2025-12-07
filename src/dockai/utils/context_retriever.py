"""
DockAI Context Retriever Module.

This module combines AST analysis and semantic search to retrieve
the most relevant context for Dockerfile generation. It acts as
the intelligence layer between the project index and the LLM.

Key Features:
- Combines multiple retrieval strategies (AST, semantic, pattern matching)
- Deduplicates and ranks retrieved content
- Generates structured summaries from code analysis
- Respects token limits with smart truncation

Architecture:
    Query → [AST Lookup] + [Semantic Search] + [Pattern Match] → Merged Context
                                                                      ↓
                                                              Ranked + Deduplicated
                                                                      ↓
                                                              Context for LLM
"""

import os
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from .indexer import ProjectIndex, FileChunk
from .code_intelligence import FileAnalysis

logger = logging.getLogger("dockai")


@dataclass
class RetrievedContext:
    """
    Container for retrieved context with metadata.
    
    Attributes:
        content: The actual text content.
        source: Source file path.
        relevance_score: How relevant this context is (0.0 - 1.0).
        context_type: Type of context ("dependency", "entry_point", "config", etc.).
    """
    content: str
    source: str
    relevance_score: float
    context_type: str


class ContextRetriever:
    """
    Retrieves optimal context for Dockerfile generation.
    
    This class orchestrates multiple retrieval strategies to gather
    the most relevant information for the LLM:
    
    1. **Must-Have Files**: Dependencies, existing Dockerfiles, configs
    2. **AST-Extracted**: Entry points, environment variables, ports
    3. **Semantic Search**: Content matching Dockerfile-related queries
    
    Example Usage:
        >>> index = ProjectIndex(use_embeddings=True)
        >>> index.index_project("/path/to/project", file_tree)
        >>> retriever = ContextRetriever(index)
        >>> context = retriever.get_dockerfile_context(max_tokens=50000)
    """
    
    # Files that should always be included if present
    MUST_HAVE_FILES = {
        # Dependency files
        "package.json", "requirements.txt", "pyproject.toml",
        "go.mod", "cargo.toml", "gemfile", "pom.xml", "build.gradle",
        "composer.json", "setup.py", "pipfile",
        # Docker files
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        ".dockerignore",
        # Config files
        ".env.example", ".env.sample", "makefile",
        # Version files
        ".nvmrc", ".python-version", ".ruby-version", ".node-version", ".tool-versions",
    }
    
    # Queries for semantic search (Dockerfile-relevant topics)
    DOCKERFILE_QUERIES = [
        "install dependencies build requirements",
        "main entry point start server application",
        "configuration environment variables settings",
        "port listen bind http server",
        "database connection redis mongo postgres",
        "build compile package bundle",
    ]
    
    def __init__(self, index: ProjectIndex):
        """
        Initialize the context retriever.
        
        Args:
            index: A populated ProjectIndex instance.
        """
        self.index = index
    
    def get_dockerfile_context(self, max_tokens: int = 50000) -> str:
        """
        Retrieve optimal context for Dockerfile generation.
        
        This method combines multiple strategies to gather comprehensive
        context while respecting token limits:
        
        1. Include all must-have files (dependencies, existing Docker files)
        2. Extract and summarize AST analysis (entry points, env vars, ports)
        3. Perform semantic search for Dockerfile-relevant content
        4. Deduplicate and merge results
        5. Truncate to fit within token limit
        
        Args:
            max_tokens: Maximum tokens for the context (approx 4 chars/token).
            
        Returns:
            Formatted string containing all relevant context.
        """
        context_parts: List[RetrievedContext] = []
        seen_files: Set[str] = set()
        
        # 1. MUST-HAVE FILES: Always include these if present
        for chunk in self.index.chunks:
            filename = os.path.basename(chunk.file_path).lower()
            if filename in self.MUST_HAVE_FILES:
                if chunk.file_path not in seen_files:
                    context_parts.append(RetrievedContext(
                        content=self._format_chunk(chunk),
                        source=chunk.file_path,
                        relevance_score=1.0,  # Highest priority
                        context_type="must_have"
                    ))
                    seen_files.add(chunk.file_path)
        
        # 2. AST-EXTRACTED INTELLIGENCE: Summarize code analysis
        ast_summary = self._generate_ast_summary()
        if ast_summary:
            context_parts.append(RetrievedContext(
                content=ast_summary,
                source="__ast_analysis__",
                relevance_score=0.95,
                context_type="ast_summary"
            ))
        
        # 3. ENTRY POINT CODE: Include actual code for detected entry points
        entry_point_code = self._get_entry_point_code()
        for code in entry_point_code:
            context_parts.append(RetrievedContext(
                content=code["content"],
                source=code["source"],
                relevance_score=0.9,
                context_type="entry_point"
            ))
            seen_files.add(code["source"])
        
        # 4. SEMANTIC SEARCH: Find relevant chunks
        for query in self.DOCKERFILE_QUERIES:
            results = self.index.search(query, top_k=3)
            for chunk in results:
                if chunk.file_path not in seen_files:
                    context_parts.append(RetrievedContext(
                        content=self._format_chunk(chunk),
                        source=chunk.file_path,
                        relevance_score=0.7,
                        context_type="semantic_match"
                    ))
                    seen_files.add(chunk.file_path)
        
        # 5. SORT by relevance and MERGE
        context_parts.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 6. BUILD final context string with token limit
        max_chars = max_tokens * 4  # Approximate chars per token
        final_context = self._build_final_context(context_parts, max_chars)
        
        logger.info(
            f"Context retriever: {len(context_parts)} sources, "
            f"{len(final_context)} chars (~{len(final_context)//4} tokens)"
        )
        
        return final_context
    
    def _format_chunk(self, chunk: FileChunk) -> str:
        """Format a chunk for inclusion in context."""
        if chunk.chunk_type == "full":
            return f"--- FILE: {chunk.file_path} ---\n{chunk.content}"
        else:
            return (
                f"--- FILE: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line}) ---\n"
                f"{chunk.content}"
            )
    
    def _generate_ast_summary(self) -> str:
        """Generate a summary of AST analysis for the LLM."""
        if not self.index.code_analysis:
            return ""
        
        parts = ["--- CODE INTELLIGENCE SUMMARY ---"]
        
        # Entry points
        entry_points = self.index.get_entry_points()
        if entry_points:
            parts.append(f"\n## Detected Entry Points:")
            for ep in entry_points[:10]:  # Limit to 10
                parts.append(f"  - {ep}")
        
        # Environment variables
        env_vars = self.index.get_all_env_vars()
        if env_vars:
            parts.append(f"\n## Environment Variables Used in Code:")
            parts.append(f"  {', '.join(sorted(env_vars)[:20])}")  # Limit to 20
        
        # Ports
        ports = self.index.get_all_ports()
        if ports:
            parts.append(f"\n## Ports Detected in Code:")
            parts.append(f"  {', '.join(str(p) for p in sorted(ports))}")
        
        # Frameworks
        frameworks = self.index.get_frameworks()
        if frameworks:
            parts.append(f"\n## Frameworks Detected:")
            parts.append(f"  {', '.join(sorted(frameworks))}")
        
        # Languages
        languages = set(a.language for a in self.index.code_analysis.values())
        if languages:
            parts.append(f"\n## Languages:")
            parts.append(f"  {', '.join(sorted(languages))}")
        
        if len(parts) > 1:
            return "\n".join(parts)
        return ""
    
    def _get_entry_point_code(self) -> List[Dict]:
        """Get the actual code for detected entry points."""
        results = []
        
        for path, analysis in self.index.code_analysis.items():
            if not analysis.entry_points:
                continue
            
            # Find the chunk containing this file
            for chunk in self.index.chunks:
                if chunk.file_path == path and chunk.chunk_type == "full":
                    results.append({
                        "source": path,
                        "content": f"--- ENTRY POINT FILE: {path} ---\n{chunk.content}"
                    })
                    break
        
        return results[:5]  # Limit to 5 entry point files
    
    def _build_final_context(
        self, 
        context_parts: List[RetrievedContext], 
        max_chars: int
    ) -> str:
        """Build the final context string with deduplication and truncation."""
        final_parts = []
        current_chars = 0
        
        for ctx in context_parts:
            content_chars = len(ctx.content)
            
            if current_chars + content_chars > max_chars:
                # Check if we can add a truncated version
                remaining = max_chars - current_chars
                if remaining > 500:  # Only add if significant space remains
                    truncated = ctx.content[:remaining-100] + "\n\n... [TRUNCATED] ..."
                    final_parts.append(truncated)
                break
            
            final_parts.append(ctx.content)
            current_chars += content_chars + 2  # +2 for newlines
        
        return "\n\n".join(final_parts)
    
    def get_quick_summary(self) -> Dict:
        """
        Get a quick summary of what the retriever found.
        
        Returns:
            Dictionary with summary statistics.
        """
        return {
            "files_indexed": len(self.index.chunks),
            "files_analyzed": len(self.index.code_analysis),
            "entry_points": self.index.get_entry_points(),
            "env_vars": self.index.get_all_env_vars(),
            "ports": self.index.get_all_ports(),
            "frameworks": self.index.get_frameworks(),
            "embeddings_available": self.index.embeddings is not None,
        }
