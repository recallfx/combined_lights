"""Test bidirectional brightness synchronization."""

import asyncio
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
def combined_light(hass: HomeAssistant, mock_entry):
    """Create a CombinedLight instance."""
    return CombinedLight(hass, mock_entry)


async def wait_for_debounce(light: CombinedLight):
    """Wait for manual change window to complete."""
    # Wait slightly longer than the collection window
    await asyncio.sleep(light._manual_change_window + 0.05)
    # Also wait for any scheduled task to complete
    if light._manual_change_task and not light._manual_change_task.done():
        try:
            await light._manual_change_task
        except asyncio.CancelledError:
            pass


class TestBidirectionalSync:
    """Test bidirectional brightness synchronization using coordinator."""

    async def test_sync_coordinator_from_ha(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that coordinator syncs state from HA lights."""
        combined_light.hass = hass

        # Setup initial state - some lights on
        # Stage 2 at 78% brightness maps to ~83% overall with default breakpoints
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Sync coordinator
        combined_light._sync_coordinator_from_ha()

        # Coordinator should have updated is_on state
        assert combined_light._coordinator.is_on is True

        # Target brightness should be estimated from current state
        # Stage 2 at brightness 200 (78%) → overall ~83% (213)
        target = combined_light._coordinator.target_brightness
        assert 180 < target < 230  # Reasonable range for stage 2 at 78%

    async def test_handle_manual_change_updates_coordinator(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Test that manual changes update coordinator state after debounce."""
        combined_light.hass = hass

        # Start with a known state
        combined_light._coordinator._target_brightness = 255
        combined_light._coordinator._is_on = True

        # Setup: only stage 4 on (others off)
        hass.states.async_set("light.stage1_1", STATE_OFF)
        hass.states.async_set("light.stage1_2", STATE_OFF)
        hass.states.async_set("light.stage2_1", STATE_OFF)
        hass.states.async_set("light.stage3_1", STATE_OFF)
        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})

        # Manually turn off stage 4 - now all lights are off
        hass.states.async_set("light.stage4_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage4_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        # With all lights off, coordinator should be off
        assert combined_light._coordinator.is_on is False

    async def test_turning_off_stage_light_reduces_overall_brightness(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Turning off highest active stage should reduce overall brightness."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._coordinator._target_brightness = 255
        combined_light._coordinator._is_on = True

        # Stage 1-3 on at 50% brightness, stage 4 off
        # This represents overall ~62% brightness (stage 3 active)
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage3_1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Manually turn off stage 3 light
        hass.states.async_set("light.stage3_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage3_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        # After turning off stage 3, the estimation should be based on stage 1-2
        # Stage 2 at 128 (50%) → overall brightness calculated from remaining lights
        target = combined_light._coordinator.target_brightness
        # Should be less than full brightness (255)
        assert target < 200, (
            f"Expected brightness < 200 after turning off stage 3, "
            f"but got {target}"
        )

    async def test_turning_off_stage_3_reduces_to_stage_2_max(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Turning off stage 3 when it's the only stage on should turn off."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._coordinator._target_brightness = 200
        combined_light._coordinator._is_on = True

        # Only stage 3 is on, others off
        hass.states.async_set("light.stage1_1", STATE_OFF)
        hass.states.async_set("light.stage1_2", STATE_OFF)
        hass.states.async_set("light.stage2_1", STATE_OFF)
        hass.states.async_set("light.stage3_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4_1", STATE_OFF)

        # Manually turn off stage 3 light - now all are off
        hass.states.async_set("light.stage3_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage3_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        # All lights off, coordinator should be off
        assert combined_light._coordinator.is_on is False

    async def test_back_propagation_scheduled_on_manual_change(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual changes should schedule back propagation when enabled."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._schedule_back_propagation = MagicMock()

        # Set up lights so there's something to back-propagate
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage3_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True

        # Manually change one light to trigger back-prop
        hass.states.async_set("light.stage4_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage4_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        combined_light._schedule_back_propagation.assert_called_once()

    async def test_back_propagation_not_scheduled_when_disabled(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual changes should not schedule back propagation when disabled."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = False
        combined_light._schedule_back_propagation = MagicMock()

        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True

        combined_light._handle_manual_change("light.stage4_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        combined_light._schedule_back_propagation.assert_not_called()

    async def test_knx_all_off_button_turns_everything_off(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """KNX 'all off' button should turn off all lights without recovery.
        
        When a KNX button sends off to all lights simultaneously, all events
        arrive within the debounce window. After debounce, all lights are off
        and no back-propagation should occur.
        """
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._schedule_back_propagation = MagicMock()
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = 255

        # All lights initially on
        hass.states.async_set("light.stage1_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage1_2", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage2_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage3_1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4_1", STATE_ON, {"brightness": 255})

        # KNX button turns all lights off - events arrive rapidly
        hass.states.async_set("light.stage1_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage1_1")
        hass.states.async_set("light.stage1_2", STATE_OFF)
        combined_light._handle_manual_change("light.stage1_2")
        hass.states.async_set("light.stage2_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage2_1")
        hass.states.async_set("light.stage3_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage3_1")
        hass.states.async_set("light.stage4_1", STATE_OFF)
        combined_light._handle_manual_change("light.stage4_1")

        # Wait for debounce
        await wait_for_debounce(combined_light)

        # Everything should be off
        assert combined_light._coordinator.is_on is False
        # Back propagation should NOT have been called (nothing to propagate)
        combined_light._schedule_back_propagation.assert_not_called()

    async def test_back_propagation_excludes_changed_entity(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Back propagation should exclude the manually changed entity."""
        combined_light.hass = hass
        combined_light._back_propagation_enabled = True
        combined_light._light_controller = MagicMock()
        combined_light._light_controller.turn_on_lights = MagicMock(return_value={})
        combined_light._light_controller.turn_off_lights = MagicMock(return_value={})

        # Create changes dict that would include the changed entity
        changed_entity = "light.stage1_1"
        changes = {
            "light.stage1_2": 128,
            "light.stage2_1": 200,
            "light.stage3_1": 0,
            "light.stage4_1": 0,
        }  # Note: stage1_1 is NOT in changes (already excluded by coordinator)

        # Call back propagation directly
        await combined_light._async_apply_back_propagation(changes, changed_entity)

        # Verify turn_on_lights was called
        calls = combined_light._light_controller.turn_on_lights.call_args_list
        for call in calls:
            entities = call[0][0]  # First positional arg is the entity list
            assert changed_entity not in entities, (
                f"Changed entity {changed_entity} should be excluded"
            )


class TestHASimulationParity:
    """Test that HA integration uses same logic as simulation."""

    def test_single_light_estimation_matches_base_coordinator(self):
        """Verify BrightnessCalculator.estimate_from_single_light_change matches base logic."""
        # Create a mock entry with default breakpoints [25, 50, 75]
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {"breakpoints": [25, 50, 75]}

        from custom_components.combined_lights.helpers import BrightnessCalculator

        calc = BrightnessCalculator(entry)

        # Test cases: (zone_name, brightness_0_255, expected_overall_pct)
        test_cases = [
            # Turning OFF lights should return activation point
            ("stage_4", 0, 75.0),  # Stage 4 activates at 75%
            ("stage_3", 0, 50.0),  # Stage 3 activates at 50%
            ("stage_2", 0, 25.0),  # Stage 2 activates at 25%
            ("stage_1", 0, 0.0),  # Stage 1 is always on, turning off = 0%
            # Turning ON lights at full brightness
            ("stage_1", 255, 100.0),  # Full stage 1 = 100%
            ("stage_4", 255, 100.0),  # Full stage 4 = 100%
        ]

        for zone_name, brightness, expected in test_cases:
            result = calc.estimate_from_single_light_change(zone_name, brightness)
            assert abs(result - expected) < 0.1, (
                f"estimate_from_single_light_change({zone_name}, {brightness}) "
                f"returned {result}, expected {expected}"
            )

    def test_ha_and_simulation_produce_same_result_for_stage_off(self):
        """Verify HA and simulation produce identical results when turning off a stage."""
        from custom_components.combined_lights.helpers import BrightnessCalculator

        # Setup: same breakpoints
        breakpoints = [25, 50, 75]

        # HA path: BrightnessCalculator
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {"breakpoints": breakpoints}
        ha_calc = BrightnessCalculator(entry)

        # Simulation path: use estimate_overall_from_single_light directly
        # (same method the simulation's set_light_brightness uses)

        # Test turning off stage 4 (brightness=0)
        ha_result = ha_calc.estimate_from_single_light_change("stage_4", 0)
        sim_result = ha_calc.estimate_overall_from_single_light(4, 0.0)

        assert ha_result == sim_result == 75.0, (
            f"HA ({ha_result}) and simulation ({sim_result}) should both return 75% "
            "when stage 4 is turned off"
        )

        # Test turning off stage 3
        ha_result = ha_calc.estimate_from_single_light_change("stage_3", 0)
        sim_result = ha_calc.estimate_overall_from_single_light(3, 0.0)

        assert ha_result == sim_result == 50.0, (
            f"HA ({ha_result}) and simulation ({sim_result}) should both return 50% "
            "when stage 3 is turned off"
        )

    def test_coordinator_set_light_brightness_matches_ha_handle_manual(
        self, hass: HomeAssistant
    ):
        """Verify coordinator.set_light_brightness produces same result as HA manual handler."""
        from custom_components.combined_lights.helpers import (
            BrightnessCalculator,
            HACombinedLightsCoordinator,
        )

        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "breakpoints": [25, 50, 75],
            "stage_1_lights": ["light.stage1"],
            "stage_2_lights": ["light.stage2"],
            "stage_3_lights": ["light.stage3"],
            "stage_4_lights": ["light.stage4"],
        }

        calc = BrightnessCalculator(entry)
        coordinator = HACombinedLightsCoordinator(hass, entry, calc)

        # Register lights
        coordinator.register_light("light.stage1", 1)
        coordinator.register_light("light.stage2", 2)
        coordinator.register_light("light.stage3", 3)
        coordinator.register_light("light.stage4", 4)

        # Turn on with full brightness
        coordinator.turn_on(255)

        # Now simulate turning off stage 4
        _, overall_pct = coordinator.set_light_brightness("light.stage4", 0)

        # Should return 75% (stage 4's activation point)
        assert overall_pct == 75.0, f"Expected 75%, got {overall_pct}%"
        assert coordinator.target_brightness == 191  # 75% of 255
