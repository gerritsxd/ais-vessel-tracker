# Dependency Management

## Overview

All dependencies are **pinned to exact versions** for reproducibility and production stability. This ensures that the project works identically across all environments.

---

## Requirements Files

### 📦 `requirements.txt` (Full)
**Use this for:** Production deployment with all features

Contains all dependencies including:
- Core web framework (Flask, Socket.IO)
- Data processing (Pandas, NumPy)
- AI/ML features (Google Gemini)
- Web automation (Playwright)
- Testing tools (pytest)

```bash
pip install -r config/requirements.txt
```

**Size:** ~90 packages  
**Features:** All (vessel tracking + AI profiling + scraping + testing)

---

### 📦 `requirements-minimal.txt` (Core Only)
**Use this for:** Basic vessel tracking without optional features

Contains only essential dependencies:
- Flask web server
- Socket.IO for real-time updates
- WebSocket client for AIS data
- Pandas for data processing
- Basic HTTP/scraping tools

```bash
pip install -r config/requirements-minimal.txt
```

**Size:** ~40 packages  
**Features:** Vessel tracking + emissions data (no AI, no automation)

---

### 📦 `requirements-dev.txt` (Development)
**Use this for:** Local development with extra tooling

Contains production dependencies plus:
- Code formatters (black, isort)
- Static type checkers (mypy)
- Coverage tools (pytest-cov)
- Debugging tools (ipdb, ipython)
- Documentation generators

```bash
pip install -r config/requirements-dev.txt
```

**Size:** ~100 packages  
**Features:** Everything + dev tools

---

## Why Pin Dependencies?

### ✅ Benefits:

1. **Reproducibility** - Same versions everywhere (dev, staging, production)
2. **Stability** - Avoid breaking changes from automatic upgrades
3. **Security** - Know exactly what versions you're running
4. **Debugging** - Easier to isolate issues when versions are consistent
5. **Professionalism** - Shows production-ready mindset

### ❌ Without Pinning:

```python
# Bad: Floating dependencies
Flask>=3.0.0          # Could install 3.0.0 or 3.9.0 or 4.0.0
requests              # Could install ANY version
```

**Problems:**
- Different team members get different versions
- Production might have different versions than dev
- Upgrades can silently break things
- Hard to reproduce bugs

### ✅ With Pinning:

```python
# Good: Exact versions
Flask==3.1.2          # Always 3.1.2
requests==2.32.5      # Always 2.32.5
```

**Benefits:**
- Everyone runs identical code
- Upgrades are intentional, not accidental
- Easy to rollback if something breaks

---

## Dependency Categories

### Core Dependencies (Always Needed)

```
Flask                # Web framework
Flask-SocketIO       # Real-time updates
websocket-client     # AIS data streaming
pandas               # Data processing
requests             # HTTP requests
beautifulsoup4       # Web scraping
```

### Optional Dependencies (Feature-Specific)

```
google-generativeai  # AI company profiling (can skip)
playwright           # Browser automation (can skip)
googlesearch-python  # Google search API (can skip)
```

### Development Dependencies (Local Only)

```
pytest               # Testing
flake8               # Linting
black                # Code formatting
mypy                 # Type checking
```

---

## Installation Guide

### Fresh Environment (Recommended)

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r config/requirements.txt

# 4. Verify installation
pip list | grep Flask
# Should show: Flask==3.1.2
```

### Existing Environment (Upgrade)

```bash
# Update all packages to pinned versions
pip install -r config/requirements.txt --upgrade

# Force reinstall if needed
pip install -r config/requirements.txt --force-reinstall
```

### Docker (Production)

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY config/requirements.txt .

# Install pinned dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "src/services/web_tracker.py"]
```

---

## Updating Dependencies

### When to Update:

- 🔒 **Security patches** - Update immediately
- 🐛 **Critical bug fixes** - Update when needed
- ✨ **New features** - Update intentionally
- 📅 **Regular maintenance** - Every 3-6 months

### How to Update:

#### 1. Update Single Package

