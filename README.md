# Juniper Mist Automation Lab

A comprehensive hands-on lab environment for learning Juniper Mist API automation using Python. This project provides interactive Jupyter-style notebooks (`.py` files) that demonstrate how to automate Juniper Mist operations including device adoption, site configuration, and network management.

## 📚 Table of Contents

- [Overview](#overview)
- [What are Python Jupyter Notebooks?](#what-are-python-jupyter-notebooks)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Labs](#running-the-labs)
- [Project Structure](#project-structure)
- [Available Labs](#available-labs)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

## Overview

This project contains interactive Python labs that teach you how to:

- Authenticate with the Juniper Mist API
- Adopt and manage network devices (SSR routers, EX switches, Access Points)
- Perform CRUD operations on sites and configurations
- Use both the `requests` library and the `mistapi` Python package
- Automate Day 1 and Day 2 network operations

## What are Python Jupyter Notebooks?

### Traditional Jupyter Notebooks

Jupyter Notebooks are interactive documents that combine live code, visualizations, and narrative text. They allow you to:

- Write and execute code in cells
- See results immediately below each code cell
- Mix code with documentation using Markdown
- Iterate and experiment interactively

**Learn more:**
- [Jupyter Project Documentation](https://jupyter.org/)
- [Jupyter Notebook Basics](https://jupyter-notebook.readthedocs.io/en/stable/)

### Python Files as Notebooks (This Project)

This project uses **Python files (`.py`) as notebooks** instead of traditional `.ipynb` files. This approach offers several advantages:

- ✅ Better version control (plain text, easy to diff)
- ✅ Works with standard Python tools
- ✅ No JSON metadata clutter
- ✅ Can be run as scripts or interactively

**How it works:**
- Files use special `# %%` cell markers to define code cells
- VS Code's Jupyter extension recognizes these markers
- You get the same interactive experience as `.ipynb` files
- Code can be executed cell-by-cell or all at once

**Learn more:**
- [VS Code Jupyter Support for Python Files](https://code.visualstudio.com/docs/python/jupyter-support-py)
- [Percent Format Documentation](https://code.visualstudio.com/docs/python/jupyter-support-py#_jupyter-code-cells)

## Prerequisites

### Required Software

1. **Python 3.8 or higher**
   - Download: [python.org/downloads](https://www.python.org/downloads/)
   - Verify installation: `python --version` or `python3 --version`

2. **Visual Studio Code**
   - Download: [code.visualstudio.com](https://code.visualstudio.com/)

3. **Git** (optional, for cloning)
   - Download: [git-scm.com](https://git-scm.com/)

4. **Make** (optional, for using Makefile)
   - **Windows**: Install via [Chocolatey](https://chocolatey.org/) (`choco install make`) or use Git Bash
   - **macOS**: Pre-installed with Xcode Command Line Tools
   - **Linux**: Usually pre-installed (`sudo apt install make` on Ubuntu/Debian)

### Required VS Code Extensions

Install these extensions in VS Code:

1. **Python Extension** (Required)
   - Extension ID: `ms-python.python`
   - Install: Open VS Code → Extensions (Ctrl+Shift+X) → Search "Python" → Install

2. **Jupyter Extension** (Required)
   - Extension ID: `ms-toolsai.jupyter`
   - Install: Extensions → Search "Jupyter" → Install

3. **Pylance** (Recommended, usually installed with Python extension)
   - Extension ID: `ms-python.vscode-pylance`
   - Provides enhanced IntelliSense and type checking

**Installation Steps:**

```bash
# Option 1: Install via VS Code UI
# 1. Open VS Code
# 2. Click Extensions icon (or press Ctrl+Shift+X)
# 3. Search for "Python" and click Install
# 4. Search for "Jupyter" and click Install

# Option 2: Install via command line
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
code --install-extension ms-python.vscode-pylance
```

### Juniper Mist Account

- Active Juniper Mist account with API access
- Organization ID and API token
- Access to Mist-managed devices (for device adoption labs)

## Installation

### Step 1: Clone or Download the Repository

```bash
# Option 1: Clone with Git
git clone https://github.com/yourusername/eg-juniper-mist-automation-lab.git
cd eg-juniper-mist-automation-lab

# Option 2: Download ZIP
# Download from GitHub and extract to your desired location
```

### Step 2: Install uv Package Manager (Recommended)

This project uses `uv` for fast Python package management.

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Or use the Makefile:**
```bash
make install-uv
```

**Learn more about uv:** [docs.astral.sh/uv](https://docs.astral.sh/uv/)

### Step 3: Set Up the Environment

**Option A: Using Makefile (Recommended)**

```bash
# Complete setup (creates venv + installs dependencies)
make setup

# Or step by step:
make venv      # Create virtual environment
make install   # Install dependencies
```

**Option B: Manual Setup**

```bash
# Create virtual environment
uv venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Register Jupyter kernel
uv run python -m ipykernel install --user --name=eg-juniper-mist --display-name="Python (Mist Lab)"
```

### Step 4: Verify Installation

```bash
# Check installed packages
uv pip list

# Run tests (optional)
make test
# or
uv run pytest tests/ -v
```

## Configuration

### Step 1: Create `.env` File

Copy the example file and add your credentials:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

### Step 2: Edit `.env` File

Open `.env` in your editor and add your Mist API token:

```bash
# .env file
MIST_API_TOKEN=your_actual_api_token_here
```

**How to get your API token:**
1. Log in to [manage.mist.com](https://manage.mist.com)
2. Go to Organization → Settings → API Tokens
3. Click "Create Token"
4. Give it a name and admin privileges
5. Copy the token to your `.env` file

⚠️ **Security Note:** Never commit the `.env` file to version control. It's already in `.gitignore`.

### Step 3: Configure `config/env.yml`

Edit `config/env.yml` with your environment-specific values:

```yaml
# config/env.yml
host: api.ac2.mist.com          # Your Mist API host
org_id: your_org_id_here        # Will be auto-populated by Lab 04
ap1_mac: your_ap1_mac_here      # Your AP MAC address
ex1_mac: your_ex1_mac_here      # Your switch MAC address
ex_ip: 10.210.6.82              # Your switch IP
ex_gateway: 10.210.6.86         # Your gateway IP
mgmt_vlan: "3630"               # Your management VLAN
vlan_1: "3680"                  # Your VLAN 1
vlan_2: "3681"                  # Your VLAN 2
# SSR MACs will be auto-populated by Lab 04
ssr1_mac: your_ssr1_mac_here
ssr2_mac: your_ssr2_mac_here
ssr3_mac: your_ssr3_mac_here
ssr4_mac: your_ssr4_mac_here
```

**Note:** Many values (like `org_id` and SSR MAC addresses) will be automatically populated when you run Lab 04.

## Running the Labs

### Opening Labs in VS Code

1. **Open the project folder in VS Code:**
   ```bash
   code .
   ```

2. **Open a lab file:**
   - Navigate to `labs/04_Performing_Juniper_Mist_Operations_With_REST_API/lab.py`
   - VS Code will recognize it as a Jupyter notebook (due to `# %%` markers)

3. **Select the Python kernel:**
   - Click on the kernel selector in the top-right corner
   - Choose "Python (Mist Lab)" or your `.venv` Python interpreter

### Running Code Cells

**Interactive Execution (Recommended):**

- Click the ▶️ "Run Cell" button above each `# %%` marker
- Or use keyboard shortcuts:
  - `Shift+Enter`: Run current cell and move to next
  - `Ctrl+Enter`: Run current cell and stay
  - `Alt+Enter`: Run current cell and insert new cell below

**Run All Cells:**

- Click "Run All" at the top of the file
- Or use Command Palette (Ctrl+Shift+P) → "Jupyter: Run All Cells"

**Run as Script:**

```bash
# Activate virtual environment first
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Run the lab
python labs/04_Performing_Juniper_Mist_Operations_With_REST_API/lab.py
```

### Interactive Features

- **Variables Explorer:** View all variables in the current session
- **Output:** See results immediately below each cell
- **Debugging:** Set breakpoints and debug interactively
- **Plots:** Visualizations appear inline (if using matplotlib/bokeh)

**Learn more:**
- [Working with Jupyter Notebooks in VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks)
- [Python Interactive Window](https://code.visualstudio.com/docs/python/jupyter-support-py)

## Project Structure

```
eg-juniper-mist-automation-lab/
├── .venv/                      # Virtual environment (created during setup)
├── config/
│   └── env.yml                 # Non-secret configuration
├── labs/
│   ├── 04_Performing_Juniper_Mist_Operations_With_REST_API/
│   │   └── lab.py              # Lab 04: API basics
│   └── data/                   # Lab data and screenshots
│       ├── L04/
│       ├── L05/
│       ├── L07/
│       ├── L08/
│       ├── L09/
│       └── L10/
├── tests/
│   ├── conftest.py             # Pytest configuration
│   ├── test_L04_integration.py # Lab 04 tests
│   └── test_L05_integration.py # Lab 05 tests
├── utils/
│   ├── __init__.py
│   ├── config.py               # Configuration loader
│   └── mist_engine.py          # Mist API utilities
├── .env                        # Your secrets (create from .env.example)
├── .env.example                # Template for .env
├── .gitignore                  # Git ignore rules
├── Makefile                    # Build automation
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

## Available Labs

### Lab 04: Performing Juniper Mist Operations with REST API

**File:** `labs/04_Performing_Juniper_Mist_Operations_With_REST_API/lab.py`

**Topics Covered:**
- Setting up API authentication
- Discovering organization ID
- Adopting SSR routers and EX switches
- Listing and managing sites
- CRUD operations with `requests` library
- CRUD operations with `mistapi` package
- Saving configuration for future labs

**Prerequisites:**
- Mist API token configured in `.env`
- Access to Mist organization
- SSR routers and EX switches available for adoption

## Troubleshooting

### Common Issues

#### 1. Jupyter Kernel Not Found

**Problem:** "No kernel found" or kernel selector shows no options

**Solution:**
```bash
# Reinstall ipykernel
uv pip install ipykernel
uv run python -m ipykernel install --user --name=eg-juniper-mist --display-name="Python (Mist Lab)"

# Restart VS Code
```

#### 2. Module Not Found Errors

**Problem:** `ModuleNotFoundError: No module named 'mistapi'`

**Solution:**
```bash
# Ensure virtual environment is activated
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Reinstall dependencies
make install
# or
uv pip install -r requirements.txt
```

#### 3. Import Errors in Notebooks

**Problem:** `ImportError` when running cells

**Solution:**
- Ensure you've selected the correct Python kernel (Python (Mist Lab))
- Restart the kernel: Command Palette → "Jupyter: Restart Kernel"
- Check that virtual environment is activated

#### 4. API Authentication Failures

**Problem:** `401 Unauthorized` or authentication errors

**Solution:**
- Verify your API token in `.env` is correct
- Check token hasn't expired in Mist portal
- Ensure no extra spaces in `.env` file
- Reload environment: Restart VS Code or kernel

#### 5. Missing Dependencies on Linux

**Problem:** `junos-eznc` installation fails

**Solution:**
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt install -y libffi-dev libssl-dev libxml2-dev libxslt1-dev python3-dev

# Then reinstall
make install
```

### Getting Help

- **VS Code Jupyter Documentation:** [code.visualstudio.com/docs/datascience/jupyter-notebooks](https://code.visualstudio.com/docs/datascience/jupyter-notebooks)
- **Mist API Documentation:** [doc.mist-lab.fr](https://doc.mist-lab.fr/)
- **mistapi Package:** [PyPI - mistapi](https://pypi.org/project/mistapi/)

## Makefile Commands

Quick reference for available `make` commands:

```bash
make help          # Show all available commands
make setup         # Complete setup (venv + install)
make venv          # Create virtual environment only
make install       # Install dependencies
make sync          # Sync dependencies (faster)
make test          # Run pytest tests
make clean         # Remove virtual environment
make reinstall     # Clean and setup from scratch
make activate      # Show activation command
make add PACKAGE=name    # Add a new package
make remove PACKAGE=name # Remove a package
```

## Resources

### Documentation

- **Jupyter Notebooks:**
  - [Jupyter Project](https://jupyter.org/)
  - [VS Code Jupyter Support](https://code.visualstudio.com/docs/datascience/jupyter-notebooks)
  - [Python Files as Notebooks](https://code.visualstudio.com/docs/python/jupyter-support-py)

- **Juniper Mist:**
  - [Mist API Documentation](https://doc.mist-lab.fr/)
  - [Mist API Reference](https://api.mist.com/api/v1/docs/)
  - [mistapi Python Package](https://pypi.org/project/mistapi/)

- **Python Tools:**
  - [uv Package Manager](https://docs.astral.sh/uv/)
  - [requests Library](https://requests.readthedocs.io/)
  - [PyYAML](https://pyyaml.org/)

### VS Code Extensions

- [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Jupyter Extension](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter)
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Happy Learning! 🚀**

For questions or issues, please open an issue on GitHub.
