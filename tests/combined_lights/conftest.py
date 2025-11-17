"""Fixtures for Combined Lights integration tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.combined_lights.const import (
    DOMAIN,
    CONF_NAME,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_LIGHTS,
    CONF_BREAKPOINTS,
    CONF_BRIGHTNESS_CURVE,
    CONF_STAGE_1_BRIGHTNESS_RANGES,
    CONF_STAGE_2_BRIGHTNESS_RANGES,
    CONF_STAGE_3_BRIGHTNESS_RANGES,
    CONF_STAGE_4_BRIGHTNESS_RANGES,
    CONF_ENABLE_BACK_PROPAGATION,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    CURVE_QUADRATIC,
)


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with default values."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Combined Lights",
        data={
            CONF_NAME: "Test Combined Lights",
            CONF_STAGE_1_LIGHTS: ["light.test_stage1"],
            CONF_STAGE_2_LIGHTS: [],
            CONF_STAGE_3_LIGHTS: [],
            CONF_STAGE_4_LIGHTS: [],
            CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
            CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
            CONF_STAGE_1_BRIGHTNESS_RANGES: DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
            CONF_STAGE_2_BRIGHTNESS_RANGES: DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
            CONF_STAGE_3_BRIGHTNESS_RANGES: DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
            CONF_STAGE_4_BRIGHTNESS_RANGES: DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
            CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
        },
    )


@pytest.fixture
def mock_config_entry_advanced():
    """Create a mock config entry with advanced configuration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Advanced Test Combined Lights",
        data={
            CONF_NAME: "Advanced Test Combined Lights",
            CONF_STAGE_1_LIGHTS: ["light.stage1_1", "light.stage1_2"],
            CONF_STAGE_2_LIGHTS: ["light.stage2_1"],
            CONF_STAGE_3_LIGHTS: [],
            CONF_STAGE_4_LIGHTS: ["light.stage4_1"],
            CONF_BREAKPOINTS: [30, 60, 90],
            CONF_BRIGHTNESS_CURVE: CURVE_QUADRATIC,
            CONF_STAGE_1_BRIGHTNESS_RANGES: [[10, 40], [50, 70], [80, 90], [95, 100]],
            CONF_STAGE_2_BRIGHTNESS_RANGES: [[0, 0], [20, 50], [60, 80], [85, 100]],
            CONF_STAGE_3_BRIGHTNESS_RANGES: [[0, 0], [0, 0], [30, 60], [70, 100]],
            CONF_STAGE_4_BRIGHTNESS_RANGES: [[0, 0], [0, 0], [0, 0], [40, 100]],
            CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
        },
    )
