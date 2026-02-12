# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an educational lab environment for learning Juniper Mist API automation using Python. Labs are written as Python files (`.py`) with `# %%` cell markers to make them executable as Jupyter notebooks in VS Code.

## Development Commands

**Setup:**
```bash
make setup          # Complete setup: create venv + install dependencies
make venv           # Create virtual environment only
make install        # Install dependencies with uv
```

**Testing:**
```bash
make test           # Run all pytest integration tests
uv run pytest tests/ -v                    # Full verbose output
uv run pytest tests/test_L04_integration.py -v  # Run specific test file
```

**Package Management:**
```bash
make add PACKAGE=name      # Add new package and update requirements.txt
make remove PACKAGE=name   # Remove package and update requirements.txt
make freeze                # Update requirements.txt with current packages
```

**Other:**
```bash
make clean          # Remove virtual environment
make reinstall      # Clean and setup from scratch
make activate       # Show activation command
```

## Configuration Architecture

**Two-file configuration system (security-focused):**

1. **`.env`** (secrets only, never committed):
   - `MIST_API_TOKEN` - Juniper Mist API token
   - Created from `.env.example`
   - Loaded via `python-dotenv`

2. **`config/env.yml`** (non-secrets, tracked in git):
   - `host` - Mist API host (e.g., api.ac2.mist.com)
   - `org_id` - Organization ID (auto-populated by Lab 04)
   - Device MACs: `ap1_mac`, `ex1_mac`, `ssr1_mac`, etc. (some auto-populated)
   - Network settings: `ex_ip`, `ex_gateway`, `mgmt_vlan`, `vlan_1`, `vlan_2`

**Loading configuration:**
```python
from utils import load_config_from_yaml
env = load_config_from_yaml()  # Returns merged dict with all config values
# env['token'] comes from .env MIST_API_TOKEN
# env['host'], env['org_id'], etc. come from config/env.yml
```

**Saving configuration:**
```python
from utils import save_config_to_yaml
save_config_to_yaml(env)  # Saves to config/env.yml, automatically excludes 'token'
```

**Important:** Secrets (`token`) are ONLY loaded from `.env` and will NOT fall back to `env.yml`. When saving, the `token` key is automatically excluded from YAML output.

## Utils Module

Located in `utils/`, provides shared functionality:

- **`config.py`**: Configuration management
  - `load_config_from_yaml()` - Loads and merges .env + env.yml
  - `save_config_to_yaml(config_dict)` - Saves non-secrets to env.yml

- **`mist_engine.py`**: API session management
  - `get_mist_session(config)` - Returns authenticated mistapi.APISession
  - `get_requests_session(token)` - Returns requests.Session with token auth

- **`__init__.py`**: Exports all utility functions for easy imports

## Lab Structure

**Lab files are Python scripts formatted as Jupyter notebooks:**
- Use `# %%` markers to define code cells
- VS Code's Jupyter extension recognizes these markers
- Can be run interactively (cell-by-cell) or as scripts
- Located in `labs/<lab_number>_<lab_name>/lab.py`

**Running labs:**
- **Interactive**: Open in VS Code, select "Python (Mist Lab)" kernel, click "Run Cell" buttons
- **Script**: `python labs/04_Performing_Juniper_Mist_Operations_With_REST_API/lab.py`

**Lab data:**
- Stored in `labs/data/<lab_number>/`
- Contains screenshots, reference code, and lab-specific resources

## Testing Strategy

**Integration tests** (run against real Mist environment):
- Located in `tests/`
- Named `test_L<lab_number>_integration.py`
- Require valid `.env` and `config/env.yml` with real credentials
- Use pytest fixtures from `tests/conftest.py`

**Available fixtures:**
- `config` - Full config dictionary
- `org_id`, `token` - Individual config values
- `mist_session` - Authenticated mistapi.APISession
- `requests_session` - Authenticated requests.Session
- `mist_api_root` - Base API URL (https://{host}/)

## API Usage Patterns

**Two API interaction methods:**

1. **Using `mistapi` package** (higher-level, recommended):
```python
import mistapi
from mistapi.api import v1 as mist
from utils import get_mist_session

session = get_mist_session(config)
result = mist.orgs.sites.listOrgSites(session, org_id=org_id)
sites = result.data
```

2. **Using `requests` library** (lower-level, more control):
```python
import requests
from utils import get_requests_session

session = get_requests_session(token)
response = session.get(f"https://{host}/api/v1/orgs/{org_id}/sites")
sites = response.json()
```

## Key Dependencies

- **mistapi** (0.55.8) - Juniper Mist API Python package
- **requests** (2.32.5) - HTTP library for REST API calls
- **junos-eznc** (2.7.1) - Junos device automation (PyEZ)
- **pyyaml** (6.0.1) - YAML configuration parsing
- **python-dotenv** (1.0.1) - Environment variable loading
- **pandas**, **holoviews**, **bokeh** - Data analysis and visualization
- **pytest** (8.0.2) - Testing framework
- **ipykernel** (6.29.2) - Jupyter kernel for notebook support

## Important Notes

- **Windows support**: This project is cross-platform. Makefile detects OS and adjusts commands accordingly.
- **Package manager**: Uses `uv` (Astral's fast Python package manager) instead of pip for faster installs.
- **Virtual environment**: Always activate `.venv` before running labs or tests.
- **Lab 04 auto-configuration**: Running Lab 04 automatically populates `org_id` and SSR MAC addresses in `config/env.yml`.
- **Path handling**: Labs use `sys.path.insert(0, ../..)` to ensure utils module is importable.
- **Module reloading**: Labs use `importlib.reload(utils)` to pick up changes during development.

## Common Patterns

**Lab initialization boilerplate:**
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import importlib
import utils
importlib.reload(utils)

from utils import load_config_from_yaml, save_config_to_yaml

env = load_config_from_yaml()
```

**Saving discovered values to config:**
```python
# After discovering org_id or device MACs:
env['org_id'] = discovered_org_id
env['ssr1_mac'] = discovered_mac
save_config_to_yaml(env)  # Persists to config/env.yml for future labs
```
