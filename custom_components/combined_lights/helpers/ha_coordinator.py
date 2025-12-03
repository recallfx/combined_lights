"""Home Assistant coordinator for Combined Lights.

This module provides the coordinator that manages combined lights state,
brightness distribution, and synchronization with Home Assistant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .brightness_calculator import BrightnessCalculator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

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


class HACombinedLightsCoordinator:
    """Coordinator for combined lights state management.

    Handles brightness distribution, state synchronization with Home Assistant,
    and back-propagation calculations.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        calculator: BrightnessCalculator,
    ):
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            calculator: Brightness calculator instance
        """
        self._hass = hass
        self._entry = entry
        self._calculator = calculator
        self._is_on = False
        self._target_brightness = 255  # 0-255
        self._lights: dict[str, LightState] = {}

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Light registration and state access
    # -------------------------------------------------------------------------

    def register_light(self, entity_id: str, stage: int) -> None:
        """Register a light entity with its stage.

        Args:
            entity_id: The light entity ID
            stage: Stage number (1-4)
        """
        self._lights[entity_id] = LightState(entity_id=entity_id, stage=stage)

    def get_lights(self) -> list[LightState]:
        """Return all light states."""
        return list(self._lights.values())

    def get_light(self, entity_id: str) -> LightState | None:
        """Get a specific light state."""
        return self._lights.get(entity_id)

    def get_lights_by_stage(self) -> dict[int, list[str]]:
        """Get light entity IDs grouped by stage.

        Returns:
            Dict mapping stage number to list of entity IDs
        """
        by_stage: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
        for light in self._lights.values():
            if light.stage in by_stage:
                by_stage[light.stage].append(light.entity_id)
        return by_stage

    def get_stage_for_entity(self, entity_id: str) -> int | None:
        """Get the stage number for a light entity.

        Args:
            entity_id: The light entity ID

        Returns:
            Stage number (1-4) or None if not found
        """
        light = self._lights.get(entity_id)
        return light.stage if light else None

    # -------------------------------------------------------------------------
    # HA state synchronization
    # -------------------------------------------------------------------------

    def sync_light_state_from_ha(self, entity_id: str) -> None:
        """Sync internal light state from Home Assistant state.

        Args:
            entity_id: The light entity ID to sync
        """
        light = self._lights.get(entity_id)
        if not light:
            return

        state = self._hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            return

        if state.state == "on":
            light.is_on = True
            light.brightness = state.attributes.get("brightness", 255) or 255
        else:
            light.is_on = False
            light.brightness = 0

    def sync_all_lights_from_ha(self) -> None:
        """Sync all internal light states from Home Assistant."""
        for entity_id in self._lights:
            self.sync_light_state_from_ha(entity_id)

        # Update overall state
        self._is_on = any(light.is_on for light in self._lights.values())

    # -------------------------------------------------------------------------
    # Brightness calculations
    # -------------------------------------------------------------------------

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

    def get_zone_brightness_for_ha(self) -> dict[str, float]:
        """Get zone brightness values keyed by zone name for HA.

        Returns:
            Dict mapping zone name (stage_1, etc.) to brightness percentage
        """
        stage_brightness = self.calculate_all_zone_brightness()
        return {f"stage_{stage}": pct for stage, pct in stage_brightness.items()}

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

    # -------------------------------------------------------------------------
    # Turn on/off operations
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Manual change handling and back-propagation
    # -------------------------------------------------------------------------

    def handle_manual_light_change(
        self, entity_id: str, brightness: int
    ) -> tuple[float, dict[str, int]]:
        """Handle a manual light change and calculate back-propagation.

        Args:
            entity_id: The light that was manually changed
            brightness: New brightness value (0-255)

        Returns:
            Tuple of (new overall percentage, back-propagation changes dict)
        """
        light = self._lights.get(entity_id)
        if not light:
            return 0.0, {}

        # Update the specific light state
        if brightness > 0:
            light.is_on = True
            light.brightness = brightness
        else:
            light.is_on = False
            light.brightness = 0

        # Update overall on/off state
        any_on = any(light.is_on for light in self._lights.values())
        self._is_on = any_on

        # Calculate new overall brightness using single-light estimation
        brightness_pct = (brightness / 255.0) * 100 if brightness > 0 else 0.0
        overall_pct = self._calculator.estimate_overall_from_single_light(
            light.stage, brightness_pct
        )

        if any_on:
            self._target_brightness = max(1, min(255, int(overall_pct / 100 * 255)))

        # Calculate back-propagation changes (excluding the changed light)
        back_prop_changes = self.apply_back_propagation(exclude_entity_id=entity_id)

        return overall_pct, back_prop_changes

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
        # If the system is off, back-propagation should ensure everything is off
        if not self._is_on:
            changes: dict[str, int] = {}
            for light in self._lights.values():
                if light.entity_id == exclude_entity_id:
                    continue
                # Only include if it needs to be turned off
                if light.is_on or light.brightness > 0:
                    light.is_on = False
                    light.brightness = 0
                    changes[light.entity_id] = 0
            return changes

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

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

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
