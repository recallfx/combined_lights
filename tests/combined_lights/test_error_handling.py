"""Tests for error handling in Combined Lights."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
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
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
        "stage_1_lights": ["light.bulb_1"],
        "stage_2_lights": ["light.bulb_2"],
        "stage_3_lights": [],
        "stage_4_lights": [],
    }
    return entry


class TestUnavailableEntities:
    """Tests for handling unavailable or unknown entity states."""

    async def test_coordinator_skips_unavailable_entities(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that coordinator skips unavailable entities when syncing."""
        light = CombinedLight(hass, mock_entry)

        # Set up lights with mixed states
        hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 100})
        hass.states.async_set("light.bulb_2", STATE_UNAVAILABLE)

        # Sync from HA
        light._coordinator.sync_all_lights_from_ha()

        # bulb_1 should have synced
        bulb1 = light._coordinator.get_light("light.bulb_1")
        assert bulb1 is not None
        assert bulb1.brightness == 100

        # bulb_2 should remain at default (unavailable is skipped)
        bulb2 = light._coordinator.get_light("light.bulb_2")
        assert bulb2 is not None
        # State should not be updated from unavailable

    async def test_coordinator_skips_unknown_entities(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that coordinator skips unknown entities when syncing."""
        light = CombinedLight(hass, mock_entry)

        # Set up lights with mixed states
        hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.bulb_2", STATE_UNKNOWN)

        # Sync from HA
        light._coordinator.sync_all_lights_from_ha()

        # bulb_1 should have synced
        bulb1 = light._coordinator.get_light("light.bulb_1")
        assert bulb1.brightness == 200

    async def test_is_on_ignores_unavailable(self, hass: HomeAssistant, mock_entry):
        """Test that is_on ignores unavailable entities."""
        light = CombinedLight(hass, mock_entry)
        light.hass = hass

        # One unavailable, one off
        hass.states.async_set("light.bulb_1", STATE_UNAVAILABLE)
        hass.states.async_set("light.bulb_2", STATE_OFF)

        assert light.is_on is False

        # Now set one to on
        hass.states.async_set("light.bulb_2", STATE_ON)
        assert light.is_on is True


class TestTotalFailure:
    """Tests for handling total service call failures."""

    @pytest.mark.asyncio
    async def test_async_turn_on_total_failure(self, hass: HomeAssistant, mock_entry):
        """Test that entity is not marked as on when all zones fail."""
        light = CombinedLight(hass, mock_entry)
        light.hass = hass

        # Mock controller to fail for all zones
        light._light_controller.turn_on_lights = AsyncMock(
            side_effect=Exception("Network failure")
        )

        # Mock async_write_ha_state
        light.async_write_ha_state = MagicMock()

        # Execute
        await light.async_turn_on(brightness=255)

        # Entity should NOT be marked as on since all zones failed
        assert light._attr_is_on is False


@pytest.mark.asyncio
async def test_control_all_zones_partial_failure(hass: HomeAssistant, mock_entry):
    """Test that failure in zone control is handled gracefully."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass

    # Mock controller to fail
    light._light_controller.turn_on_lights = AsyncMock(
        side_effect=Exception("Controller failed completely")
    )

    # Mock async_write_ha_state
    light.async_write_ha_state = MagicMock()

    # Execute - should not raise
    await light.async_turn_on(brightness=255)

    # Entity should NOT be marked as on since control failed
    assert light._attr_is_on is False


class TestAsyncTurnOff:
    """Tests for async_turn_off functionality."""

    @pytest.mark.asyncio
    async def test_async_turn_off_tracks_expected_states_before_call(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are tracked BEFORE awaiting service call."""
        light = CombinedLight(hass, mock_entry)
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
            return {entity: 0 for entity in lights}

        light._light_controller.turn_off_lights = mock_turn_off_lights
        light.async_write_ha_state = MagicMock()

        # Execute turn_off
        await light.async_turn_off()

        # Verify that all tracks happened BEFORE all service_calls
        track_indices = [i for i, op in enumerate(operation_order) if op[0] == "track"]
        service_indices = [
            i for i, op in enumerate(operation_order) if op[0] == "service_call"
        ]

        assert len(track_indices) == 2, f"Expected 2 track calls, got {track_indices}"
        assert len(service_indices) == 2, (
            f"Expected 2 service calls, got {service_indices}"
        )
        assert max(track_indices) < min(service_indices), (
            f"All track calls must happen before service calls. Order: {operation_order}"
        )

    @pytest.mark.asyncio
    async def test_async_turn_off_cleans_up_on_failure(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are cleaned up when turn_off fails."""
        light = CombinedLight(hass, mock_entry)
        light.hass = hass

        # Mock controller to fail
        light._light_controller.turn_off_lights = AsyncMock(
            side_effect=Exception("Network failure")
        )

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
        light = CombinedLight(hass, mock_entry)
        light.hass = hass
        light._attr_is_on = True  # Start with light on

        # Mock controller
        light._light_controller.turn_off_lights = AsyncMock(
            return_value={"light.bulb_1": 0, "light.bulb_2": 0}
        )

        light.async_write_ha_state = MagicMock()

        # Execute turn_off
        await light.async_turn_off()

        # Verify state is off
        assert light._attr_is_on is False
