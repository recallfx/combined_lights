#!/usr/bin/env python3
"""Simple test script to verify Stage 4 functionality in the Combined Lights integration."""

import sys
import os

# Add the config directory to Python path so we can import the custom component
sys.path.insert(0, "/workspaces/ha_core/config/custom_components")

from combined_lights.const import (
    DEFAULT_BREAKPOINTS,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
)


def test_stage_4_configuration():
    """Test that Stage 4 configuration is properly defined."""
    print("Testing Stage 4 Configuration...")

    print(f"Default Breakpoints: {DEFAULT_BREAKPOINTS}")
    print(f"Expected: [25, 50, 75] for 4 stages")

    print(f"\nStage 1 Brightness Ranges: {DEFAULT_STAGE_1_BRIGHTNESS_RANGES}")
    print(f"Stage 2 Brightness Ranges: {DEFAULT_STAGE_2_BRIGHTNESS_RANGES}")
    print(f"Stage 3 Brightness Ranges: {DEFAULT_STAGE_3_BRIGHTNESS_RANGES}")
    print(f"Stage 4 Brightness Ranges: {DEFAULT_STAGE_4_BRIGHTNESS_RANGES}")

    # Verify we have 4 ranges for each stage (one for each slider stage)
    assert len(DEFAULT_STAGE_1_BRIGHTNESS_RANGES) == 4, (
        "Stage 1 should have 4 brightness ranges"
    )
    assert len(DEFAULT_STAGE_2_BRIGHTNESS_RANGES) == 4, (
        "Stage 2 should have 4 brightness ranges"
    )
    assert len(DEFAULT_STAGE_3_BRIGHTNESS_RANGES) == 4, (
        "Stage 3 should have 4 brightness ranges"
    )
    assert len(DEFAULT_STAGE_4_BRIGHTNESS_RANGES) == 4, (
        "Stage 4 should have 4 brightness ranges"
    )

    print("\n✅ All configuration tests passed!")


def test_stage_calculation():
    """Test that stage calculation works with 4 stages."""

    # Simulate the stage calculation logic
    def get_stage_from_brightness(brightness_pct, breakpoints):
        if brightness_pct <= breakpoints[0]:
            return 0  # Stage 1
        if brightness_pct <= breakpoints[1]:
            return 1  # Stage 2
        if brightness_pct <= breakpoints[2]:
            return 2  # Stage 3
        return 3  # Stage 4

    breakpoints = DEFAULT_BREAKPOINTS

    test_cases = [
        (10, 0, "Stage 1"),  # 10% -> Stage 1
        (25, 0, "Stage 1"),  # 25% -> Stage 1
        (30, 1, "Stage 2"),  # 30% -> Stage 2
        (50, 1, "Stage 2"),  # 50% -> Stage 2
        (60, 2, "Stage 3"),  # 60% -> Stage 3
        (75, 2, "Stage 3"),  # 75% -> Stage 3
        (80, 3, "Stage 4"),  # 80% -> Stage 4
        (100, 3, "Stage 4"),  # 100% -> Stage 4
    ]

    print("\nTesting Stage Calculation...")
    for brightness, expected_stage, stage_name in test_cases:
        actual_stage = get_stage_from_brightness(brightness, breakpoints)
        print(f"  {brightness}% -> Stage {actual_stage + 1} ({stage_name})")
        assert actual_stage == expected_stage, (
            f"Expected stage {expected_stage}, got {actual_stage}"
        )

    print("✅ All stage calculation tests passed!")


def test_stage_4_ranges():
    """Test that Stage 4 has appropriate brightness ranges."""
    print("\nTesting Stage 4 Brightness Ranges...")

    # Stage 4 should be off for stages 1, 2, 3 and active only in stage 4
    expected_stage_4 = [[0, 0], [0, 0], [0, 0], [1, 100]]

    print(f"Stage 4 ranges: {DEFAULT_STAGE_4_BRIGHTNESS_RANGES}")
    print(f"Expected: {expected_stage_4}")

    assert DEFAULT_STAGE_4_BRIGHTNESS_RANGES == expected_stage_4, (
        "Stage 4 ranges don't match expected pattern"
    )

    print("✅ Stage 4 brightness ranges test passed!")


if __name__ == "__main__":
    test_stage_4_configuration()
    test_stage_calculation()
    test_stage_4_ranges()
    print("\n🎉 All tests passed! Stage 4 is properly configured.")
