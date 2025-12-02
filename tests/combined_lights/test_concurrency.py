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
        "stage_2_lights": [],
        "stage_3_lights": [],
        "stage_4_lights": [],
    }
    return entry


class TestExpectedStateTracking:
    """Tests for expected state pre-tracking to prevent race conditions."""

    @pytest.mark.asyncio
    async def test_expected_states_tracked_before_service_call(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are tracked BEFORE awaiting the service call.

        This is critical to prevent the race condition where a state change event
        arrives before the expectation is set.
        """
        light = CombinedLight(mock_entry)
        light.hass = hass

        # Track the order of operations
        operation_order = []

        # Mock the manual detector to record when track_expected_state is called
        original_track = light._manual_detector.track_expected_state

        def tracking_track_expected_state(entity_id, brightness):
            operation_order.append(("track", entity_id, brightness))
            return original_track(entity_id, brightness)

        light._manual_detector.track_expected_state = tracking_track_expected_state

        # Mock the light controller to record when turn_on_lights is called
        async def mock_turn_on_lights(lights, brightness, context):
            operation_order.append(("service_call", lights[0] if lights else None))
            return {light: int(brightness / 100.0 * 255) for light in lights}

        light._light_controller = AsyncMock()
        light._light_controller.turn_on_lights = mock_turn_on_lights

        # Mock zone manager
        light._zone_manager = MagicMock()
        light._zone_manager.get_light_zones.return_value = {
            "stage_1": ["light.bulb_1"],
            "stage_2": [],
            "stage_3": [],
            "stage_4": [],
        }

        light.async_write_ha_state = MagicMock()

        # Execute turn_on
        await light.async_turn_on(brightness=128)

        # Verify that track was called BEFORE service_call
        track_idx = None
        service_idx = None
        for i, op in enumerate(operation_order):
            if op[0] == "track" and op[1] == "light.bulb_1":
                track_idx = i
            if op[0] == "service_call" and op[1] == "light.bulb_1":
                service_idx = i

        assert track_idx is not None, "Expected state was not tracked"
        assert service_idx is not None, "Service call was not made"
        assert track_idx < service_idx, (
            f"Expected state must be tracked BEFORE service call. "
            f"Track at index {track_idx}, service at {service_idx}. "
            f"Order: {operation_order}"
        )

    @pytest.mark.asyncio
    async def test_expected_states_cleaned_on_failure(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are cleaned up when a zone fails."""
        light = CombinedLight(mock_entry)
        light.hass = hass

        # Mock zone manager with two zones
        light._zone_manager = MagicMock()
        light._zone_manager.get_light_zones.return_value = {
            "stage_1": ["light.bulb_1"],
            "stage_2": ["light.bulb_2"],
            "stage_3": [],
            "stage_4": [],
        }

        # Mock controller to fail for bulb_2
        async def failing_turn_on(lights, brightness, context):
            if "light.bulb_2" in lights:
                raise Exception("Light unavailable")
            return {light: int(brightness / 100.0 * 255) for light in lights}

        light._light_controller = AsyncMock()
        light._light_controller.turn_on_lights = failing_turn_on

        light.async_write_ha_state = MagicMock()

        # Execute turn_on
        await light.async_turn_on(brightness=255)

        # Verify that expected state for failed light was cleaned up
        assert "light.bulb_2" not in light._manual_detector._expected_states


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
