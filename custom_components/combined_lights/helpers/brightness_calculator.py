"""Brightness calculator helper."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from ..const import (
    CONF_BREAKPOINTS,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_2_CURVE,
    CONF_STAGE_3_CURVE,
    CONF_STAGE_4_CURVE,
    CURVE_CBRT,
    CURVE_CUBIC,
    CURVE_QUADRATIC,
    CURVE_SQRT,
    DEFAULT_BREAKPOINTS,
    DEFAULT_STAGE_1_CURVE,
    DEFAULT_STAGE_2_CURVE,
    DEFAULT_STAGE_3_CURVE,
    DEFAULT_STAGE_4_CURVE,
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
        
        # Determine stage index from zone name
        try:
            stage_idx = int(zone_name.split("_")[1]) - 1
        except (IndexError, ValueError):
            return 0.0

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
        # (overall_pct - activation_point) / (100 - activation_point)
        range_span = 100 - activation_point
        if range_span <= 0:
            return 100.0 if overall_pct >= 100 else 0.0
            
        progress = (overall_pct - activation_point) / range_span
        progress = max(0.0, min(1.0, progress))

        # Apply curve
        curve_type = self._get_stage_curve(stage_idx)
        curved_progress = self._apply_brightness_curve(progress, curve_type)

        # Map to 1-100% brightness (or 0 if off, but we handled that above)
        # We map 0.0-1.0 progress to 1-100 brightness (since 0 is off)
        # Actually, let's map to 1-255 scale logic: 1% is minimum on.
        return 1.0 + (curved_progress * 99.0)

    def _apply_brightness_curve(self, progress: float, curve_type: str) -> float:
        """Apply brightness curve to linear progress for more natural feel."""
        if curve_type == CURVE_QUADRATIC:
            # Quadratic curve (ease-in): y = x^2
            return progress * progress
        if curve_type == CURVE_CUBIC:
            # Cubic curve (ease-in strong): y = x^3
            return progress * progress * progress
        if curve_type == CURVE_SQRT:
            # Square root curve (ease-out): y = √x
            return progress ** 0.5
        if curve_type == CURVE_CBRT:
            # Cube root curve (ease-out strong): y = ∛x
            return progress ** (1/3)
        # Linear curve: even response
        return progress

    def _get_breakpoints(self) -> list[int]:
        """Get breakpoints from configuration."""
        return self._entry.data.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS)

    def _get_stage_curve(self, stage_idx: int) -> str:
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
        breakpoints = self._get_breakpoints()
        
        # Find the highest active stage (the one that activates last)
        # In progressive zones, higher stages activate at higher overall brightness.
        # So we should look at the highest stage that is ON.
        highest_active_stage_idx = -1
        highest_stage_brightness = 0.0
        
        for i in range(4):
            zone_name = f"stage_{i+1}"
            brightness = zone_brightness.get(zone_name)
            if brightness and brightness > 0:
                highest_active_stage_idx = i
                highest_stage_brightness = brightness

        if highest_active_stage_idx == -1:
            return 0.0

        # Calculate overall brightness based on the highest active stage
        # We reverse the calculation: 
        # brightness = 1 + (curved_progress * 99)
        # curved_progress = (brightness - 1) / 99
        
        curved_progress = max(0.0, (highest_stage_brightness - 1.0) / 99.0)
        
        # Reverse curve
        curve_type = self._get_stage_curve(highest_active_stage_idx)
        progress = self._reverse_brightness_curve(curved_progress, curve_type)
        
        # Map back to overall percentage
        # progress = (overall - activation) / (100 - activation)
        # overall = activation + progress * (100 - activation)
        
        if highest_active_stage_idx == 0:
            activation_point = 0
        else:
            activation_point = breakpoints[highest_active_stage_idx - 1]
            
        range_span = 100 - activation_point
        overall_pct = activation_point + (progress * range_span)
        
        return max(0.0, min(100.0, overall_pct))

    def estimate_manual_indicator_from_zones(
        self, zone_brightness: dict[str, float | None]
    ) -> float:
        """Estimate slider percentage for manual updates using stage coverage.
        
        For progressive zones, we can just use the standard estimation logic
        since it finds the "highest" active stage and calculates from there.
        """
        return self.estimate_overall_brightness_from_zones(zone_brightness)

    def _reverse_brightness_curve(self, curved_value: float, curve_type: str) -> float:
        """Reverse the brightness curve to get linear progress.

        Args:
            curved_value: The curved brightness value (0.0-1.0)
            curve_type: Type of curve (linear, quadratic, cubic, sqrt, cbrt)

        Returns:
            Linear progress value (0.0-1.0)
        """
        if curve_type == CURVE_QUADRATIC:
            # y = x^2 -> x = sqrt(y)
            return curved_value ** 0.5
        if curve_type == CURVE_CUBIC:
            # y = x^3 -> x = cbrt(y)
            return curved_value ** (1/3)
        if curve_type == CURVE_SQRT:
            # y = sqrt(x) -> x = y^2
            return curved_value ** 2
        if curve_type == CURVE_CBRT:
            # y = cbrt(x) -> x = y^3
            return curved_value ** 3
        # Linear: no transformation needed
        return curved_value
