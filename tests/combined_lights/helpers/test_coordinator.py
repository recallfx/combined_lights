"""Tests for BrightnessCalculator and HACombinedLightsCoordinator."""

from unittest.mock import MagicMock

import pytest

from custom_components.combined_lights.helpers import (
    BrightnessCalculator,
    HACombinedLightsCoordinator,
    LightState,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = {
        "breakpoints": [30, 60, 90],
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
    }
    return entry


@pytest.fixture
def calculator(mock_config_entry):
    """Create a BrightnessCalculator instance."""
    return BrightnessCalculator(mock_config_entry)


@pytest.fixture
def coordinator(mock_config_entry, calculator):
    """Create a HACombinedLightsCoordinator instance."""
    hass = MagicMock()
    coord = HACombinedLightsCoordinator(hass, mock_config_entry, calculator)
    # Register default lights for testing
    for i in range(1, 5):
        coord.register_light(f"light.stage_{i}", i)
    return coord


class TestLightState:
    """Test LightState dataclass."""

    def test_brightness_pct_when_off(self):
        """Test brightness percentage when light is off."""
        light = LightState(entity_id="light.test", stage=1, is_on=False, brightness=0)
        assert light.brightness_pct == 0.0

    def test_brightness_pct_at_full(self):
        """Test brightness percentage at full brightness."""
        light = LightState(entity_id="light.test", stage=1, is_on=True, brightness=255)
        assert light.brightness_pct == 100.0

    def test_brightness_pct_at_half(self):
        """Test brightness percentage at half brightness."""
        light = LightState(entity_id="light.test", stage=1, is_on=True, brightness=128)
        assert 50.0 < light.brightness_pct < 51.0  # ~50.2%

    def test_to_dict(self):
        """Test dictionary conversion."""
        light = LightState(entity_id="light.test", stage=2, is_on=True, brightness=255)
        d = light.to_dict()
        assert d["entity_id"] == "light.test"
        assert d["stage"] == 2
        assert d["state"] == "on"
        assert d["brightness"] == 255
        assert d["brightness_pct"] == 100


class TestBrightnessCalculator:
    """Test BrightnessCalculator class."""

    def test_get_stage_from_brightness_stage_1(self, calculator):
        """Test stage detection for stage 1 (0-30%)."""
        assert calculator.get_stage_from_brightness(0) == 0
        assert calculator.get_stage_from_brightness(15) == 0
        assert calculator.get_stage_from_brightness(30) == 0

    def test_get_stage_from_brightness_stage_2(self, calculator):
        """Test stage detection for stage 2 (30-60%)."""
        assert calculator.get_stage_from_brightness(31) == 1
        assert calculator.get_stage_from_brightness(45) == 1
        assert calculator.get_stage_from_brightness(60) == 1

    def test_get_stage_from_brightness_stage_3(self, calculator):
        """Test stage detection for stage 3 (60-90%)."""
        assert calculator.get_stage_from_brightness(61) == 2
        assert calculator.get_stage_from_brightness(75) == 2
        assert calculator.get_stage_from_brightness(90) == 2

    def test_get_stage_from_brightness_stage_4(self, calculator):
        """Test stage detection for stage 4 (90-100%)."""
        assert calculator.get_stage_from_brightness(91) == 3
        assert calculator.get_stage_from_brightness(95) == 3
        assert calculator.get_stage_from_brightness(100) == 3

    def test_calculate_zone_brightness_stage_1_always_on(self, calculator):
        """Stage 1 should always be on when overall brightness > 0."""
        assert calculator.calculate_zone_brightness(1, 1) > 0
        assert calculator.calculate_zone_brightness(50, 1) > 0
        assert calculator.calculate_zone_brightness(100, 1) > 0

    def test_calculate_zone_brightness_stage_2_activation(self, calculator):
        """Stage 2 activates at 30%."""
        # Below activation point
        assert calculator.calculate_zone_brightness(29, 2) == 0
        assert calculator.calculate_zone_brightness(30, 2) == 0
        # Above activation point
        assert calculator.calculate_zone_brightness(31, 2) > 0

    def test_calculate_zone_brightness_stage_3_activation(self, calculator):
        """Stage 3 activates at 60%."""
        # Below activation point
        assert calculator.calculate_zone_brightness(59, 3) == 0
        assert calculator.calculate_zone_brightness(60, 3) == 0
        # Above activation point
        assert calculator.calculate_zone_brightness(61, 3) > 0

    def test_calculate_zone_brightness_stage_4_activation(self, calculator):
        """Stage 4 activates at 90%."""
        # Below activation point
        assert calculator.calculate_zone_brightness(89, 4) == 0
        assert calculator.calculate_zone_brightness(90, 4) == 0
        # Above activation point
        assert calculator.calculate_zone_brightness(91, 4) > 0

    def test_calculate_zone_brightness_at_100_percent(self, calculator):
        """All stages should be at 100% when overall is 100%."""
        assert calculator.calculate_zone_brightness(100, 1) == 100
        assert calculator.calculate_zone_brightness(100, 2) == 100
        assert calculator.calculate_zone_brightness(100, 3) == 100
        assert calculator.calculate_zone_brightness(100, 4) == 100

    def test_calculate_zone_brightness_with_string_zone_name(self, calculator):
        """Test zone brightness with string zone name."""
        assert calculator.calculate_zone_brightness(100, "stage_1") == 100
        assert calculator.calculate_zone_brightness(100, "stage_2") == 100

    def test_estimate_overall_from_single_light_stage_1_off(self, calculator):
        """Stage 1 OFF should return 0%."""
        result = calculator.estimate_overall_from_single_light(1, 0)
        assert result == 0.0

    def test_estimate_overall_from_single_light_stage_2_off(self, calculator):
        """Stage 2 OFF should return 30% (activation point)."""
        result = calculator.estimate_overall_from_single_light(2, 0)
        assert result == 30.0

    def test_estimate_overall_from_single_light_stage_3_off(self, calculator):
        """Stage 3 OFF should return 60% (activation point)."""
        result = calculator.estimate_overall_from_single_light(3, 0)
        assert result == 60.0

    def test_estimate_overall_from_single_light_stage_4_off(self, calculator):
        """Stage 4 OFF should return 90% (activation point)."""
        result = calculator.estimate_overall_from_single_light(4, 0)
        assert result == 90.0

    def test_estimate_overall_from_single_light_roundtrip(self, calculator):
        """Test that estimate_overall -> calculate_zone gives same brightness."""
        test_cases = [
            (1, 50),
            (1, 100),
            (2, 50),
            (2, 100),
            (3, 50),
            (3, 100),
            (4, 50),
            (4, 100),
        ]

        for stage, brightness_pct in test_cases:
            overall = calculator.estimate_overall_from_single_light(
                stage, brightness_pct
            )
            calculated = calculator.calculate_zone_brightness(overall, stage)
            assert abs(calculated - brightness_pct) < 1.0, (
                f"Stage {stage} at {brightness_pct}%: "
                f"overall={overall:.1f}%, calculated back={calculated:.1f}%"
            )

    def test_estimate_overall_from_zones_all_off(self, calculator):
        """All zones off should return 0%."""
        result = calculator.estimate_overall_from_zones(
            {1: None, 2: None, 3: None, 4: None}
        )
        assert result == 0.0

    def test_estimate_overall_from_zones_stage_1_only(self, calculator):
        """Only stage 1 on should estimate overall based on stage 1 brightness."""
        result = calculator.estimate_overall_from_zones(
            {1: 50.0, 2: None, 3: None, 4: None}
        )
        assert 45 < result < 55  # Should be around 50%

    def test_estimate_overall_from_zones_highest_active(self, calculator):
        """Should use highest active stage for estimation."""
        result = calculator.estimate_overall_from_zones(
            {1: 100.0, 2: 100.0, 3: 50.0, 4: None}
        )
        # Stage 3 is highest active, 50% brightness within stage 3 range
        assert 60 < result < 100

    def test_estimate_overall_brightness_from_zones_string_keys(self, calculator):
        """Test estimate with string zone names."""
        result = calculator.estimate_overall_brightness_from_zones(
            {"stage_1": 50.0, "stage_2": None, "stage_3": None, "stage_4": None}
        )
        assert 45 < result < 55

    def test_estimate_from_single_light_change(self, calculator):
        """Test estimate from single light change with zone name."""
        result = calculator.estimate_from_single_light_change("stage_2", 128)
        assert 30 < result < 100

    def test_apply_brightness_curve_linear(self, calculator):
        """Linear curve should be identity."""
        assert calculator._apply_brightness_curve(0.0, "linear") == 0.0
        assert calculator._apply_brightness_curve(0.5, "linear") == 0.5
        assert calculator._apply_brightness_curve(1.0, "linear") == 1.0

    def test_apply_brightness_curve_quadratic(self, calculator):
        """Quadratic curve should be x^2."""
        assert calculator._apply_brightness_curve(0.0, "quadratic") == 0.0
        assert calculator._apply_brightness_curve(0.5, "quadratic") == 0.25
        assert calculator._apply_brightness_curve(1.0, "quadratic") == 1.0

    def test_apply_brightness_curve_cubic(self, calculator):
        """Cubic curve should be x^3."""
        assert calculator._apply_brightness_curve(0.0, "cubic") == 0.0
        assert calculator._apply_brightness_curve(0.5, "cubic") == 0.125
        assert calculator._apply_brightness_curve(1.0, "cubic") == 1.0

    def test_apply_brightness_curve_sqrt(self, calculator):
        """Sqrt curve should be x^0.5."""
        assert calculator._apply_brightness_curve(0.0, "sqrt") == 0.0
        assert abs(calculator._apply_brightness_curve(0.25, "sqrt") - 0.5) < 0.01
        assert calculator._apply_brightness_curve(1.0, "sqrt") == 1.0

    def test_apply_brightness_curve_cbrt(self, calculator):
        """Cbrt curve should be x^(1/3)."""
        assert calculator._apply_brightness_curve(0.0, "cbrt") == 0.0
        assert abs(calculator._apply_brightness_curve(0.125, "cbrt") - 0.5) < 0.01
        assert calculator._apply_brightness_curve(1.0, "cbrt") == 1.0

    def test_reverse_brightness_curve_roundtrip(self, calculator):
        """Test that apply->reverse gives original value."""
        for curve in ["linear", "quadratic", "cubic", "sqrt", "cbrt"]:
            for value in [0.1, 0.3, 0.5, 0.7, 0.9]:
                curved = calculator._apply_brightness_curve(value, curve)
                reversed_value = calculator._reverse_brightness_curve(curved, curve)
                assert abs(reversed_value - value) < 0.01, (
                    f"Curve {curve}, value {value}: "
                    f"curved={curved:.3f}, reversed={reversed_value:.3f}"
                )


class TestHACombinedLightsCoordinator:
    """Test HACombinedLightsCoordinator class."""

    def test_initial_state_is_off(self, coordinator):
        """Coordinator should start in OFF state."""
        assert not coordinator.is_on
        assert coordinator.current_stage == 0

    def test_turn_on_default_brightness(self, coordinator):
        """Turn on with default brightness."""
        coordinator.turn_on()

        assert coordinator.is_on
        assert coordinator.target_brightness == 255
        assert coordinator.target_brightness_pct == 100.0

    def test_turn_on_with_brightness(self, coordinator):
        """Turn on with specific brightness."""
        coordinator.turn_on(brightness=128)

        assert coordinator.is_on
        assert coordinator.target_brightness == 128
        assert 50.0 < coordinator.target_brightness_pct < 51.0

    def test_turn_off(self, coordinator):
        """Turn off should set all lights to off."""
        coordinator.turn_on()
        coordinator.turn_off()

        assert not coordinator.is_on
        for light in coordinator.get_lights():
            assert not light.is_on
            assert light.brightness == 0

    def test_current_stage_calculation(self, coordinator):
        """Test current stage is calculated from brightness."""
        # Stage 1: 0-30%
        coordinator.turn_on(brightness=int(15 / 100 * 255))
        assert coordinator.current_stage == 1

        # Stage 2: 30-60%
        coordinator.turn_on(brightness=int(45 / 100 * 255))
        assert coordinator.current_stage == 2

        # Stage 3: 60-90%
        coordinator.turn_on(brightness=int(75 / 100 * 255))
        assert coordinator.current_stage == 3

        # Stage 4: 90-100%
        coordinator.turn_on(brightness=int(95 / 100 * 255))
        assert coordinator.current_stage == 4

    def test_apply_brightness_to_lights(self, coordinator):
        """Test brightness is distributed to lights based on stage."""
        coordinator.turn_on(brightness=int(50 / 100 * 255))

        lights = {light.entity_id: light for light in coordinator.get_lights()}

        assert lights["light.stage_1"].is_on
        assert lights["light.stage_2"].is_on
        assert not lights["light.stage_3"].is_on
        assert not lights["light.stage_4"].is_on

    def test_set_light_brightness_updates_overall(self, coordinator):
        """Setting single light brightness updates overall state."""
        coordinator.turn_on()

        # Set stage 2 to 50% brightness
        _, overall_pct = coordinator.set_light_brightness("light.stage_2", 128)

        # Overall should be somewhere in stage 2 range
        assert 30 < overall_pct < 100

    def test_set_light_brightness_off_returns_activation_point(self, coordinator):
        """Turning off a light should set overall to activation point."""
        coordinator.turn_on()

        # Turn off stage 3
        _, overall_pct = coordinator.set_light_brightness("light.stage_3", 0)

        # Stage 3 activates at 60%, so overall should be 60%
        assert overall_pct == 60.0

    def test_handle_manual_light_change(self, coordinator):
        """Test handling manual light change with back-propagation."""
        coordinator.turn_on()

        overall_pct, back_prop = coordinator.handle_manual_light_change(
            "light.stage_2", 128
        )

        assert 30 < overall_pct < 100
        assert "light.stage_1" in back_prop
        assert "light.stage_2" not in back_prop  # Excluded

    def test_apply_back_propagation(self, coordinator):
        """Back-propagation updates other lights based on overall brightness."""
        coordinator.turn_on(brightness=int(50 / 100 * 255))

        # Manually set stage 1 to different value
        coordinator._lights["light.stage_1"].brightness = 200

        # Apply back-propagation excluding stage 1
        changes = coordinator.apply_back_propagation(exclude_entity_id="light.stage_1")

        # Stage 1 should not be in changes
        assert "light.stage_1" not in changes
        # Other stages should be updated
        assert "light.stage_2" in changes

    def test_get_lights(self, coordinator):
        """Test getting all light states."""
        lights = coordinator.get_lights()

        assert len(lights) == 4
        entity_ids = [light.entity_id for light in lights]
        assert "light.stage_1" in entity_ids
        assert "light.stage_4" in entity_ids

    def test_get_light(self, coordinator):
        """Test getting a specific light state."""
        light = coordinator.get_light("light.stage_2")

        assert light is not None
        assert light.entity_id == "light.stage_2"
        assert light.stage == 2

    def test_get_light_not_found(self, coordinator):
        """Test getting non-existent light returns None."""
        light = coordinator.get_light("light.nonexistent")
        assert light is None

    def test_get_lights_by_stage(self, coordinator):
        """Test getting lights grouped by stage."""
        by_stage = coordinator.get_lights_by_stage()

        assert len(by_stage[1]) == 1
        assert "light.stage_1" in by_stage[1]

    def test_get_stage_for_entity(self, coordinator):
        """Test getting stage for entity."""
        assert coordinator.get_stage_for_entity("light.stage_2") == 2
        assert coordinator.get_stage_for_entity("light.nonexistent") is None

    def test_get_zone_brightness_for_ha(self, coordinator):
        """Test getting zone brightness with HA-style keys."""
        coordinator.turn_on(brightness=255)

        zone_brightness = coordinator.get_zone_brightness_for_ha()

        assert "stage_1" in zone_brightness
        assert "stage_4" in zone_brightness
        assert zone_brightness["stage_1"] == 100

    def test_reset(self, coordinator):
        """Test reset returns to initial state."""
        coordinator.turn_on(brightness=200)
        coordinator.reset()

        assert not coordinator.is_on
        assert coordinator.target_brightness == 255  # Default
        for light in coordinator.get_lights():
            assert not light.is_on
            assert light.brightness == 0

    def test_calculate_all_zone_brightness(self, coordinator):
        """Test calculating brightness for all zones."""
        coordinator.turn_on(brightness=255)  # 100%

        zone_brightness = coordinator.calculate_all_zone_brightness()

        assert 1 in zone_brightness
        assert 2 in zone_brightness
        assert 3 in zone_brightness
        assert 4 in zone_brightness
        # At 100%, all zones should be at 100%
        assert zone_brightness[1] == 100
        assert zone_brightness[2] == 100
        assert zone_brightness[3] == 100
        assert zone_brightness[4] == 100
