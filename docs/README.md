# DockAI Documentation

Welcome to the DockAI documentation. This guide covers everything from getting started to advanced customization.

## Documentation Index

### Getting Started

- **[Getting Started](./getting-started.md)** — Installation, configuration, and your first run
- **[FAQ](./faq.md)** — Frequently asked questions

### Core Concepts

- **[Architecture](./architecture.md)** — How DockAI works under the hood
- **[Configuration](./configuration.md)** — All configuration options
- **[Customization](./customization.md)** — Fine-tuning agents for your stack

### Integration

- **[GitHub Actions](./github-actions.md)** — CI/CD integration guide
- **[Platform Integration](./platform-integration.md)** — Embedding DockAI in your platform

### Reference

- **[API Reference](./api-reference.md)** — Module and function documentation

## Quick Links

### Installation

```bash
pip install dockai-cli
```

### Configuration

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### Usage

```bash
dockai build /path/to/your/project
```

## Documentation Structure

```
docs/
├── README.md              # This file
├── getting-started.md     # Installation and first run
├── architecture.md        # How DockAI works
├── configuration.md       # Configuration options
├── customization.md       # Fine-tuning guide
├── api-reference.md       # API documentation
├── github-actions.md      # CI/CD integration
├── platform-integration.md # Platform embedding
└── faq.md                 # Common questions
```

## Need Help?

- Check the [FAQ](./faq.md) for common questions
- Open an issue on [GitHub](https://github.com/itzzjb/dockai/issues)
- See [Contributing](../CONTRIBUTING.md) to help improve DockAI
