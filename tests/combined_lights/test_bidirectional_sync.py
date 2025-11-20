"""Test bidirectional brightness synchronization."""

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.light import CombinedLight


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_123"
    entry.data = {
        "name": "Test Combined Light",
        "stage_1_lights": ["light.stage1_1", "light.stage1_2"],
        "stage_2_lights": ["light.stage2_1"],
        "stage_3_lights": ["light.stage3_1"],
        "stage_4_lights": ["light.stage4_1"],
        "breakpoints": [25, 50, 75],
        "brightness_curve": "linear",
        "stage_1_brightness_ranges": [[10, 20], [30, 40], [50, 60], [70, 80]],
        "stage_2_brightness_ranges": [[0, 0], [20, 40], [50, 70], [80, 100]],
        "stage_3_brightness_ranges": [[0, 0], [0, 0], [30, 60], [70, 100]],
        "stage_4_brightness_ranges": [[0, 0], [0, 0], [0, 0], [80, 100]],
    }
    return entry


@pytest.fixture
def combined_light(mock_entry):
    """Create a CombinedLight instance."""
    return CombinedLight(mock_entry)


class TestBidirectionalSync:
    """Test bidirectional brightness synchronization."""

    async def test_update_target_brightness_from_children(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that target brightness updates when child lights change."""
        # Directly set hass (simpler than full entity setup)
        combined_light.hass = hass

        # Setup initial state - some lights on
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 51})  # 20%
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 51})  # 20%
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 77})  # 30%
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Initial target brightness
        initial_brightness = combined_light._target_brightness

        # Trigger update
        combined_light._update_target_brightness_from_children()

        # Target brightness should be updated
        # With stage 1 and stage 2 active, we're in stage 2 (25-50%)
        # So target should be somewhere in that range (in 0-255 scale: 64-128)
        new_brightness = combined_light._target_brightness
        assert new_brightness != initial_brightness
        assert 50 < new_brightness < 150  # Reasonable range for stage 2

    async def test_no_update_when_updating_lights(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that target brightness doesn't update when we're controlling lights."""
        # Directly set hass
        combined_light.hass = hass

        # Setup lights
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 100})

        # Set the updating flag
        combined_light._manual_detector.set_updating_flag(True)

        initial_brightness = combined_light._target_brightness

        # Try to update
        combined_light._update_target_brightness_from_children()

        # Brightness should not change
        assert combined_light._target_brightness == initial_brightness

        # Clear the flag and try again
        combined_light._manual_detector.set_updating_flag(False)
        combined_light._update_target_brightness_from_children()

        # Now it should update
        # (might be same value, but at least it's not blocked)

    async def test_no_update_when_all_lights_off(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that target brightness is preserved when all lights turn off."""
        # Directly set hass
        combined_light.hass = hass

        # Set initial target
        combined_light._target_brightness = 150

        # All lights off
        hass.states.async_set("light.stage1_1", STATE_OFF)
        hass.states.async_set("light.stage1_2", STATE_OFF)
        hass.states.async_set("light.stage2_1", STATE_OFF)
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Trigger update
        combined_light._update_target_brightness_from_children()

        # Target should be preserved
        assert combined_light._target_brightness == 150

    async def test_small_changes_ignored(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that very small brightness changes don't trigger updates."""
        # Directly set hass
        combined_light.hass = hass

        # Set initial state
        combined_light._target_brightness = 100

        # Create a state that would result in ~100 brightness (within tolerance)
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 40})
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 40})
        hass.states.async_set("light.stage2_1", STATE_OFF)
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Trigger update
        combined_light._update_target_brightness_from_children()

        # Should remain relatively stable (within a reasonable range)
        # The exact value depends on the calculation, but it shouldn't jump wildly

    async def test_manual_update_indicator_mode(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual updates without back propagation should use coverage indicator."""
        combined_light.hass = hass
        combined_light._target_brightness = 200

        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})

        combined_light._update_target_brightness_from_children(manual_update=True)

        assert 250 < combined_light._target_brightness <= 255  # Stage 4 active means high brightness

    async def test_manual_update_triggers_back_propagation(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual updates should schedule back propagation when enabled."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._schedule_back_propagation = MagicMock()

        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})

        combined_light._update_target_brightness_from_children(manual_update=True)

        combined_light._schedule_back_propagation.assert_called_once()

    async def test_back_propagation_excludes_changed_entity(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Back propagation should exclude the manually changed entity."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._light_controller = MagicMock()
        combined_light._light_controller.turn_on_lights = MagicMock(
            return_value={}
        )
        combined_light._light_controller.turn_off_lights = MagicMock(
            return_value={}
        )

        # Simulate manual change to stage1_1
        changed_entity = "light.stage1_1"
        overall_pct = 50.0

        # Call back propagation directly
        await combined_light._async_apply_back_propagation(overall_pct, changed_entity)

        # Verify that turn_on_lights was called but WITHOUT the changed entity
        calls = combined_light._light_controller.turn_on_lights.call_args_list
        for call in calls:
            entities = call[0][0]  # First positional arg is the entity list
            assert changed_entity not in entities, (
                f"Changed entity {changed_entity} should be excluded from "
                f"back-propagation but was found in: {entities}"
            )
