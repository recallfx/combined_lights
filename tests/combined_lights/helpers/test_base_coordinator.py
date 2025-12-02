"""Tests for BaseBrightnessCalculator and BaseCombinedLightsCoordinator."""

import pytest

from custom_components.combined_lights.helpers.base_coordinator import (
    BaseBrightnessCalculator,
    BaseCombinedLightsCoordinator,
    LightState,
)


class MockBrightnessCalculator(BaseBrightnessCalculator):
    """Concrete implementation for testing."""

    def __init__(self, breakpoints: list[int] = None, curves: dict[int, str] = None):
        self._breakpoints = breakpoints or [30, 60, 90]
        self._curves = curves or {}

    def get_breakpoints(self) -> list[int]:
        return self._breakpoints

    def get_stage_curve(self, stage_idx: int) -> str:
        return self._curves.get(stage_idx, "linear")


class MockCoordinator(BaseCombinedLightsCoordinator):
    """Concrete implementation for testing."""

    def __init__(self, calculator: BaseBrightnessCalculator):
        super().__init__(calculator)
        # Add default lights for testing
        for i in range(1, 5):
            entity_id = f"light.stage_{i}"
            self._lights[entity_id] = LightState(entity_id=entity_id, stage=i)


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


class TestBaseBrightnessCalculator:
    """Test BaseBrightnessCalculator class."""

    def test_get_stage_from_brightness_stage_1(self):
        """Test stage detection for stage 1 (0-30%)."""
        calc = MockBrightnessCalculator()
        assert calc.get_stage_from_brightness(0) == 0
        assert calc.get_stage_from_brightness(15) == 0
        assert calc.get_stage_from_brightness(30) == 0

    def test_get_stage_from_brightness_stage_2(self):
        """Test stage detection for stage 2 (30-60%)."""
        calc = MockBrightnessCalculator()
        assert calc.get_stage_from_brightness(31) == 1
        assert calc.get_stage_from_brightness(45) == 1
        assert calc.get_stage_from_brightness(60) == 1

    def test_get_stage_from_brightness_stage_3(self):
        """Test stage detection for stage 3 (60-90%)."""
        calc = MockBrightnessCalculator()
        assert calc.get_stage_from_brightness(61) == 2
        assert calc.get_stage_from_brightness(75) == 2
        assert calc.get_stage_from_brightness(90) == 2

    def test_get_stage_from_brightness_stage_4(self):
        """Test stage detection for stage 4 (90-100%)."""
        calc = MockBrightnessCalculator()
        assert calc.get_stage_from_brightness(91) == 3
        assert calc.get_stage_from_brightness(95) == 3
        assert calc.get_stage_from_brightness(100) == 3

    def test_calculate_zone_brightness_stage_1_always_on(self):
        """Stage 1 should always be on when overall brightness > 0."""
        calc = MockBrightnessCalculator()
        # Stage 1 active from 0%, so at 1% overall it should be on
        assert calc.calculate_zone_brightness(1, 1) > 0
        assert calc.calculate_zone_brightness(50, 1) > 0
        assert calc.calculate_zone_brightness(100, 1) > 0

    def test_calculate_zone_brightness_stage_2_activation(self):
        """Stage 2 activates at 30%."""
        calc = MockBrightnessCalculator()
        # Below activation point
        assert calc.calculate_zone_brightness(29, 2) == 0
        assert calc.calculate_zone_brightness(30, 2) == 0
        # Above activation point
        assert calc.calculate_zone_brightness(31, 2) > 0

    def test_calculate_zone_brightness_stage_3_activation(self):
        """Stage 3 activates at 60%."""
        calc = MockBrightnessCalculator()
        # Below activation point
        assert calc.calculate_zone_brightness(59, 3) == 0
        assert calc.calculate_zone_brightness(60, 3) == 0
        # Above activation point
        assert calc.calculate_zone_brightness(61, 3) > 0

    def test_calculate_zone_brightness_stage_4_activation(self):
        """Stage 4 activates at 90%."""
        calc = MockBrightnessCalculator()
        # Below activation point
        assert calc.calculate_zone_brightness(89, 4) == 0
        assert calc.calculate_zone_brightness(90, 4) == 0
        # Above activation point
        assert calc.calculate_zone_brightness(91, 4) > 0

    def test_calculate_zone_brightness_at_100_percent(self):
        """All stages should be at 100% when overall is 100%."""
        calc = MockBrightnessCalculator()
        assert calc.calculate_zone_brightness(100, 1) == 100
        assert calc.calculate_zone_brightness(100, 2) == 100
        assert calc.calculate_zone_brightness(100, 3) == 100
        assert calc.calculate_zone_brightness(100, 4) == 100

    def test_estimate_overall_from_single_light_stage_1_off(self):
        """Stage 1 OFF should return 0%."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_single_light(1, 0)
        assert result == 0.0

    def test_estimate_overall_from_single_light_stage_2_off(self):
        """Stage 2 OFF should return 30% (activation point)."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_single_light(2, 0)
        assert result == 30.0

    def test_estimate_overall_from_single_light_stage_3_off(self):
        """Stage 3 OFF should return 60% (activation point)."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_single_light(3, 0)
        assert result == 60.0

    def test_estimate_overall_from_single_light_stage_4_off(self):
        """Stage 4 OFF should return 90% (activation point)."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_single_light(4, 0)
        assert result == 90.0

    def test_estimate_overall_from_single_light_roundtrip(self):
        """Test that estimate_overall -> calculate_zone gives same brightness."""
        calc = MockBrightnessCalculator()
        
        # Test various stage/brightness combinations
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
            overall = calc.estimate_overall_from_single_light(stage, brightness_pct)
            calculated = calc.calculate_zone_brightness(overall, stage)
            assert abs(calculated - brightness_pct) < 1.0, (
                f"Stage {stage} at {brightness_pct}%: "
                f"overall={overall:.1f}%, calculated back={calculated:.1f}%"
            )

    def test_estimate_overall_from_zones_all_off(self):
        """All zones off should return 0%."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_zones({1: None, 2: None, 3: None, 4: None})
        assert result == 0.0

    def test_estimate_overall_from_zones_stage_1_only(self):
        """Only stage 1 on should estimate overall based on stage 1 brightness."""
        calc = MockBrightnessCalculator()
        # Stage 1 at 50% brightness -> overall ~50%
        result = calc.estimate_overall_from_zones({1: 50.0, 2: None, 3: None, 4: None})
        assert 45 < result < 55  # Should be around 50%

    def test_estimate_overall_from_zones_highest_active(self):
        """Should use highest active stage for estimation."""
        calc = MockBrightnessCalculator()
        result = calc.estimate_overall_from_zones({1: 100.0, 2: 100.0, 3: 50.0, 4: None})
        # Stage 3 is highest active, 50% brightness within stage 3 range
        assert 60 < result < 100

    def test_apply_brightness_curve_linear(self):
        """Linear curve should be identity."""
        calc = MockBrightnessCalculator()
        assert calc._apply_brightness_curve(0.0, "linear") == 0.0
        assert calc._apply_brightness_curve(0.5, "linear") == 0.5
        assert calc._apply_brightness_curve(1.0, "linear") == 1.0

    def test_apply_brightness_curve_quadratic(self):
        """Quadratic curve should be x^2."""
        calc = MockBrightnessCalculator()
        assert calc._apply_brightness_curve(0.0, "quadratic") == 0.0
        assert calc._apply_brightness_curve(0.5, "quadratic") == 0.25
        assert calc._apply_brightness_curve(1.0, "quadratic") == 1.0

    def test_apply_brightness_curve_cubic(self):
        """Cubic curve should be x^3."""
        calc = MockBrightnessCalculator()
        assert calc._apply_brightness_curve(0.0, "cubic") == 0.0
        assert calc._apply_brightness_curve(0.5, "cubic") == 0.125
        assert calc._apply_brightness_curve(1.0, "cubic") == 1.0

    def test_apply_brightness_curve_sqrt(self):
        """Sqrt curve should be x^0.5."""
        calc = MockBrightnessCalculator()
        assert calc._apply_brightness_curve(0.0, "sqrt") == 0.0
        assert abs(calc._apply_brightness_curve(0.25, "sqrt") - 0.5) < 0.01
        assert calc._apply_brightness_curve(1.0, "sqrt") == 1.0

    def test_apply_brightness_curve_cbrt(self):
        """Cbrt curve should be x^(1/3)."""
        calc = MockBrightnessCalculator()
        assert calc._apply_brightness_curve(0.0, "cbrt") == 0.0
        assert abs(calc._apply_brightness_curve(0.125, "cbrt") - 0.5) < 0.01
        assert calc._apply_brightness_curve(1.0, "cbrt") == 1.0

    def test_reverse_brightness_curve_roundtrip(self):
        """Test that apply->reverse gives original value."""
        calc = MockBrightnessCalculator()
        
        for curve in ["linear", "quadratic", "cubic", "sqrt", "cbrt"]:
            for value in [0.1, 0.3, 0.5, 0.7, 0.9]:
                curved = calc._apply_brightness_curve(value, curve)
                reversed_value = calc._reverse_brightness_curve(curved, curve)
                assert abs(reversed_value - value) < 0.01, (
                    f"Curve {curve}, value {value}: "
                    f"curved={curved:.3f}, reversed={reversed_value:.3f}"
                )


class TestBaseCombinedLightsCoordinator:
    """Test BaseCombinedLightsCoordinator class."""

    def test_initial_state_is_off(self):
        """Coordinator should start in OFF state."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        assert not coord.is_on
        assert coord.current_stage == 0

    def test_turn_on_default_brightness(self):
        """Turn on with default brightness."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on()
        
        assert coord.is_on
        assert coord.target_brightness == 255
        assert coord.target_brightness_pct == 100.0

    def test_turn_on_with_brightness(self):
        """Turn on with specific brightness."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on(brightness=128)
        
        assert coord.is_on
        assert coord.target_brightness == 128
        assert 50.0 < coord.target_brightness_pct < 51.0

    def test_turn_off(self):
        """Turn off should set all lights to off."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on()
        coord.turn_off()
        
        assert not coord.is_on
        for light in coord.get_lights():
            assert not light.is_on
            assert light.brightness == 0

    def test_current_stage_calculation(self):
        """Test current stage is calculated from brightness."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        # Stage 1: 0-30%
        coord.turn_on(brightness=int(15 / 100 * 255))
        assert coord.current_stage == 1
        
        # Stage 2: 30-60%
        coord.turn_on(brightness=int(45 / 100 * 255))
        assert coord.current_stage == 2
        
        # Stage 3: 60-90%
        coord.turn_on(brightness=int(75 / 100 * 255))
        assert coord.current_stage == 3
        
        # Stage 4: 90-100%
        coord.turn_on(brightness=int(95 / 100 * 255))
        assert coord.current_stage == 4

    def test_apply_brightness_to_lights(self):
        """Test brightness is distributed to lights based on stage."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        # At 50% overall, stages 1 and 2 should be on
        coord.turn_on(brightness=int(50 / 100 * 255))
        
        lights = {l.entity_id: l for l in coord.get_lights()}
        
        assert lights["light.stage_1"].is_on
        assert lights["light.stage_2"].is_on
        assert not lights["light.stage_3"].is_on
        assert not lights["light.stage_4"].is_on

    def test_set_light_brightness_updates_overall(self):
        """Setting single light brightness updates overall state."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on()
        
        # Set stage 2 to 50% brightness
        _, overall_pct = coord.set_light_brightness("light.stage_2", 128)
        
        # Overall should be somewhere in stage 2 range
        assert 30 < overall_pct < 100

    def test_set_light_brightness_off_returns_activation_point(self):
        """Turning off a light should set overall to activation point."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on()
        
        # Turn off stage 3
        _, overall_pct = coord.set_light_brightness("light.stage_3", 0)
        
        # Stage 3 activates at 60%, so overall should be 60%
        assert overall_pct == 60.0

    def test_apply_back_propagation(self):
        """Back-propagation updates other lights based on overall brightness."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        # Set to 50% overall
        coord.turn_on(brightness=int(50 / 100 * 255))
        
        # Manually set stage 1 to different value
        coord._lights["light.stage_1"].brightness = 200
        
        # Apply back-propagation excluding stage 1
        changes = coord.apply_back_propagation(exclude_entity_id="light.stage_1")
        
        # Stage 1 should not be in changes
        assert "light.stage_1" not in changes
        # Other stages should be updated
        assert "light.stage_2" in changes

    def test_get_lights(self):
        """Test getting all light states."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        lights = coord.get_lights()
        
        assert len(lights) == 4
        entity_ids = [l.entity_id for l in lights]
        assert "light.stage_1" in entity_ids
        assert "light.stage_4" in entity_ids

    def test_get_light(self):
        """Test getting a specific light state."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        light = coord.get_light("light.stage_2")
        
        assert light is not None
        assert light.entity_id == "light.stage_2"
        assert light.stage == 2

    def test_get_light_not_found(self):
        """Test getting non-existent light returns None."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        light = coord.get_light("light.nonexistent")
        
        assert light is None

    def test_reset(self):
        """Test reset returns to initial state."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on(brightness=200)
        coord.reset()
        
        assert not coord.is_on
        assert coord.target_brightness == 255  # Default
        for light in coord.get_lights():
            assert not light.is_on
            assert light.brightness == 0

    def test_calculate_all_zone_brightness(self):
        """Test calculating brightness for all zones."""
        calc = MockBrightnessCalculator()
        coord = MockCoordinator(calc)
        
        coord.turn_on(brightness=255)  # 100%
        
        zone_brightness = coord.calculate_all_zone_brightness()
        
        assert 1 in zone_brightness
        assert 2 in zone_brightness
        assert 3 in zone_brightness
        assert 4 in zone_brightness
        # At 100%, all zones should be at 100%
        assert zone_brightness[1] == 100
        assert zone_brightness[2] == 100
        assert zone_brightness[3] == 100
        assert zone_brightness[4] == 100
