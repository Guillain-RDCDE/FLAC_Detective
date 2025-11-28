.PHONY: help install install-dev format lint test test-cov clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make format       - Format code with black and isort"
	@echo "  make lint         - Run linters (flake8, mypy, pylint)"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make clean        - Remove build artifacts and cache"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pip install -r requirements-dev.txt

format:
	black src tests
	isort src tests

lint:
	flake8 src tests
	mypy src
	pylint src/flac_detective

test:
	pytest

test-cov:
	pytest --cov=flac_detective --cov-report=html --cov-report=term

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
