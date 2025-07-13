"""Light platform for Combined Lights integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceNotFound
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BACKGROUND_BRIGHTNESS_RANGES,
    CONF_BACKGROUND_LIGHTS,
    CONF_BREAKPOINTS,
    CONF_BRIGHTNESS_CURVE,
    CONF_CEILING_BRIGHTNESS_RANGES,
    CONF_CEILING_LIGHTS,
    CONF_FEATURE_BRIGHTNESS_RANGES,
    CONF_FEATURE_LIGHTS,
    CURVE_CUBIC,
    CURVE_QUADRATIC,
    DEFAULT_BACKGROUND_BRIGHTNESS_RANGES,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_CEILING_BRIGHTNESS_RANGES,
    DEFAULT_FEATURE_BRIGHTNESS_RANGES,
)

_LOGGER = logging.getLogger(__name__)


# Utility functions to eliminate code duplication
def get_config_value(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Get configuration value with default fallback."""
    return entry.data.get(key, default)


def get_light_zones(entry: ConfigEntry) -> dict[str, list[str]]:
    """Get all light zones from configuration."""
    return {
        "background": get_config_value(entry, CONF_BACKGROUND_LIGHTS, []),
        "feature": get_config_value(entry, CONF_FEATURE_LIGHTS, []),
        "ceiling": get_config_value(entry, CONF_CEILING_LIGHTS, []),
    }


