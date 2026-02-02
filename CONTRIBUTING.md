# Contributing to JIRA Sprint Reporter

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for everyone.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable behaviors:**
- Harassment of any kind
- Trolling or insulting comments
- Publishing others' private information
- Other conduct inappropriate in a professional setting

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of JIRA and Agile methodologies
- Familiarity with Python and web technologies

### Find an Issue

1. Browse [open issues](https://github.com/yourcompany/jira-sprint-reporter/issues)
2. Look for issues tagged with `good-first-issue` or `help-wanted`
3. Comment on the issue to express interest
4. Wait for maintainer confirmation before starting work

---

## 💻 Development Setup

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/jira-sprint-reporter.git
cd jira-sprint-reporter
```

### 2. Set Up Upstream Remote

```bash
git remote add upstream https://github.com/yourcompany/jira-sprint-reporter.git
git fetch upstream
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 4. Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install Playwright browsers
playwright install chromium
```

### 5. Configure Environment

```bash
# Copy environment template
cp .env_template .env

# Edit .env with your test JIRA credentials
# Use a test JIRA instance if possible
```

### 6. Verify Setup

```bash
# Run tests
pytest

# Run the reporter
python jira_sprint_reporter.py
```

---

## 🤝 How to Contribute

### Types of Contributions

1. **Bug Fixes**: Fix reported issues
2. **Features**: Implement new functionality
3. **Documentation**: Improve or add documentation
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize existing code
6. **Refactoring**: Improve code quality

### Contribution Workflow

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # Or
   git checkout -b fix/bug-description
   ```

2. **Make Changes**
   - Write clean, readable code
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add velocity tracking feature"
   ```

4. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill out the PR template
   - Link related issues

---

## 📏 Coding Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) style guide:

```python
# Good
def calculate_velocity(story_points: List[int]) -> float:
    """
    Calculate average velocity from story points.
    
    Args:
        story_points: List of story point values
        
    Returns:
        Average velocity
    """
    if not story_points:
        return 0.0
    return sum(story_points) / len(story_points)


# Bad
def calc_vel(pts):
    if not pts: return 0
    return sum(pts)/len(pts)
```

### Code Formatting

Use **Black** for code formatting:

```bash
# Format all Python files
black .

# Check formatting
black --check .
```

### Linting

Use **flake8** for linting:

```bash
# Run linter
flake8 jira_sprint_reporter.py

# Configuration in .flake8
[flake8]
max-line-length = 100
ignore = E203, W503
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional

def fetch_sprint_issues(
    sprint_id: int,
    max_results: int = 50
) -> List[Dict]:
    """Fetch issues with type hints."""
    pass
```

### Documentation

Follow Google-style docstrings:

```python
def send_email_with_screenshots(
    screenshots: Dict[str, str],
    email_html: str,
    subject: Optional[str] = None
) -> bool:
    """
    Send email with embedded screenshot images.

    This function sends an HTML email with screenshots embedded as
    inline images using Content-ID references.

    Args:
        screenshots: Dictionary mapping section names to image file paths
        email_html: HTML content for the email body
        subject: Optional email subject line. If None, uses default format

    Returns:
        True if email was sent successfully, False otherwise

    Raises:
        SMTPAuthenticationError: If email credentials are invalid
        FileNotFoundError: If screenshot files don't exist

    Example:
        >>> screenshots = {'header': 'header.png', 'summary': 'summary.png'}
        >>> html = '<html><body>...</body></html>'
        >>> success = send_email_with_screenshots(screenshots, html)
        >>> print(success)
        True
    """
    pass
```

---

## 🧪 Testing Guidelines

### Writing Tests

Use **pytest** for testing:

```python
# tests/test_issue_parser.py
import pytest
from jira_sprint_reporter import IssueParser

def test_parse_issues_with_valid_data():
    """Test parsing issues with valid JIRA response."""
    issues = [
        {
            'key': 'PROJ-123',
            'fields': {
                'summary': 'Test Issue',
                'status': {'name': 'Done'},
                'assignee': {'displayName': 'John Doe'}
            }
        }
    ]
    
    df = IssueParser.parse_issues(issues)
    
    assert len(df) == 1
    assert df.iloc[0]['Task ID'] == 'PROJ-123'
    assert df.iloc[0]['Status'] == 'Done'

def test_parse_issues_with_empty_list():
    """Test parsing with no issues."""
    df = IssueParser.parse_issues([])
    assert len(df) == 0
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_issue_parser.py

# Run specific test
pytest tests/test_issue_parser.py::test_parse_issues_with_valid_data
```

### Test Coverage

Aim for **80%+ code coverage** for new features:

```bash
# Generate coverage report
pytest --cov=. --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

---

## 📝 Pull Request Process

### Before Creating PR

1. **Update from upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**
   ```bash
   pytest
   ```

3. **Run linters**
   ```bash
   black --check .
   flake8 .
   ```

4. **Update documentation**
   - Update README if adding features
   - Update API_INTEGRATION_GUIDE for integrations
   - Add docstrings to new functions

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123
Related to #456

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Screenshots (if applicable)
[Add screenshots here]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests pass
```

### PR Review Process

1. Maintainer reviews code
2. Automated tests run via CI/CD
3. Feedback provided via comments
4. Make requested changes
5. Push updates to same branch
6. Re-review and approval
7. Merge by maintainer

---

## 🐛 Issue Reporting

### Bug Reports

Use this template for bug reports:

```markdown
**Describe the Bug**
Clear description of what the bug is

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen

**Screenshots**
If applicable, add screenshots

**Environment:**
- OS: [e.g., Windows 10]
- Python Version: [e.g., 3.9.5]
- Package Version: [e.g., 2.0.1]

**Additional Context**
Any other context about the problem
```

### Feature Requests

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of what you want

**Describe alternatives you've considered**
Other solutions you've thought about

**Additional context**
Any other context or screenshots
```

---

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

---

## 📚 Resources

### Documentation
- [Python Style Guide](https://pep8.org/)
- [Google Docstring Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Conventional Commits](https://www.conventionalcommits.org/)

### Tools
- [Black Formatter](https://github.com/psf/black)
- [Flake8 Linter](https://flake8.pycqa.org/)
- [pytest Documentation](https://docs.pytest.org/)

### Learning
- [Git Workflow Guide](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [Python Testing](https://realpython.com/pytest-python-testing/)

---

## ❓ Questions?

- **GitHub Discussions**: Ask questions
- **Slack**: Join our community
- **Email**: vinaykumar.kv@outlook.com

---

**Thank you for contributing! 🎉**
