<p align="center">
  <img src="https://img.shields.io/badge/🐳-DockAI-blue?style=for-the-badge&logoColor=white" alt="DockAI Logo" />
</p>

<h1 align="center">DockAI</h1>

<p align="center">
  <strong>AI-Powered Dockerfile Generation Framework</strong>
</p>

<p align="center">
  <em>Generate production-ready Dockerfiles from first principles using AI agents</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/dockai-cli/"><img src="https://img.shields.io/pypi/v/dockai-cli?style=flat-square&color=blue" alt="PyPI Version" /></a>
  <a href="https://pypi.org/project/dockai-cli/"><img src="https://img.shields.io/pypi/pyversions/dockai-cli?style=flat-square" alt="Python Version" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License" /></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-documentation">Docs</a> •
  <a href="#-github-actions">CI/CD</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🎯 What is DockAI?

DockAI is an **agentic AI framework** that analyzes your codebase and generates optimized, production-ready Dockerfiles. Unlike template-based tools, DockAI uses **first-principles reasoning** to understand your application and create Dockerfiles from scratch—handling everything from standard stacks to legacy systems.

```bash
pip install dockai-cli
dockai build /path/to/project
```

That's it. DockAI handles the rest.

---

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>🧠 First-Principles AI</h3>
      <p>No templates. Analyzes file structures, dependencies, and code patterns to deduce the optimal containerization strategy.</p>
    </td>
    <td width="50%">
      <h3>🔄 Self-Correcting Workflow</h3>
      <p>Builds and tests Dockerfiles in a sandbox. If something fails, AI reflects, learns, and retries with a new approach.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🛡️ Security-First</h3>
      <p>Built-in Trivy CVE scanning and Hadolint linting. Enforces non-root users, minimal base images, and hardened configs.</p>
    </td>
    <td width="50%">
      <h3>🤖 10 Specialized Agents</h3>
      <p>Each agent handles a specific task: analysis, planning, generation, review, and more. All fully customizable.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⚡ Multi-Provider LLMs</h3>
      <p>Supports OpenAI, Azure, Gemini, Anthropic, and Ollama. <strong>Mix and match providers</strong> per agent (e.g., OpenAI for analysis, Ollama for generation).</p>
    </td>
    <td width="50%">
      <h3>🔧 Fully Customizable</h3>
      <p>Override prompts, instructions, and model selection per agent. Use <code>.dockai</code> files for repo-specific configs.</p>
    </td>
  <tr>
    <td width="50%">
      <h3>📦 Smart Registry Integration</h3>
      <p>Automatically validates base images against <strong>Docker Hub, GCR, Quay, and GHCR</strong>. Prioritizes small, secure variants like <code>alpine</code> and <code>slim</code>.</p>
    </td>
    <td width="50%">
      <h3>🚀 Performance Optimized</h3>
      <p>Intelligent caching prevents redundant network calls. Semantic version sorting ensures you always get the latest stable releases.</p>
    </td>
  </tr>
</table>

---

## 🚀 Three Ways to Use DockAI

DockAI is designed to fit into any workflow, whether you are a developer, a DevOps engineer, or an AI user.

### 1. The CLI (For Developers)
Perfect for running locally on your machine.

```bash
# Install
pip install dockai-cli

# Run
dockai build .
```

### 2. GitHub Actions (For CI/CD)
Automate Dockerfile generation in your pipelines.

```yaml
steps:
  - uses: actions/checkout@v3
  - uses: itzzjb/dockai@v3
    with:
      openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### 3. MCP Server (For AI Agents)
Use DockAI directly inside **Claude Desktop**, **Cursor**, or any MCP-compliant tool.

1.  Install `dockai-cli`.
2.  Configure your MCP client:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"]
    }
  }
}
```
3.  Ask your AI: *"Analyze this project and generate a Dockerfile for it."*

---

### Configuration

Create a `.env` file:

```bash
# Required: Choose your LLM provider and add the API key
OPENAI_API_KEY=sk-your-api-key

# Optional: Use a different provider (openai, azure, gemini, anthropic, ollama)
# DOCKAI_LLM_PROVIDER=openai
```

### Usage

```bash
# Generate Dockerfile for your project
dockai build /path/to/project

# With verbose output
dockai build /path/to/project --verbose
```

---

## 🏗️ How It Works

