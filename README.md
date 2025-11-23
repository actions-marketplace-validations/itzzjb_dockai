# DockAI

**The End of Manual Dockerfiles: Automated, Intelligent, Production-Ready.**

DockAI is a robust, enterprise-grade Python CLI tool designed to intelligently analyze a software repository and generate a production-ready, optimized Dockerfile. It uses a novel two-stage LLM pipeline to first understand the project structure ("The Brain") and then architect the build environment ("The Architect").

## 💡 Why DockAI?

**Automated Dockerfiles > Human Written > Cloud Native Buildpacks**

DockAI represents the next evolution in containerization.

*   **Better than Humans**: Humans forget best practices, security patches, and layer optimizations. DockAI applies the collective knowledge of thousands of expert DevOps engineers to every single build, ensuring multi-stage optimization, non-root users, and perfect caching strategies every time.
*   **Better than Buildpacks**: Cloud Native Buildpacks are opaque "black boxes" that add bloat and are hard to debug. DockAI generates a **transparent, standard Dockerfile** that you can read, audit, and modify. You get the automation of buildpacks with the control of a handwritten file.

## ✨ Key Features

*   **Zero-Config Automation**: Developers never need to write a Dockerfile again. The GitHub Action automatically generates a perfect, up-to-date Dockerfile on every commit.
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
    *   **Task**: Identifies the technology stack (e.g., Python/Flask, Node/Express) and pinpoints the *exact* files needed for context (e.g., `package.json`, `requirements.txt`).

3.  **Stage 2: The Architect (`generator.py`)**:
    *   **Input**: Content of the critical files identified in Stage 1.
    *   **Task**: Writes a multi-stage, security-focused Dockerfile with version pinning and cache optimization.

## 🚀 Getting Started

### Prerequisites

*   Python 3.8+
*   An OpenAI API Key

### Installation

**From PyPI (Recommended):**

```bash
pip install dockai-cli
```

**From Source (Development):**

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

You can use DockAI directly in your GitHub Actions workflow to automatically generate a Dockerfile on every push. This ensures your Dockerfile is always perfectly in sync with your code changes, without any manual intervention.

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

## 🎨 Custom Instructions

DockAI supports custom instructions to tailor the Dockerfile generation to your specific needs. You can provide instructions in **natural language** using two methods:

### Method 1: Environment Variables

Set environment variables to provide instructions:

```bash
export DOCKAI_ANALYZER_INSTRUCTIONS="Always include package-lock.json if it exists"
export DOCKAI_GENERATOR_INSTRUCTIONS="Use port 8080 and install ffmpeg"
dockai .
```

Or in your `.env` file:

```bash
DOCKAI_ANALYZER_INSTRUCTIONS="Always include package-lock.json if it exists."
DOCKAI_GENERATOR_INSTRUCTIONS="Ensure all images are based on Alpine Linux."
```

### Method 2: `.dockai` File

Create a `.dockai` file in your project root with section-based instructions:

```
# Instructions for the analyzer (file selection stage)
[analyzer]
Always include package-lock.json or yarn.lock if they exist.
Look for any .env.example files to understand environment variables.
Include docker-compose.yml if present.

# Instructions for the generator (Dockerfile creation stage)
[generator]
Ensure the container runs as a non-root user named 'appuser'.
Do not expose any ports other than 8080.
Install 'curl' and 'vim' for debugging purposes.
Set the timezone to 'UTC'.
Define an environment variable 'APP_ENV' with value 'production'.
```

**Note:** If you don't use sections (`[analyzer]` and `[generator]`), the instructions will be applied to both stages.

### Use Cases for Custom Instructions

**Analyzer Instructions:**
- "Always include lock files (package-lock.json, yarn.lock, poetry.lock)"
- "Look for configuration files in the config/ directory"
- "Include any .proto files for gRPC services"

**Generator Instructions:**
- "Use Alpine-based images only"
- "Install system dependencies: ffmpeg, imagemagick, ghostscript"
- "Expose port 3000 instead of the default"
- "Add health check using curl to /health endpoint"
- "Set NODE_ENV to production"
- "Create a non-root user named 'nodeuser'"

### GitHub Action with Custom Instructions

```yaml
- name: Run DockAI
  uses: itzzjb/dockai@main
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    model_analyzer: gpt-4o-mini
    model_generator: gpt-4o
    analyzer_instructions: "Always include yarn.lock if present"
    generator_instructions: "Use Alpine Linux and install curl"
```

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
