.PHONY: help install test test-cov test-fast test-failed validate pretty pv run migrate migration

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install --no-interaction --no-ansi

test:  ## Run all tests without coverage
	poetry run pytest --no-cov

test-cov:  ## Run tests with coverage report
	poetry run pytest --cov=nutrition_tracking_api --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-fast:  ## Run tests until first failure
	poetry run pytest -x

test-failed:  ## Run tests from last-failed
	poetry run pytest --last-failed --no-cov

validate:  ## Lint code with ruff, mypy and black
	poetry run ruff check nutrition_tracking_api tests
	poetry run mypy nutrition_tracking_api tests
	poetry run black --check nutrition_tracking_api tests

pretty:  ## Format code with black and ruff
	poetry run ruff check --fix-only nutrition_tracking_api tests
	poetry run black nutrition_tracking_api tests

pv: ## Runs validate and pretty
	make pretty
	make validate

run:  ## Run the application
	poetry run uvicorn nutrition_tracking_api.api.main:app --reload

migrate:  ## Apply database migrations
	poetry run alembic upgrade head

migration:  ## Create a new migration (use: make migration MESSAGE="description")
	poetry run alembic revision --autogenerate -m "$(MESSAGE)"
