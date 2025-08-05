# Contributing to Vortex

Guide for developers contributing to the Vortex project.

## Development Setup

1. Clone the repository
2. Install with development dependencies:
   ```bash
   uv pip install -e ".[dev,test,lint]"
   ```

## Code Quality

### Testing
- Run tests: `uv run pytest`
- See [testing.md](testing.md) for detailed testing guidelines

### Code Style
- Format code: `uv run black src/vortex/`
- Sort imports: `uv run isort src/vortex/`
- Check style: `uv run flake8 src/vortex/`

## Architecture

The project follows Clean Architecture principles:
- `models/` - Domain models
- `services/` - Business logic
- `providers/` - External data sources
- `storage/` - Data persistence
- `cli/` - User interface
- `shared/` - Cross-cutting concerns

## Submitting Changes

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request