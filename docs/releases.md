# Releases

This document describes DockAI's release process, versioning strategy, and how to create new releases. It also serves as a changelog for significant versions.

---

## 📋 Table of Contents

1. [Versioning Strategy](#versioning-strategy)
2. [Release Types](#release-types)
3. [Creating a Release](#creating-a-release)
4. [Release Checklist](#release-checklist)
5. [Changelog](#changelog)

---

## Versioning Strategy

DockAI follows **Semantic Versioning (SemVer)** with the format `MAJOR.MINOR.PATCH`:

| Component | When to Increment | Example |
|-----------|-------------------|---------|
| **MAJOR** | Breaking changes to CLI, API, or workflows | 2.0.0 → 3.0.0 |
| **MINOR** | New features, backward-compatible | 3.0.0 → 3.1.0 |
| **PATCH** | Bug fixes, documentation updates | 3.1.0 → 3.1.1 |

### Version Tags

DockAI uses two types of Git tags:

| Tag Type | Example | Purpose |
|----------|---------|---------|
| Full version | `v3.1.0` | Point to specific release |
| Major version | `v3` | Always points to latest 3.x |

The major version tag (e.g., `v3`) is updated with each release to always point to the latest stable version in that major line. This allows GitHub Actions users to pin to `@v3` and get automatic updates.

### Where Version is Stored

Version must be updated in two files:

1. **`pyproject.toml`**: Package version for PyPI
   ```toml
   [project]
   version = "3.1.0"
   ```

2. **`src/dockai/__init__.py`**: Runtime version
   ```python
   __version__ = "3.1.0"
   ```

---

## Release Types

### Major Releases (X.0.0)

**Trigger**: Breaking changes that require user action

Examples of breaking changes:
- CLI argument changes
- Configuration file format changes
- Removed features
- Changed default behavior

**Process**:
1. Create migration guide in documentation
2. Announce in release notes
3. Update all documentation
4. Consider deprecation period

### Minor Releases (X.Y.0)

**Trigger**: New features, improvements, non-breaking changes

Examples:
- New LLM provider support
- New CLI options
- New agents or workflow improvements
- Performance improvements

**Process**:
1. Update documentation for new features
2. Add to changelog
3. Update version numbers

### Patch Releases (X.Y.Z)

**Trigger**: Bug fixes, security patches, documentation updates

Examples:
- Fix API compatibility issues
- Security vulnerability patches
- Typo corrections
- Dependency updates

**Process**:
1. Minimal changes
2. Focus on stability
3. Quick turnaround

---

## Creating a Release

### Step 1: Update Version Numbers

Update version in both files:

**`pyproject.toml`**:
```toml
[project]
name = "dockai-cli"
version = "3.2.0"  # Update this
```

**`src/dockai/__init__.py`**:
```python
__version__ = "3.2.0"  # Update this
```

### Step 2: Update Changelog

Add release notes to this file (see format below).

### Step 3: Commit Changes

```bash
git add pyproject.toml src/dockai/__init__.py docs/releases.md
git commit -m "chore: bump version to 3.2.0"
```

### Step 4: Create Tags

```bash
# Create full version tag
git tag v3.2.0

# Update major version tag (force move)
git tag -f v3
```

### Step 5: Push Everything

```bash
git push origin main
git push origin v3.2.0
git push origin v3 --force
```

### Step 6: Create GitHub Release

1. Go to GitHub → Releases → "Create a new release"
2. Choose tag: `v3.2.0`
3. Title: `v3.2.0`
4. Copy changelog entry to description
5. Publish release

### Step 7: Verify PyPI Release

If CI is configured to publish to PyPI:
```bash
pip install dockai-cli==3.2.0
dockai --version
```

---

## Release Checklist

Use this checklist for every release:

### Pre-Release

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version numbers updated in both files
- [ ] Breaking changes documented (if any)
- [ ] Migration guide written (for major releases)

### Release

- [ ] Changes committed
- [ ] Full version tag created (e.g., `v3.2.0`)
- [ ] Major version tag updated (e.g., `v3`)
- [ ] Changes pushed to main
- [ ] Tags pushed to origin
- [ ] GitHub Release created
- [ ] PyPI package updated (if applicable)

### Post-Release

- [ ] Verify PyPI installation works
- [ ] Verify Docker image builds
- [ ] Verify GitHub Action works with new tag
- [ ] Announce release (if significant)

---

## Changelog

### v3.1.5 (2025-12-05)

**Fixes**:
- Documentation consistency improvements
- Fixed CLI flag references in FAQ to use environment variables
- Updated agent counts in CLI help text
- Fixed token usage breakdowns in documentation

**Documentation**:
- Ensured all version references are synchronized
- Corrected node counts and deprecated terminology

### v3.1.4 (2025-12-04)

**Fixes**:
- Minor bug fixes and stability improvements

### v3.1.3 (2025-12-03)

**Fixes**:
- Bug fixes for LangSmith observability integration
- Improved GitHub Actions workflow

### v3.1.2 (2025-12-03)

**Features**:
- Added LangSmith observability support in GitHub Actions

**Fixes**:
- Version synchronization improvements

### v3.1.1 (2025-12-XX)

**Fixes**:
- Minor stability improvements
- Documentation updates

### v3.1.0 (2024-XX-XX)

**Features**:
- Comprehensive documentation enhancement
- Improved explanation of architecture and design decisions
- Better getting started guide with detailed workflow explanation

**Documentation**:
- Complete rewrite of all documentation files
- Added design rationale throughout
- Added troubleshooting sections
- Added example configurations

### v3.0.0 (2024-XX-XX)

**Breaking Changes**:
- Renamed CLI entry point
- Updated configuration file format
- Changed default models for some agents

**Features**:
- LangGraph-based multi-agent architecture
- 10 specialized AI agents
- Self-correcting workflow with reflection loop
- Support for 5 LLM providers (OpenAI, Azure, Gemini, Anthropic, Ollama)
- MCP server for AI assistant integration
- OpenTelemetry tracing support
- Enhanced security scanning with Trivy
- Dockerfile linting with Hadolint

**Improvements**:
- Better error messages
- Improved retry logic
- Enhanced project scanning
- Rate limiting for API calls

### v2.x.x

Legacy versions. See GitHub releases for historical changelog.

---

## Release Notes Template

Use this template for GitHub releases:

```markdown
## What's Changed

### Features
- Feature 1 description
- Feature 2 description

### Bug Fixes
- Fix for issue #123
- Fix for issue #456

### Documentation
- Updated getting started guide
- Added FAQ section

### Breaking Changes
- Change 1 (migration: do X)
- Change 2 (migration: do Y)

## Upgrade Guide

### From v3.0.x to v3.1.0

No breaking changes. Simply update:

```bash
pip install --upgrade dockai-cli
```

### From v2.x to v3.0

See [Migration Guide](./docs/migration.md)

## Full Changelog

https://github.com/itzzjb/dockai/compare/v3.0.0...v3.1.0
```

---

## Git Commands Reference

### View All Tags

```bash
git tag -l
```

### Delete Local Tag

```bash
git tag -d v3.1.0
```

### Delete Remote Tag

```bash
git push origin --delete v3.1.0
```

### Move Tag to Different Commit

```bash
git tag -f v3 <commit-hash>
git push origin v3 --force
```

### View Tag Details

```bash
git show v3.1.0
```

---

## PyPI Publishing

### Manual Publishing

```bash
# Build
python -m build

# Upload to PyPI
twine upload dist/*
```

### CI/CD Publishing

Configure GitHub Actions to publish on tag push:

```yaml
on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: pip install build twine
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

---

## Docker Image Publishing

Docker images are published to GitHub Container Registry (GHCR):

```yaml
on:
  push:
    tags:
      - 'v*'

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/itzzjb/dockai:${{ github.ref_name }}
            ghcr.io/itzzjb/dockai:latest
```

---

## Next Steps

- [Getting Started](./getting-started.md)
- [Architecture](./architecture.md)
- [Contributing Guidelines](https://github.com/itzzjb/dockai/blob/main/CONTRIBUTING.md)
