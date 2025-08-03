# BC-Utils Installation Guide

## 🚀 Quick Start with uv (Recommended)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver, 10-100x faster than pip.

### 1. Install uv

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (using pip):**
```bash
pip install uv
```

### 2. Install BC-Utils

**Development Installation:**
```bash
# Clone repository
git clone https://github.com/makutaku/bc-utils.git
cd bc-utils

# Create virtual environment and install
uv venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows

# Install bc-utils with all dependencies
uv pip install -e .
```

**From PyPI (when published):**
```bash
uv pip install bc-utils
```

### 3. Verify Installation

```bash
# Test CLI is working
bcutils --help

# Verify version
bcutils --version

# Test CLI structure
python verify_cli_structure.py
```

## 📦 Dependency Groups

BC-Utils supports optional dependency groups for different use cases:

```bash
# Development dependencies (pytest, flake8)
uv pip install -e ".[dev]"

# Testing only
uv pip install -e ".[test]"

# Linting tools only  
uv pip install -e ".[lint]"

# All optional dependencies
uv pip install -e ".[dev,test,lint]"
```

## 🐍 Python Version Support

BC-Utils supports Python 3.8+ with the following recommendations:

```bash
# Check Python version
python --version

# Use specific Python version with uv
uv venv --python 3.11
uv venv --python python3.10
```

## 🔧 Development Setup

For contributors and developers:

```bash
# Clone and setup development environment
git clone https://github.com/makutaku/bc-utils.git
cd bc-utils

# Create development environment with uv
uv venv --python 3.11
source .venv/bin/activate

# Install in development mode with all dependencies
uv pip install -e ".[dev,test,lint]"

# Verify development setup
uv run pytest
uv run flake8 src/bcutils/
```

## 🏃‍♂️ Running Commands

With uv, you can run commands directly without activating the virtual environment:

```bash
# Run CLI directly
uv run bcutils --help

# Run tests
uv run pytest

# Run linting
uv run flake8 src/bcutils/

# Format code
uv run black src/bcutils/
uv run isort src/bcutils/
```

## 🐳 Container Installation

For container environments:

```dockerfile
# Dockerfile example
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy and install
COPY . /app
WORKDIR /app

# Install with uv
RUN uv pip install --system .

# Run CLI
ENTRYPOINT ["bcutils"]
```

## 🔄 Migration from pip

If you're currently using pip, migration to uv is simple:

```bash
# Old pip workflow
pip install -e .
pip install -r requirements.txt

# New uv workflow (much faster)
uv pip install -e .
# No requirements.txt needed - uv reads pyproject.toml
```

## ⚡ Performance Comparison

**Installation Speed Comparison:**
- **pip**: ~30-60 seconds for full installation
- **uv**: ~3-5 seconds for same installation
- **uv speedup**: 10-20x faster

**Resolution Speed:**
- **pip**: Can take minutes for complex dependency resolution
- **uv**: Resolves dependencies in seconds

## 🛠️ Troubleshooting

**uv not found after installation:**
```bash
# Add to PATH (usually done automatically)
export PATH="$HOME/.cargo/bin:$PATH"

# Or restart shell
exec $SHELL
```

**Permission errors:**
```bash
# Use --user flag if needed
uv pip install --user -e .
```

**Virtual environment issues:**
```bash
# Remove and recreate environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

**Dependency conflicts:**
```bash
# Update all dependencies
uv pip install --upgrade -e .

# Force reinstall
uv pip install --force-reinstall -e .
```

## 📚 Additional Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [BC-Utils CLI Guide](CLAUDE.md#modern-cli-usage)
- [Configuration Guide](CLAUDE.md#configuration-management)
- [Development Guide](CLAUDE.md#development-commands)

## 💡 Why uv?

- **🚀 10-100x faster** than pip
- **🔒 Reliable** dependency resolution
- **🎯 Drop-in replacement** for pip commands  
- **📦 Modern Python packaging** support
- **🔄 Compatible** with existing pip workflows
- **⚡ Built in Rust** for maximum performance