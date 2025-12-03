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
        if not light_entities:
            return {}

        brightness_value = int(brightness_pct / 100.0 * 255)
        expected_states = {}

        _LOGGER.debug(
            "LightController.turn_on_lights: brightness_pct=%.1f%%, brightness_value=%d, entities=%s",
            brightness_pct,
            brightness_value,
            light_entities,
        )

        try:
            # Call service with all entities at once - more efficient and atomic
            await self._hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": light_entities,
                    "brightness": brightness_value,
                },
                blocking=True,
                context=context,
            )
            # Mark all entities as expected to have new brightness
            for entity_id in light_entities:
                expected_states[entity_id] = brightness_value
            _LOGGER.debug(
                "Called light.turn_on for %s with brightness %d",
                light_entities,
                brightness_value,
            )
        except (ServiceNotFound, ValueError) as err:
            _LOGGER.error("Failed to control lights %s: %s", light_entities, err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unexpected error controlling lights %s: %s", light_entities, err
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
        if not light_entities:
            return {}

        expected_states = {}

        try:
            # Call service with all entities at once - more efficient and atomic
            await self._hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": light_entities},
                blocking=True,
                context=context,
            )
            # Mark all entities as expected to be off
            for entity_id in light_entities:
                expected_states[entity_id] = 0
            _LOGGER.debug("Called light.turn_off for %s", light_entities)
        except (ServiceNotFound, ValueError) as err:
            _LOGGER.error("Failed to turn off lights %s: %s", light_entities, err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unexpected error turning off lights %s: %s", light_entities, err
            )

        return expected_states
