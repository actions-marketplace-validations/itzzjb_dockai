# Frequently Asked Questions

Common questions about DockAI and their answers.

---

## General Questions

### What makes DockAI different from other Dockerfile generators?

DockAI uses **first-principles reasoning** instead of templates. It:

- Analyzes file structures, dependencies, and code patterns
- Deduces the optimal containerization strategy
- Has a **self-correcting workflow** that learns from failures
- Can be **fully customized** for your technology stack

### Does DockAI replace DevOps engineers?

**No.** DockAI is designed to **augment** your team, not replace it. It provides intelligent defaults that work for many projects, but the real value comes when DevOps engineers customize it with organizational knowledge—approved base images, security policies, and lessons learned.

### Which AI models does DockAI support?

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini |
| **Azure OpenAI** | GPT-4o, GPT-4o-mini |
| **Google Gemini** | Gemini 1.5 Pro, Gemini 1.5 Flash |
| **Anthropic** | Claude Sonnet 4, Claude 3.5 Haiku |

Different models can be assigned to different agents for cost optimization.

### How much does it cost to run?

Token usage varies by project complexity:

| Project Size | Tokens Used | Estimated Cost (GPT-4o) |
|-------------|-------------|------------------------|
| Small | 5,000-10,000 | ~$0.05-0.10 |
| Medium | 15,000-30,000 | ~$0.15-0.30 |
| Complex (with retries) | 50,000+ | ~$0.50+ |

DockAI reports token usage after each run. Well-customized instances typically use fewer tokens due to fewer retries.

---

## Technical Questions

### Can I use DockAI with private registries?

Yes! DockAI supports:

- **Docker Hub** (default)
- **Google Container Registry** (GCR)
- **Quay.io**
- **AWS ECR** (limited—skips tag verification)

Custom registries can be configured via instructions to the Planner agent.

### What if my project has unusual requirements?

Use custom instructions to guide the AI:

```bash
export DOCKAI_GENERATOR_INSTRUCTIONS="This project requires libmagic and poppler-utils at runtime"
dockai build .
```

Or create a `.dockai` file with specific guidance:

```ini
[instructions_generator]
This project requires libmagic and poppler-utils at runtime.
The entrypoint script is in /scripts/start.sh
```

### Does it work offline?

**No.** DockAI requires internet access to:

1. Call LLM APIs for AI reasoning
2. Verify Docker image tags against registries
3. (Optionally) Run Trivy security scans

### How do I skip security scanning?

```bash
export DOCKAI_SKIP_SECURITY_SCAN=true
dockai build .
```

Or in GitHub Actions:

```yaml
- uses: itzzjb/dockai@v2
  with:
    skip_security_scan: 'true'
```

### Can I see what prompts DockAI is using?

Run with the `--verbose` flag:

```bash
dockai build . --verbose
```

This shows detailed logs including prompts and AI responses.

### What languages/frameworks are supported?

DockAI uses first-principles reasoning, so it can handle any language or framework. It has been tested with:

- **Python**: Django, Flask, FastAPI, Celery
- **Node.js**: Express, Next.js, NestJS, React
- **Go**: Standard library, Gin, Echo
- **Java**: Spring Boot, Maven, Gradle
- **Ruby**: Rails, Sinatra
- **Rust**: Cargo-based projects
- **PHP**: Laravel, Symfony

Even legacy or custom frameworks can be containerized—just provide guidance via custom instructions.

---

## Customization Questions

### Why should I customize DockAI?

| Scenario | Default | Customized |
|----------|---------|------------|
| Base images | Public defaults | Your approved images |
| Security | Generic practices | Your compliance requirements |
| Success rate | ~60% first attempt | ~85%+ first attempt |

### How long does customization take?

Customization is progressive:

| Timeline | Activity |
|----------|----------|
| **Day 1** | Add basic instructions for approved base images |
| **Week 1** | Add common error fixes you've encountered |
| **Month 1** | Repository-specific `.dockai` files |
| **Ongoing** | Continuous refinement |

### Can I use DockAI with custom/proprietary frameworks?

Absolutely! Teach DockAI about your internal frameworks:

```ini
[instructions_analyzer]
We use "InternalFramework v3" which requires:
- Python 3.11 with our custom runtime
- Environment variable INTERNAL_CONFIG_PATH
- Connection to internal package registry

[instructions_generator]
For InternalFramework projects:
- Use our base image: company-registry.io/internal-python:3.11
- Set INTERNAL_CONFIG_PATH=/app/config
- Run framework init command before start
```

---