```mermaid
graph TD
    Start([▶ Start]) --> Scan[📂 Scanner]
    Scan --> Analyze[🧠 Analyzer]
    Analyze --> Read[📖 Reader]
    Read --> Health[🏥 Health Detector]
    Health --> Ready[⏱️ Readiness Detector]
    Ready --> Plan[📝 Planner]
    Plan --> Generate[⚙️ Generator]
    Generate --> Review[🔒 Security Reviewer]
    
    Review -- Secure --> Validate[✅ Validator]
    Review -- Issues & Can Retry --> Reflect[🤔 Reflector]
    Review -- Critical & Max Retries --> Fail([❌ Fail])
    
    Validate -- Success --> End([🏁 Finish])
    Validate -- Failure --> Reflect
    
    Reflect --> Increment[🔄 Increment Retry]
    
    Increment -- Fix Code --> Generate
    Increment -- New Strategy --> Plan
    Increment -- Re-Analyze --> Analyze
    Increment -- Max Retries --> Fail
```

---

## 🤖 The 10 AI Agents

| Agent | Role | Model Type |
|-------|------|------------|
| **Analyzer** | Project discovery & stack detection | Fast |
| **Planner** | Strategic build planning | Fast |
| **Generator** | Dockerfile creation | Powerful |
| **Generator (Iterative)** | Debugging failed Dockerfiles | Powerful |
| **Reviewer** | Security audit & hardening | Fast |
| **Reflector** | Failure analysis & learning | Powerful |
| **Health Detector** | Health endpoint discovery | Fast |
| **Readiness Detector** | Startup pattern analysis | Fast |
| **Error Analyzer** | Error classification | Fast |
| **Iterative Improver** | Targeted fix application | Powerful |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required* |
| `GOOGLE_API_KEY` | Google Gemini API key | Required* |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Required* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Required* |
| `OLLAMA_BASE_URL` | Ollama Base URL | `http://localhost:11434` |
| `DOCKAI_LLM_PROVIDER` | Provider (`openai`, `azure`, `gemini`, `anthropic`, `ollama`) | `openai` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy scanning | `false` |
| `DOCKAI_SKIP_HADOLINT` | Skip Hadolint linting | `false` |
| `DOCKAI_TRUNCATION_ENABLED` | Enable file truncation | `false` |
| `DOCKAI_TOKEN_LIMIT` | Token limit for auto-truncation | `100000` |
| `DOCKAI_MAX_FILE_CHARS` | Max chars per file (when truncating) | `200000` |
| `DOCKAI_MAX_FILE_LINES` | Max lines per file (when truncating) | `5000` |

*Only one API key required for your chosen provider.

### Repository-Level Configuration

Create a `.dockai` file in your project root:

```ini
[instructions_analyzer]
This is a Django application with Celery workers.

[instructions_generator]
Use gunicorn as the WSGI server.
Run database migrations at container start.

[instructions_reviewer]
All containers must run as non-root (UID >= 10000).
```

---

## 🔗 GitHub Actions

```yaml
name: Auto-Dockerize

on:
  push:
    branches: [main]

jobs:
  dockai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: itzzjb/dockai@v3
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

> 💡 **Tip**: By default, the Dockerfile is generated at runtime and not committed. If you want to save it to your repository, see the [Committing Generated Dockerfile](./docs/github-actions.md#committing-generated-dockerfile) guide.

### Multi-Provider Example

```yaml
- uses: itzzjb/dockai@v3
  with:
    llm_provider: gemini
    google_api_key: ${{ secrets.GOOGLE_API_KEY }}
    max_retries: 5
    strict_security: true
```

### Mixed Provider Example

Use **Ollama** locally for most tasks, but **OpenAI** for complex analysis:

```bash
# .env
DOCKAI_LLM_PROVIDER=ollama
DOCKAI_MODEL_ANALYZER=openai/gpt-4o-mini
```

See [GitHub Actions Guide](./docs/github-actions.md) for all options.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [**Getting Started**](./docs/getting-started.md) | Installation, configuration, first run |
| [**Architecture**](./docs/architecture.md) | Deep dive into the internal design |
| [**Configuration**](./docs/configuration.md) | Full reference for env vars and inputs |
| [**Customization**](./docs/customization.md) | Tuning agents for your organization |
| [**API Reference**](./docs/api-reference.md) | Module and function documentation |
| [**GitHub Actions**](./docs/github-actions.md) | CI/CD integration guide |
| [**MCP Server**](./docs/mcp-server.md) | AI Agent integration guide |
| [**Releases**](./docs/releases.md) | Release process and version management |
| [**FAQ**](./docs/faq.md) | Frequently asked questions |

> 💡 **MCP Support**: Expose DockAI as a [Model Context Protocol](https://modelcontextprotocol.io/) server for use in any MCP client.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|----------|
| **Python 3.10+** | Core runtime |
| **LangGraph** | Stateful agent workflow orchestration |
| **LangChain** | LLM provider integration |
| **Pydantic** | Structured output validation |
| **Rich + Typer** | Beautiful CLI interface |
| **Trivy** | Security vulnerability scanning |
| **Hadolint** | Dockerfile linting and best practices |

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues and pull requests.

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/itzzjb">itzzjb</a></sub>
</p>
