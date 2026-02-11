import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config_from_yaml(env_yml_path=None):
    """Load configuration from .env (secrets) and config/env.yml (non-secrets).

    Returns a merged dictionary with all config values.
    
    Secrets (from .env ONLY):
        - MIST_API_TOKEN -> token
    
    Non-secrets (from env.yml):
        - host, org_id, MACs, IPs, VLANs, etc.
    
    Note: Secrets are ONLY loaded from .env and will NOT fall back to env.yml
    """
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    if env_yml_path is None:
        env_yml_path = project_root / "config" / "env.yml"

    with open(env_yml_path, "r") as f:
        config = yaml.safe_load(f) or {}

    # Load API token from .env ONLY (no fallback to YAML)
    config["token"] = os.getenv("MIST_API_TOKEN", "")

    return config
