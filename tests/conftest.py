"""pytest fixtures."""

import pathlib
import pytest


# Workaround for editable install namespace package path hook issue
# The setuptools editable finder adds a placeholder path "__editable__..." to
# namespace packages, which Home Assistant's loader tries to iterate over.
# We patch pathlib.Path.iterdir to handle this gracefully.
_original_iterdir = pathlib.Path.iterdir


def _patched_iterdir(self):
    """Skip non-existent paths (e.g., editable install placeholders)."""
    if not self.exists():
        return iter([])
    return _original_iterdir(self)


pathlib.Path.iterdir = _patched_iterdir


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    return
