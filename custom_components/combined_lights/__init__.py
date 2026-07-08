"""The Combined Lights integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BREAKPOINTS,
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_1_OFF_TURNS_OFF,
    CONF_STAGE_2_CURVE,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_CURVE,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_CURVE,
    CONF_STAGE_4_LIGHTS,
    CURVE_CBRT,
    CURVE_CUBIC,
    CURVE_LINEAR,
    CURVE_QUADRATIC,
    CURVE_SQRT,
    DEFAULT_BREAKPOINTS,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    DEFAULT_STAGE_1_CURVE,
    DEFAULT_STAGE_1_OFF_TURNS_OFF,
    DEFAULT_STAGE_2_CURVE,
    DEFAULT_STAGE_3_CURVE,
    DEFAULT_STAGE_4_CURVE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Define the platforms this integration will set up.
PLATFORMS: list[str] = ["light"]

_CURVES = [CURVE_LINEAR, CURVE_QUADRATIC, CURVE_CUBIC, CURVE_SQRT, CURVE_CBRT]


def _light_list(value: Any) -> list[str]:
    """Validate a list of light entity ids."""
    return vol.All(cv.ensure_list, [cv.entity_id])(value)


def _breakpoints(value: Any) -> list[int]:
    """Validate the three progressive brightness breakpoints."""
    points = vol.All(cv.ensure_list, [vol.Coerce(int)], vol.Length(min=3, max=3))(
        value
    )
    if points != sorted(points) or points[0] < 0 or points[-1] >= 100:
        raise vol.Invalid("breakpoints must be ascending values from 0 to 99")
    return points


COMBINED_LIGHT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_STAGE_1_LIGHTS, default=[]): _light_list,
        vol.Optional(CONF_STAGE_2_LIGHTS, default=[]): _light_list,
        vol.Optional(CONF_STAGE_3_LIGHTS, default=[]): _light_list,
        vol.Optional(CONF_STAGE_4_LIGHTS, default=[]): _light_list,
        vol.Optional(
            CONF_ENABLE_BACK_PROPAGATION, default=DEFAULT_ENABLE_BACK_PROPAGATION
        ): cv.boolean,
        vol.Optional(
            CONF_STAGE_1_OFF_TURNS_OFF, default=DEFAULT_STAGE_1_OFF_TURNS_OFF
        ): cv.boolean,
        vol.Optional(CONF_BREAKPOINTS, default=DEFAULT_BREAKPOINTS): _breakpoints,
        vol.Optional(CONF_STAGE_1_CURVE, default=DEFAULT_STAGE_1_CURVE): vol.In(
            _CURVES
        ),
        vol.Optional(CONF_STAGE_2_CURVE, default=DEFAULT_STAGE_2_CURVE): vol.In(
            _CURVES
        ),
        vol.Optional(CONF_STAGE_3_CURVE, default=DEFAULT_STAGE_3_CURVE): vol.In(
            _CURVES
        ),
        vol.Optional(CONF_STAGE_4_CURVE, default=DEFAULT_STAGE_4_CURVE): vol.In(
            _CURVES
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [COMBINED_LIGHT_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Combined Lights from YAML."""
    yaml_configs = config.get(DOMAIN)
    if not yaml_configs:
        return True

    for yaml_config in yaml_configs:
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=dict(yaml_config),
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Combined Lights from a config entry."""
    # Forward the setup to the light platform, providing the list of platforms.
    # This will be called on initial setup and after reconfiguration.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the platforms that were set up.
    # This will be called before reconfiguration to clean up the current setup.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
