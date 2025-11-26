# DockAI 🐳🤖
> **The Universal AI DevOps Architect for Dockerizing Applications**

DockAI is a powerful, agentic CLI tool that autonomously generates, validates, and optimizes production-ready Dockerfiles for **ANY** application. 

Unlike simple template generators, DockAI acts as a **Universal DevOps Architect**. It uses a stateful, cyclic workflow to reason from first principles, allowing it to containerize not just standard stacks (Node, Python, Go) but also legacy systems and **future technologies** it has never seen before.

---

## 🌟 Key Features

### 🧠 Universal Agentic Brain
- **First-Principles Reasoning**: Doesn't rely on hardcoded templates. It analyzes file extensions, shebangs, and build scripts to deduce how to build and run *any* code.
- **Future-Proof**: Can handle unknown or future programming languages by analyzing their runtime requirements (e.g., "This looks like a new compiled language, I need to install its toolchain").
- **Strategic Planning**: Acts as an Architect, planning the build strategy (multi-stage, static linking, security hardening) before writing code.

### 🔄 Self-Correcting Workflow
- **Automated Debugging**: If the build fails, DockAI doesn't just give up. It performs a "Post-Mortem" analysis, reads the error logs, understands the root cause (e.g., "missing system library `libxyz`"), and **fixes its own code**.
- **Iterative Improvement**: It learns from each attempt, refining the Dockerfile until it passes all validation checks.

### 🛡️ Robust Validation & Security
- **Sandboxed Verification**: Every generated Dockerfile is built and run in a secure, resource-limited sandbox.
- **Smart Health Checks**: 
    - Automatically detects health endpoints (e.g., `/health`).
    - **Robust Fallback**: Checks from inside the container first, but falls back to host-based checks for secure "distroless" images that lack `curl`.
- **Readiness Detection**: Uses AI to predict startup log patterns (e.g., "Server ready on port 8080") to intelligently wait for the app to start.
- **Security First**: Proactively plans for non-root users, pinned versions, and minimal base images. Integrated with **Trivy** for vulnerability scanning.

### 💎 Developer Experience
- **Beautiful UI**: Powered by `Rich`, featuring real-time status spinners, formatted logs, and clear error reports.
- **Cost Awareness**: Tracks and reports token usage for every stage.
- **Production Ready**: Generates optimized, multi-stage Dockerfiles following industry best practices.

---

## 🏗️ Architecture Deep Dive

DockAI is built on **LangGraph**, enabling a cyclic, stateful workflow that mimics a human engineer's problem-solving process.

### The Agentic Workflow

The agent moves through a sophisticated graph of nodes:

1.  **Scanner (`scanner.py`)**: Efficiently maps the project structure, respecting `.gitignore`.
2.  **Analyzer (`analyzer.py`)**: The "Brain". Deduced the tech stack, entry points, and dependencies from first principles.
3.  **Reader (`nodes.py`)**: Smartly reads critical files (using "Head & Tail" truncation for large files) to gather context without wasting tokens.
4.  **Health & Readiness Detectors**: AI scans code for health routes and startup log patterns.
5.  **Planner (`agent.py`)**: The "Architect". Formulates a detailed build plan (Base Image, Multi-stage strategy, Security).
6.  **Generator (`generator.py`)**: The "Builder". Writes the Dockerfile based on the plan.
7.  **Security Reviewer (`reviewer.py`)**: Static analysis for security best practices.
8.  **Validator (`validator.py`)**: The "Test Engineer". Builds, runs, and verifies the container.
9.  **Reflector (`agent.py`)**: The "Debugger". Analyzes failures and guides the next iteration.

### The Graph

```mermaid
graph TD
    Start --> Scan[📂 Scanner]
    Scan --> Analyze[🧠 Analyzer]
    Analyze --> Read[📖 Reader]
    Read --> Health[🏥 Detect Health]
    Health --> Ready[⏱️ Detect Readiness]
    Ready --> Plan[📝 Planner]
    Plan --> Generate[⚙️ Generator]
    Generate --> Review[🔒 Security Review]
    
    Review -- Pass --> Validate[✅ Validator]
    Review -- Fail --> Reflect[🤔 Reflector]
    
    Validate -- Success --> End((🏁 Finish))
    Validate -- Failure --> Reflect
    
    Reflect --> Retry{Retry Strategy}
    Retry -- Fix Code --> Generate
    Retry -- New Plan --> Plan
    Retry -- Re-Analyze --> Analyze
    Retry -- Max Retries --> Fail((❌ Fail))
```

