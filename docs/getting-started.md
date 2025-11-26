# Getting Started with DockAI

This guide will help you install, configure, and run DockAI for the first time.

## Prerequisites

Before installing DockAI, ensure you have:

- **Python 3.10+** — DockAI requires Python 3.10 or higher
- **Docker** — Must be installed and running
- **API Key** — Access to one of the supported LLM providers:
  - OpenAI (GPT-4o recommended)
  - Azure OpenAI
  - Google Gemini
  - Anthropic Claude

### Optional: Trivy for Security Scanning

For vulnerability scanning, install Trivy:

```bash
# macOS
brew install trivy

# Linux (Debian/Ubuntu)
sudo apt-get install trivy

# Or DockAI will use the Docker image automatically
docker pull aquasec/trivy
```

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install dockai-cli
```

### Option 2: Install from Source

```bash
git clone https://github.com/itzzjb/dockai.git
cd dockai
pip install -e .
```

## Configuration

### Step 1: Create Environment File

Create a `.env` file in your working directory:

```bash
# Required: Your LLM provider API key
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Choose provider (default: openai)
# DOCKAI_LLM_PROVIDER=openai

# Optional: Maximum retry attempts (default: 3)
# MAX_RETRIES=3
```

### Step 2: Verify Docker is Running

```bash
docker info
```

If Docker is not running, start it before using DockAI.

## Your First Run

Navigate to any project directory and run:

```bash
dockai build .
```

### Example Output

```
╭──────────────────────────────────────────────────────────────────╮
│                           DockAI                                  │
│        The Customizable AI Dockerfile Generation Framework        │
╰──────────────────────────────────────────────────────────────────╯

INFO     Scanning directory: /path/to/project
INFO     Found 42 files to analyze
INFO     Analyzing repository needs...
INFO     Reading 5 critical files...
INFO     Detecting health endpoints...
INFO     Creating strategic plan...
INFO     Generating Dockerfile...
INFO     Reviewing for security issues...
INFO     Validating Dockerfile (build & run)...

✅ Success! Dockerfile validated successfully.
Final Dockerfile saved to /path/to/project/Dockerfile

╭─────────────────── 📊 Usage Summary ────────────────────╮
│ Total Tokens: 4,523                                     │
│                                                         │
│ Breakdown by Stage:                                     │
│   • analyzer: 892 tokens                                │
│   • planner: 756 tokens                                 │
│   • generator: 1,234 tokens                             │
│   • reviewer: 645 tokens                                │
│   • validator: 996 tokens                               │
╰─────────────────────────────────────────────────────────╯
```

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Enable detailed debug logging |
| `--help` | `-h` | Show help message |

### Verbose Mode

For debugging or understanding the AI's reasoning:

```bash
dockai build . --verbose
```

## Next Steps

- **[Configuration](./configuration.md)** — Learn about all configuration options
- **[Customization](./customization.md)** — Fine-tune DockAI for your stack
- **[Architecture](./architecture.md)** — Understand how DockAI works
- **[GitHub Actions](./github-actions.md)** — Set up CI/CD integration

## Troubleshooting

### "OPENAI_API_KEY not found"

Ensure your `.env` file exists and contains your API key:

```bash
echo "OPENAI_API_KEY=sk-your-key" > .env
```

### "Docker build failed"

1. Verify Docker is running: `docker info`
2. Check the error message for specific issues
3. Try running with `--verbose` for more details

### Rate Limit Errors

DockAI handles rate limits automatically with exponential backoff. If you see persistent rate limit errors:

1. Wait a few minutes and try again
2. Consider upgrading your API tier
3. Reduce `MAX_RETRIES` to limit API calls

### Need More Help?

- Check the [FAQ](./faq.md) for common questions
- Open an issue on [GitHub](https://github.com/itzzjb/dockai/issues)
