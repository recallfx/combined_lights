"""Test Stage 4 functionality in the Combined Lights integration."""

import pytest

from custom_components.combined_lights.const import (
    DEFAULT_BREAKPOINTS,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
)


class TestStage4Configuration:
    """Test Stage 4 configuration constants and calculations."""

    def test_default_breakpoints_are_correct(self):
        """Test that default breakpoints are properly configured for 4 stages."""
        expected_breakpoints = [25, 50, 75]
        assert DEFAULT_BREAKPOINTS == expected_breakpoints

    def test_all_stages_have_four_brightness_ranges(self):
        """Test that all stages have exactly 4 brightness ranges."""
        stage_ranges = [
            DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
            DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
            DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
            DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
        ]

        for i, ranges in enumerate(stage_ranges, 1):
            assert len(ranges) == 4, f"Stage {i} should have 4 brightness ranges"

    def test_stage_4_brightness_ranges_are_correct(self):
        """Test that Stage 4 has correct brightness ranges."""
        # Stage 4 should be off for stages 1, 2, 3 and active only in stage 4
        expected_stage_4 = [[0, 0], [0, 0], [0, 0], [1, 100]]
        assert DEFAULT_STAGE_4_BRIGHTNESS_RANGES == expected_stage_4

    @pytest.mark.parametrize(
        "brightness_pct,expected_stage",
        [
            (10, 0),  # 10% -> Stage 1
            (25, 0),  # 25% -> Stage 1
            (30, 1),  # 30% -> Stage 2
            (50, 1),  # 50% -> Stage 2
            (60, 2),  # 60% -> Stage 3
            (75, 2),  # 75% -> Stage 3
            (80, 3),  # 80% -> Stage 4
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
