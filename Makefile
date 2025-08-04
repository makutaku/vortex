.PHONY: help install dev test lint clean build

help:
	@echo "Available commands:"
	@echo "  install    Install package and dependencies"
	@echo "  dev        Install in development mode"
	@echo "  test       Run tests"
	@echo "  lint       Run linting"
	@echo "  clean      Clean build artifacts"
	@echo "  build      Build the project"

install:
	uv pip install -e .

dev:
	uv pip install -e .

test:
	python -m pytest tests/ -v

lint:
	flake8 src/vortex tests/

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

build:
	./scripts/build.sh