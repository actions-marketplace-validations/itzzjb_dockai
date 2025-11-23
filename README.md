# DockAI

**Production-Ready Two-Stage LLM Pipeline for Optimized Dockerfile Generation**

DockAI is a robust, enterprise-grade Python CLI tool designed to intelligently analyze a software repository and generate a production-ready, optimized Dockerfile. It uses a novel two-stage LLM pipeline to first understand the project structure ("The Brain") and then architect the build environment ("The Architect").

## ✨ Key Features

*   **Two-Stage Pipeline**: Separates analysis (cheap/fast) from generation (smart/expensive) for cost-efficiency.
*   **Intelligent Scanning**: Uses `pathspec` to fully respect `.gitignore` and `.dockerignore` patterns (including wildcards like `*.log` or `secret_*.json`).
*   **Robust & Reliable**: Built-in automatic retries with exponential backoff for all AI API calls to handle network instability.
*   **Observability**: Structured logging with a `--verbose` mode for deep debugging and transparency.
*   **Security First**: Generates non-root, multi-stage builds by default.

## 🧠 Architecture

The system operates in three distinct phases:

1.  **The Intelligent Scanner (`scanner.py`)**:
    *   Maps the entire repository file tree.
    *   Automatically filters out files based on `.gitignore` and `.dockerignore` using industry-standard wildcard matching.

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

## 🤖 Usage as GitHub Action

You can use DockAI directly in your GitHub Actions workflow to automatically generate a Dockerfile on every push (or manually).

### Example Workflow

Create a file `.github/workflows/dockai.yml`:

```yaml
name: Generate Dockerfile
on:
  workflow_dispatch: # Allows manual triggering

jobs:
  generate:
    runs-on: ubuntu-latest
    permissions:
      contents: write # Needed to push the generated Dockerfile back
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Run DockAI
        uses: itzzjb/dockai@main
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          model_analyzer: gpt-4o-mini
          model_generator: gpt-4o
          
      - name: Commit and Push Dockerfile
        run: |
          git config --global user.name "DockAI Bot"
          git config --global user.email "bot@dockai.com"
          git add Dockerfile
          git commit -m "ci: generate optimized Dockerfile via DockAI" || echo "No changes to commit"
          git push
```

## 💻 CLI Usage

Once installed, the `dockai` command is available globally in your terminal.

Run the tool by pointing it to the target repository path.

```bash
dockai /path/to/target/repo
```

**Example (Current Directory):**
```bash
dockai .
```

**Verbose Mode (for debugging):**
```bash
dockai . --verbose
```

### What to Expect

The CLI uses a rich terminal interface to show progress:
1.  **Scanning**: Locates files, respecting all ignore patterns.
2.  **Analyzing**: "The Brain" decides what matters.
3.  **Reading**: Only reads the content of critical files (privacy/token efficient).
4.  **Generating**: "The Architect" builds the Dockerfile.
5.  **Result**: A `Dockerfile` is saved to the target directory.

## 🛠️ Development

### Running Tests

This project uses `pytest` for testing. To run the test suite:

```bash
pytest
```

### Project Structure

The project follows a modern `src`-layout:

*   `src/dockai/`: Source code package.
    *   `main.py`: The CLI orchestrator using `typer` and `rich`.
    *   `scanner.py`: Directory traversal logic with `pathspec`.
    *   `analyzer.py`: Interface for the Stage 1 LLM call (with retries).
    *   `generator.py`: Interface for the Stage 2 LLM call (with retries).
*   `tests/`: Unit and integration tests.
*   `pyproject.toml`: Build configuration and dependency management.
