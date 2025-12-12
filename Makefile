.PHONY: help install install-dev test test-cov lint format clean run docker-build docker-up docker-down docker-logs docker-test docker-dev docker-prod docker-clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --no-dev

install-dev: ## Install development dependencies
	uv sync

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=phone_address_service --cov-report=html --cov-report=term

lint: ## Run linting
	python -m py_compile phone_address_service/**/*.py

format: ## Format code (placeholder - add black/ruff if needed)
	@echo "Code formatting not configured yet"

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run: ## Run the application
	uv run python main.py

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop services with Docker Compose
	docker-compose down

docker-logs: ## View Docker Compose logs
	docker-compose logs -f
docker-build: ## Build Docker image
	docker build -t phone-address-service .

docker-test: ## Run integration tests with Docker
	docker-compose -f docker-compose.yml -f docker-compose.test.yml up --build --abort-on-container-exit

docker-dev: ## Start development environment
	docker-compose --profile dev up --build

docker-prod: ## Start production environment
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

docker-clean: ## Clean Docker resources
	docker-compose down -v
	docker system prune -f