"""Zone manager helper."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_LIGHTS,
)


class ZoneManager:
    """Manages light zones and their configuration."""

    def __init__(self, entry: ConfigEntry):
        """Initialize the zone manager.

        Args:
            entry: Config entry containing zone configuration
        """
        self._entry = entry

    def get_light_zones(self) -> dict[str, list[str]]:
        """Get all light zones from configuration."""
        return {
            "stage_1": self._entry.data.get(CONF_STAGE_1_LIGHTS, []),
            "stage_2": self._entry.data.get(CONF_STAGE_2_LIGHTS, []),
            "stage_3": self._entry.data.get(CONF_STAGE_3_LIGHTS, []),
            "stage_4": self._entry.data.get(CONF_STAGE_4_LIGHTS, []),
        }

    def get_all_lights(self) -> list[str]:
        """Get all light entity IDs across all zones."""
        all_lights = []
        for lights in self.get_light_zones().values():
            all_lights.extend(lights)
        return all_lights

    def get_zone_lights(self, zone_name: str) -> list[str]:
        """Get lights for a specific zone."""
        zones = self.get_light_zones()
        return zones.get(zone_name, [])

    def get_average_brightness(
        self, hass: HomeAssistant, light_entities: list[str]
    ) -> int | None:
        """Get average brightness of lights that are on.

        Args:
            hass: Home Assistant instance
            light_entities: List of light entity IDs

        Returns:
            Average brightness or None if no lights are on
        """
        brightness_values = []
        for entity_id in light_entities:
            state = hass.states.get(entity_id)
            if state and state.state == "on":
                brightness = state.attributes.get("brightness")
                if brightness is not None:
                    brightness_values.append(brightness)

        return (
            int(sum(brightness_values) / len(brightness_values))
            if brightness_values
            else None
        )

    def is_any_light_on(self, hass: HomeAssistant) -> bool:
        """Check if any controlled light is on."""
        all_lights = self.get_all_lights()
        for entity_id in all_lights:
            state = hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    def get_zone_brightness_dict(self, hass: HomeAssistant) -> dict[str, float | None]:
        """Get current brightness for each zone.

        Args:
            hass: Home Assistant instance

        Returns:
            Dictionary mapping zone names to average brightness percentage (0-100)
            or None if zone is completely off
        """
        zones = self.get_light_zones()
        zone_brightness = {}

        for zone_name, lights in zones.items():
            if not lights:
                zone_brightness[zone_name] = None
                continue

            avg_brightness = self.get_average_brightness(hass, lights)
            if avg_brightness is None:
                zone_brightness[zone_name] = None
            else:
                # Convert from 0-255 to 0-100
                zone_brightness[zone_name] = (avg_brightness / 255.0) * 100

        return zone_brightness
