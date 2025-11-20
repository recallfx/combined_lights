"""Tests for concurrency handling in Combined Lights."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
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
        "stage_2_brightness_ranges": [[0, 0]],
        "stage_3_brightness_ranges": [[0, 0]],
        "stage_4_brightness_ranges": [[0, 0]],
        "stage_1_lights": ["light.bulb_1"],
    }
    return entry


@pytest.mark.asyncio
async def test_async_turn_on_concurrency(hass: HomeAssistant, mock_entry):
    """Test that async_turn_on is serialized."""
    light = CombinedLight(mock_entry)
    light.hass = hass
    light._light_controller = AsyncMock()
    light._zone_manager = MagicMock()
    light._zone_manager.get_light_zones.return_value = {"stage_1": ["light.bulb_1"]}
    light._zone_manager.get_all_lights.return_value = ["light.bulb_1"]
    # Mock async_write_ha_state to avoid NoEntitySpecifiedError
    light.async_write_ha_state = MagicMock()

    # Mock _control_all_zones to take some time
    async def slow_control(*args, **kwargs):
        await asyncio.sleep(0.05)

    light._control_all_zones = AsyncMock(side_effect=slow_control)

    # Start two turn_on calls concurrently
    task1 = asyncio.create_task(light.async_turn_on(brightness=100))
    task2 = asyncio.create_task(light.async_turn_on(brightness=200))

    await asyncio.gather(task1, task2)

    # Verify that _control_all_zones was called twice
    assert light._control_all_zones.call_count == 2


@pytest.mark.asyncio
async def test_lock_acquisition(hass: HomeAssistant, mock_entry):
    """Test that lock is acquired during operations."""
    light = CombinedLight(mock_entry)
    light.hass = hass
    light._light_controller = AsyncMock()
    light.async_write_ha_state = MagicMock()
    light._zone_manager = MagicMock()
    light._zone_manager.get_light_zones.return_value = {}
    light._control_all_zones = AsyncMock()

    # Mock the lock to verify acquisition
    # Use MagicMock for the lock object, but AsyncMock for context manager methods
    light._lock = MagicMock()
    light._lock.locked.return_value = False
    light._lock.__aenter__ = AsyncMock(return_value=None)
    light._lock.__aexit__ = AsyncMock(return_value=None)

    await light.async_turn_on(brightness=100)

    # Verify lock was acquired
    light._lock.__aenter__.assert_called_once()
    light._lock.__aexit__.assert_called_once()


@pytest.mark.asyncio
async def test_back_propagation_concurrency(hass: HomeAssistant, mock_entry):
    """Test that back propagation respects the lock."""
    light = CombinedLight(mock_entry)
    light.hass = hass
    light._light_controller = AsyncMock()
    light._zone_manager = MagicMock()
    light._zone_manager.get_light_zones.return_value = {"stage_1": ["light.bulb_1"]}
    light._control_all_zones = AsyncMock()

    # Mock the lock
    light._lock = MagicMock()
    light._lock.locked.return_value = False
    light._lock.__aenter__ = AsyncMock(return_value=None)
    light._lock.__aexit__ = AsyncMock(return_value=None)

    await light._async_apply_back_propagation(50.0)

    # Verify lock was acquired
    light._lock.__aenter__.assert_called_once()
    light._lock.__aexit__.assert_called_once()
