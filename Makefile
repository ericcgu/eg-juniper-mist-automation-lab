# Makefile for Juniper Mist Automation Lab
# Cross-platform support for Windows and macOS/Linux
# Uses uv for fast Python package management

# Detect OS
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    VENV_BIN = .venv/Scripts
    PYTHON = python
    RM_CMD = if exist .venv rmdir /s /q .venv
    ACTIVATE_MSG = .venv\Scripts\activate
    UV_INSTALL = powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
else
    DETECTED_OS := $(shell uname -s)
    VENV_BIN = .venv/bin
    PYTHON = python3
    RM_CMD = rm -rf .venv
    ACTIVATE_MSG = source .venv/bin/activate
    UV_INSTALL = curl -LsSf https://astral.sh/uv/install.sh | sh
endif

# Variables
VENV_DIR = .venv
PYTHON_VENV = $(VENV_BIN)/python
UV = uv

# Default target
.PHONY: help
help:
	@echo "Detected OS: $(DETECTED_OS)"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup       - Create venv and install all dependencies (using uv)"
	@echo "  make venv        - Create virtual environment only"
	@echo "  make install     - Install dependencies from requirements.txt"
	@echo "  make sync        - Sync dependencies (faster than install)"
	@echo "  make clean       - Remove virtual environment"
	@echo "  make test        - Run pytest tests"
	@echo "  make freeze      - Update requirements.txt with current packages"
	@echo "  make activate    - Show command to activate venv"
	@echo "  make reinstall   - Clean and setup from scratch"
	@echo "  make install-uv  - Install uv package manager"

# Install uv if not present
.PHONY: install-uv
install-uv:
	@echo "Installing uv package manager..."
	@$(UV_INSTALL)
	@echo "uv installed successfully!"

# Create virtual environment using uv
.PHONY: venv
venv:
	@echo "Creating virtual environment for $(DETECTED_OS) using uv..."
	@$(UV) venv $(VENV_DIR)
	@echo "Virtual environment created in $(VENV_DIR)/"

# Install dependencies using uv
.PHONY: install
install:
	@echo "Installing dependencies with uv..."
	@$(UV) pip install -r requirements.txt
	@echo "Registering Jupyter kernel..."
	@$(UV) run python -m ipykernel install --user --name=eg-juniper-mist --display-name="Python (Mist Lab)"
	@echo "Dependencies installed successfully!"

# Sync dependencies (faster, recommended)
.PHONY: sync
sync:
	@echo "Syncing dependencies with uv..."
	@$(UV) pip sync requirements.txt
	@echo "Dependencies synced successfully!"

# Setup: create venv and install dependencies
.PHONY: setup
setup: venv install
	@echo ""
	@echo "Setup complete! Activate the virtual environment with:"
	@echo "  $(ACTIVATE_MSG)"

# Clean up virtual environment
.PHONY: clean
clean:
	@echo "Removing virtual environment..."
	@$(RM_CMD)
	@echo "Virtual environment removed."

# Run tests
.PHONY: test
test:
	@echo "Running tests..."
	@$(UV) run pytest tests/ -v

# Freeze current packages to requirements.txt
.PHONY: freeze
freeze:
	@echo "Updating requirements.txt..."
	@$(UV) pip freeze > requirements.txt
	@echo "requirements.txt updated!"

# Show activation command
.PHONY: activate
activate:
	@echo "To activate the virtual environment, run:"
	@echo "  $(ACTIVATE_MSG)"

# Reinstall: clean and setup
.PHONY: reinstall
reinstall: clean setup
	@echo "Reinstallation complete!"

# Show detected OS
.PHONY: os
os:
	@echo "Detected OS: $(DETECTED_OS)"

# Add package with uv
.PHONY: add
add:
	@echo "Usage: make add PACKAGE=package-name"
	@echo "Example: make add PACKAGE=requests"
ifdef PACKAGE
	@$(UV) pip install $(PACKAGE)
	@$(UV) pip freeze > requirements.txt
	@echo "Added $(PACKAGE) and updated requirements.txt"
endif

# Remove package with uv
.PHONY: remove
remove:
	@echo "Usage: make remove PACKAGE=package-name"
	@echo "Example: make remove PACKAGE=requests"
ifdef PACKAGE
	@$(UV) pip uninstall $(PACKAGE) -y
	@$(UV) pip freeze > requirements.txt
	@echo "Removed $(PACKAGE) and updated requirements.txt"
endif
