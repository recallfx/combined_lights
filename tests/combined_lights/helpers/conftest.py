"""Fixtures for helper tests."""

import pytest


@pytest.fixture(scope="session")
def fixture_dir():
    """Return fixture directory path."""
    return "combined_lights"
