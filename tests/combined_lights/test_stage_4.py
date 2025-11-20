"""Test Stage 4 functionality in the Combined Lights integration."""

import pytest

from custom_components.combined_lights.const import DEFAULT_BREAKPOINTS


class TestStage4Configuration:
    """Test Stage 4 configuration constants and calculations."""

    def test_default_breakpoints_are_correct(self):
        """Test that default breakpoints are properly configured for 4 stages."""
        expected_breakpoints = [30, 60, 90]
        assert DEFAULT_BREAKPOINTS == expected_breakpoints

    @pytest.mark.parametrize(
        "brightness_pct,expected_stage",
        [
            (10, 0),  # 10% -> Stage 1
            (25, 0),  # 25% -> Stage 1
            (30, 0),  # 30% -> Stage 1 (inclusive)
            (31, 1),  # 31% -> Stage 2
            (50, 1),  # 50% -> Stage 2
            (60, 1),  # 60% -> Stage 2 (inclusive)
            (61, 2),  # 61% -> Stage 3
            (75, 2),  # 75% -> Stage 3
            (90, 2),  # 90% -> Stage 3 (inclusive)
            (91, 3),  # 91% -> Stage 4
            (100, 3),  # 100% -> Stage 4
        ],
    )
    def test_stage_calculation_from_brightness(self, brightness_pct, expected_stage):
        """Test that brightness percentage correctly maps to stage."""

        def get_stage_from_brightness(brightness_pct, breakpoints):
            """Calculate stage from brightness percentage."""
            if brightness_pct <= breakpoints[0]:
                return 0  # Stage 1
            if brightness_pct <= breakpoints[1]:
                return 1  # Stage 2
            if brightness_pct <= breakpoints[2]:
                return 2  # Stage 3
            return 3  # Stage 4

        actual_stage = get_stage_from_brightness(brightness_pct, DEFAULT_BREAKPOINTS)
        assert actual_stage == expected_stage, (
            f"Brightness {brightness_pct}% should map to stage {expected_stage + 1}, "
            f"but got stage {actual_stage + 1}"
        )
