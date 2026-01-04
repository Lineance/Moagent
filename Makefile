.PHONY: help install install-dev install-all install-web test test-cov lint format clean docs run build upload

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
VENV := venv
ACTIVATE := $(VENV)/bin/activate
PACKAGE_NAME := moagent

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)MoAgent - Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install core dependencies
	@echo "$(BLUE)Installing MoAgent...$(NC)"
	pip install -e .
	@echo "$(GREEN)✓ Installation complete$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -e ".[dev]"
	@echo "$(GREEN)✓ Development installation complete$(NC)"

install-all: ## Install all dependencies (including optional)
	@echo "$(BLUE)Installing all dependencies...$(NC)"
	pip install -e ".[all]"
	@echo "$(GREEN)✓ Full installation complete$(NC)"

install-web: ## Install web application dependencies
	@echo "$(BLUE)Installing web application dependencies...$(NC)"
	pip install -r requirements-web.txt
	@echo "$(GREEN)✓ Web application installation complete$(NC)"

venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(YELLOW)Activate with: source $(ACTIVATE)$(NC)"

init: venv install-dev ## Create venv and install dev dependencies
	@echo "$(GREEN)✓ Environment initialized$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest -ra

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=$(PACKAGE_NAME) --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-fast: ## Run fast tests only (skip slow)
	@echo "$(BLUE)Running fast tests...$(NC)"
	pytest -m "not slow" -ra

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest -m "unit" -ra

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	ruff check .
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	black .
	ruff check --fix .
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run type checker
	@echo "$(BLUE)Running type checker...$(NC)"
	mypy moagent/
	@echo "$(GREEN)✓ Type checking complete$(NC)"

check: lint type-check test ## Run all checks (lint, type-check, test)

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*.so" -delete 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@cd docs && make html
	@echo "$(GREEN)✓ Documentation generated in docs/_build/html/$(NC)"

docs-serve: docs ## Serve documentation
	@echo "$(BLUE)Serving documentation at http://localhost:8000$(NC)"
	@cd docs/_build/html && $(PYTHON) -m http.server 8000

run: ## Run the application
	@echo "$(BLUE)Running MoAgent...$(NC)"
	$(PYTHON) -m moagent

run-web: ## Run the web application
	@echo "$(BLUE)Running web application...$(NC)"
	@cd web_app && $(PYTHON) app.py

build: ## Build distribution packages
	@echo "$(BLUE)Building packages...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Build complete$(NC)"

upload: build ## Upload to PyPI
	@echo "$(BLUE)Uploading to PyPI...$(NC)"
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)✓ Upload complete$(NC)"

upload-test: build ## Upload to Test PyPI
	@echo "$(BLUE)Uploading to Test PyPI...$(NC)"
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "$(GREEN)✓ Upload complete$(NC)"

playwright-install: ## Install Playwright browsers
	@echo "$(BLUE)Installing Playwright browsers...$(NC)"
	playwright install chromium
	@echo "$(GREEN)✓ Playwright browsers installed$(NC)"

db-init: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	$(PYTHON) -c "from moagent.storage import get_storage; import os; db_url = os.getenv('DATABASE_URL', 'sqlite:///./data/moagent.db'); storage = get_storage(db_url); print('Database initialized')"

db-reset: clean ## Reset database
	@echo "$(YELLOW)Deleting database...$(NC)"
	rm -f ./data/moagent.db
	$(MAKE) db-init

hooks: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

update-deps: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	pip install --upgrade -e ".[all]"
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

# Development helpers
dev: install-dev hooks playwright-install ## Complete dev setup
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Run 'make test' to verify installation$(NC)"

# Quick commands
qtest: ## Quick test (skip slow tests)
	pytest -m "not slow" -q

qformat: ## Quick format (changed files only)
	black .
	ruff check --fix .

serve-web: run-web ## Alias for run-web
