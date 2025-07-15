.PHONY: help install dev test lint typecheck format run migrate upgrade downgrade clean

# Default target
help:
	@echo "Coffee Tasting API - Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install production dependencies"
	@echo "  dev         Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  run         Start the development server"
	@echo "  test        Run tests"
	@echo "  lint        Run linting (ruff)"
	@echo "  typecheck   Run type checking (mypy)"
	@echo "  format      Format code (ruff)"
	@echo ""
	@echo "Database:"
	@echo "  migrate     Create new migration"
	@echo "  upgrade     Apply migrations"
	@echo "  downgrade   Rollback last migration"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       Clean up cache files"
	@echo "  jwt         Generate JWT token for testing (requires USER_ID and EMAIL)"

# Installation
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# Development server
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term-missing

# Code quality
lint:
	ruff check .

typecheck:
	mypy app

format:
	ruff format .

# Fix common issues
fix:
	ruff check --fix .
	ruff format .

# Database migrations
migrate:
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

# Database utilities
db-current:
	alembic current

db-history:
	alembic history

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .mypy_cache/ 2>/dev/null || true
	rm -rf .ruff_cache/ 2>/dev/null || true

# Docker (if needed later)
docker-build:
	docker build -t coffee-tasting-api .

docker-run:
	docker run -p 8000:8000 coffee-tasting-api

# JWT token generation for testing
jwt:
	@if [ -z "$(USER_ID)" ] || [ -z "$(EMAIL)" ]; then \
		echo "Usage: make jwt USER_ID=<user_id> EMAIL=<email> [ROLE=<role>] [HOURS=<hours>]"; \
		echo "Example: make jwt USER_ID=abc123 EMAIL=user@example.com"; \
		echo "Example: make jwt USER_ID=abc123 EMAIL=user@example.com ROLE=service_role HOURS=24"; \
		exit 1; \
	fi
	@python local_dev_tools/generate_jwt.py "$(USER_ID)" "$(EMAIL)" "$(ROLE)" "$(HOURS)"

# Development shortcuts
check: lint typecheck test

all: clean format lint typecheck test