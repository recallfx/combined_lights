"""Brightness calculator helper."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from ..const import (
    CONF_BREAKPOINTS,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_2_CURVE,
    CONF_STAGE_3_CURVE,
    CONF_STAGE_4_CURVE,
    DEFAULT_BREAKPOINTS,
    DEFAULT_STAGE_1_CURVE,
    DEFAULT_STAGE_2_CURVE,
    DEFAULT_STAGE_3_CURVE,
    DEFAULT_STAGE_4_CURVE,
)


class BrightnessCalculator:
    """Handles all brightness calculation logic using HA ConfigEntry."""

    def __init__(self, entry: ConfigEntry):
        """Initialize the brightness calculator.

        Args:
            entry: Config entry containing configuration
        """
        self._entry = entry

    def get_breakpoints(self) -> list[int]:
        """Get breakpoints from configuration."""
        return self._entry.data.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS)

    def get_stage_curve(self, stage_idx: int) -> str:
        """Get brightness curve for a specific stage."""
        if stage_idx == 0:
            return self._entry.data.get(CONF_STAGE_1_CURVE, DEFAULT_STAGE_1_CURVE)
        if stage_idx == 1:
            return self._entry.data.get(CONF_STAGE_2_CURVE, DEFAULT_STAGE_2_CURVE)
        if stage_idx == 2:
            return self._entry.data.get(CONF_STAGE_3_CURVE, DEFAULT_STAGE_3_CURVE)
        if stage_idx == 3:
            return self._entry.data.get(CONF_STAGE_4_CURVE, DEFAULT_STAGE_4_CURVE)
        return "linear"

    def get_stage_from_brightness(self, brightness_pct: float) -> int:
        """Determine stage index (0-3) based on brightness percentage.

        Args:
            brightness_pct: Brightness percentage (0-100)

        Returns:
            Stage index (0-3)
        """
        breakpoints = self.get_breakpoints()

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
        zone_name: str | int,
    ) -> float:
        """Calculate brightness for a zone.

        Args:
            overall_pct: Overall brightness percentage
            zone_name: Name of the zone (stage_1, stage_2, etc.) or stage number (1-4)

        Returns:
            Zone brightness percentage (0-100)
        """
        # Handle both string zone names and integer stage numbers
        if isinstance(zone_name, int):
            stage = zone_name
        else:
            # Extract stage number from zone name
            try:
                stage = int(zone_name.split("_")[1])
            except (IndexError, ValueError):
                return 0.0

        breakpoints = self.get_breakpoints()
        stage_idx = stage - 1

        # Determine activation point for this stage
        if stage_idx == 0:
            activation_point = 0
        elif stage_idx <= len(breakpoints):
            activation_point = breakpoints[stage_idx - 1]
        else:
            return 0.0

        # If overall brightness is below activation point, zone is off
        if overall_pct <= activation_point:
            return 0.0

        # Calculate progress from activation point to 100%
        range_span = 100 - activation_point
        if range_span <= 0:
            return 100.0 if overall_pct >= 100 else 0.0

        progress = (overall_pct - activation_point) / range_span
        progress = max(0.0, min(1.0, progress))

        # Apply curve
        curve_type = self.get_stage_curve(stage_idx)
        curved_progress = self._apply_brightness_curve(progress, curve_type)

        # Map to 1-100% brightness (1% is minimum when on)
        return 1.0 + (curved_progress * 99.0)

    def estimate_overall_from_zones(
        self, zone_brightness: dict[int, float | None]
    ) -> float:
        """Estimate overall brightness from current zone brightness values.

        This handles unusual states where higher stages are on but lower stages
        are off. In the progressive model, if Stage 3 is off, overall brightness
        must be below 60% (Stage 3's activation point), so Stage 4 should also
        be off.

        Args:
            zone_brightness: Dict mapping stage number (1-4) to current
                           brightness percentage (0-100), or None if off.

        Returns:
            Estimated overall brightness percentage (0-100)
        """
        breakpoints = self.get_breakpoints()  # e.g., [30, 60, 90]

        # Find the lowest stage that is OFF but has a higher stage that's ON
        # This indicates an inconsistent state that we need to respect
        lowest_off_stage_with_higher_on: int | None = None
        highest_active_stage = 0
        highest_stage_brightness = 0.0

        for stage in range(1, 5):
            brightness = zone_brightness.get(stage)
            if brightness and brightness > 0:
                highest_active_stage = stage
                highest_stage_brightness = brightness

        # Check for "gaps" - if a lower stage is off but a higher stage is on,
        # the user manually turned off the lower stage
        for stage in range(1, highest_active_stage):
            brightness = zone_brightness.get(stage)
            if brightness is None or brightness == 0:
                lowest_off_stage_with_higher_on = stage
                break

        if highest_active_stage == 0:
            return 0.0

        # If there's a gap (lower stage off, higher on), cap overall brightness
        # to just below the off stage's activation point
        if lowest_off_stage_with_higher_on is not None:
            if lowest_off_stage_with_higher_on == 1:
                # Stage 1 is off but higher stages on - shouldn't happen normally
                # Cap to 0 since Stage 1 is always supposed to be on
                return 0.0
            # Cap to just below the activation point of the off stage
            # Stage 2 activates at breakpoints[0] (30), Stage 3 at [1] (60), etc.
            activation_point = breakpoints[lowest_off_stage_with_higher_on - 2]
            return max(0.0, activation_point - 1)

        return self._reverse_stage_brightness(
            highest_active_stage, highest_stage_brightness
        )

    def estimate_overall_brightness_from_zones(
        self, zone_brightness: dict[str, float | None]
    ) -> float:
        """Estimate overall brightness from current zone brightness values.

        Args:
            zone_brightness: Dict mapping zone names to current brightness percentages
                           (0-100). None means the zone is completely off.

        Returns:
            Estimated overall brightness percentage (0-100)
        """
        # Convert zone names to stage numbers
        stage_brightness: dict[int, float | None] = {}
        for zone_name, brightness in zone_brightness.items():
            try:
                stage = int(zone_name.split("_")[1])
                stage_brightness[stage] = brightness
            except (IndexError, ValueError):
                continue

        return self.estimate_overall_from_zones(stage_brightness)

    def estimate_manual_indicator_from_zones(
        self, zone_brightness: dict[str, float | None]
    ) -> float:
        """Estimate slider percentage for manual updates using stage coverage.

        For progressive zones, we can just use the standard estimation logic
        since it finds the "highest" active stage and calculates from there.
        """
        return self.estimate_overall_brightness_from_zones(zone_brightness)

    def estimate_overall_from_single_light(
        self, stage: int, brightness_pct: float
    ) -> float:
        """Calculate overall brightness that would produce given brightness for a stage.

        This is used for back-propagation when a single light is manually changed.
        If the light is OFF (brightness_pct = 0), returns the activation point
        of that stage (the maximum overall brightness where that stage is still off).

        Args:
            stage: Stage number (1-4)
            brightness_pct: Target brightness percentage (0-100) for that stage

        Returns:
            Overall brightness percentage (0-100)
        """
        breakpoints = self.get_breakpoints()

        if brightness_pct <= 0:
            # Light is OFF - return the activation point (max overall where this stage is off)
            if stage == 1:
                return 0.0  # Stage 1 is always on if overall > 0
            else:
                # Stage N activates at breakpoint[N-2]
                return float(breakpoints[stage - 2])

        return self._reverse_stage_brightness(stage, brightness_pct)

    def estimate_from_single_light_change(
        self, zone_name: str, brightness: int
    ) -> float:
        """Estimate overall brightness when a single light is manually changed.

        Args:
            zone_name: Zone name (e.g., "stage_1", "stage_2")
            brightness: New brightness value (0-255), 0 means light is OFF

        Returns:
            Estimated overall brightness percentage (0-100)
        """
        # Extract stage number from zone name
        try:
            stage = int(zone_name.split("_")[1])
        except (IndexError, ValueError):
            return 0.0

        # Convert brightness to percentage
        brightness_pct = (brightness / 255.0) * 100 if brightness > 0 else 0.0

        return self.estimate_overall_from_single_light(stage, brightness_pct)

    def _reverse_stage_brightness(self, stage: int, brightness_pct: float) -> float:
        """Reverse calculate overall brightness from a stage's brightness.

        Args:
            stage: Stage number (1-4)
            brightness_pct: Brightness percentage (1-100)

        Returns:
            Overall brightness percentage (0-100)
        """
        breakpoints = self.get_breakpoints()
        stage_idx = stage - 1

        # Reverse the calculation
        # brightness = 1 + (curved_progress * 99)
        # curved_progress = (brightness - 1) / 99
        curved_progress = max(0.0, min(1.0, (brightness_pct - 1.0) / 99.0))

        # Reverse curve
        curve_type = self.get_stage_curve(stage_idx)
        progress = self._reverse_brightness_curve(curved_progress, curve_type)

        # Map back to overall percentage
        # progress = (overall - activation) / (100 - activation)
        # overall = activation + progress * (100 - activation)
        if stage_idx == 0:
            activation_point = 0
        else:
            activation_point = breakpoints[stage_idx - 1]

        range_span = 100 - activation_point
        overall_pct = activation_point + (progress * range_span)

        return max(0.0, min(100.0, overall_pct))

    def _apply_brightness_curve(self, progress: float, curve_type: str) -> float:
        """Apply brightness curve to linear progress."""
        if curve_type == "quadratic":
            return progress * progress
        if curve_type == "cubic":
            return progress * progress * progress
        if curve_type == "sqrt":
            return progress**0.5
        if curve_type == "cbrt":
            return progress ** (1 / 3)
        # Linear
        return progress

    def _reverse_brightness_curve(self, curved_value: float, curve_type: str) -> float:
        """Reverse the brightness curve to get linear progress."""
        if curve_type == "quadratic":
            return curved_value**0.5
        if curve_type == "cubic":
            return curved_value ** (1 / 3)
        if curve_type == "sqrt":
            return curved_value**2
        if curve_type == "cbrt":
            return curved_value**3
        # Linear
        return curved_value
