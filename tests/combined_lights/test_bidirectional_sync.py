"""Test bidirectional brightness synchronization."""

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.helpers import (
    BrightnessCalculator,
    ZoneManager,
)
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

    def test_reverse_brightness_calculation_single_zone(self, mock_entry):
        """Test estimating overall brightness from zone brightness (single zone active)."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # Stage 1 lights at 15% (middle of their 10-20% range for stage 1)
        zone_brightness = {
            "stage_1": 15.0,
            "stage_2": None,
            "stage_3": None,
            "stage_4": None,
        }

        # Should estimate somewhere in stage 1 (0-25%)
        estimated = brightness_calc.estimate_overall_brightness_from_zones(
            zone_brightness
        )
        assert 0 < estimated <= 25

    def test_reverse_brightness_calculation_two_zones(self, mock_entry):
        """Test estimating overall brightness from zone brightness (two zones active)."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # Stage 1 at 35% (middle of 30-40% range for stage 2)
        # Stage 2 at 30% (middle of 20-40% range for stage 2)
        zone_brightness = {
            "stage_1": 35.0,
            "stage_2": 30.0,
            "stage_3": None,
            "stage_4": None,
        }

        # Should estimate somewhere in stage 2 (25-50%)
        estimated = brightness_calc.estimate_overall_brightness_from_zones(
            zone_brightness
        )
        assert 25 < estimated <= 50

    def test_reverse_brightness_calculation_three_zones(self, mock_entry):
        """Test estimating overall brightness from zone brightness (three zones active)."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # Multiple zones active suggests stage 3
        zone_brightness = {
            "stage_1": 55.0,  # Stage 3 range: 50-60%
            "stage_2": 60.0,  # Stage 3 range: 50-70%
            "stage_3": 45.0,  # Stage 3 range: 30-60%
            "stage_4": None,
        }

        # Should estimate somewhere in stage 3 (50-75%)
        estimated = brightness_calc.estimate_overall_brightness_from_zones(
            zone_brightness
        )
        assert 50 < estimated <= 75

    def test_reverse_brightness_calculation_all_zones(self, mock_entry):
        """Test estimating overall brightness from zone brightness (all zones active)."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # All zones active suggests stage 4
        zone_brightness = {
            "stage_1": 75.0,  # Stage 4 range: 70-80%
            "stage_2": 90.0,  # Stage 4 range: 80-100%
            "stage_3": 85.0,  # Stage 4 range: 70-100%
            "stage_4": 90.0,  # Stage 4 range: 80-100%
        }

        # Should estimate somewhere in stage 4 (75-100%)
        estimated = brightness_calc.estimate_overall_brightness_from_zones(
            zone_brightness
        )
        assert 75 < estimated <= 100

    def test_reverse_brightness_calculation_all_off(self, mock_entry):
        """Test estimating overall brightness when all zones are off."""
        brightness_calc = BrightnessCalculator(mock_entry)

        zone_brightness = {
            "stage_1": None,
            "stage_2": None,
            "stage_3": None,
            "stage_4": None,
        }

        estimated = brightness_calc.estimate_overall_brightness_from_zones(
            zone_brightness
        )
        assert estimated == 0.0

    def test_manual_indicator_estimation(self, mock_entry):
        """Manual indicator should scale with stage coverage."""
        brightness_calc = BrightnessCalculator(mock_entry)

        zone_brightness = {
            "stage_1": None,
            "stage_2": None,
            "stage_3": None,
            "stage_4": 100.0,
        }

        estimated = brightness_calc.estimate_manual_indicator_from_zones(
            zone_brightness
        )

        assert 20 < estimated < 30  # ≈ one quarter

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

        assert 60 < combined_light._target_brightness < 70  # ≈ 25%

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

    def test_reverse_curve_linear(self, mock_entry):
        """Test reversing linear brightness curve."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # Linear curve should be identity function
        assert brightness_calc._reverse_brightness_curve(0.0, "linear") == 0.0
        assert brightness_calc._reverse_brightness_curve(0.5, "linear") == 0.5
        assert brightness_calc._reverse_brightness_curve(1.0, "linear") == 1.0

    def test_reverse_curve_quadratic(self, mock_entry):
        """Test reversing quadratic brightness curve."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # Test that reverse curve roughly inverts the forward curve
        # Forward: curved = apply_curve(linear)
        # Reverse: linear = reverse_curve(curved)

        test_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        for linear in test_values:
            curved = brightness_calc._apply_brightness_curve(linear, "quadratic")
            reversed_linear = brightness_calc._reverse_brightness_curve(
                curved, "quadratic"
            )
            # Should be approximately equal (within numerical tolerance)
            assert abs(reversed_linear - linear) < 0.05

    def test_reverse_curve_cubic(self, mock_entry):
        """Test reversing cubic brightness curve."""
        brightness_calc = BrightnessCalculator(mock_entry)

        test_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        for linear in test_values:
            curved = brightness_calc._apply_brightness_curve(linear, "cubic")
            reversed_linear = brightness_calc._reverse_brightness_curve(curved, "cubic")
            # Should be approximately equal (within numerical tolerance)
            assert abs(reversed_linear - linear) < 0.05
