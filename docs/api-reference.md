# 📚 API Reference

This document covers the internal API of the `dockai` Python package.

---

## Core Workflow

### `dockai.workflow.graph`

The definition of the LangGraph state machine.

#### `create_graph() -> CompiledStateGraph`
Builds and compiles the state graph.

---

## Agents

### `dockai.agents.analyzer`
**Analyzer Agent**: Identifies the technology stack.

### `dockai.agents.generator`
**Generator Agent**: Writes the Dockerfile.

### `dockai.agents.reviewer`
**Reviewer Agent**: Audits for security.

---

## Context Engine (RAG)

The core innovation in v4.0 is the RAG-based context engine.

### `dockai.utils.indexer`

Handles semantic indexing of the codebase.

#### `class ProjectIndex`
The main entry point for indexing.

*   `__init__(use_embeddings: bool = True)`
*   `index_project(root_path: str, file_tree: List[str])`: Analyzes and chunks all files.
*   `search(query: str, top_k: int) -> List[FileChunk]`: Semantically searches the codebase.

#### `class FileChunk`
Represents a piece of code.
*   `file_path`: Path to file.
*   `content`: The code content.
*   `metadata`: Dict containing `is_config`, `is_dependency`, etc.

### `dockai.utils.context_retriever`

Orchestrates information retrieval for the LLM.

#### `class ContextRetriever`
*   `get_dockerfile_context(max_tokens: int) -> str`: The main method used by agents. It:
    1.  Identifies "Must-Have" files (package.json, etc).
    2.  Extracts AST entry points.
    3.  Performs Graph Traversal (following imports).
    4.  Refines with Semantic Search queries.
    5.  Returns a condensed string fitting the token limit.

### `dockai.utils.code_intelligence`

AST Analysis tools.

*   `analyze_file(path: str, content: str) -> FileAnalysis`: Extracts classes, functions, and imports from code files.

---

## Utilities

### `dockai.utils.registry`

Smart container registry client.

*   `get_docker_tags(image_name: str, target_version: Optional[str]) -> List[str]`: Fetches *real* tags from Docker Hub, Quay, GCR, GHCR. Automatically filters by target version and prefers `alpine`/`slim`.

### `dockai.utils.validator`

Docker validator.

*   `validate_dockerfile(...)`: Runs `docker build` and performs health checks.
