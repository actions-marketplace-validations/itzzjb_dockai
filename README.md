# DockAI 🐳🤖

> **AI-Powered Dockerfile Generation Framework**

[![PyPI version](https://badge.fury.io/py/dockai-cli.svg)](https://badge.fury.io/py/dockai-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

DockAI is an intelligent, agentic CLI framework that analyzes your codebase and generates production-ready Dockerfiles using AI. It uses first-principles reasoning to containerize any application—from standard stacks to legacy systems and future technologies.

## ✨ Key Features

- **🧠 First-Principles Reasoning** — Analyzes file structures and code to deduce requirements, no templates needed
- **🔄 Self-Correcting Workflow** — Automatically debugs and fixes failed builds through reflection
- **🛡️ Security-First** — Built-in security review with Trivy integration for vulnerability scanning
- **🎯 10 Customizable AI Agents** — Fine-tune each agent for your organization's standards
- **⚡ Multi-Provider Support** — Works with OpenAI, Azure OpenAI, Google Gemini, and Anthropic

## 🚀 Quick Start

### Installation

```bash
pip install dockai-cli
```

### Configuration

Create a `.env` file with your API key:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### Usage

```bash
dockai build /path/to/your/project
```

That's it! DockAI will analyze your project and generate an optimized Dockerfile.

## 📖 Documentation

For comprehensive documentation, see the [docs](./docs/) directory:

- **[Getting Started](./docs/getting-started.md)** — Installation, configuration, and first run
- **[Architecture](./docs/architecture.md)** — How DockAI works under the hood
- **[Configuration](./docs/configuration.md)** — All configuration options
- **[Customization](./docs/customization.md)** — Fine-tuning agents for your stack
- **[API Reference](./docs/api-reference.md)** — Module and function documentation
- **[GitHub Actions](./docs/github-actions.md)** — CI/CD integration guide
- **[Platform Integration](./docs/platform-integration.md)** — Embedding DockAI in your platform

## 🏗️ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      DockAI Workflow                            │
├─────────────────────────────────────────────────────────────────┤
│  1. SCAN      → Discover project files                          │
│  2. ANALYZE   → AI deduces technology stack                     │
│  3. PLAN      → Strategic build planning                        │
│  4. GENERATE  → Create Dockerfile                               │
│  5. REVIEW    → Security audit                                  │
│  6. VALIDATE  → Build & test in sandbox                         │
│  7. REFLECT   → If failed: analyze, learn, retry                │
│  8. OUTPUT    → Production-ready Dockerfile                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 The 10 AI Agents

| Agent | Role |
|-------|------|
| **Analyzer** | Project discovery and stack detection |
| **Planner** | Strategic build planning |
| **Generator** | Dockerfile creation |
| **Reviewer** | Security audit |
| **Validator** | Build and runtime testing |
| **Reflector** | Failure analysis and learning |
| **Health Detector** | Health endpoint discovery |
| **Readiness Detector** | Startup pattern analysis |
| **Error Analyzer** | Error classification |
| **Iterative Improver** | Targeted fix application |

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DOCKAI_LLM_PROVIDER` | LLM provider (`openai`, `azure`, `gemini`, `anthropic`) | `openai` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |
| `DOCKAI_SKIP_SECURITY_SCAN` | Skip Trivy scanning | `false` |

See [Configuration Documentation](./docs/configuration.md) for all options.

### Repository Configuration

Create a `.dockai` file in your project root:

```ini
[instructions_analyzer]
This is a Django application with Celery workers.

[instructions_generator]
Use gunicorn as the WSGI server.
Include database migration step.

[instructions_reviewer]
All containers must run as non-root.
```

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
      - uses: itzzjb/dockai@v2
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

See [GitHub Actions Guide](./docs/github-actions.md) for advanced usage.

## 🛠️ Technology Stack

- **Python 3.10+** — Core runtime
- **LangGraph** — Stateful agent workflow orchestration
- **LangChain** — LLM integration
- **Pydantic** — Structured output validation
- **Rich & Typer** — Beautiful CLI interface
- **Trivy** — Security vulnerability scanning

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/itzzjb/dockai.git
cd dockai
pip install -e ".[test]"
pytest tests/
```

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

---

**Built with ❤️ by [Januda Bethmin](https://github.com/itzzjb)**
