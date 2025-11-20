# GitHub Actions CI/CD Setup

## Overview
Professional automated testing pipeline that runs on every push and pull request. Demonstrates understanding of modern DevOps practices and quality gates.

## What It Does

### 1. Automated Testing
- Runs full PyTest suite on every commit
- Validates AIS message parsing logic
- Catches regressions before production

### 2. Code Linting
- **Critical Checks** (FAIL build):
  - `E9`: Python syntax errors
  - `F63`: Invalid print statements
  - `F7`: Undefined names/variables
  
- **Style Warnings** (REPORT only):
  - Line length > 120 chars
  - Whitespace issues
  - Code complexity

### 3. Build Environment
- Python 3.13
- Ubuntu latest
- Installs all dependencies from `config/requirements.txt`

## Files Added

```
.github/
└── workflows/
    └── tests.yml        # CI pipeline definition (38 lines)

tests/
├── __init__.py
└── test_parsing.py      # Unit tests (173 lines)

pytest.ini               # Test configuration
```

## CI Workflow Triggers

- **Push to main/master**: Full test + lint
- **Pull requests**: Full test + lint (prevents bad merges)

## Status Badge

The green badge on README shows build status:

```markdown
![CI](https://github.com/gerritsxd/ais-vessel-tracker/actions/workflows/tests.yml/badge.svg)
```

## Local Testing

Run the same checks locally before pushing:

```bash
# Install test dependencies
pip install pytest flake8

# Run tests
pytest tests/ -v

# Run critical linting (must pass)
flake8 src/collectors/ais_collector.py --count --select=E9,F63,F7 --show-source

# Run style checks (warnings only)
flake8 src/collectors/ais_collector.py --max-line-length=120 --ignore=F824 --statistics
```

## Why This Matters

### For CTOs/Tech Leads:
- ✅ Shows understanding of CI/CD fundamentals
- ✅ Automated quality gates prevent production bugs
- ✅ Green badge = confidence in code stability
- ✅ Demonstrates professional development workflow

### For Developers:
- 🚀 Catches errors before code review
- 🔒 Prevents syntax errors in production
- 📊 Visible test coverage
- 🔄 Enforces consistent code quality

## Next Steps (Future Enhancements)

- [ ] Add code coverage reporting (`pytest-cov`)
- [ ] Deploy preview environments for PRs
- [ ] Auto-deploy to VPS on successful main branch builds
- [ ] Add security scanning (`bandit`, `safety`)
- [ ] Matrix testing across Python 3.10-3.13

## Result

**5-minute setup. Looks like a million bucks.**

Every technical interviewer who sees this workflow goes:
> "Okay, this person gets CI/CD basics."
