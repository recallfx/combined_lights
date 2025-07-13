"""Config flow for Combined Lights."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

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
    CURVE_LINEAR,
    CURVE_QUADRATIC,
    DEFAULT_BACKGROUND_BRIGHTNESS_RANGES,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_CEILING_BRIGHTNESS_RANGES,
    DEFAULT_FEATURE_BRIGHTNESS_RANGES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# Utility functions to eliminate code duplication
def create_light_entity_selector() -> selector.EntitySelector:
    """Create light entity selector for reuse."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light", multiple=True)
    )


def create_basic_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Create basic configuration schema with optional defaults."""
    defaults = defaults or {}
    
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): selector.TextSelector(),
            vol.Optional(
                CONF_BACKGROUND_LIGHTS,
                default=defaults.get(CONF_BACKGROUND_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_FEATURE_LIGHTS,
                default=defaults.get(CONF_FEATURE_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_CEILING_LIGHTS,
                default=defaults.get(CONF_CEILING_LIGHTS, []),
            ): create_light_entity_selector(),
        }
    )


def create_curve_selector() -> selector.SelectSelector:
    """Create brightness curve selector for reuse."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": CURVE_LINEAR, "label": "Linear (even response)"},
                {"value": CURVE_QUADRATIC, "label": "Quadratic (more precision at low brightness)"},
                {"value": CURVE_CUBIC, "label": "Cubic (maximum precision at low brightness)"},
            ]
        )
    )


def create_advanced_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Create advanced configuration schema with optional defaults."""
    defaults = defaults or {}
    
    return vol.Schema(
        {
            vol.Optional(
                CONF_BREAKPOINTS,
                default=defaults.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS),
                description="Slider breakpoints (e.g., [30, 60, 90])",
            ): selector.ObjectSelector(),
            vol.Optional(
                CONF_BRIGHTNESS_CURVE,
                default=defaults.get(CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE),
                description="Brightness response curve",
            ): create_curve_selector(),
            vol.Optional(
                CONF_BACKGROUND_BRIGHTNESS_RANGES,
                default=defaults.get(CONF_BACKGROUND_BRIGHTNESS_RANGES, DEFAULT_BACKGROUND_BRIGHTNESS_RANGES),
                description="Background brightness ranges for each stage",
            ): selector.ObjectSelector(),
            vol.Optional(
                CONF_FEATURE_BRIGHTNESS_RANGES,
                default=defaults.get(CONF_FEATURE_BRIGHTNESS_RANGES, DEFAULT_FEATURE_BRIGHTNESS_RANGES),
                description="Feature brightness ranges for each stage",
            ): selector.ObjectSelector(),
            vol.Optional(
                CONF_CEILING_BRIGHTNESS_RANGES,
                default=defaults.get(CONF_CEILING_BRIGHTNESS_RANGES, DEFAULT_CEILING_BRIGHTNESS_RANGES),
                description="Ceiling brightness ranges for each stage",
            ): selector.ObjectSelector(),
        }
    )


def merge_config_with_defaults(config_data: dict[str, Any], user_input: dict[str, Any]) -> dict[str, Any]:
    """Merge configuration data with defaults for missing values."""
    return {
        **config_data,
        CONF_BREAKPOINTS: user_input.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS),
        CONF_BRIGHTNESS_CURVE: user_input.get(CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE),
        CONF_BACKGROUND_BRIGHTNESS_RANGES: user_input.get(
            CONF_BACKGROUND_BRIGHTNESS_RANGES,
            DEFAULT_BACKGROUND_BRIGHTNESS_RANGES,
        ),
        CONF_FEATURE_BRIGHTNESS_RANGES: user_input.get(
            CONF_FEATURE_BRIGHTNESS_RANGES, DEFAULT_FEATURE_BRIGHTNESS_RANGES
        ),
        CONF_CEILING_BRIGHTNESS_RANGES: user_input.get(
            CONF_CEILING_BRIGHTNESS_RANGES, DEFAULT_CEILING_BRIGHTNESS_RANGES
        ),
    }


class CombinedLightsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Combined Lights."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store basic configuration
            self._config_data.update(user_input)

            # Proceed to advanced configuration
            return await self.async_step_advanced()

        # Use utility function to create schema
        data_schema = create_basic_schema()

        # Show the form to the user.
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Configure your light zones. Next step will allow customizing breakpoints and brightness ranges."
            },
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle advanced configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge advanced configuration with defaults using utility function
            config_data = merge_config_with_defaults(self._config_data, user_input)

            # Create the config entry
            return self.async_create_entry(
                title=self._config_data[CONF_NAME], data=config_data
            )

        # Use utility function to create advanced schema
        data_schema = create_advanced_schema()

        return self.async_show_form(
            step_id="advanced",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "Advanced: Configure breakpoints and brightness ranges.\n"
                    "Breakpoints: [30, 60, 90] means 1-30%, 31-60%, 61-90%, 91-100%\n"
                    "Brightness ranges: [[min, max], ...] for each stage"
                )
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}

        # Get the config entry being reconfigured
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if config_entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            # Store basic configuration for reconfiguration
            self._config_data = {**config_entry.data, **user_input}

            # Proceed to advanced configuration
            return await self.async_step_reconfigure_advanced()

        # Use utility function to create schema with current values as defaults
        data_schema = create_basic_schema(config_entry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Update your light zones configuration. Next step will allow customizing breakpoints and brightness ranges."
            },
        )

    async def async_step_reconfigure_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle advanced reconfiguration step."""
        errors: dict[str, str] = {}

        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if config_entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            # Merge advanced configuration with current config data using utility function
            updated_config = merge_config_with_defaults(self._config_data, user_input)

            # Update the config entry
            return self.async_update_reload_and_abort(
                config_entry,
                data_updates=updated_config,
                reason="reconfigure_successful",
            )

        # Use utility function to create advanced schema with current values as defaults
        data_schema = create_advanced_schema(config_entry.data)

        return self.async_show_form(
            step_id="reconfigure_advanced",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "Advanced: Update breakpoints and brightness ranges.\n"
                    "Breakpoints: [30, 60, 90] means 1-30%, 31-60%, 61-90%, 91-100%\n"
                    "Brightness ranges: [[min, max], ...] for each stage"
                )
            },
        )
