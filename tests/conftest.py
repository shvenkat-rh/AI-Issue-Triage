"""Pytest configuration and shared fixtures for the test suite."""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to Python path so tests can import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


@pytest.fixture(scope="session")
def project_root():
    """Fixture providing the project root directory."""
    return parent_dir


@pytest.fixture(scope="session")
def env_vars():
    """Fixture to ensure environment variables are loaded."""
    from dotenv import load_dotenv

    load_dotenv()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests requiring API access")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add integration marker to tests that use analyzer fixtures
        if "analyzer" in item.fixturenames or "api_key" in item.fixturenames:
            item.add_marker(pytest.mark.integration)

        # Add slow marker to batch tests
        if "batch" in item.name.lower():
            item.add_marker(pytest.mark.slow)
