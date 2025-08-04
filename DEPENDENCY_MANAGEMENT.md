# Dependency Management Strategy

## Overview

This document outlines the standardized dependency management approach for the Vortex project.

## Key Changes

### 1. Single Source of Truth
- **Removed:** `requirements.txt` (duplicate dependency definitions)
- **Standardized:** All dependencies managed through `pyproject.toml`
- **Updated:** All scripts and documentation to use `pyproject.toml`

### 2. Consistent Versioning Strategy

**Core Dependencies:**
- Use `>=X.Y.Z,<X+1` for major version bounds (prevents breaking changes)
- Use `>=X.Y.Z` for stable libraries where compatibility is maintained
- Group dependencies by purpose with comments

**Example:**
```toml
dependencies = [
    # Core HTTP and networking
    "requests>=2.31.0,<3.0",
    
    # Data processing and analysis  
    "numpy>=1.19.4,<2.0",
    "pandas>=2.1.4,<3.0",
]
```

### 3. Security-First Approach
- **Minimum versions** set to latest secure releases
- **Upper bounds** prevent automatic upgrades to potentially breaking versions
- **Regular updates** recommended for security patches

## Dependency Categories

### Core Dependencies
- **HTTP/Networking:** requests
- **Data Processing:** numpy, pandas, scipy, pyarrow
- **Web Scraping:** beautifulsoup4
- **Time Handling:** pytz
- **Trading Integration:** ib-insync, yfinance
- **CLI/UI:** click, rich
- **Configuration:** pydantic, pydantic-settings, tomli, tomli-w

### Optional Dependencies
- **dev:** Basic development tools
- **test:** Testing frameworks and utilities
- **lint:** Code quality and formatting tools

## Installation Commands

### Standard Installation
```bash
# Install package with all dependencies
pip install -e .

# Install with optional dependencies
pip install -e ".[test,lint]"
```

### Using uv (Recommended)
```bash
# Install package (faster than pip)
uv pip install -e .

# Install with optional dependencies
uv pip install -e ".[test,lint]"
```

### Development Workflow
```bash
# Install in development mode
make install

# Or directly
uv pip install -e ".[dev,test,lint]"
```

## Version Update Guidelines

### When to Update
- **Security vulnerabilities** in dependencies
- **New features** needed from updated versions
- **Bug fixes** in upstream packages
- **Quarterly reviews** for routine updates

### How to Update
1. Check for security advisories
2. Review changelogs for breaking changes
3. Update version constraints in `pyproject.toml`
4. Test thoroughly with new versions
5. Update this document if strategy changes

## Files Updated

### Removed
- `requirements.txt` - No longer needed

### Modified
- `pyproject.toml` - Standardized all version constraints
- `Makefile` - Updated install command
- `scripts/build.sh` - Removed requirements.txt reference
- `INSTALLATION.md` - Updated installation instructions
- `docs/design/hld/07-deployment-architecture.md` - Updated Docker example

## Migration Benefits

1. **Consistency:** Single source of truth for all dependencies
2. **Security:** Minimum versions protect against known vulnerabilities  
3. **Stability:** Upper bounds prevent unexpected breaking changes
4. **Maintainability:** Clear categorization and documentation
5. **Modern Tooling:** Full compatibility with uv and modern Python packaging

## Compatibility

- **Python:** 3.8+ (as specified in project metadata)
- **Package Managers:** pip, uv, poetry, pipenv
- **Platforms:** Cross-platform (Linux, macOS, Windows)
- **Containers:** Docker, Podman compatible