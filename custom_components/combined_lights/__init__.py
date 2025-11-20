"""The Combined Lights integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
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

_LOGGER = logging.getLogger(__name__)

# Define the platforms this integration will set up.
PLATFORMS: list[str] = ["light"]


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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migration from version 1 (range-based) to version 2 (curve-based)
        # Actually we are keeping version 1 but changing data structure
        # Check if we have old data structure
        data = {**config_entry.data}
        
        if "stage_1_brightness_ranges" in data:
            _LOGGER.info("Migrating Combined Lights config to curve-based format")
            
            # Remove old range keys
            for i in range(1, 5):
                range_key = f"stage_{i}_brightness_ranges"
                if range_key in data:
                    del data[range_key]
            
            # Remove old global curve key if present
            if "brightness_curve" in data:
                del data["brightness_curve"]
                
            # Add new curve keys with defaults
            data[CONF_STAGE_1_CURVE] = DEFAULT_STAGE_1_CURVE
            data[CONF_STAGE_2_CURVE] = DEFAULT_STAGE_2_CURVE
            data[CONF_STAGE_3_CURVE] = DEFAULT_STAGE_3_CURVE
            data[CONF_STAGE_4_CURVE] = DEFAULT_STAGE_4_CURVE
            
            # Ensure breakpoints exist
            if CONF_BREAKPOINTS not in data:
                data[CONF_BREAKPOINTS] = DEFAULT_BREAKPOINTS
                
            hass.config_entries.async_update_entry(config_entry, data=data)
            _LOGGER.info("Migration to curve-based format successful")

    return True
