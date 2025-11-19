"""Brightness calculator helper."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from ..const import (
    CONF_BREAKPOINTS,
    CONF_BRIGHTNESS_CURVE,
    CONF_STAGE_1_BRIGHTNESS_RANGES,
    CONF_STAGE_2_BRIGHTNESS_RANGES,
    CONF_STAGE_3_BRIGHTNESS_RANGES,
    CONF_STAGE_4_BRIGHTNESS_RANGES,
    CURVE_CUBIC,
    CURVE_QUADRATIC,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
)


class BrightnessCalculator:
    """Handles all brightness calculation logic."""

    def __init__(self, entry: ConfigEntry):
        """Initialize the brightness calculator.

        Args:
            entry: Config entry containing configuration
        """
        self._entry = entry

    def get_stage_from_brightness(self, brightness_pct: float) -> int:
        """Determine stage based on brightness percentage.

        Args:
            brightness_pct: Brightness percentage (0-100)

        Returns:
            Stage index (0-3)
        """
        breakpoints = self._get_breakpoints()

        if brightness_pct <= breakpoints[0]:
            return 0  # Stage 1
        if brightness_pct <= breakpoints[1]:
            return 1  # Stage 2
        if brightness_pct <= breakpoints[2]:
            return 2  # Stage 3
        return 3  # Stage 4

    def calculate_zone_brightness(
        self,
        overall_pct: float,
        zone_name: str,
    ) -> float:
        """Calculate brightness for a zone.

        Args:
            overall_pct: Overall brightness percentage
            zone_name: Name of the zone (stage_1, stage_2, etc.)

        Returns:
            Zone brightness percentage (0-100)
        """
        breakpoints = self._get_breakpoints()
        brightness_ranges = self._get_brightness_ranges()

        stage = self.get_stage_from_brightness(overall_pct)
        zone_ranges = brightness_ranges[zone_name]

        return self._calculate_zone_brightness_from_config(
            overall_pct, stage, zone_ranges, breakpoints
        )

    def _calculate_zone_brightness_from_config(
        self,
        overall_pct: float,
        stage: int,
        zone_ranges: list[list[int]],
        breakpoints: list[int],
    ) -> float:
        """Calculate brightness for a zone based on configuration."""
        # Get the brightness range for this stage
        if stage >= len(zone_ranges):
            return 0.0

        stage_range = zone_ranges[stage]

        # If the range is [0, 0], the zone should be off
        if stage_range[0] == 0 and stage_range[1] == 0:
            return 0.0

        # Calculate position within the current stage
        stage_boundaries = [
            (0, breakpoints[0]),  # Stage 1
            (breakpoints[0], breakpoints[1]),  # Stage 2
            (breakpoints[1], breakpoints[2]),  # Stage 3
            (breakpoints[2], 100),  # Stage 4
        ]

        if stage >= len(stage_boundaries):
            return 0.0

        stage_start, stage_end = stage_boundaries[stage]

        # Calculate progress within the stage (0.0 to 1.0)
        if stage_end == stage_start:
            progress = 0.0
        else:
            progress = max(
                0.0, min(1.0, (overall_pct - stage_start) / (stage_end - stage_start))
            )

        # Apply brightness curve to the progress
        curve_type = self._get_brightness_curve()
        curved_progress = self._apply_brightness_curve(progress, curve_type)

        # Map progress to the configured brightness range for this zone
        min_brightness, max_brightness = stage_range
        return min_brightness + (curved_progress * (max_brightness - min_brightness))

    def _apply_brightness_curve(self, progress: float, curve_type: str) -> float:
        """Apply brightness curve to linear progress for more natural feel."""
        if curve_type == CURVE_QUADRATIC:
            # Gentle curve: more linear at very low values, curve kicks in higher
            if progress < 0.1:
                return progress * 0.9 + (progress**0.5) * 0.1
            return 0.4 * progress + 0.6 * (progress**0.5)
        if curve_type == CURVE_CUBIC:
            # More aggressive curve for maximum low-end precision
            if progress < 0.1:
                return progress * 0.8 + (progress ** (1 / 3)) * 0.2
            return 0.2 * progress + 0.8 * (progress ** (1 / 3))
        # Linear curve: even response
        return progress

    def _get_breakpoints(self) -> list[int]:
        """Get breakpoints from configuration."""
        return self._entry.data.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS)

    def _get_brightness_curve(self) -> str:
        """Get brightness curve from configuration."""
        return self._entry.data.get(CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE)

    def _get_brightness_ranges(self) -> dict[str, list[list[int]]]:
        """Get brightness ranges from configuration."""
        return {
            "stage_1": self._entry.data.get(
                CONF_STAGE_1_BRIGHTNESS_RANGES, DEFAULT_STAGE_1_BRIGHTNESS_RANGES
            ),
            "stage_2": self._entry.data.get(
                CONF_STAGE_2_BRIGHTNESS_RANGES, DEFAULT_STAGE_2_BRIGHTNESS_RANGES
            ),
            "stage_3": self._entry.data.get(
                CONF_STAGE_3_BRIGHTNESS_RANGES, DEFAULT_STAGE_3_BRIGHTNESS_RANGES
            ),
            "stage_4": self._entry.data.get(
                CONF_STAGE_4_BRIGHTNESS_RANGES, DEFAULT_STAGE_4_BRIGHTNESS_RANGES
            ),
        }

    def estimate_overall_brightness_from_zones(
        self, zone_brightness: dict[str, float | None]
    ) -> float:
        """Estimate overall brightness from current zone brightness values.

        This is the inverse operation of calculate_zone_brightness. Given the current
        brightness of each zone, estimate what overall brightness percentage would
        produce this state.

        Args:
            zone_brightness: Dict mapping zone names to current brightness percentages
                           (0-100). None means the zone is completely off.

        Returns:
            Estimated overall brightness percentage (0-100)
        """
        breakpoints = self._get_breakpoints()
        brightness_ranges = self._get_brightness_ranges()

        # Find the highest active stage
        highest_active_stage = -1
        for i, zone_name in enumerate(["stage_1", "stage_2", "stage_3", "stage_4"]):
            zone_pct = zone_brightness.get(zone_name, 0.0)
            if zone_pct and zone_pct > 0:
                highest_active_stage = i

        # If no zones are active, return 0
        if highest_active_stage == -1:
            return 0.0

        # Use the highest active zone to estimate overall brightness
        zone_name = f"stage_{highest_active_stage + 1}"
        zone_pct = zone_brightness.get(zone_name, 0.0) or 0.0
        zone_ranges = brightness_ranges[zone_name]

        # Determine which stage we're in based on which zones are active
        current_stage = highest_active_stage

        # Get the brightness range for this zone in this stage
        if current_stage >= len(zone_ranges):
            return 0.0

        stage_range = zone_ranges[current_stage]
        min_brightness, max_brightness = stage_range

        # If this zone should be off in this stage, move to the next stage
        if min_brightness == 0 and max_brightness == 0:
            current_stage += 1
            if current_stage >= len(zone_ranges):
                return 0.0
            stage_range = zone_ranges[current_stage]
            min_brightness, max_brightness = stage_range

        # Calculate stage boundaries
        stage_boundaries = [
            (0, breakpoints[0]),  # Stage 1: 0-25%
            (breakpoints[0], breakpoints[1]),  # Stage 2: 25-50%
            (breakpoints[1], breakpoints[2]),  # Stage 3: 50-75%
            (breakpoints[2], 100),  # Stage 4: 75-100%
        ]

        if current_stage >= len(stage_boundaries):
            return 100.0

        stage_start, stage_end = stage_boundaries[current_stage]

        # Calculate progress within the brightness range (0.0 to 1.0)
        if max_brightness == min_brightness:
            progress = 0.5  # Middle of the stage if no range defined
        else:
            # Reverse the brightness mapping
            progress = (zone_pct - min_brightness) / (max_brightness - min_brightness)
            progress = max(0.0, min(1.0, progress))

        # Reverse the curve application
        curve_type = self._get_brightness_curve()
        linear_progress = self._reverse_brightness_curve(progress, curve_type)

        # Map progress back to overall brightness
        overall_pct = stage_start + (linear_progress * (stage_end - stage_start))

        return max(0.0, min(100.0, overall_pct))

    def estimate_manual_indicator_from_zones(
        self, zone_brightness: dict[str, float | None]
    ) -> float:
        """Estimate slider percentage for manual updates using stage coverage.

        This treats each stage as an equal portion of the slider and bases the
        indicator on how many stages are active plus progress through the
        highest active stage. It keeps the UI intuitive when only a subset of
        stages is toggled manually (e.g., stage 4 lights on alone ≈ 25%).
        """

        stage_names = ["stage_1", "stage_2", "stage_3", "stage_4"]
        total_stages = len(stage_names)
        brightness_ranges = self._get_brightness_ranges()

        active_indices: list[int] = []
        stage_progress: dict[int, float] = {}

        for idx, zone_name in enumerate(stage_names):
            zone_pct = zone_brightness.get(zone_name)
            if zone_pct is None or zone_pct <= 0:
                continue

            zone_ranges = brightness_ranges[zone_name]
            if idx >= len(zone_ranges):
                continue

            min_brightness, max_brightness = zone_ranges[idx]
            if max_brightness <= min_brightness:
                normalized = 1.0
            else:
                normalized = (zone_pct - min_brightness) / (
                    max_brightness - min_brightness
                )
                normalized = max(0.0, min(1.0, normalized))

            active_indices.append(idx)
            stage_progress[idx] = normalized

        if not active_indices:
            return 0.0

        active_count = len(active_indices)
        highest_stage = max(active_indices)
        progress = stage_progress.get(highest_stage, 1.0)
        stage_fraction = 100.0 / total_stages

        return max(
            0.0,
            min(100.0, stage_fraction * (active_count - 1) + progress * stage_fraction),
        )

    def _reverse_brightness_curve(self, curved_value: float, curve_type: str) -> float:
        """Reverse the brightness curve to get linear progress.

        Args:
            curved_value: The curved brightness value (0.0-1.0)
            curve_type: Type of curve (linear, quadratic, cubic)

        Returns:
            Linear progress value (0.0-1.0)
        """
        if curve_type == CURVE_QUADRATIC:
            # Reverse of: 0.4 * progress + 0.6 * (progress**0.5)
            # This is approximate - we'll use iterative approach
            if curved_value < 0.1:
                # Reverse of: progress * 0.9 + (progress**0.5) * 0.1
                # Approximate solution
                return curved_value / 0.95
            # Solve: 0.4*x + 0.6*sqrt(x) = curved_value
            # Approximate with Newton's method iteration (simplified)
            x = curved_value  # Initial guess
            for _ in range(5):  # Few iterations for convergence
                fx = 0.4 * x + 0.6 * (x**0.5) - curved_value
                fpx = 0.4 + 0.3 / (x**0.5) if x > 0 else 1
                x = max(0, x - fx / fpx)
            return x

        if curve_type == CURVE_CUBIC:
            # Reverse of: 0.2 * progress + 0.8 * (progress ** (1/3))
            if curved_value < 0.1:
                # Reverse of: progress * 0.8 + (progress ** (1/3)) * 0.2
                return curved_value / 0.9
            # Solve: 0.2*x + 0.8*x^(1/3) = curved_value
            x = curved_value  # Initial guess
            for _ in range(5):
                fx = 0.2 * x + 0.8 * (x ** (1 / 3)) - curved_value
                fpx = 0.2 + (0.8 / 3) / (x ** (2 / 3)) if x > 0 else 1
                x = max(0, x - fx / fpx)
            return x

        # Linear: no transformation needed
        return curved_value