## Platform Integration

### Can I embed DockAI into my platform?

**Yes!** DockAI is designed for platform integration. See the [Platform Integration Guide](./platform-integration.md) for:

- Building a DockAI API service
- Integrating with Backstage, Port, Choreo
- Multi-tenant configuration
- Webhook handling

### Is DockAI suitable for multi-tenant platforms?

Yes! The layered configuration system supports:

- **Platform-level defaults**: Security policies, approved images
- **Team-level overrides**: Team-specific registries or conventions
- **Repository-level customization**: `.dockai` file per project

### How do I share customizations across teams?

1. **Version control `.dockai` files** with your code
2. **Use organization-level GitHub Actions variables** for company-wide settings
3. **Create `.dockai` templates** for common project types
4. **Document learnings** in your customization instructions

---

## Troubleshooting

### "OPENAI_API_KEY not found"

Ensure your `.env` file exists and contains your API key:

```bash
echo "OPENAI_API_KEY=sk-your-key" > .env
```

Or set the environment variable directly:

```bash
export OPENAI_API_KEY=sk-your-key
```

### "Docker not running"

Start Docker before running DockAI:

```bash
# macOS/Windows
# Open Docker Desktop

# Linux
sudo systemctl start docker
```

### "Build failed after max retries"

This usually means the project has unusual requirements. Try:

1. **Increase retries**:
   ```bash
   export MAX_RETRIES=5
   ```

2. **Add custom instructions**:
   ```bash
   export DOCKAI_GENERATOR_INSTRUCTIONS="This project requires specific runtime dependencies"
   ```

3. **Check the error output** for clues and add them to reflector instructions:
   ```ini
   [instructions_reflector]
   Known issue: This project requires xyz package
   ```

### "Rate limit exceeded"

DockAI has built-in rate limiting with exponential backoff. If you're hitting limits:

1. **Use a paid API tier** with higher limits
2. **Reduce model usage** by using faster models for simple agents
3. **Cache results** when possible

### "Trivy scan failed"

If Trivy isn't installed, DockAI falls back to the Docker image:

```bash
# Pull the Trivy image
docker pull aquasec/trivy

# Or skip security scanning
export DOCKAI_SKIP_SECURITY_SCAN=true
```

### "Memory limit exceeded during validation"

Increase validation resources:

```bash
export DOCKAI_VALIDATION_MEMORY=1g
export DOCKAI_VALIDATION_CPUS=2.0
```

---

## Security Questions

### Is my code sent to the AI?

Yes, portions of your code are sent to the LLM for analysis. Specifically:

- File paths and names
- Contents of critical files (dependencies, configs, main entry points)
- Build and run logs during validation

If you have sensitive code, consider:

- Using Azure OpenAI with data privacy agreements
- Self-hosting an LLM (not currently supported, but planned)
- Using `.gitignore` to exclude sensitive files from analysis

### How does DockAI handle secrets?

DockAI's security reviewer explicitly checks for:

- Hardcoded API keys
- Passwords in Dockerfiles
- Credentials in environment variables

It will flag these as security issues and suggest fixes.

### Is DockAI SOC 2 / HIPAA compliant?

DockAI itself is a tool—compliance depends on how you configure and deploy it:

- **Use enterprise LLM providers** (Azure OpenAI) with compliance certifications
- **Enable strict security mode** to fail on vulnerabilities
- **Customize the reviewer** with your compliance requirements

---

## Performance Questions

### How long does a typical run take?

| Scenario | Time |
|----------|------|
| Simple project, first attempt success | 30-60 seconds |
| Medium project, 1-2 retries | 1-3 minutes |
| Complex project, multiple retries | 3-10 minutes |

### How can I speed up DockAI?

1. **Use faster models** for simple agents (analyzer, reviewer)
2. **Skip security scanning** if not needed
3. **Add custom instructions** to reduce retries
4. **Pre-warm Docker images** for common base images

### How can I reduce costs?

1. **Use `gpt-4o-mini`** or equivalent for fast agents
2. **Add custom instructions** to reduce retries
3. **Cache analysis results** for similar projects
4. **Skip security scanning** in development

---

## Next Steps

- **[Getting Started](./getting-started.md)**: Installation and first run
- **[Configuration](./configuration.md)**: All configuration options
- **[Customization](./customization.md)**: Fine-tune for your stack

---

## 📚 References

- **[Getting Started](./getting-started.md)**: Installation guide
- **[Configuration](./configuration.md)**: Full configuration reference
- **[GitHub Actions](./github-actions.md)**: CI/CD setup

