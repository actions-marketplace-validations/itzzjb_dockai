# DockAI: Adaptive Agentic Dockerfile Generator

DockAI is an advanced, AI-powered CLI tool that generates production-ready Dockerfiles for any project. It uses a sophisticated **LangGraph** agentic workflow to analyze, plan, generate, validate, and iteratively improve Docker configurations.

## 🚀 Key Features

*   **Adaptive Agent Workflow**: Uses LangGraph to plan, reflect, and iterate like a human engineer.
*   **Smart Readiness Checks**: Automatically detects application startup patterns in logs to verify readiness (no more fixed sleep times).
*   **Health Endpoint Detection**: Scans code to find and configure health checks automatically.
*   **Security-First**: Integrated Trivy scanning and best-practice enforcement (non-root users, minimal images).
*   **Iterative Self-Correction**: If a build or validation fails, the agent analyzes the error, reflects on the root cause, and applies targeted fixes.
*   **Multi-Language Support**: Works with Python, Node.js, Go, Java, Rust, PHP, and more.

## 🏗️ Architecture

The core logic is implemented as a stateful graph in `src/dockai/graph.py`, with individual steps defined in `src/dockai/nodes.py`.

### Workflow Steps

1.  **Scan**: Fast directory traversal to build a file tree.
2.  **Analyze**: AI analyzes project structure, stack, and requirements.
3.  **Read Files**: selectively reads critical configuration and source files.
4.  **Detect Health**: AI scans code for health check endpoints.
5.  **Detect Readiness**: AI identifies log patterns that indicate successful startup.
6.  **Plan**: AI formulates a build strategy (base image, multi-stage, etc.).
7.  **Generate**: Creates the Dockerfile (fresh or iterative improvement).
8.  **Review**: Security review of the generated Dockerfile.
9.  **Validate**: Builds and runs the container in a sandboxed environment.
10. **Reflect**: If validation fails, AI analyzes logs to determine root cause and fix strategy.

## 🛠️ Installation

```bash
pip install dockai-cli
```

### Prerequisites

*   **Docker**: Must be installed and running.
*   **OpenAI API Key**: Required for AI capabilities.

## 🚦 Usage

1.  Set your OpenAI API key:
    ```bash
    export OPENAI_API_KEY=your_key_here
    ```

2.  Run DockAI in your project directory:
    ```bash
    dockai run .
    ```

### Configuration

You can configure DockAI using environment variables or a `.env` file:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MODEL_ANALYZER` | Model for analysis/planning (faster/cheaper) | `gpt-4o-mini` |
| `MODEL_GENERATOR` | Model for generation/reflection (smarter) | `gpt-4o` |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Max allowed image size in MB | `500` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy security scan | `false` |
| `DOCKAI_STRICT_SECURITY` | Fail on security vulnerabilities | `false` |
| `MAX_RETRIES` | Maximum number of improvement iterations | `5` |

## 🧪 Development

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
pytest
```

## 📂 Project Structure

*   `src/dockai/`: Source code
    *   `main.py`: CLI entry point
    *   `graph.py`: LangGraph workflow definition
    *   `nodes.py`: Individual graph node implementations
    *   `agent.py`: AI interaction logic (prompts & chains)
    *   `validator.py`: Docker build/run validation logic
    *   `errors.py`: AI error classification
    *   `ui.py`: Rich-based UI components
*   `tests/`: Unit and integration tests

## 📄 License

MIT
