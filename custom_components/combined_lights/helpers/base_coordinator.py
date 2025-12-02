"""Base coordinator for Combined Lights.

This module contains the core logic for managing combined lights,
independent of Home Assistant specifics. It can be used by both
the HA integration and standalone simulations.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class LightState:
    """Represents the state of a single light."""

    entity_id: str
    stage: int
    is_on: bool = False
    brightness: int = 0  # 0-255

    @property
    def brightness_pct(self) -> float:
        """Return brightness as percentage (0-100)."""
        return (self.brightness / 255 * 100) if self.brightness else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_id": self.entity_id,
            "stage": self.stage,
            "state": "on" if self.is_on else "off",
            "brightness": self.brightness,
            "brightness_pct": round(self.brightness_pct),
        }


class BaseBrightnessCalculator(ABC):
    """Abstract base for brightness calculations."""

    @abstractmethod
    def get_breakpoints(self) -> list[int]:
        """Get the breakpoints for stage activation."""

    @abstractmethod
    def get_stage_curve(self, stage_idx: int) -> str:
        """Get the brightness curve type for a stage."""

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

    def calculate_zone_brightness(self, overall_pct: float, stage: int) -> float:
        """Calculate brightness for a specific stage.

        Args:
            overall_pct: Overall brightness percentage (0-100)
            stage: Stage number (1-4)

        Returns:
            Zone brightness percentage (0-100)
        """
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

        Args:
            zone_brightness: Dict mapping stage number (1-4) to current
                           brightness percentage (0-100), or None if off.

        Returns:
            Estimated overall brightness percentage (0-100)
        """
        # Find the highest active stage
        highest_active_stage = 0
        highest_stage_brightness = 0.0

        for stage in range(1, 5):
            brightness = zone_brightness.get(stage)
            if brightness and brightness > 0:
                highest_active_stage = stage
                highest_stage_brightness = brightness

        if highest_active_stage == 0:
            return 0.0

        return self._reverse_stage_brightness(
            highest_active_stage, highest_stage_brightness
        )

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


