# GitHub Repository Setup Guide

This guide walks you through setting up your AI Cover Letter Generator repository on GitHub with CI/CD, badges, and code coverage tracking.

## Table of Contents
1. [Create GitHub Repository](#create-github-repository)
2. [Update README Badges](#update-readme-badges)
3. [Push to GitHub](#push-to-github)
4. [Verify CI/CD Pipeline](#verify-cicd-pipeline)
5. [Optional: Add License](#optional-add-license)

---

## 1. Create GitHub Repository

### Option A: Via GitHub Website

1. Go to https://github.com/new
2. Fill in repository details:
   - **Repository name:** `ai-cover-letter-generator` (or your preferred name)
   - **Description:** `AI-powered cover letter generator using RAG (Retrieval-Augmented Generation)`
   - **Visibility:** Public (recommended for Codecov free tier)
   - **Initialize:** ❌ DO NOT initialize with README, .gitignore, or license (you already have these)
3. Click "Create repository"

### Option B: Via GitHub CLI

```bash
# Install GitHub CLI if needed
# macOS: brew install gh
# Windows: winget install --id GitHub.cli
# Linux: See https://github.com/cli/cli#installation

# Login to GitHub
gh auth login

# Create repository
gh repo create ai-cover-letter-generator \
  --public \
  --description "AI-powered cover letter generator using RAG" \
  --source=. \
  --remote=origin
```

---

## 2. Update README Badges

**Current badges in README.md use placeholder `YOUR_USERNAME`.**

### Update Badge URLs

Replace `YOUR_USERNAME` with your actual GitHub username in `README.md`:

```markdown
# Before
[![CI](https://github.com/YOUR_USERNAME/ai-cover-letter-generator/workflows/CI/badge.svg)]

# After (example)
[![CI](https://github.com/yourusername/ai-cover-letter-generator/workflows/CI/badge.svg)]
```

### Quick Find & Replace

**macOS/Linux:**
```bash
# Replace YOUR_USERNAME with your actual username
sed -i '' 's/YOUR_USERNAME/yourusername/g' README.md
```

**Or manually edit** lines 3-5 in `README.md`:
```markdown
[![CI](https://github.com/yourusername/ai-cover-letter-generator/workflows/CI/badge.svg)](https://github.com/yourusername/ai-cover-letter-generator/actions)
[![Tests](https://img.shields.io/badge/tests-74%20passed-success)](https://github.com/yourusername/ai-cover-letter-generator/actions)
[![Coverage](https://img.shields.io/badge/coverage-60%25-green)](https://github.com/yourusername/ai-cover-letter-generator)
```

**Note:** The test count and coverage badges are static. Update them manually as your test suite grows.

---

## 3. Push to GitHub

### Initial Push

```bash
# Check current status
git status

# Add all changes
git add .

# Commit
git commit -m "Add CI/CD and professional project setup

- Added GitHub Actions CI/CD pipeline with matrix testing
- Added README badges (CI, tests, coverage, Python version, code style)
- Set up pre-commit hooks (Black, Ruff, Bandit)
- Added comprehensive tests (74 tests, 60% coverage)
- Created ARCHITECTURE.md and CONTRIBUTING.md
- Added performance profiling tools
- Fully configurable via environment variables
"

# Add remote (if not already added)
git remote add origin https://github.com/yourusername/ai-cover-letter-generator.git

# Push to GitHub
git push -u origin main
```

### If You're on a Different Branch

```bash
# Check current branch
git branch

# If not on main, create and switch to main
git checkout -b main

# Or rename current branch to main
git branch -M main

# Then push
git push -u origin main
```

---

## 4. Verify CI/CD Pipeline

### Check GitHub Actions

1. Go to your repository on GitHub
2. Click the **"Actions"** tab
3. You should see your first workflow run

**Expected workflows:**
- ✅ Lint & Format Check
- ✅ Test (Python 3.11 & 3.12, Ubuntu/macOS/Windows)
- ✅ Type Check
- ✅ Check Dependencies

### View Test Results

1. Click on the workflow run
2. Expand each job to see details
3. Look for:
   - ✅ All tests passing
   - ✅ Coverage report in test output
   - ✅ Codecov upload successful

### Check Badges

1. Go to your repository main page
2. Badges should now display:
   - **CI:** Should show "passing" (green)
   - **Tests:** Shows "74 passed" (green)
   - **Coverage:** Shows "60%" (green)
   - **Python:** Shows "3.11+" (blue)
   - **Code style:** Shows "black" (black)
   - **License:** Shows "MIT" (yellow)

### View Coverage in CI

1. Click on a workflow run in the Actions tab
2. Expand the "Test" job for Ubuntu + Python 3.11
3. Look for "Coverage Report Summary" - this shows detailed coverage
4. HTML coverage report is also generated (see artifacts if uploaded)

---

## 5. Optional: Add License

### Choose a License

The badges reference an MIT license. To add one:

**Option A: Via GitHub**
1. In your repository, click "Add file" → "Create new file"
2. Name it `LICENSE`
3. Click "Choose a license template"
4. Select **MIT License**
5. Fill in your name and year
6. Commit

**Option B: Manual**
Create `LICENSE` file with MIT license text:

```
MIT License

Copyright (c) 2024 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Troubleshooting

### CI Workflow Fails

**Problem:** GitHub Actions workflow fails

**Solutions:**
1. Check the error message in Actions tab
2. Ensure all dependencies are in `pyproject.toml`
3. Verify Python version compatibility (3.11+)
4. Check if system dependencies (poppler) installed correctly

### Coverage Not Showing in Summary

**Problem:** Coverage report not visible in workflow summary

**Solutions:**
1. Check that the workflow completed successfully
2. Ensure tests ran on Ubuntu + Python 3.11 (coverage only runs there)
3. Look for "Coverage Report Summary" in the workflow logs
4. Verify pytest-cov is installed

### Badges Not Showing

**Problem:** Badges show "unknown" or don't load

**Solutions:**
1. Wait a few minutes for first workflow to complete
2. Verify badge URLs have correct username/repo name
3. Clear browser cache
4. Static badges (tests, coverage) can be manually updated as needed

### Tests Fail on Windows

**Problem:** Tests pass locally but fail on Windows in CI

**Solutions:**
1. Check for path separator issues (`/` vs `\`)
2. Verify line ending handling (CRLF vs LF)
3. Review Windows-specific test output in Actions

---

## Next Steps

After setup is complete:

### 1. Enable Branch Protection

1. Go to **Settings** → **Branches**
2. Add rule for `main` branch:
   - ✅ Require status checks before merging
   - ✅ Require branches to be up to date
   - Select: CI workflow checks

### 2. Set Up Issue Templates

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

Create templates for:
- Bug reports
- Feature requests
- Questions

### 3. Add Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines (black, ruff)
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
```

### 4. Enable Discussions (Optional)

1. Go to **Settings** → **Features**
2. Enable **Discussions**
3. Create categories:
   - Q&A
   - Ideas
   - Show and tell

### 5. Add Topics to Repository

1. On repository main page, click ⚙️ next to "About"
2. Add topics: `ai`, `cover-letter`, `rag`, `python`, `openai`, `claude`, `llm`
3. This helps people discover your project

---

## Sharing Your Project

Once everything is set up:

### Reddit
- r/Python
- r/datascience
- r/MachineLearning

### Hacker News
- https://news.ycombinator.com/submit

### Twitter/X
Share with hashtags: #Python #AI #OpenSource #RAG #LLM

### Dev.to / Medium
Write a blog post about:
- Why you built it
- Architecture decisions (link to ARCHITECTURE.md)
- Challenges faced
- Results

---

## Maintenance

### Regular Updates

```bash
# Update dependencies
pip install --upgrade pip
pip install --upgrade -e ".[dev]"

# Run tests
pytest

# Update pre-commit hooks
pre-commit autoupdate
pre-commit run --all-files

# Check for security issues
pip install safety
safety check
```

### Monthly Tasks

1. Review and merge Dependabot PRs
2. Check Codecov trends
3. Review open issues
4. Update documentationLets

---

## Success Checklist

- [ ] Repository created on GitHub
- [ ] README badges updated with your username
- [ ] Code pushed to GitHub
- [ ] CI workflow passing (all jobs green)
- [ ] Coverage report visible in workflow summary
- [ ] All badges showing correctly
- [ ] License added (if applicable)
- [ ] Branch protection enabled (recommended)

---

**Congratulations! Your repository is now fully set up with professional CI/CD and coverage tracking!** 🎉

For questions or issues, check:
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [pytest-cov Docs](https://pytest-cov.readthedocs.io/)
- [pre-commit Docs](https://pre-commit.com/)