def get_brightness_ranges(entry: ConfigEntry) -> dict[str, list[list[int]]]:
    """Get all brightness ranges from configuration."""
    return {
        "background": get_config_value(
            entry,
            CONF_BACKGROUND_BRIGHTNESS_RANGES,
            DEFAULT_BACKGROUND_BRIGHTNESS_RANGES,
        ),
        "feature": get_config_value(
            entry, CONF_FEATURE_BRIGHTNESS_RANGES, DEFAULT_FEATURE_BRIGHTNESS_RANGES
        ),
        "ceiling": get_config_value(
            entry, CONF_CEILING_BRIGHTNESS_RANGES, DEFAULT_CEILING_BRIGHTNESS_RANGES
        ),
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Combined Lights light entity."""
    # Create a single combined light entity
    async_add_entities([CombinedLight(entry)], True)


class CombinedLight(LightEntity):
    """Combined Light entity that controls multiple light zones."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Combined Light."""
        self._entry = entry
        self._attr_name = get_config_value(entry, "name", "Combined Lights")
        self._attr_unique_id = f"{entry.entry_id}_combined_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._remove_listener = None
        self._target_brightness = 255  # Track the intended brightness

        # No device info - entity will be created without a device

    async def async_added_to_hass(self) -> None:
        """Entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Initialize target brightness based on current state
        if self.is_on and not hasattr(self, "_target_brightness_initialized"):
            # If lights are already on, estimate target brightness from current state
            self._sync_target_brightness_from_lights()
            self._target_brightness_initialized = True

        # Get all controlled lights
        all_lights = self._get_all_controlled_lights()

        # Listen for state changes of controlled lights
        @callback
        def light_state_changed(event: Event) -> None:
            """Handle controlled light state changes."""
            entity_id = event.data.get("entity_id")
            if entity_id in all_lights:
                # Only schedule update, don't recalculate target brightness
                # This prevents feedback loops while still updating the is_on state
                self.async_schedule_update_ha_state()

        self._remove_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, light_state_changed
        )

    def _sync_target_brightness_from_lights(self) -> None:
        """Sync target brightness from actual light states (used during initialization)."""
        # Get configuration
        breakpoints = get_config_value(
            self._entry, CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS
        )
        light_zones = get_light_zones(self._entry)

        # Get average brightness from each zone
        zone_brightness = {
            zone: self._get_average_brightness(lights)
            for zone, lights in light_zones.items()
        }

        # Simple heuristic: use the highest brightness from active zones
        # and map it to an appropriate target brightness
        max_brightness = 0
        if zone_brightness["ceiling"]:
            # Ceiling lights suggest we're in stage 3 or 4
            max_brightness = max(
                max_brightness,
                breakpoints[2] * 255 // 100 + zone_brightness["ceiling"] // 2,
            )
        elif zone_brightness["feature"]:
            # Feature lights suggest we're in stage 2 or 3
            max_brightness = max(
                max_brightness,
                breakpoints[1] * 255 // 100 + zone_brightness["feature"] // 2,
            )
        elif zone_brightness["background"]:
            # Background lights suggest we're in stage 1 or 2
            max_brightness = max(max_brightness, zone_brightness["background"])

        if max_brightness > 0:
            self._target_brightness = min(255, max_brightness)
            self._attr_brightness = self._target_brightness

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from Home Assistant."""
        if self._remove_listener:
            self._remove_listener()
        await super().async_will_remove_from_hass()

    def _get_all_controlled_lights(self) -> list[str]:
        """Get all controlled light entity IDs."""
        light_zones = get_light_zones(self._entry)
        return sum(light_zones.values(), [])  # Flatten all zone lists

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if any controlled light is on."""
        all_lights = self._get_all_controlled_lights()
        for entity_id in all_lights:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    @property
    def brightness(self) -> int | None:
        """Return the target brightness of the combined light."""
        if not self.is_on:
            return None
        return self._target_brightness

    def _get_average_brightness(self, light_entities: list[str]) -> int | None:
        """Get average brightness of lights that are on."""
        brightness_values = []
        for entity_id in light_entities:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                brightness = state.attributes.get("brightness")
                if brightness is not None:
                    brightness_values.append(brightness)

        return (
            int(sum(brightness_values) / len(brightness_values))
            if brightness_values
            else None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the combined light."""
        if ATTR_BRIGHTNESS in kwargs:
            self._target_brightness = kwargs[ATTR_BRIGHTNESS]
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        self._attr_is_on = True

        # Get configuration using utility functions
        breakpoints = get_config_value(
            self._entry, CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS
        )
        light_zones = get_light_zones(self._entry)
        brightness_ranges = get_brightness_ranges(self._entry)

        # Convert brightness to percentage (0-100)
        brightness_pct = (self._target_brightness / 255.0) * 100

        # Determine which stage we're in based on breakpoints
        stage = self._get_stage_from_brightness(brightness_pct, breakpoints)

        # Calculate and apply brightness for each zone
        zone_brightness = {}
        for zone_name in ["background", "feature", "ceiling"]:
            zone_brightness[zone_name] = self._calculate_zone_brightness_from_config(
                brightness_pct, stage, brightness_ranges[zone_name], breakpoints
            )

        # Control all zones
        await self._control_all_zones(light_zones, zone_brightness)

        _LOGGER.info(
            "Combined light turned on - overall: %s%% (stage %s) | background: %s%% | feature: %s%% | ceiling: %s%%",
            int(brightness_pct),
            stage + 1,
            int(zone_brightness["background"])
            if zone_brightness["background"] > 0
            else 0,
            int(zone_brightness["feature"]) if zone_brightness["feature"] > 0 else 0,
            int(zone_brightness["ceiling"]) if zone_brightness["ceiling"] > 0 else 0,
        )

        self.async_write_ha_state()

    async def _control_all_zones(
        self, light_zones: dict[str, list[str]], zone_brightness: dict[str, float]
    ) -> None:
        """Control all light zones based on calculated brightness values."""
        for zone_name, lights in light_zones.items():
            if not lights:
                continue

            brightness = zone_brightness[zone_name]
            if brightness > 0:
                await self._control_lights(lights, brightness / 100.0)
            else:
                await self._turn_off_lights(lights)

    def _get_stage_from_brightness(
        self, brightness_pct: float, breakpoints: list[int]
    ) -> int:
        """Determine stage based on brightness percentage and breakpoints."""
        if brightness_pct <= breakpoints[0]:
            return 0  # Stage 1: 0% to breakpoints[0]%
        if brightness_pct <= breakpoints[1]:
            return 1  # Stage 2: breakpoints[0]% to breakpoints[1]%
        if brightness_pct <= breakpoints[2]:
            return 2  # Stage 3: breakpoints[1]% to breakpoints[2]%
        return 3  # Stage 4: breakpoints[2]% to 100%

    def _calculate_zone_brightness_from_config(
        self,
        overall_pct: float,
        stage: int,
        zone_ranges: list[list[int]],
        breakpoints: list[int],
    ) -> float:
        """Calculate brightness for a zone based on configuration and current stage."""
        # Get the brightness range for this stage
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

        stage_start, stage_end = stage_boundaries[stage]

        # Calculate progress within the stage (0.0 to 1.0)
        if stage_end == stage_start:
            progress = 0.0
        else:
            progress = max(
                0.0, min(1.0, (overall_pct - stage_start) / (stage_end - stage_start))
            )

        # Map progress to the configured brightness range for this zone
        min_brightness, max_brightness = stage_range

        # Apply brightness curve to the progress
        curve_type = get_config_value(
            self._entry, CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE
        )
        curved_progress = self._apply_brightness_curve(progress, curve_type)

        return min_brightness + (curved_progress * (max_brightness - min_brightness))

    def _apply_brightness_curve(self, progress: float, curve_type: str) -> float:
        """Apply brightness curve to linear progress for more natural feel."""
        if curve_type == CURVE_QUADRATIC:
            # Gentle curve: more linear at very low values, curve kicks in higher
            # For very low progress (< 10%), use mostly linear
            if progress < 0.1:
                return progress * 0.9 + (progress**0.5) * 0.1
            # For higher progress, use more curve
            return 0.4 * progress + 0.6 * (progress**0.5)
        if curve_type == CURVE_CUBIC:
            # More aggressive curve for maximum low-end precision
            if progress < 0.1:
                return progress * 0.8 + (progress ** (1 / 3)) * 0.2
            return 0.2 * progress + 0.8 * (progress ** (1 / 3))
        # Linear curve: even response
        return progress

    async def _control_lights(
        self, light_entities: list[str], brightness_pct: float
    ) -> None:
        """Turn on lights with specified brightness."""
        brightness_value = int(brightness_pct * 255)

        for entity_id in light_entities:
            try:
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {
                        "entity_id": entity_id,
                        "brightness": brightness_value,
                    },
                )
            except (ServiceNotFound, ValueError) as err:
                _LOGGER.error("Failed to control light %s: %s", entity_id, err)

    async def _turn_off_lights(self, light_entities: list[str]) -> None:
        """Turn off lights."""
        for entity_id in light_entities:
            try:
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {"entity_id": entity_id},
                )
            except (ServiceNotFound, ValueError) as err:
                _LOGGER.error("Failed to turn off light %s: %s", entity_id, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the combined light."""
        self._attr_is_on = False

        # Turn off all configured lights
        all_lights = self._get_all_controlled_lights()

        if all_lights:
            await self._turn_off_lights(all_lights)

        _LOGGER.info("Combined light turned off - all configured lights turned off")

        self.async_write_ha_state()
