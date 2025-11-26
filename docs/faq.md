# Frequently Asked Questions

## General Questions

### What makes DockAI different from other Dockerfile generators?

DockAI uses **first-principles reasoning** instead of templates. It can containerize applications it has never seen before by analyzing file structures, build scripts, and runtime requirements. It also has a **self-correcting workflow** that learns from failures and can be **fully customized** for your specific technology stack.

### Does DockAI replace DevOps engineers?

**No.** DockAI is designed to **augment** your team, not replace it. It provides intelligent defaults that work for many projects, but the real value comes when DevOps engineers customize it with organizational knowledge—approved base images, security policies, common patterns, and lessons learned.

### Which AI models does DockAI use?

DockAI supports multiple LLM providers:
- **OpenAI**: GPT-4o, GPT-4o-mini (default)
- **Azure OpenAI**: Same models via Azure
- **Google Gemini**: Gemini 1.5 Pro, Gemini 1.5 Flash
- **Anthropic**: Claude Sonnet 4, Claude 3.5 Haiku

Different models can be assigned to different agents for cost optimization.

### How much does it cost to run?

Token usage varies by project complexity:

| Project Size | Tokens Used | Estimated Cost |
|-------------|-------------|----------------|
| Small | 5,000-10,000 | ~$0.01-0.03 |
| Medium | 15,000-30,000 | ~$0.05-0.15 |
| Complex (with retries) | 50,000+ | ~$0.20+ |

DockAI reports token usage after each run. Well-customized instances typically use fewer tokens due to fewer retries.

## Technical Questions

### Can I use DockAI with private registries?

Yes! DockAI supports:
- Docker Hub (default)
- Google Container Registry (GCR)
- Quay.io
- AWS ECR (limited - skips tag verification)

Custom registries can be configured via instructions to the Planner agent.

### What if my project has unusual requirements?

Use custom instructions to guide the AI:

```bash
export DOCKAI_GENERATOR_INSTRUCTIONS="This project requires libmagic and poppler-utils at runtime"
```

Or create a `.dockai` file with specific guidance.

### Does it work offline?

No. DockAI requires internet access to:
1. Call LLM APIs for AI reasoning
2. Verify Docker image tags against registries
3. (Optionally) Run Trivy security scans

### How do I skip security scanning?

```bash
export DOCKAI_SKIP_SECURITY_SCAN=true
```

Or in GitHub Actions:
```yaml
skip_security_scan: 'true'
```

### Can I see what prompts DockAI is using?

Run with the `--verbose` flag to see detailed logs including prompts:

```bash
dockai build . --verbose
```

## Customization Questions

### Why should I customize DockAI?

Default configuration works well for standard projects, but customization significantly improves results:

| Scenario | Default | Customized |
|----------|---------|------------|
| Base images | Public defaults | Your approved images |
| Security | Generic practices | Your compliance requirements |
| Success rate | ~60% first attempt | ~85%+ first attempt |

### How long does customization take?

Customization is progressive:
- **Day 1**: Add basic instructions for approved base images
- **Week 1**: Add common error fixes you've encountered
- **Month 1**: Repository-specific `.dockai` files
- **Ongoing**: Continuous refinement

### Can I use DockAI with custom/proprietary frameworks?

Absolutely! Teach DockAI about your internal frameworks:

```ini
[instructions_analyzer]
We use "InternalFramework v3" which requires:
- Python 3.11 with our custom runtime
- Environment variable INTERNAL_CONFIG_PATH
- Connection to internal package registry
```

## Platform Integration

### Can I embed DockAI into my platform?

**Yes!** DockAI is designed for platform integration. See the [Platform Integration Guide](./platform-integration.md) for:
- Building a DockAI API service
- Integrating with Choreo, SkyU, Backstage
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

## Troubleshooting

### "OPENAI_API_KEY not found"

Ensure your `.env` file exists and contains your API key:

```bash
echo "OPENAI_API_KEY=sk-your-key" > .env
```

### "Docker build failed"

1. Verify Docker is running: `docker info`
2. Check the error message for specific issues
3. Run with `--verbose` for more details
4. Check if it's a project issue vs Dockerfile issue

### Rate limit errors

DockAI handles rate limits automatically with exponential backoff. If errors persist:
1. Wait a few minutes and retry
2. Consider upgrading your API tier
3. Reduce `MAX_RETRIES` to limit API calls

### Security scan failures

If strict security is enabled and scans fail:
1. Review the vulnerability report
2. Either fix vulnerabilities or set `strict_security: 'false'`
3. Use approved base images that are regularly patched

### Container exits immediately

Common causes:
- Application daemonizing (should run in foreground)
- Missing environment variables
- Configuration file not found

Check logs with `docker logs <container>` or run with `--verbose`.

## Performance

### How can I speed up DockAI?

1. **Use faster models** for analysis:
   ```bash
   export DOCKAI_MODEL_ANALYZER=gpt-4o-mini
   ```

2. **Skip security scanning** during development:
   ```bash
   export DOCKAI_SKIP_SECURITY_SCAN=true
   ```

3. **Cache Docker layers** by organizing Dockerfile efficiently

4. **Pre-configure common patterns** to reduce retries

### How can I reduce API costs?

1. **Use cheaper models** for simple tasks (analyzer, reviewer)
2. **Customize instructions** to reduce retry attempts
3. **Skip validation** for trusted repositories
4. **Cache successful configurations** and reuse them

## Contributing

### How do I contribute to DockAI?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines. Development setup:

```bash
git clone https://github.com/itzzjb/dockai.git
cd dockai
pip install -e ".[test]"
pytest tests/
```

### Where do I report bugs?

Open an issue on [GitHub](https://github.com/itzzjb/dockai/issues) with:
- DockAI version
- Python version
- Error message and logs
- Steps to reproduce

### Can I request new features?

Yes! Open a GitHub issue with:
- Use case description
- Expected behavior
- Any relevant examples

## Getting Help

- **Documentation**: This docs directory
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and community support

---

Still have questions? [Open an issue](https://github.com/itzzjb/dockai/issues) on GitHub.
