"""Home Assistant coordinator for Combined Lights.

This module provides an HA-specific coordinator that extends the base
coordinator with Home Assistant service calls and event handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .base_coordinator import BaseCombinedLightsCoordinator, LightState
from .brightness_calculator import BrightnessCalculator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class HACombinedLightsCoordinator(BaseCombinedLightsCoordinator):
    """Home Assistant coordinator extending the base coordinator.

    Adds HA service calls and state synchronization while using
    the same core logic as the simulation.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        calculator: BrightnessCalculator,
    ):
        """Initialize the HA coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            calculator: Brightness calculator instance
        """
        super().__init__(calculator)
        self._hass = hass
        self._entry = entry

    def register_light(self, entity_id: str, stage: int) -> None:
        """Register a light entity with its stage.

        Args:
            entity_id: The light entity ID
            stage: Stage number (1-4)
        """
        self._lights[entity_id] = LightState(entity_id=entity_id, stage=stage)

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

    def handle_manual_light_change(
        self, entity_id: str, brightness: int
    ) -> tuple[float, dict[str, int]]:
        """Handle a manual light change and calculate back-propagation.

        This mirrors the simulation's async_set_light_brightness() logic.

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
        # This matches the simulation behavior - estimate_overall_from_single_light
        # handles brightness=0 specially by returning the stage's threshold
        brightness_pct = (brightness / 255.0) * 100 if brightness > 0 else 0.0
        overall_pct = self._calculator.estimate_overall_from_single_light(
            light.stage, brightness_pct
        )

        if any_on:
            self._target_brightness = max(1, min(255, int(overall_pct / 100 * 255)))

        # Calculate back-propagation changes (excluding the changed light)
        back_prop_changes = self.apply_back_propagation(exclude_entity_id=entity_id)

        return overall_pct, back_prop_changes

    def get_zone_brightness_for_ha(self) -> dict[str, float]:
        """Get zone brightness values keyed by zone name for HA.

        Returns:
            Dict mapping zone name (stage_1, etc.) to brightness percentage
        """
        stage_brightness = self.calculate_all_zone_brightness()
        return {f"stage_{stage}": pct for stage, pct in stage_brightness.items()}

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
