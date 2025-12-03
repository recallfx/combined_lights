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
from .base_coordinator import BaseBrightnessCalculator


class BrightnessCalculator(BaseBrightnessCalculator):
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

    # Alias for backward compatibility
    _get_breakpoints = get_breakpoints

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

    # Alias for backward compatibility
    _get_stage_curve = get_stage_curve

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

        return super().calculate_zone_brightness(overall_pct, stage)

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

    def estimate_from_single_light_change(
        self, zone_name: str, brightness: int
    ) -> float:
        """Estimate overall brightness when a single light is manually changed.

        This mirrors the logic in BaseCombinedLightsCoordinator.set_light_brightness()
        to ensure HA integration and simulation behave identically.

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

        # Use the same method as BaseCombinedLightsCoordinator.set_light_brightness()
        return self.estimate_overall_from_single_light(stage, brightness_pct)
