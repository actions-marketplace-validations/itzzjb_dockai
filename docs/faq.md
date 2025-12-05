# Frequently Asked Questions

This FAQ addresses common questions about DockAI, from basic usage to advanced topics. If your question isn't answered here, check the other documentation or open an issue on GitHub.

---

## 📋 Table of Contents

1. [General Questions](#general-questions)
2. [Costs and Pricing](#costs-and-pricing)
3. [Security](#security)
4. [LLM Providers](#llm-providers)
5. [Dockerfile Quality](#dockerfile-quality)
6. [Performance](#performance)
7. [Customization](#customization)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)

---

## General Questions

### What is DockAI?

DockAI is an AI-powered tool that generates optimized Dockerfiles by analyzing your project's source code. Unlike template-based tools, DockAI uses multi-agent AI to understand your specific codebase and create Dockerfiles tailored to your exact requirements.

### How is DockAI different from other Dockerfile generators?

| Feature | Template-Based Tools | DockAI |
|---------|---------------------|--------|
| Analysis | Pattern matching | Deep code analysis |
| Output | Generic templates | Project-specific |
| Adaptation | Manual adjustment | AI-driven |
| Learning | Static rules | Uses latest LLM knowledge |
| Self-correction | None | Multi-iteration refinement |

### What projects does DockAI support?

DockAI supports **any** project type because it uses AI analysis rather than predefined templates. However, it works best with:

- **Well-supported**: Python, Node.js, Go, Java, Rust
- **Supported**: Ruby, PHP, .NET, C/C++
- **Any language**: AI will analyze and adapt

### Do I need Docker installed?

Yes, DockAI requires Docker for:
1. **Validation**: Building the generated Dockerfile to verify it works
2. **Security scanning**: Running Trivy to check for vulnerabilities
3. **Ollama provider**: Running local LLMs in containers

You can set `DOCKAI_SKIP_HEALTH_CHECK=true` to skip health check validation, but this is not recommended.

### What are the system requirements?

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11+ |
| Docker | 20.10+ | Latest |
| RAM | 4GB | 8GB+ |
| Network | Required | Stable connection |

---

## Costs and Pricing

### Is DockAI free to use?

**DockAI itself is completely free and open source.** However, you pay for LLM API usage based on your provider:

| Provider | Cost Model | Typical Cost per Dockerfile |
|----------|------------|----------------------------|
| OpenAI | Pay-per-token | $0.01 - $0.10 |
| Azure OpenAI | Pay-per-token | Similar to OpenAI |
| Google Gemini | Free tier available | Free - $0.05 |
| Anthropic | Pay-per-token | $0.01 - $0.15 |
| Ollama | Free (local) | $0 (just compute) |

### How can I minimize API costs?

1. **Use cheaper models for simple tasks** (via environment variables):
   ```bash
   DOCKAI_MODEL_ANALYZER=gpt-4o-mini \
   DOCKAI_MODEL_GENERATOR=gpt-4o \
   dockai build .
   ```

2. **Use Gemini's free tier** for development:
   ```bash
   DOCKAI_LLM_PROVIDER=gemini dockai build .
   ```

3. **Use Ollama** for unlimited free usage:
   ```bash
   DOCKAI_LLM_PROVIDER=ollama dockai build .
   ```

4. **Limit retries** to control iterations:
   ```bash
   MAX_RETRIES=2 dockai build .
   ```

### What's the estimated token usage?

| Agent | Typical Input Tokens | Output Tokens |
|-------|---------------------|---------------|
| Analyzer | 2,000-10,000 | 500-2,000 |
| Blueprint | 1,000-3,000 | 500-1,500 |
| Generator | 2,000-5,000 | 500-2,000 |
| Reviewer | 1,000-3,000 | 500-1,500 |

**Total per run**: ~10,000-30,000 tokens (varies with project size)

---

## Security

### Is my code sent to external servers?

**Yes**, portions of your code are sent to LLM providers for analysis. Specifically:
- File names and structure
- Package manifests (package.json, requirements.txt)
- Relevant source code snippets
- Configuration files

**Mitigation options**:
1. Use **Ollama** for completely local processing
2. Use **Azure OpenAI** with your organization's data controls
3. Review what's sent with `--verbose` flag
4. Add sensitive files to `.dockerignore`

### What security scanning does DockAI perform?

1. **Hadolint**: Dockerfile best practice linting
2. **Trivy**: Container vulnerability scanning
   - Scans for CVEs in base images
   - Scans for vulnerable packages
   - Configurable severity thresholds

### How do I enforce security in CI/CD?

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    strict_security: 'true'  # Fail on ANY vulnerability
```

### Does DockAI expose secrets?

DockAI is designed to **never** include secrets in Dockerfiles:
- The AI is instructed to use build args or environment variables
- Security reviewer checks for hardcoded credentials
- You should always review generated Dockerfiles

---

## LLM Providers

### Which LLM provider should I choose?

| Provider | Best For | Pros | Cons |
|----------|----------|------|------|
| **OpenAI** | General use | High quality, reliable | Costs money |
| **Azure OpenAI** | Enterprise | Compliance, SLAs | Setup complexity |
| **Gemini** | Budget-conscious | Free tier | Quality varies |
| **Anthropic** | Complex projects | Great reasoning | More expensive |
| **Ollama** | Privacy-focused | Free, local | Requires GPU |

### Can I use different models for different agents?

Yes! This is recommended for cost optimization (via environment variables):

```bash
DOCKAI_MODEL_ANALYZER=gpt-4o-mini \
DOCKAI_MODEL_GENERATOR=gpt-4o \
DOCKAI_MODEL_REVIEWER=gpt-4o-mini \
dockai build .
```

### What Ollama models work best?

| Model | VRAM Required | Quality | Speed |
|-------|--------------|---------|-------|
| llama3.2:3b | 4GB | Good | Fast |
| llama3.1:8b | 8GB | Better | Medium |
| codellama:13b | 16GB | Best for code | Slow |
| deepseek-coder:6.7b | 8GB | Good for code | Medium |

### How do I set up Ollama?

```bash
# Install Ollama
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# Use with DockAI
DOCKAI_LLM_PROVIDER=ollama dockai build .
```

If Ollama isn't installed, DockAI will automatically run it in Docker.

---

## Dockerfile Quality

### How good are the generated Dockerfiles?

DockAI generates **production-quality** Dockerfiles that follow best practices:

- ✅ Multi-stage builds when beneficial
- ✅ Proper layer caching
- ✅ Non-root users
- ✅ Health checks
- ✅ Security scanning
- ✅ Optimized image size

### Why didn't DockAI use multi-stage builds?

Multi-stage builds aren't always necessary. DockAI decides based on:
- Project type (compiled vs interpreted)
- Build complexity
- Image size considerations

For simple Python scripts, single-stage is often better.

To force multi-stage:
```bash
DOCKAI_GENERATOR_INSTRUCTIONS="Always use multi-stage builds" dockai build .
```

### Why is my image still large?

Image size depends on:
1. **Base image**: Alpine is smaller than Debian
2. **Dependencies**: Some packages are large
3. **Assets**: Static files, data, etc.

Solutions:
```bash
DOCKAI_GENERATOR_INSTRUCTIONS="Minimize image size. Use Alpine. Remove unnecessary files." dockai build .
```

### Can DockAI generate docker-compose.yml?

Currently, DockAI focuses on **Dockerfile generation only**. Docker Compose support may be added in future versions.

---

## Performance

### How long does generation take?

| Step | Typical Time |
|------|--------------|
| Project analysis | 5-15 seconds |
| Dockerfile generation | 10-30 seconds |
| Build validation | 30-300 seconds |
| Security scanning | 10-60 seconds |
| **Total** | **1-6 minutes** |

### Why is it slow?

Most time is spent on:
1. **LLM API calls**: Network latency + inference time
2. **Docker build**: Downloading base images, building
3. **Security scan**: Vulnerability database lookup

To speed up:
```bash
# Skip health check validation
DOCKAI_SKIP_HEALTH_CHECK=true dockai build .

# Skip security scan
DOCKAI_SKIP_SECURITY_SCAN=true dockai build .

# Use faster models (via environment variable)
DOCKAI_MODEL_ANALYZER=gpt-4o-mini dockai build .
```

### Does DockAI cache anything?

Currently, DockAI doesn't cache between runs. Each run:
- Re-analyzes the project
- Makes fresh LLM calls
- Rebuilds the Docker image

Docker itself caches layers, so rebuilds are faster.

---

## Customization

### How do I add organization standards?

Use custom instructions (via environment variable or `.dockai` file):

```bash
DOCKAI_GENERATOR_INSTRUCTIONS="
ORGANIZATION REQUIREMENTS:
- Use company-registry.io base images only
- Run as UID 10000
- Include standard labels
- Follow security policy v2.1
" dockai build .
```

### Can I modify the prompts?

Yes, for complete control use environment variables:

```bash
# Replace the analyzer prompt entirely
DOCKAI_PROMPT_ANALYZER="Your custom prompt here" dockai build .
```

See [Customization Guide](./customization.md) for details.

### How do I handle monorepos?

Specify the service path:

```bash
dockai build ./services/api
dockai build ./services/worker
```

### Can I generate Dockerfiles for multiple services?

Run DockAI for each service:

```bash
for service in api worker frontend; do
  dockai build ./services/$service
done
```

---

## CI/CD Integration

### How do I use DockAI in GitHub Actions?

```yaml
- uses: itzzjb/dockai@v3
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

See [GitHub Actions Guide](./github-actions.md) for detailed examples.

### Should I commit the generated Dockerfile?

| Approach | Pros | Cons |
|----------|------|------|
| **Commit** | Version control, code review, offline builds | May get stale |
| **Generate at build** | Always fresh, no maintenance | Requires API access |

Recommendation: **Commit for production**, generate in CI for validation.

### How do I integrate with GitLab CI?

```yaml
build:
  image: python:3.11
  services:
    - docker:dind
  script:
    - pip install dockai-cli
    - dockai build .
  variables:
    OPENAI_API_KEY: $OPENAI_API_KEY
    DOCKER_HOST: tcp://docker:2375
```

### Can I use DockAI with Jenkins?

```groovy
pipeline {
  agent any
  environment {
    OPENAI_API_KEY = credentials('openai-api-key')
  }
  stages {
    stage('Generate Dockerfile') {
      steps {
        sh 'pip install dockai-cli'
        sh 'dockai build .'
      }
    }
  }
}
```

---

## Troubleshooting

### "API key not found"

**Cause**: Environment variable not set or incorrect name.

**Solution**:
```bash
# Check if set
echo $OPENAI_API_KEY

# Set it
export OPENAI_API_KEY=sk-your-key

# Then run
dockai build .
```

### "Docker build failed"

**Common causes**:
1. **Network issues**: Can't download base image
2. **Missing dependencies**: Project needs additional packages
3. **Permission issues**: Running as wrong user

**Solutions**:
```bash
# Check Docker is running
docker ps

# Try with more retries (via environment variable)
MAX_RETRIES=5 dockai build .

# Add debugging instructions (via environment variable)
DOCKAI_GENERATOR_INSTRUCTIONS="Add verbose output during build" dockai build .
```

### "Rate limit exceeded"

**Cause**: Too many API requests in short time.

**Solutions**:
1. Wait and retry
2. Use different API key
3. Use local provider (Ollama)
4. Reduce `MAX_RETRIES` environment variable

### "Out of memory"

**Cause**: Docker build using too much memory.

**Solutions**:
```bash
# Increase validation memory limit (via environment variable)
DOCKAI_VALIDATION_MEMORY=2g dockai build .

# Or skip health check
DOCKAI_SKIP_HEALTH_CHECK=true dockai build .
```

### "Hadolint/Trivy not found"

**Cause**: Tools not installed.

**Solution**: DockAI uses Docker-based versions automatically. Ensure Docker is running:
```bash
docker ps
```

### "Permission denied" errors

**Solutions**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or
newgrp docker
```

---

## Contributing

### How can I contribute to DockAI?

1. **Report bugs**: Open GitHub issues
2. **Suggest features**: Discuss in issues first
3. **Submit PRs**: Follow contribution guidelines
4. **Improve docs**: Documentation PRs welcome
5. **Share**: Tell others about DockAI

### Where's the source code?

GitHub: https://github.com/itzzjb/dockai

### What's the license?

DockAI is licensed under the **MIT License** - use it freely in personal and commercial projects.

### How do I report a security vulnerability?

Please report security issues privately via GitHub Security Advisory, not public issues.

---

## Still Have Questions?

- **Documentation**: Check other guides in this documentation
- **GitHub Issues**: https://github.com/itzzjb/dockai/issues
- **Discussions**: https://github.com/itzzjb/dockai/discussions

---

## Quick Links

- [Getting Started](./getting-started.md)
- [Configuration Reference](./configuration.md)
- [Architecture Deep Dive](./architecture.md)
- [Customization Guide](./customization.md)
- [GitHub Actions](./github-actions.md)
- [MCP Server](./mcp-server.md)