```bash
# Check current version
pip show Flask

# Update to specific version
pip install Flask==3.2.0

# Test everything still works
pytest

# Update requirements.txt
pip freeze | grep Flask
# Copy output to requirements.txt
```

#### 2. Update All Packages

```bash
# Export current state (backup)
pip freeze > config/requirements-freeze-backup.txt

# Update all to latest compatible versions
pip install -r config/requirements.txt --upgrade

# Export new state
pip freeze > config/requirements-freeze.txt

# Manually review and update requirements.txt
# Test thoroughly before committing!
```

#### 3. Check for Updates

```bash
# Show outdated packages
pip list --outdated

# Or use pip-review (install first)
pip install pip-review
pip-review --local --interactive
```

---

## Troubleshooting

### Problem: Dependency Conflicts

```bash
ERROR: Cannot install flask==3.1.2 and werkzeug==2.0.0
```

**Solution:** Check compatible versions
```bash
pip install Flask==3.1.2 --dry-run
# Shows what versions are compatible
```

### Problem: Missing System Dependencies

```bash
ERROR: Failed to build numpy
```

**Solution (Windows):**
```bash
# Install Visual C++ Build Tools
# Or use pre-built wheels
pip install --only-binary :all: numpy==2.3.3
```

**Solution (Linux):**
```bash
sudo apt-get install python3-dev build-essential
```

### Problem: Package Not Found

```bash
ERROR: Could not find a version that satisfies Flask==3.1.2
```

**Solution:** Check Python version compatibility
```bash
python --version  # Should be 3.13+
pip --version     # Should match Python version
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies (pinned)
        run: |
          pip install -r config/requirements.txt
      
      - name: Run tests
        run: pytest
```

**Benefits:**
- Same versions in CI as in production
- No random test failures from version changes
- Faster builds (can cache exact versions)

---

## Best Practices

### ✅ Do:

- Pin all direct dependencies
- Include transitive dependencies (indirect)
- Document why each package is needed
- Test after updating any version
- Keep requirements.txt in git
- Use virtual environments

### ❌ Don't:

- Use floating versions (`Flask>=3.0`)
- Use wildcards (`Flask==3.*`)
- Install packages without updating requirements.txt
- Mix pip and conda in same environment
- Commit virtual environment folders

---

## Version Pinning Examples

### Exact Version (Recommended)
```python
Flask==3.1.2          # Exact version only
```

### Compatible Version (Use Sparingly)
```python
Flask~=3.1.2          # 3.1.x only (>=3.1.2, <3.2.0)
```

### Minimum Version (Avoid)
```python
Flask>=3.1.2          # Any version >= 3.1.2 (risky!)
```

### Version Range (Avoid)
```python
Flask>=3.1.0,<4.0.0   # Range (still risky!)
```

**Recommendation:** Use exact versions (`==`) for production code.

---

## Dependency Tree

View what depends on what:

```bash
pip install pipdeptree
pipdeptree

# Example output:
# Flask==3.1.2
#   ├── Werkzeug==3.1.3
#   ├── Jinja2==3.1.6
#   │   └── MarkupSafe==3.0.3
#   ├── click==8.3.0
#   └── itsdangerous==2.2.0
```

This helps understand:
- Why a package is installed
- What breaks if you remove something
- Conflict sources

---

## Security Updates

### Check for vulnerabilities:

```bash
pip install safety
safety check -r config/requirements.txt

# Or use GitHub Dependabot (automatic)
```

### Example vulnerability:

```
Vulnerability found in requests==2.25.0
Recommended: Upgrade to requests>=2.31.0
CVE-2023-xxxxx: HTTPS certificate validation bypass
```

**Action:** Update immediately in requirements.txt

---

## Summary

**Status:** ✅ All dependencies pinned to exact versions

**Files:**
- `config/requirements.txt` - Full (production)
- `config/requirements-minimal.txt` - Core only
- `config/requirements-dev.txt` - Development tools

**Benefits:**
- 100% reproducible builds
- No surprise breakages
- Professional deployment practices
- Interview-ready codebase

**Command to remember:**
```bash
pip install -r config/requirements.txt
```

🎯 **This is production-quality dependency management.**
