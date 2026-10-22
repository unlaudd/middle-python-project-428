.PHONY: help install build start clean contract test migrate seed

.DEFAULT_GOAL := help

help: ## Show this help message with a list of available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install project dependencies (Python via uv and Node.js via npm)
	uv sync
	npm ci

build: ## Build the frontend and copy static files to the public/ directory
	rm -rf public/assets public/index.html
	mkdir -p public
	cp -R node_modules/@hexlet/python-flight-booking-frontend/dist/. public/

contract: ## Generate OpenAPI specification from the TypeSpec contract
	npx tsp compile contract

migrate: ## Apply database migrations
	uv run python -m app.migrate

seed: ## Seed reference data (idempotently)
	uv run python -m app.seed

start: migrate seed ## Apply migrations, seed data, and start the server
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $${PORT:-8080}

lint: ## Run linter and formatter checks
	uv run ruff check .
	uv run ruff format --check .

test: ## Run tests using pytest
	uv run pytest -v

clean: ## Clean generated files, caches, and virtual environments
	rm -rf public
	rm -rf .venv
	rm -rf node_modules
	rm -f openapi.yaml
