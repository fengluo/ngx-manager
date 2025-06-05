# Nginx Manager Makefile
# Simplifies development and deployment tasks

PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python

# Default target
.PHONY: help
help:
	@echo "Nginx Manager Development Toolkit"
	@echo ""
	@echo "Available targets:"
	@echo "  setup-dev     - Setup development environment"
	@echo "  setup-prod    - Setup production environment"
	@echo "  install       - Install package in current environment"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  test-e2e      - Run end-to-end tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code with black"
	@echo "  clean         - Clean build artifacts and cache"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-start  - Start Docker container"
	@echo "  docker-stop   - Stop Docker container"
	@echo "  package       - Build distribution packages"
	@echo ""

# Environment setup
.PHONY: setup-dev
setup-dev:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	@echo ""
	@echo "Development environment ready!"
	@echo "Activate with: source $(VENV)/bin/activate"

.PHONY: setup-prod
setup-prod:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install .
	@echo ""
	@echo "Production environment ready!"
	@echo "Activate with: source $(VENV)/bin/activate"

# Install package
.PHONY: install
install:
	pip install -e .

# Testing
.PHONY: test
test:
	$(PYTHON_VENV) -m pytest tests/ -v

.PHONY: test-unit
test-unit:
	$(PYTHON_VENV) -m pytest tests/unit/ -v

.PHONY: test-integration
test-integration:
	$(PYTHON_VENV) -m pytest tests/integration/ -v

.PHONY: test-e2e
test-e2e:
	$(PYTHON_VENV) -m pytest tests/e2e/ -v

.PHONY: test-coverage
test-coverage:
	$(PYTHON_VENV) -m pytest tests/ --cov=nginx_manager --cov-report=html --cov-report=term

# Code quality
.PHONY: lint
lint:
	$(PYTHON_VENV) -m flake8 nginx_manager/ tests/
	$(PYTHON_VENV) -m mypy nginx_manager/

.PHONY: format
format:
	$(PYTHON_VENV) -m black nginx_manager/ tests/

# Cleanup
.PHONY: clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker operations
.PHONY: docker-build
docker-build:
	docker build -t nginx-manager .

.PHONY: docker-start
docker-start:
	docker run -d --name nginx-manager \
		-p 80:80 -p 443:443 \
		-v $(PWD)/config:/app/config \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/certs:/app/certs \
		--restart unless-stopped \
		nginx-manager

.PHONY: docker-stop
docker-stop:
	docker stop nginx-manager || true
	docker rm nginx-manager || true

.PHONY: docker-logs
docker-logs:
	docker logs -f nginx-manager

# Package building
.PHONY: package
package: clean
	$(PYTHON_VENV) -m build

.PHONY: package-upload-test
package-upload-test: package
	$(PYTHON_VENV) -m twine upload --repository testpypi dist/*

.PHONY: package-upload
package-upload: package
	$(PYTHON_VENV) -m twine upload dist/*

# Quick start commands
.PHONY: run
run:
	$(PYTHON) nginx_manager.py

.PHONY: status
status:
	$(PYTHON) nginx_manager.py status

.PHONY: setup-system
setup-system:
	$(PYTHON) nginx_manager.py setup

# Development helpers
.PHONY: dev-server
dev-server:
	$(PYTHON) nginx_manager.py add -d dev.local -b http://localhost:3000 --no-ssl

.PHONY: check-deps
check-deps:
	$(PYTHON_VENV) -m pip check
	$(PYTHON_VENV) -m pip list --outdated 