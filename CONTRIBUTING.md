# Contributing to Cover Letter Generator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Areas for Contribution](#areas-for-contribution)

## Code of Conduct

This project follows a simple code of conduct:
- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other contributors

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-cover-letter-generator.git
   cd ai-cover-letter-generator
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites
- Python 3.11 or higher
- pip and virtualenv
- Git

### Setup Steps

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install the package in editable mode with dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

4. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys for testing.

5. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Code Style

This project uses automated code formatting and linting:

### Code Formatting
- **Black** for code formatting (line length: 100)
- **Ruff** for linting and import sorting
- **Bandit** for security checks

### Running Code Quality Tools

```bash
# Format code with black
black src/ tests/

# Run ruff linter
ruff check src/ tests/ --fix

# Run security checks
bandit -r src/ -c pyproject.toml

# Or run all pre-commit hooks
pre-commit run --all-files
```

### Style Guidelines

1. **Line Length**: Maximum 100 characters
2. **Type Hints**: Use type hints for function arguments and return values
3. **Docstrings**: Use Google-style docstrings for all public functions and classes
4. **Naming**:
   - Functions and variables: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_CASE`

### Example Function

```python
def generate_cover_letter(
    job_description: str,
    company_name: str,
    job_title: str,
    custom_context: Optional[str] = None
) -> Tuple[str, dict]:
    """Generate a personalized cover letter.

    Args:
        job_description: Full text of the job posting
        company_name: Name of the company
        job_title: Title of the position
        custom_context: Optional additional context

    Returns:
        Tuple of (cover_letter_text, cost_info_dict)

    Raises:
        ValueError: If required parameters are missing
    """
    # Implementation here
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/cover_letter_generator --cov-report=html

# Run specific test file
pytest tests/test_generator.py

# Run tests matching a pattern
pytest -k "test_chunking"
```

### Writing Tests

1. **Location**: Place tests in the `tests/` directory
2. **Naming**: Test files should start with `test_`
3. **Structure**: Use descriptive test names that explain what is being tested

```python
def test_chunk_text_respects_paragraph_boundaries():
    """Test that text chunking preserves paragraph boundaries."""
    text = "Paragraph one.\\n\\nParagraph two.\\n\\nParagraph three."
    chunks = chunk_text(text, chunk_size=30, overlap=5)

    # Each paragraph should be in a separate chunk
    assert len(chunks) >= 3
    assert "Paragraph one" in chunks[0]
```

### Test Coverage Goals
- Aim for **70%+ coverage** on new code
- Critical paths (generation, retrieval, scoring) should have **90%+ coverage**
- All bug fixes should include a regression test

## Submitting Changes

### Before Submitting

1. **Run tests**: Ensure all tests pass
   ```bash
   pytest
   ```

2. **Run code quality checks**:
   ```bash
   pre-commit run --all-files
   ```

3. **Update documentation**: If you changed functionality, update the README.md

4. **Test manually**: Actually run the CLI and verify your changes work

### Commit Messages

Use clear, descriptive commit messages following this format:

```
<type>: <short description>

<longer description if needed>

Fixes #<issue_number>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat: Add support for custom output templates

Added ability to specify custom PDF templates for cover letter
generation. Users can now provide their own ReportLab templates
via the OUTPUT_TEMPLATE environment variable.

Fixes #42
```

### Pull Request Process

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to any related issues
   - Screenshots/examples if relevant

3. **Respond to feedback**: Be open to suggestions and make requested changes

4. **Wait for review**: A maintainer will review your PR

## Areas for Contribution

Here are some areas where contributions are especially welcome:

### High Priority
- **Integration tests**: Add end-to-end tests for critical flows
- **Error handling**: Improve error messages and recovery
- **Performance**: Optimize vector search and embedding generation
- **Documentation**: Improve setup guides, add video tutorials

### Medium Priority
- **New LLM providers**: Add support for more LLM providers (Gemini, local models)
- **Output formats**: Support for more output formats (HTML, plain text)
- **UI improvements**: Better CLI interface, progress indicators
- **Caching**: Add intelligent caching for embeddings and job analyses

### Low Priority
- **Web interface**: Add optional web UI
- **Mobile support**: Create a mobile companion app
- **Analytics**: Better tracking of application outcomes
- **A/B testing**: Framework for testing different prompts

### Bug Fixes
Always welcome! If you find a bug:
1. Check if an issue already exists
2. If not, create a new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
3. Submit a PR with the fix and a test

## Questions?

If you have questions:
- Check the [README.md](README.md) first
- Look at existing [issues](https://github.com/YOUR_USERNAME/ai-cover-letter-generator/issues)
- Open a new issue with the `question` label

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🙏
