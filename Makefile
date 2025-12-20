.PHONY: help install install-dev install-hooks format lint type-check test test-cov test-unit test-integration coverage-report clean build pre-commit update-hooks check

help:
	@echo "FLAC Detective - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make install-hooks    - Install pre-commit hooks"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           - Format code with black and isort"
	@echo "  make lint             - Run flake8 linter"
	@echo "  make type-check       - Run mypy type checker"
	@echo "  make pre-commit       - Run all pre-commit hooks"
	@echo "  make check            - Run all quality checks (lint + type + test)"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make coverage-report  - Generate detailed coverage report"
	@echo ""
	@echo "Build & Cleanup:"
	@echo "  make build            - Build distribution packages"
	@echo "  make clean            - Remove build artifacts and cache"
	@echo ""
	@echo "Utility:"
	@echo "  make update-hooks     - Update pre-commit hooks to latest versions"
	@echo ""

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-hooks:
	@echo "Installing pre-commit hooks..."
	@python scripts/setup_precommit.py || (pip install pre-commit && pre-commit install)
	@echo "✅ Pre-commit hooks installed!"

format:
	@echo "Running Black code formatter..."
	black src tests
	@echo "Running isort import sorter..."
	isort src tests
	@echo "✅ Code formatting complete!"

lint:
	@echo "Running flake8 linter..."
	flake8 src tests
	@echo "✅ Linting complete!"

type-check:
	@echo "Running mypy type checker..."
	mypy src --config-file=pyproject.toml
	@echo "✅ Type checking complete!"

pre-commit:
	@echo "Running pre-commit hooks on all files..."
	pre-commit run --all-files

update-hooks:
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate
	@echo "✅ Hooks updated!"

check: lint type-check test
	@echo "✅ All quality checks passed!"

test:
	pytest

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=flac_detective --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "✅ Coverage report generated in htmlcov/index.html"
	@echo ""
	@echo "📊 Coverage Summary:"
	@echo "  • Minimum required: 80%"
	@echo "  • HTML report: htmlcov/index.html"
	@echo "  • XML report: coverage.xml"

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

coverage-report:
	@echo "Generating detailed coverage report..."
	@python scripts/coverage_report.py

build: clean
	@echo "Building distribution packages..."
	python -m build
	@echo "✅ Build complete! Files in dist/"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	rm -rf .eggs *.egg
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"
