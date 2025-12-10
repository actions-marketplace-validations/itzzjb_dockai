# DockAI Documentation

Welcome to the DockAI documentation! This guide will help you understand and use DockAI effectively.

## 📚 Documentation Overview

### Getting Started
- **[Getting Started](getting-started.md)** - Installation, setup, and first steps
- **[Configuration](configuration.md)** - Complete reference for all configuration options
- **[LLM Providers](llm-providers.md)** - Detailed setup guides for OpenAI, Gemini, Anthropic, Azure, and Ollama

### Core Concepts
- **[Architecture](architecture.md)** - Deep dive into v4.0 architecture, RAG system, and multi-agent workflow
- **[FAQ](faq.md)** - Frequently asked questions and troubleshooting

### Integration & Advanced
- **[GitHub Actions](github-actions.md)** - Using DockAI in CI/CD pipelines
- **[MCP Integration](mcp-integration.md)** - Using DockAI with Model Context Protocol (Claude Desktop, VSCode, etc.)
- **[API Reference](api-reference.md)** - Code-level documentation for developers

## 🚀 Quick Links

### New to DockAI?
Start here: [Getting Started Guide](getting-started.md)

### Want to understand how it works?
Read: [Architecture Documentation](architecture.md)

### Need to configure something?
Check: [Configuration Reference](configuration.md)

### Using in CI/CD?
See: [GitHub Actions Guide](github-actions.md)

### Having issues?
Try: [FAQ & Troubleshooting](faq.md)

## 📖 Documentation Structure

```
docs/
├── README.md                 # This file
├── getting-started.md        # Installation and first steps
├── architecture.md           # Deep architectural overview
├── configuration.md          # Complete configuration reference
├── llm-providers.md          # LLM provider setup guides
├── github-actions.md         # CI/CD integration
├── api-reference.md          # Code-level API documentation
└── faq.md                    # FAQ and troubleshooting
```

## 🎯 Common Tasks

### Installing DockAI
```bash
pip install dockai-cli
```
See: [Installation](getting-started.md#installation)

### Basic Usage
```bash
export OPENAI_API_KEY="sk-..."
dockai build .
```
See: [First Run](getting-started.md#first-run)

### Choosing an LLM Provider
DockAI supports OpenAI, Google Gemini, Anthropic Claude, Azure OpenAI, and Ollama.

See: [LLM Providers Guide](llm-providers.md)

### Customizing Dockerfiles
Use custom instructions to guide the AI:
```bash
export DOCKAI_GENERATOR_INSTRUCTIONS="Always use Alpine. Pin versions."
dockai build .
```
See: [Custom Instructions](configuration.md#custom-instructions)

### Understanding the Workflow
DockAI uses a multi-agent system orchestrated by LangGraph with RAG for context retrieval.

See: [Architecture](architecture.md#agent-workflow)

### Using in GitHub Actions
```yaml
- uses: itzzjb/dockai@v4
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```
See: [GitHub Actions Guide](github-actions.md)

## 🤔 Common Questions

**Q: How much does DockAI cost per run?**  
A: Typically $0.02-$0.10 depending on the model. Gemini is cheapest (~$0.02). See: [FAQ - Costs](faq.md#how-much-does-dockai-cost-per-run)

**Q: What languages/frameworks are supported?**  
A: Virtually any language or framework! DockAI uses AI to understand your code, not templates. See: [FAQ - Supported Languages](faq.md#what-languagesframeworks-does-dockai-support)

**Q: Can DockAI update an existing Dockerfile?**  
A: Yes! It analyzes the existing Dockerfile and uses it as context. See: [FAQ - Existing Dockerfiles](faq.md#can-dockai-update-an-existing-dockerfile)

**Q: How does RAG work?**  
A: RAG indexes all files with semantic embeddings, then retrieves only relevant context for the LLM. See: [Architecture - RAG](architecture.md#rag-context-engine)

**Q: How do I debug failures?**  
A: Run with `--verbose` flag and check the reflection output. See: [Troubleshooting](getting-started.md#troubleshooting)

For more: [Full FAQ](faq.md)

## 🏗️ Architecture Highlights

### v4.0 Improvements
- **RAG-Based Context**: Intelligent semantic search for targeted context retrieval
- **Multi-Agent System**: 8 specialized agents for different tasks
- **Adaptive Learning**: AI analyzes failures and tries new strategies
- **LangGraph Orchestration**: Sophisticated workflow with conditional routing

**Workflow Overview:**
```
Scan → Analyze → Read Files (RAG) → Blueprint → Generate 
→ Review → Validate → Reflect (on failure) → Retry or Reanalyze
```

See: [Architecture Documentation](architecture.md)

## ⚙️ Configuration Highlights

### Environment Variables
DockAI supports 100+ environment variables for customization:

**Most Important:**
- `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` - LLM provider keys
- `DOCKAI_LLM_PROVIDER` - Choose provider (`openai`, `gemini`, `anthropic`, `azure`, `ollama`)
- `DOCKAI_MODEL_*` - Per-agent model selection
- `MAX_RETRIES` - Max attempts to fix failures
- `DOCKAI_USE_RAG` - Enable RAG (default: true)

See: [Full Configuration Reference](configuration.md)

## 🔗 External Resources

- **GitHub Repository**: [github.com/itzzjb/dockai](https://github.com/itzzjb/dockai)
- **PyPI Package**: [pypi.org/project/dockai-cli](https://pypi.org/project/dockai-cli/)
- **GitHub Actions Marketplace**: [github.com/marketplace/actions/dockai](https://github.com/marketplace/actions/dockai)
- **Issues**: [github.com/itzzjb/dockai/issues](https://github.com/itzzjb/dockai/issues)
- **Discussions**: [github.com/itzzjb/dockai/discussions](https://github.com/itzzjb/dockai/discussions)

## 📝 Contributing to Documentation

Found a typo? Want to improve the docs? PRs are welcome!

1. Fork the repo
2. Edit the docs in `docs/`
3. Submit a PR

See: [CONTRIBUTING.md](../CONTRIBUTING.md)

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/itzzjb/dockai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/itzzjb/dockai/discussions)
- **Email**: desilvabethmin@gmail.com

---

**Happy Dockerizing! 🐳🤖**
