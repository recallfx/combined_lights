"""Tests for error handling in Combined Lights."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from custom_components.combined_lights.light import CombinedLight
from custom_components.combined_lights.const import CONF_ENABLE_BACK_PROPAGATION


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "name": "Test Light",
        CONF_ENABLE_BACK_PROPAGATION: False,
        "breakpoints": [25, 50, 75],
        "stage_1_brightness_ranges": [[1, 100]],
        "stage_2_brightness_ranges": [[1, 100]],
        "stage_1_lights": ["light.bulb_1"],
        "stage_2_lights": ["light.bulb_2"],
    }
    return entry


@pytest.mark.asyncio
async def test_control_all_zones_partial_failure(hass: HomeAssistant, mock_entry):
    """Test that failure in one zone does not prevent others from updating."""
    light = CombinedLight(mock_entry)
    light.hass = hass
    light._light_controller = AsyncMock()
    light._zone_manager = MagicMock()

    # Setup two zones
    light._zone_manager.get_light_zones.return_value = {
        "stage_1": ["light.bulb_1"],
        "stage_2": ["light.bulb_2"],
    }

    # Mock controller to fail for the first zone but succeed for the second
    async def side_effect(lights, *args, **kwargs):
        if "light.bulb_1" in lights:
            raise Exception("Controller failed completely")
        return {"light.bulb_2": 100}

    light._light_controller.turn_on_lights.side_effect = side_effect

    # Call _control_all_zones
    # We need to pass the arguments manually as we are calling the private method directly
    # or we can call async_turn_on which calls it.
    # Let's call async_turn_on to be more realistic, but we need to mock _build_zone_brightness_map
    # to ensure both zones get brightness.

    light._build_zone_brightness_map = MagicMock(
        return_value={"stage_1": 50.0, "stage_2": 50.0}
    )

    # We also need to mock the lock since we are calling async_turn_on
    light._lock = MagicMock()
    light._lock.locked.return_value = False
    light._lock.__aenter__ = AsyncMock()
    light._lock.__aexit__ = AsyncMock()

    # Mock async_write_ha_state
    light.async_write_ha_state = MagicMock()

    # Execute
    await light.async_turn_on(brightness=255)

    # Verify that turn_on_lights was called for both zones (even though first failed)
    # The side_effect raises exception for first zone.
    # If exception is NOT caught in _control_all_zones, the second call won't happen.

    assert light._light_controller.turn_on_lights.call_count == 2