class BaseCombinedLightsCoordinator(ABC):
    """Abstract base coordinator for combined lights logic.

    This class contains the core state management and brightness
    distribution logic, independent of how lights are actually controlled.
    """

    def __init__(self, calculator: BaseBrightnessCalculator):
        """Initialize the coordinator.

        Args:
            calculator: Brightness calculator instance
        """
        self._calculator = calculator
        self._is_on = False
        self._target_brightness = 255  # 0-255
        self._lights: dict[str, LightState] = {}

    @property
    def is_on(self) -> bool:
        """Return if the combined light is on."""
        return self._is_on

    @property
    def target_brightness(self) -> int:
        """Return the target brightness (0-255)."""
        return self._target_brightness

    @property
    def target_brightness_pct(self) -> float:
        """Return target brightness as percentage (0-100)."""
        return (self._target_brightness / 255.0) * 100

    @property
    def current_stage(self) -> int:
        """Return the current stage (1-4) based on brightness, or 0 if off."""
        if not self._is_on:
            return 0
        stage_idx = self._calculator.get_stage_from_brightness(
            self.target_brightness_pct
        )
        return stage_idx + 1

    def get_lights(self) -> list[LightState]:
        """Return all light states."""
        return list(self._lights.values())

    def get_light(self, entity_id: str) -> LightState | None:
        """Get a specific light state."""
        return self._lights.get(entity_id)

    def calculate_all_zone_brightness(self) -> dict[int, float]:
        """Calculate brightness for all stages based on current target.

        Returns:
            Dict mapping stage number (1-4) to brightness percentage
        """
        overall_pct = self.target_brightness_pct
        return {
            stage: self._calculator.calculate_zone_brightness(overall_pct, stage)
            for stage in range(1, 5)
        }

    def apply_brightness_to_lights(self) -> dict[str, int]:
        """Apply calculated brightness to all lights.

        Returns:
            Dict mapping entity_id to new brightness value (0-255)
        """
        zone_brightness = self.calculate_all_zone_brightness()
        changes: dict[str, int] = {}

        for light in self._lights.values():
            stage_brightness_pct = zone_brightness.get(light.stage, 0)

            if stage_brightness_pct > 0:
                new_brightness = int(stage_brightness_pct / 100 * 255)
                light.is_on = True
                light.brightness = new_brightness
            else:
                new_brightness = 0
                light.is_on = False
                light.brightness = 0

            changes[light.entity_id] = new_brightness

        return changes

    def turn_on(self, brightness: int | None = None) -> dict[str, int]:
        """Turn on the combined light.

        Args:
            brightness: Optional target brightness (0-255)

        Returns:
            Dict mapping entity_id to new brightness value
        """
        if brightness is not None:
            self._target_brightness = max(1, min(255, brightness))

        self._is_on = True
        return self.apply_brightness_to_lights()

    def turn_off(self) -> dict[str, int]:
        """Turn off all lights.

        Returns:
            Dict mapping entity_id to 0
        """
        self._is_on = False
        changes: dict[str, int] = {}

        for light in self._lights.values():
            light.is_on = False
            light.brightness = 0
            changes[light.entity_id] = 0

        return changes

    def set_light_brightness(
        self, entity_id: str, brightness: int
    ) -> tuple[dict[str, int], float]:
        """Manually set a single light's brightness.

        Args:
            entity_id: The light to change
            brightness: New brightness value (0-255)

        Returns:
            Tuple of (changes dict, estimated overall percentage)
        """
        light = self._lights.get(entity_id)
        if not light:
            return {}, 0.0

        # Update the specific light
        if brightness > 0:
            light.is_on = True
            light.brightness = brightness
        else:
            light.is_on = False
            light.brightness = 0

        # Update overall state
        any_on = any(light.is_on for light in self._lights.values())
        self._is_on = any_on

        # Calculate overall brightness based on the changed light
        # This is the key for back-propagation to work correctly
        overall_pct = 0.0
        if any_on:
            brightness_pct = (brightness / 255.0) * 100 if brightness > 0 else 0.0
            overall_pct = self._calculator.estimate_overall_from_single_light(
                light.stage, brightness_pct
            )
            self._target_brightness = max(1, min(255, int(overall_pct / 100 * 255)))

        return {entity_id: brightness}, overall_pct

    def apply_back_propagation(
        self, exclude_entity_id: str | None = None
    ) -> dict[str, int]:
        """Apply back-propagation to update all lights except the excluded one.

        Args:
            exclude_entity_id: Entity to exclude from updates

        Returns:
            Dict mapping entity_id to new brightness value
        """
        zone_brightness = self.calculate_all_zone_brightness()
        changes: dict[str, int] = {}

        for light in self._lights.values():
            if light.entity_id == exclude_entity_id:
                continue

            stage_brightness_pct = zone_brightness.get(light.stage, 0)

            if stage_brightness_pct > 0:
                new_brightness = int(stage_brightness_pct / 100 * 255)
                light.is_on = True
                light.brightness = new_brightness
            else:
                new_brightness = 0
                light.is_on = False
                light.brightness = 0

            changes[light.entity_id] = new_brightness

        return changes

    def _estimate_overall_from_current_lights(self) -> float:
        """Estimate overall brightness from current light states."""
        zone_brightness: dict[int, float | None] = {}

        for light in self._lights.values():
            if light.is_on and light.brightness > 0:
                zone_brightness[light.stage] = light.brightness_pct
            else:
                zone_brightness[light.stage] = None

        return self._calculator.estimate_overall_from_zones(zone_brightness)

    def reset(self) -> None:
        """Reset to initial state."""
        self._is_on = False
        self._target_brightness = 255

        for light in self._lights.values():
            light.is_on = False
            light.brightness = 0
