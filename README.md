# DockAI

**University Thesis Project: Two-Stage LLM Pipeline for Optimized Dockerfile Generation**

DockAI is a Python CLI tool designed to intelligently analyze a software repository and generate a production-ready, optimized Dockerfile. It uses a novel two-stage LLM pipeline to first understand the project structure ("The Brain") and then architect the build environment ("The Architect").

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

1.  **Clone the repository** (if applicable) or navigate to the project folder.

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory and add your OpenAI API key:
    ```bash
    OPENAI_API_KEY=sk-your-api-key-here
    ```

## 💻 Usage

Run the tool by pointing it to the target repository path. You can analyze the current directory (`.`) or any other path.

```bash
python main.py /path/to/target/repo
```

**Example:**
```bash
python main.py .
```

### What to Expect

The CLI uses a rich terminal interface to show progress:
1.  **Scanning**: Locates files.
2.  **Analyzing**: "The Brain" decides what matters.
3.  **Reading**: Only reads the content of critical files (privacy/token efficient).
4.  **Generating**: "The Architect" builds the Dockerfile.
5.  **Result**: A `Dockerfile` is saved to the target directory.

## 📂 Project Structure

*   `main.py`: The CLI orchestrator using `typer` and `rich`.
*   `scanner.py`: Directory traversal logic.
*   `analyzer.py`: Interface for the Stage 1 LLM call.
*   `generator.py`: Interface for the Stage 2 LLM call.
*   `requirements.txt`: Project dependencies.
