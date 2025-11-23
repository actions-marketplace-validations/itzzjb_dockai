# DockAI

**University Thesis Project: Two-Stage LLM Pipeline for Optimized Dockerfile Generation**

DockAI is a production-ready Python CLI tool designed to intelligently analyze a software repository and generate a production-ready, optimized Dockerfile. It uses a novel two-stage LLM pipeline to first understand the project structure ("The Brain") and then architect the build environment ("The Architect").

## 🧠 Architecture

The system operates in three distinct phases:

1.  **The Intelligent Scanner (`scanner.py`)**:
    *   Maps the entire repository file tree.
    *   Intelligently ignores build artifacts (`node_modules`, `venv`, etc.) to reduce noise.

2.  **Stage 1: The Brain (`analyzer.py`)**:
    *   **Input**: JSON list of file paths.
    *   **Model**: GPT-4o-mini (optimized for speed/cost).
    *   **Task**: Identifies the technology stack (e.g., Python/Flask, Node/Express) and pinpoints the *exact* files needed for context (e.g., `package.json`, `requirements.txt`).

3.  **Stage 2: The Architect (`generator.py`)**:
    *   **Input**: Content of the critical files identified in Stage 1.
    *   **Model**: GPT-4o (optimized for quality).
    *   **Task**: Writes a multi-stage, security-focused Dockerfile with version pinning and cache optimization.

## 🚀 Getting Started

### Prerequisites

*   Python 3.8+
*   An OpenAI API Key

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/itzzjb/dockai.git
    cd dockai
    ```

2.  **Install the package**:
    You can install the tool locally using pip. We recommend installing in "editable" mode (`-e`) if you plan to modify the code.
    ```bash
    pip install -e .
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory and add your OpenAI API key and model configurations:
    ```bash
    OPENAI_API_KEY=sk-your-api-key-here
    MODEL_ANALYZER=gpt-4o-mini
    MODEL_GENERATOR=gpt-4o
    ```

## 💻 Usage

Once installed, the `dockai` command is available globally in your terminal.

Run the tool by pointing it to the target repository path.

```bash
dockai /path/to/target/repo
```

**Example (Current Directory):**
```bash
dockai .
```

### What to Expect

The CLI uses a rich terminal interface to show progress:
1.  **Scanning**: Locates files.
2.  **Analyzing**: "The Brain" decides what matters.
3.  **Reading**: Only reads the content of critical files (privacy/token efficient).
4.  **Generating**: "The Architect" builds the Dockerfile.
5.  **Result**: A `Dockerfile` is saved to the target directory.

## �️ Development

### Running Tests

This project uses `pytest` for testing. To run the test suite:

```bash
pytest
```

### Project Structure

The project follows a modern `src`-layout:

*   `src/dockai/`: Source code package.
    *   `main.py`: The CLI orchestrator using `typer` and `rich`.
    *   `scanner.py`: Directory traversal logic.
    *   `analyzer.py`: Interface for the Stage 1 LLM call.
    *   `generator.py`: Interface for the Stage 2 LLM call.
*   `tests/`: Unit and integration tests.
*   `pyproject.toml`: Build configuration and dependency management.
