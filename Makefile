.PHONY: help install dev test lint format clean run docker-up docker-down

help: ## Show this help message
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies with uv
	uv pip install -e .

install-pip: ## Install with standard pip
	pip install -e .

dev: ## Install development dependencies with uv
	uv pip install -e ".[dev]"
	pre-commit install

dev-pip: ## Install dev dependencies with standard pip
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

lint: ## Run linters
	ruff check app tests
	mypy app

format: ## Format code
	ruff format app tests
	ruff check --fix app tests

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache

run: ## Run the application
	python main.py

run-dev: ## Run in development mode with reload
	aria serve --reload

run-uv: ## Run with uv script (handles venv and deps)
	./scripts/uv-run.sh

uv-sync: ## Sync dependencies with uv
	uv pip sync requirements.txt

uv-compile: ## Compile requirements with uv
	uv pip compile pyproject.toml -o requirements.lock

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

redis: ## Start Redis server
	redis-server

setup-hooks: ## Setup git hooks
	pre-commit install
	pre-commit run --all-files

migrate: ## Run database migrations
	echo "TODO: Implement database migrations"

shell: ## Open Python shell with app context
	ipython -i -c "from app import *"
