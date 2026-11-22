.PHONY: help venv install dev down logs test lint format migrate revision build run-prod-local scan \
        sim-up sim-deploy sim-down tf-init tf-plan tf-apply tf-destroy clean

# Default target
help:
	@echo "TaskFlow API - Available targets:"
	@echo ""
	@echo "Development:"
	@echo "  venv          Create Python 3.12 virtualenv"
	@echo "  install       Install Python dependencies into venv"
	@echo "  dev           Start local development environment"
	@echo "  down          Stop development environment"
	@echo "  logs          Tail application logs"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linters (ruff, mypy)"
	@echo "  format        Format code with ruff"
	@echo ""
	@echo "Database:"
	@echo "  migrate       Run database migrations"
	@echo "  revision      Create new migration (use m=\"message\")"
	@echo ""
	@echo "Docker:"
	@echo "  build         Build Docker image locally"
	@echo "  run-prod-local Run production stack locally"
	@echo "  scan          Run Trivy security scan"
	@echo ""
	@echo "EC2 Simulation:"
	@echo "  sim-up        Create Multipass VM for EC2 rehearsal"
	@echo "  sim-deploy    Deploy to simulated EC2"
	@echo "  sim-down      Destroy Multipass VM"
	@echo ""
	@echo "Terraform:"
	@echo "  tf-init       Initialize Terraform"
	@echo "  tf-plan       Plan infrastructure changes"
	@echo "  tf-apply      Apply infrastructure (requires confirmation)"
	@echo "  tf-destroy    Destroy infrastructure (requires confirmation)"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         Clean up generated files"

# Variables
DOCKER_REPO := ghcr.io/koushik926/taskflow-api
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
APP_VERSION := 1.0.0
IMAGE_TAG := $(GIT_SHA)

# Python virtualenv
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic

# =============================================================================
# Development
# =============================================================================

$(VENV)/bin/activate:
	@echo "Creating Python 3.12 virtualenv..."
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip -q

venv: $(VENV)/bin/activate

install: venv
	@echo "Installing Python dependencies..."
	$(PIP) install -r requirements-dev.txt

dev:
	@echo "Starting development environment..."
	GIT_SHA=$(GIT_SHA) BUILD_TIME=$(BUILD_TIME) APP_VERSION=$(APP_VERSION) docker compose up -d --build
	@echo ""
	@echo "Services starting..."
	@echo "  API:  http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"
	@sleep 2
	docker compose ps

down:
	@echo "Stopping development environment..."
	docker compose down

logs:
	docker compose logs -f app

# =============================================================================
# Testing & Quality
# =============================================================================

test: venv
	@echo "Starting test database..."
	docker compose -f docker-compose.test.yml up -d
	@sleep 3
	@echo "Running tests..."
	DATABASE_URL=postgresql+asyncpg://taskflow:taskflow@localhost:5433/taskflow_test \
		$(PYTEST) --cov=app --cov-report=term-missing --cov-fail-under=85
	@echo "Stopping test database..."
	docker compose -f docker-compose.test.yml down -v

lint: venv
	@echo "Running ruff check..."
	$(RUFF) check app tests
	@echo "Running ruff format check..."
	$(RUFF) format --check app tests
	@echo "Running mypy..."
	$(MYPY) app

format: venv
	@echo "Formatting code..."
	$(RUFF) format app tests
	$(RUFF) check --fix app tests

# =============================================================================
# Database
# =============================================================================

migrate: venv
	@echo "Running migrations..."
	$(ALEMBIC) upgrade head

revision: venv
ifndef m
	$(error Migration message required: make revision m="your message")
endif
	@echo "Creating migration: $(m)"
	$(ALEMBIC) revision --autogenerate -m "$(m)"

# =============================================================================
# Docker
# =============================================================================

build:
	@echo "Building Docker image..."
	docker buildx build \
		--platform linux/arm64 \
		--build-arg GIT_SHA=$(GIT_SHA) \
		--build-arg BUILD_TIME=$(BUILD_TIME) \
		--build-arg APP_VERSION=$(APP_VERSION) \
		-t $(DOCKER_REPO):$(IMAGE_TAG) \
		-t $(DOCKER_REPO):latest \
		--load \
		.
	@echo ""
	@echo "Image built: $(DOCKER_REPO):$(IMAGE_TAG)"
	@docker images $(DOCKER_REPO):$(IMAGE_TAG) --format "Size: {{.Size}}"

build-multiarch:
	@echo "Building multi-arch Docker image..."
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		--build-arg GIT_SHA=$(GIT_SHA) \
		--build-arg BUILD_TIME=$(BUILD_TIME) \
		--build-arg APP_VERSION=$(APP_VERSION) \
		-t $(DOCKER_REPO):$(IMAGE_TAG) \
		-t $(DOCKER_REPO):latest \
		--push \
		.

run-prod-local:
	@echo "Starting production stack locally..."
	IMAGE_TAG=$(IMAGE_TAG) docker compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "Production stack running:"
	@echo "  App: http://localhost:80"
	@sleep 3
	docker compose -f docker-compose.prod.yml ps

stop-prod-local:
	docker compose -f docker-compose.prod.yml down

scan:
	@echo "Running Trivy security scan..."
	@if command -v trivy >/dev/null 2>&1; then \
		trivy image --severity HIGH,CRITICAL $(DOCKER_REPO):$(IMAGE_TAG); \
	else \
		echo "Trivy not installed. Install with: brew install trivy"; \
	fi

# =============================================================================
# EC2 Simulation (Multipass)
# =============================================================================

sim-up:
	@echo "Creating EC2 simulation VM..."
	./scripts/sim-up.sh

sim-deploy:
	@echo "Deploying to simulated EC2..."
	./scripts/sim-deploy.sh

sim-down:
	@echo "Destroying EC2 simulation VM..."
	./scripts/sim-down.sh

# =============================================================================
# Terraform
# =============================================================================

tf-init:
	@echo "Initializing Terraform..."
	cd infra/terraform && terraform init

tf-plan:
	@echo "Planning infrastructure..."
	cd infra/terraform && terraform plan

tf-apply:
	@echo "Applying infrastructure..."
	@echo "WARNING: This will create AWS resources and may incur costs!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	cd infra/terraform && terraform apply

tf-destroy:
	@echo "Destroying infrastructure..."
	@echo "WARNING: This will destroy all infrastructure!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	cd infra/terraform && terraform destroy

# =============================================================================
# Maintenance
# =============================================================================

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/ 2>/dev/null || true
	@echo "Done."
