"""Config validator helper."""
from __future__ import annotations


class ConfigValidator:
    """Validates configuration data."""

    @staticmethod
    def validate_brightness_ranges(ranges: list[list[int]]) -> bool:
        """Validate that brightness ranges are valid.

        Args:
            ranges: List of [min, max] ranges

        Returns:
            True if valid, False otherwise
        """
        if not ranges:
            return True

        for r in ranges:
            if len(r) != 2:
                return False
            if not (0 <= r[0] <= 100) or not (0 <= r[1] <= 100):
                return False
            # Allow [0, 0] for off, otherwise min must be <= max
            if r[0] > r[1] and not (r[0] == 0 and r[1] == 0):
                return False

        return True

    @staticmethod
    def validate_breakpoints(breakpoints: list[int]) -> bool:
        """Validate breakpoints.

        Args:
            breakpoints: List of breakpoints

        Returns:
            True if valid, False otherwise
        """
        if len(breakpoints) != 3:
            return False

        # Check if sorted and within range
        if not (0 < breakpoints[0] < breakpoints[1] < breakpoints[2] < 100):
            return False

        return True
