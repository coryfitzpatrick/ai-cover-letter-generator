# Quick Start: Push to GitHub

This is the streamlined version for getting your project on GitHub fast.

## 1. Create GitHub Repository

```bash
# Option A: Via GitHub CLI (easiest)
gh repo create ai-cover-letter-generator --public --source=. --remote=origin

# Option B: Via website
# Go to https://github.com/new
# Create repo (don't initialize with README)
# Then run: git remote add origin https://github.com/YOUR_USERNAME/ai-cover-letter-generator.git
```

## 2. Update README Badges

Replace `YOUR_USERNAME` in lines 3-4 of `README.md` with your GitHub username:

```bash
# Quick replace (macOS/Linux)
sed -i '' 's/YOUR_USERNAME/yourusername/g' README.md

# Or edit manually - just change YOUR_USERNAME to your actual username
```

## 3. Set Up Codecov (2 minutes)

1. Go to https://codecov.io and sign in with GitHub
2. Add your repository: https://app.codecov.io/gh
3. Copy the repository upload token
4. Add to GitHub Secrets:
   - Go to: https://github.com/yourusername/ai-cover-letter-generator/settings/secrets/actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: [paste token]

## 4. Push to GitHub

```bash
# Check status
git status

# Add and commit
git add .
git commit -m "Add CI/CD and professional project setup

- GitHub Actions CI/CD with matrix testing (Python 3.11/3.12, macOS/Ubuntu/Windows)
- Comprehensive test suite (74 tests, 60% coverage, targeting 80%)
- Pre-commit hooks (Black, Ruff, Bandit)
- Architecture documentation (ARCHITECTURE.md)
- Contribution guidelines (CONTRIBUTING.md)
- Performance profiling tools
- Fully configurable via environment variables
- Cross-platform support
"

# Push
git push -u origin main
```

## 5. Verify Everything Works

1. Go to https://github.com/yourusername/ai-cover-letter-generator
2. Check that badges are showing (may take 1-2 minutes)
3. Click "Actions" tab - CI should be running
4. Wait for all jobs to complete (about 5-10 minutes)
5. Check Codecov: https://codecov.io/gh/yourusername/ai-cover-letter-generator

## That's It! 🎉

Your repository is now:
- ✅ Public on GitHub
- ✅ Running automated tests on every push
- ✅ Tracking code coverage
- ✅ Enforcing code quality with pre-commit hooks
- ✅ Fully documented
- ✅ Ready for contributors

---

## Next Steps (Optional)

### Enable Branch Protection
Settings → Branches → Add rule for `main`:
- ✅ Require status checks before merging
- ✅ Require branches to be up to date
- Select: all CI workflow checks

### Share Your Project
- Reddit: r/Python, r/datascience, r/MachineLearning
- Twitter/X: #Python #AI #OpenSource #RAG
- Hacker News: https://news.ycombinator.com/submit
- Dev.to: Write a blog post about it

---

**For detailed instructions, see [GITHUB_SETUP.md](GITHUB_SETUP.md)**