---

## 🛠️ Technology Stack

*   **Language**: Python 3.10+
*   **Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) (Stateful Agents)
*   **AI Models**: OpenAI (GPT-4o for complex reasoning, GPT-4o-mini for fast analysis)
*   **Containerization**: Docker SDK for Python
*   **UI/CLI**: [Rich](https://github.com/Textualize/rich) & [Typer](https://typer.tiangolo.com/)
*   **Validation**: [Pydantic](https://docs.pydantic.dev/) for structured data.
*   **Security**: [Trivy](https://github.com/aquasecurity/trivy)

---

## 🚀 Getting Started

### Prerequisites

*   **Docker**: Must be installed and running.
*   **Python**: Version 3.10 or higher.
*   **OpenAI API Key**: Access to GPT-4o is recommended for best results.

### Installation

1.  **Install via Pip**:
    ```bash
    pip install dockai-cli
    ```

2.  **Or Install from Source (for development)**:
    ```bash
    git clone https://github.com/yourusername/dockai.git
    cd dockai
    pip install -e .
    ```

3.  **Set up Environment**:
    Create a `.env` file in the root directory:
    ```bash
    OPENAI_API_KEY=sk-your-api-key-here
    # Optional overrides
    # MODEL_GENERATOR=gpt-4o
    # MODEL_ANALYZER=gpt-4o-mini
    ```

### Usage

Navigate to any application folder and run:

```bash
dockai build .
```

**Options:**
*   `--verbose` / `-v`: Enable detailed debug logging.
*   `--no-cache`: Force a fresh analysis.

### Example Output

```text
DockAI 🐳
Universal AI DevOps Architect

[INFO] Scanning project directory...
[INFO] Detected Stack: Custom Rust Service
[INFO] Formulating build strategy (Multi-stage, Distroless)...
[INFO] Generating Dockerfile (Attempt 1)...
[INFO] Validating Dockerfile...
[INFO] Building image (250MB limit)...
[INFO] Running container (Sandboxed)...
[INFO] Detected startup pattern: "Service ready on 0.0.0.0:8080"
[INFO] Health check passed (Host Fallback)!
[INFO] Security scan passed.

✅ Success! Dockerfile validated successfully.
📄 Final Dockerfile saved to ./Dockerfile
```

---

## 🤖 GitHub Actions Integration

DockAI can run as a GitHub Action to automatically containerize your applications in your CI/CD pipeline.

### Usage Example

Create a workflow file `.github/workflows/dockerize.yml`:

```yaml
name: Auto-Dockerize with DockAI

on:
  push:
    branches: [ "main" ]

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run DockAI
        uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `openai_api_key` | Your OpenAI API Key. | **Yes** | - |
| `project_path` | Path to the project root. | No | `.` |
| `model_generator` | Model for generation. | No | `gpt-4o` |
| `model_analyzer` | Model for analysis. | No | `gpt-4o-mini` |
| `max_retries` | Max retry attempts. | No | `3` |
| `skip_security_scan` | Skip Trivy scan. | No | `false` |
| `strict_security` | Fail on any vulnerability. | No | `false` |
| `max_image_size_mb` | Max image size in MB. | No | `500` |
| `skip_health_check` | Skip health checks. | No | `false` |

---

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | **Required**. Your OpenAI API key. | - |
| `MODEL_GENERATOR` | Model for generation/reflection. | `gpt-4o` |
| `MODEL_ANALYZER` | Model for analysis/planning. | `gpt-4o-mini` |
| `MAX_RETRIES` | Max attempts to fix a failing Dockerfile. | `3` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Set to `true` to skip Trivy scans. | `false` |
| `DOCKAI_STRICT_SECURITY` | Set to `true` to fail on any vulnerability. | `false` |
| `DOCKAI_MAX_IMAGE_SIZE_MB` | Max image size in MB (0 to disable). | `500` |
| `DOCKAI_SKIP_HEALTH_CHECK` | Set to `true` to skip health checks. | `false` |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Built with ❤️ by Januda Bethmin*
