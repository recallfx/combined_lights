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

from .const import CONF_BACKGROUND_LIGHTS, CONF_CEILING_LIGHTS, CONF_FEATURE_LIGHTS

_LOGGER = logging.getLogger(__name__)


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
        self._attr_name = entry.data.get("name", "Combined Lights")
        self._attr_unique_id = f"{entry.entry_id}_combined_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._remove_listener = None

        # No device info - entity will be created without a device

    async def async_added_to_hass(self) -> None:
        """Entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Get all controlled lights
        all_lights = self._get_all_controlled_lights()

        # Listen for state changes of controlled lights
        @callback
        def light_state_changed(event: Event) -> None:
            """Handle controlled light state changes."""
            entity_id = event.data.get("entity_id")
            if entity_id in all_lights:
                self.async_schedule_update_ha_state()

        self._remove_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, light_state_changed
        )

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from Home Assistant."""
        if self._remove_listener:
            self._remove_listener()
        await super().async_will_remove_from_hass()

    def _get_all_controlled_lights(self) -> list[str]:
        """Get all controlled light entity IDs."""
        background_lights = self._entry.data.get(CONF_BACKGROUND_LIGHTS, [])
        feature_lights = self._entry.data.get(CONF_FEATURE_LIGHTS, [])
        ceiling_lights = self._entry.data.get(CONF_CEILING_LIGHTS, [])
        return background_lights + feature_lights + ceiling_lights

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
        """Return the brightness of the combined light based on controlled lights."""
        if not self.is_on:
            return None

        # Calculate effective brightness based on which zones are active
        background_lights = self._entry.data.get(CONF_BACKGROUND_LIGHTS, [])
        feature_lights = self._entry.data.get(CONF_FEATURE_LIGHTS, [])
        ceiling_lights = self._entry.data.get(CONF_CEILING_LIGHTS, [])

        # Check which zones have lights on
        background_on = any(
            self.hass.states.get(entity_id)
            and self.hass.states.get(entity_id).state == "on"
            for entity_id in background_lights
        )
        feature_on = any(
            self.hass.states.get(entity_id)
            and self.hass.states.get(entity_id).state == "on"
            for entity_id in feature_lights
        )
        ceiling_on = any(
            self.hass.states.get(entity_id)
            and self.hass.states.get(entity_id).state == "on"
            for entity_id in ceiling_lights
        )

        # Estimate overall brightness based on active zones
        if ceiling_on:
            # If ceiling lights are on, we're in the 66-100% range
            # Get average brightness of ceiling lights
            ceiling_brightness = self._get_average_brightness(ceiling_lights)
            if ceiling_brightness:
                # Map ceiling brightness to the 66-100% range
                return int(166 + (ceiling_brightness * 89 / 255))
        elif feature_on:
            # If feature lights are on, we're in the 33-66% range
            feature_brightness = self._get_average_brightness(feature_lights)
            if feature_brightness:
                # Map feature brightness to the 33-66% range
                return int(84 + (feature_brightness * 84 / 255))
        elif background_on:
            # If only background lights are on, we're in the 0-33% range
            background_brightness = self._get_average_brightness(background_lights)
            if background_brightness:
                # Map background brightness to the 0-33% range
                return int(background_brightness * 84 / 255)

        # Default to current brightness if we can't determine
        return self._attr_brightness

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
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        self._attr_is_on = True

        # Control the actual lights based on brightness and zone configuration
        brightness_pct = self._attr_brightness / 255.0

        # Get configured light entities from config entry
        background_lights = self._entry.data.get(CONF_BACKGROUND_LIGHTS, [])
        feature_lights = self._entry.data.get(CONF_FEATURE_LIGHTS, [])
        ceiling_lights = self._entry.data.get(CONF_CEILING_LIGHTS, [])

        # Define breakpoints - you can make these configurable later
        # Background: 0.0 - 0.33 (0% - 33%)
        # Feature: 0.33 - 0.66 (33% - 66%)
        # Ceiling: 0.66 - 1.0 (66% - 100%)

        # Calculate brightness for each zone
        background_brightness = self._calculate_zone_brightness(
            brightness_pct, 0.0, 0.33
        )
        feature_brightness = self._calculate_zone_brightness(brightness_pct, 0.33, 0.66)
        ceiling_brightness = self._calculate_zone_brightness(brightness_pct, 0.66, 1.0)

        # Control background lights
        if background_lights and background_brightness > 0:
            await self._control_lights(background_lights, background_brightness)
        elif background_lights:
            await self._turn_off_lights(background_lights)

        # Control feature lights
        if feature_lights and feature_brightness > 0:
            await self._control_lights(feature_lights, feature_brightness)
        elif feature_lights:
            await self._turn_off_lights(feature_lights)

        # Control ceiling lights
        if ceiling_lights and ceiling_brightness > 0:
            await self._control_lights(ceiling_lights, ceiling_brightness)
        elif ceiling_lights:
            await self._turn_off_lights(ceiling_lights)

        _LOGGER.info(
            "Combined light turned on - brightness: %s%% | background: %s%% | feature: %s%% | ceiling: %s%%",
            int(brightness_pct * 100),
            int(background_brightness * 100) if background_brightness > 0 else 0,
            int(feature_brightness * 100) if feature_brightness > 0 else 0,
            int(ceiling_brightness * 100) if ceiling_brightness > 0 else 0,
        )

        self.async_write_ha_state()

    def _calculate_zone_brightness(
        self, overall_pct: float, zone_start: float, zone_end: float
    ) -> float:
        """Calculate brightness for a specific zone based on overall brightness and breakpoints."""
        if overall_pct <= zone_start:
            return 0.0
        if overall_pct >= zone_end:
            return 1.0
        # Linear interpolation within the zone
        zone_range = zone_end - zone_start
        return (overall_pct - zone_start) / zone_range

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
        background_lights = self._entry.data.get(CONF_BACKGROUND_LIGHTS, [])
        feature_lights = self._entry.data.get(CONF_FEATURE_LIGHTS, [])
        ceiling_lights = self._entry.data.get(CONF_CEILING_LIGHTS, [])

        all_lights = background_lights + feature_lights + ceiling_lights

        if all_lights:
            await self._turn_off_lights(all_lights)

        _LOGGER.info("Combined light turned off - all configured lights turned off")

        self.async_write_ha_state()
