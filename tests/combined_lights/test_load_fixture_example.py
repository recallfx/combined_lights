"""Test load_fixture functionality with Combined Lights."""

import json
from pytest_homeassistant_custom_component.common import load_fixture, MockConfigEntry

from custom_components.combined_lights.helpers import BrightnessCalculator
from custom_components.combined_lights.const import DOMAIN


class TestLoadFixtureExample:
    """Test using load_fixture for configuration-heavy tests."""

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
