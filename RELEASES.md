# Release Process

This document contains all the commands needed for releasing new versions of DockAI.

## 📋 Release Checklist

Before creating a new release:

- [ ] All tests pass (`pytest`)
- [ ] Documentation is updated
- [ ] `pyproject.toml` version is bumped
- [ ] `CHANGELOG.md` is updated (if exists)
- [ ] All changes are committed and pushed

---

## 🏷️ Creating a New Release Tag

### 1. Create a Specific Version Tag (e.g., v3.1.0)

```bash
# Create an annotated tag with a message
git tag -a v3.1.0 -m "Release v3.1.0"

# Or create a lightweight tag
git tag v3.1.0
```

### 2. Push the Specific Version Tag

```bash
# Push the specific version tag to remote
git push origin v3.1.0
```

---

## 🔄 Updating Major Version Alias

After releasing a new version, update the major version alias (e.g., `v3`) to point to the latest version.

### 1. Create/Update the Major Version Alias Tag

```bash
# Force create/update the v3 tag to point to current HEAD
git tag -f v3

# Or point it to a specific tag
git tag -f v3 v3.1.0
```

### 2. Push the Major Version Alias Tag

```bash
# Force push the major version alias (overwrites existing remote tag)
git push origin v3 -f
```

---

## 🚀 Complete Release Workflow

### Example: Releasing v3.1.0

```bash
# 1. Ensure you're on the main branch with latest changes
git checkout main
git pull origin main

# 2. Update version in pyproject.toml (manually or with script)
# Edit pyproject.toml: version = "3.1.0"

# 3. Commit version bump
git add pyproject.toml
git commit -m "Bump version to 3.1.0"
git push origin main

# 4. Create the specific version tag
git tag -a v3.1.0 -m "Release v3.1.0"

# 5. Push the specific version tag
git push origin v3.1.0

# 6. Update the major version alias
git tag -f v3

# 7. Push the major version alias
git push origin v3 -f
```

---

## 📦 Release Types

### Patch Release (v3.0.1)

Bug fixes and minor updates. No breaking changes.

```bash
# Update version to 3.0.1 in pyproject.toml
git tag -a v3.0.1 -m "Release v3.0.1 - Bug fixes"
git push origin v3.0.1
git tag -f v3
git push origin v3 -f
```

### Minor Release (v3.1.0)

New features, no breaking changes.

```bash
# Update version to 3.1.0 in pyproject.toml
git tag -a v3.1.0 -m "Release v3.1.0 - New features"
git push origin v3.1.0
git tag -f v3
git push origin v3 -f
```

### Major Release (v4.0.0)

Breaking changes, major updates.

```bash
# Update version to 4.0.0 in pyproject.toml
git tag -a v4.0.0 -m "Release v4.0.0 - Major update"
git push origin v4.0.0

# Create new major version alias
git tag -f v4
git push origin v4 -f

# Keep v3 pointing to latest v3.x.x for users still on v3
```

---

## 🔍 Useful Git Tag Commands

### List All Tags

```bash
# List all tags
git tag -l

# List tags matching a pattern
git tag -l "v3*"
```

### View Tag Details

```bash
# Show tag information
git show v3.1.0

# Show what commit a tag points to
git rev-list -n 1 v3
```

### Delete a Tag

```bash
# Delete local tag
git tag -d v3.1.0

# Delete remote tag
git push origin --delete v3.1.0
```

### Move a Tag to a Different Commit

```bash
# Delete the old tag locally
git tag -d v3

# Create the tag at a specific commit
git tag v3 <commit-hash>

# Force push to update remote
git push origin v3 -f
```

---

## 🎯 Quick Reference

| Action | Command |
|--------|---------|
| Create version tag | `git tag -a v3.1.0 -m "Release v3.1.0"` |
| Push version tag | `git push origin v3.1.0` |
| Update major alias | `git tag -f v3` |
| Push major alias | `git push origin v3 -f` |
| List all tags | `git tag -l` |
| Delete local tag | `git tag -d v3.1.0` |
| Delete remote tag | `git push origin --delete v3.1.0` |

---

## 📝 Notes

- **Lightweight vs Annotated Tags**: Use annotated tags (`-a`) for releases as they include metadata (author, date, message)
- **Force Push**: The `-f` flag is needed when updating existing tags (like major version aliases)
- **Semantic Versioning**: Follow [SemVer](https://semver.org/) - `MAJOR.MINOR.PATCH`
  - **MAJOR**: Breaking changes
  - **MINOR**: New features, backward compatible
  - **PATCH**: Bug fixes, backward compatible
- **GitHub Actions**: Users referencing `itzzjb/dockai@v3` will automatically get the latest v3.x.x version when you update the `v3` tag

---

## 🔗 Related Files

- `pyproject.toml` - Version number
- `README.md` - Documentation and examples
- `action.yml` - GitHub Action configuration
- `.github/workflows/` - CI/CD workflows

