"""Tests for error handling in Combined Lights."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from custom_components.combined_lights.light import CombinedLight
from custom_components.combined_lights.const import CONF_ENABLE_BACK_PROPAGATION
from custom_components.combined_lights.helpers import ZoneManager


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
        "stage_3_lights": [],
        "stage_4_lights": [],
    }
    return entry


class TestUnavailableEntities:
    """Tests for handling unavailable or unknown entity states."""

    async def test_zone_manager_skips_unavailable_entities(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that ZoneManager skips unavailable entities when calculating brightness."""
        zone_manager = ZoneManager(mock_entry)

        # Set up lights with mixed states
        hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 100})
        hass.states.async_set("light.bulb_2", STATE_UNAVAILABLE)

        # Get average brightness - should only consider bulb_1
        result = zone_manager.get_average_brightness(
            hass, ["light.bulb_1", "light.bulb_2"]
        )
        assert result == 100  # Only bulb_1 is counted

    async def test_zone_manager_skips_unknown_entities(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that ZoneManager skips unknown entities when calculating brightness."""
        zone_manager = ZoneManager(mock_entry)

        # Set up lights with mixed states
        hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.bulb_2", STATE_UNKNOWN)

        # Get average brightness - should only consider bulb_1
        result = zone_manager.get_average_brightness(
            hass, ["light.bulb_1", "light.bulb_2"]
        )
        assert result == 200

    async def test_zone_manager_all_unavailable_returns_none(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that all unavailable entities returns None."""
        zone_manager = ZoneManager(mock_entry)

        # All lights unavailable
        hass.states.async_set("light.bulb_1", STATE_UNAVAILABLE)
        hass.states.async_set("light.bulb_2", STATE_UNAVAILABLE)

        result = zone_manager.get_average_brightness(
            hass, ["light.bulb_1", "light.bulb_2"]
        )
        assert result is None

    async def test_is_any_light_on_ignores_unavailable(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that is_any_light_on ignores unavailable entities."""
        zone_manager = ZoneManager(mock_entry)

        # One unavailable, one off
        hass.states.async_set("light.bulb_1", STATE_UNAVAILABLE)
        hass.states.async_set("light.bulb_2", STATE_OFF)

        assert zone_manager.is_any_light_on(hass) is False

        # Now set one to on
        hass.states.async_set("light.bulb_2", STATE_ON)
        assert zone_manager.is_any_light_on(hass) is True


class TestTotalFailure:
    """Tests for handling total service call failures."""

    @pytest.mark.asyncio
    async def test_async_turn_on_total_failure(self, hass: HomeAssistant, mock_entry):
        """Test that entity is not marked as on when all zones fail."""
        light = CombinedLight(mock_entry)
        light.hass = hass
        light._light_controller = AsyncMock()
        light._zone_manager = MagicMock()

        # Setup zones
        light._zone_manager.get_light_zones.return_value = {
            "stage_1": ["light.bulb_1"],
            "stage_2": ["light.bulb_2"],
            "stage_3": [],
            "stage_4": [],
        }

        # Mock controller to fail for all zones
        light._light_controller.turn_on_lights.side_effect = Exception(
            "Network failure"
        )

        light._build_zone_brightness_map = MagicMock(
            return_value={
                "stage_1": 50.0,
                "stage_2": 50.0,
                "stage_3": 0.0,
                "stage_4": 0.0,
            }
        )

        # Mock async_write_ha_state
        light.async_write_ha_state = MagicMock()

        # Execute
        await light.async_turn_on(brightness=255)

        # Entity should NOT be marked as on since all zones failed
        assert light._attr_is_on is False


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


class TestAsyncTurnOff:
    """Tests for async_turn_off functionality."""

    @pytest.mark.asyncio
    async def test_async_turn_off_tracks_expected_states_before_call(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are tracked BEFORE awaiting service call."""
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

        # Mock the light controller to record when turn_off_lights is called
        async def mock_turn_off_lights(lights, context):
            for entity in lights:
                operation_order.append(("service_call", entity))
            return {light: 0 for light in lights}

        light._light_controller = AsyncMock()
        light._light_controller.turn_off_lights = mock_turn_off_lights

        # Mock zone manager
        light._zone_manager = MagicMock()
        light._zone_manager.get_all_lights.return_value = ["light.bulb_1", "light.bulb_2"]

        light.async_write_ha_state = MagicMock()

        # Execute turn_off
        await light.async_turn_off()

        # Verify that all tracks happened BEFORE all service_calls
        track_indices = [i for i, op in enumerate(operation_order) if op[0] == "track"]
        service_indices = [i for i, op in enumerate(operation_order) if op[0] == "service_call"]

        assert len(track_indices) == 2, f"Expected 2 track calls, got {track_indices}"
        assert len(service_indices) == 2, f"Expected 2 service calls, got {service_indices}"
        assert max(track_indices) < min(service_indices), (
            f"All track calls must happen before service calls. Order: {operation_order}"
        )

    @pytest.mark.asyncio
    async def test_async_turn_off_cleans_up_on_failure(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are cleaned up when turn_off fails."""
        light = CombinedLight(mock_entry)
        light.hass = hass

        # Mock zone manager
        light._zone_manager = MagicMock()
        light._zone_manager.get_all_lights.return_value = ["light.bulb_1", "light.bulb_2"]

        # Mock controller to fail
        light._light_controller = AsyncMock()
        light._light_controller.turn_off_lights.side_effect = Exception("Network failure")

        light.async_write_ha_state = MagicMock()

        # Execute turn_off
        await light.async_turn_off()

        # Verify that expected states were cleaned up
        assert "light.bulb_1" not in light._manual_detector._expected_states
        assert "light.bulb_2" not in light._manual_detector._expected_states

    @pytest.mark.asyncio
    async def test_async_turn_off_sets_attr_is_on_false(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that async_turn_off sets _attr_is_on to False."""
        light = CombinedLight(mock_entry)
        light.hass = hass
        light._attr_is_on = True  # Start with light on

        # Mock zone manager
        light._zone_manager = MagicMock()
        light._zone_manager.get_all_lights.return_value = ["light.bulb_1"]

        # Mock controller
        light._light_controller = AsyncMock()
        light._light_controller.turn_off_lights.return_value = {"light.bulb_1": 0}

        light.async_write_ha_state = MagicMock()

        # Execute turn_off
        await light.async_turn_off()

        # Verify state is off
        assert light._attr_is_on is False
