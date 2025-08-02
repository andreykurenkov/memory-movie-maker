.PHONY: help install install-dev test test-unit test-integration test-e2e coverage lint format type-check clean run setup-dev

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests
	pytest tests/unit/

test-integration:  ## Run integration tests
	pytest tests/integration/

test-e2e:  ## Run end-to-end tests
	pytest tests/e2e/

coverage:  ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term

lint:  ## Run linting checks
	flake8 src/ tests/
	pylint src/

format:  ## Format code with black and isort
	black src/ tests/
	isort src/ tests/

type-check:  ## Run type checking with mypy
	mypy src/

clean:  ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/
	rm -rf data/temp/*

run:  ## Run the application
	python -m memory_movie_maker

setup-dev:  ## Set up development environment
	./scripts/setup_dev.sh