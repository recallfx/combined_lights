"""Light controller helper."""

from __future__ import annotations

import logging

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceNotFound

_LOGGER = logging.getLogger(__name__)


class LightController:
    """Handles light control operations."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the light controller.

        Args:
            hass: Home Assistant instance
        """
        self._hass = hass

    async def turn_on_lights(
        self,
        light_entities: list[str],
        brightness_pct: float,
        context: Context,
    ) -> dict[str, int]:
        """Turn on lights with specified brightness.

        Args:
            light_entities: Light entity IDs to control
            brightness_pct: Brightness percentage (0-100)
            context: Home Assistant context

        Returns:
            Dictionary mapping entity_id to expected brightness value
        """
        brightness_value = int(brightness_pct / 100.0 * 255)
        expected_states = {}

        _LOGGER.debug(
            "LightController.turn_on_lights: brightness_pct=%.1f%%, brightness_value=%d, entities=%s",
            brightness_pct,
            brightness_value,
            light_entities,
        )

        for entity_id in light_entities:
            try:
                await self._hass.services.async_call(
                    "light",
                    "turn_on",
                    {
                        "entity_id": entity_id,
                        "brightness": brightness_value,
                    },
                    context=context,
                )
                expected_states[entity_id] = brightness_value
                _LOGGER.debug(
                    "Called light.turn_on for %s with brightness %d",
                    entity_id,
                    brightness_value,
                )
            except (ServiceNotFound, ValueError) as err:
                _LOGGER.error("Failed to control light %s: %s", entity_id, err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected error controlling light %s: %s", entity_id, err
                )

        return expected_states

    async def turn_off_lights(
        self,
        light_entities: list[str],
        context: Context,
    ) -> dict[str, int]:
        """Turn off lights.

        Args:
            light_entities: Light entity IDs to turn off
            context: Home Assistant context

        Returns:
            Dictionary mapping entity_id to expected brightness value (0)
        """
        expected_states = {}

        for entity_id in light_entities:
            try:
                await self._hass.services.async_call(
                    "light",
                    "turn_off",
                    {"entity_id": entity_id},
                    context=context,
                )
                expected_states[entity_id] = 0
            except (ServiceNotFound, ValueError) as err:
                _LOGGER.error("Failed to turn off light %s: %s", entity_id, err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected error turning off light %s: %s", entity_id, err
                )

        return expected_states
