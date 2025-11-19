"""Tests for ZoneManager helper."""

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.combined_lights.const import DOMAIN
from custom_components.combined_lights.helpers import ZoneManager


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_123",
        data={
            "name": "Test Combined Light",
            "stage_1_lights": ["light.stage1_1", "light.stage1_2"],
            "stage_2_lights": ["light.stage2_1"],
            "stage_3_lights": ["light.stage3_1"],
            "stage_4_lights": ["light.stage4_1"],
        },
    )


class TestZoneManager:
    """Test ZoneManager class."""

    def test_zone_brightness_dict(self, hass: HomeAssistant, mock_entry):
        """Test getting zone brightness as a dictionary."""
        # Setup mock states
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 51})  # 20%
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 102})  # 40%
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 128})  # 50%
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_OFF)

        zone_manager = ZoneManager(mock_entry)
        zone_brightness = zone_manager.get_zone_brightness_dict(hass)

        # Stage 1: average of 51 and 102 = 76.5, which is ~30%
        assert zone_brightness["stage_1"] is not None
        assert 25 < zone_brightness["stage_1"] < 35

        # Stage 2: 128 = ~50%
        assert zone_brightness["stage_2"] is not None
        assert 48 < zone_brightness["stage_2"] < 52

        # Stage 3 & 4: off
        assert zone_brightness["stage_3"] is None
        assert zone_brightness["stage_4"] is None
