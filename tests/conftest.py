import sys
import os

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utils import load_config_from_yaml, get_mist_session, get_requests_session


@pytest.fixture(scope="session")
def config():
    """Load config from .env and config/env.yml."""
    return load_config_from_yaml()


@pytest.fixture(scope="session")
def org_id(config):
    """Return the org_id from config."""
    return config["org_id"]


@pytest.fixture(scope="session")
def token(config):
    """Return the API token from config."""
    return config["token"]


@pytest.fixture(scope="session")
def mist_session(config):
    """Create an authenticated mistapi session."""
    return get_mist_session(config)


@pytest.fixture(scope="session")
def requests_session(token):
    """Create an authenticated requests session."""
    return get_requests_session(token)


@pytest.fixture(scope="session")
def mist_api_root(config):
    """Return the base API URL."""
    return f"https://{config['host']}/"
