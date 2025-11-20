"""Tests for BrightnessCalculator helper."""

import json

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from custom_components.combined_lights.const import DOMAIN
from custom_components.combined_lights.helpers import BrightnessCalculator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_123",
        data={
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
        },
    )


class TestBrightnessCalculator:
    """Test BrightnessCalculator class."""

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

        assert 95 < estimated <= 100  # Stage 4 active means high brightness

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

    def test_reverse_curve_sqrt(self, mock_entry):
        """Test reversing sqrt (ease-out) brightness curve."""
        brightness_calc = BrightnessCalculator(mock_entry)

        test_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        for linear in test_values:
            curved = brightness_calc._apply_brightness_curve(linear, "sqrt")
            reversed_linear = brightness_calc._reverse_brightness_curve(curved, "sqrt")
            # Should be approximately equal (within numerical tolerance)
            assert abs(reversed_linear - linear) < 0.05

    def test_reverse_curve_cbrt(self, mock_entry):
        """Test reversing cbrt (ease-out strong) brightness curve."""
        brightness_calc = BrightnessCalculator(mock_entry)

        test_values = [0.1, 0.3, 0.5, 0.7, 0.9]
        for linear in test_values:
            curved = brightness_calc._apply_brightness_curve(linear, "cbrt")
            reversed_linear = brightness_calc._reverse_brightness_curve(curved, "cbrt")
            # Should be approximately equal (within numerical tolerance)
            assert abs(reversed_linear - linear) < 0.05

    def test_ease_out_curves_characteristic(self, mock_entry):
        """Test that ease-out curves produce higher brightness at 50% progress."""
        brightness_calc = BrightnessCalculator(mock_entry)

        # At 50% progress:
        # - Ease-in (quadratic): 0.5^2 = 0.25 (lower)
        # - Linear: 0.5
        # - Ease-out (sqrt): sqrt(0.5) ≈ 0.707 (higher)
        
        sqrt_result = brightness_calc._apply_brightness_curve(0.5, "sqrt")
        linear_result = brightness_calc._apply_brightness_curve(0.5, "linear")
        quadratic_result = brightness_calc._apply_brightness_curve(0.5, "quadratic")
        
        assert sqrt_result > linear_result > quadratic_result
        assert abs(sqrt_result - 0.707) < 0.01


    def test_brightness_calculation_with_fixture_data(self):
        """Test brightness calculation using fixture data."""
        # Load test cases from fixture
        test_data = json.loads(load_fixture("brightness_test_cases.json"))

        for test_case in test_data["test_cases"]:
            # Create a config entry with the test case configuration
            config_entry = MockConfigEntry(
                domain=DOMAIN,
                title=f"Test Case: {test_case['name']}",
                data=test_case["config"],
            )

            # Create brightness calculator
            brightness_calc = BrightnessCalculator(config_entry)

            # Calculate zone brightness
            result = brightness_calc.calculate_zone_brightness(
                test_case["input"]["brightness"], test_case["input"]["zone"]
            )

            # Assert expected result
            assert result == test_case["expected"], (
                f"Test case '{test_case['name']}' failed: "
                f"expected {test_case['expected']}, got {result}"
            )

    def test_config_loading_with_fixtures(self):
        """Test loading configuration from fixtures."""
        # Test basic configuration
        basic_config = json.loads(load_fixture("config_basic.json"))
        basic_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Basic Config Test",
            data=basic_config,
        )

        assert basic_entry.data["name"] == "Basic Test Combined Lights"
        assert basic_entry.data["brightness_curve"] == "linear"
        assert basic_entry.data["breakpoints"] == [20, 50, 80]

        # Test advanced configuration
        advanced_config = json.loads(load_fixture("config_advanced.json"))
        advanced_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Advanced Config Test",
            data=advanced_config,
        )

        assert advanced_entry.data["name"] == "Advanced Test Combined Lights"
        assert advanced_entry.data["brightness_curve"] == "quadratic"
        assert advanced_entry.data["breakpoints"] == [30, 60, 90]
        assert len(advanced_entry.data["stage_1_lights"]) == 2
        assert len(advanced_entry.data["stage_2_lights"]) == 1
