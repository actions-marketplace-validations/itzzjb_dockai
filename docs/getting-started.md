# 🚀 Getting Started

## Installation

DockAI is a Python package. We recommend using `pip` or `uv`.

### Prerequisites
*   Python 3.10+
*   Docker Engine (running)

### Install via pip

```bash
pip install dockai-cli
```

### Install via uv (Recommended)

`uv` is a faster alternative to pip.

**Option A: Install as a tool (Recommended)**
This installs `dockai` in an isolated environment and makes it available globally.
```bash
uv tool install dockai-cli
```

**Option B: Install in current environment**
```bash
uv pip install dockai-cli
```

---

## First Run

1.  **Navigate to your project**:
    ```bash
    cd /path/to/my/app
    ```

2.  **Set your API Key**:
    ```bash
    export OPENAI_API_KEY=sk-your-key-here
    ```

3.  **Run DockAI**:
    ```bash
    dockai build .
    ```

---

## What Happens Next?

1.  **Scanning**: DockAI scans your files.
2.  **Indexing**: It builds a local vector index of your code (might take 10-30s for large repos).
3.  **Planning**: It proposes a build plan (e.g., "Use Python 3.11-slim with multi-stage build").
4.  **Generating**: It writes a `Dockerfile`.
5.  **Validating**: It runs `docker build`.
    *   If it fails, it enters a **Self-Correction Loop** to fix the errors.
6.  **Done**: You have a `Dockerfile` and `.dockerignore`.

---

## Configuration using `.env`

You don't need to export variables every time. Create a `.env` file in your directory:

```bash
# .env
OPENAI_API_KEY=sk-...
DOCKAI_USE_RAG=true          # Enable for better context on large apps
DOCKAI_READ_ALL_FILES=true
```

See [Configuration](./configuration.md) for all options.
