"""Config flow for Combined Lights."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_BREAKPOINTS,
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_1_LIGHTS,
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
    DEFAULT_STAGE_1_CURVE,
    DEFAULT_STAGE_2_CURVE,
    DEFAULT_STAGE_3_CURVE,
    DEFAULT_STAGE_4_CURVE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# Utility functions to eliminate code duplication
def create_light_entity_selector() -> selector.EntitySelector:
    """Create light entity selector for reuse."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light", multiple=True)
    )


def create_curve_selector() -> selector.SelectSelector:
    """Create brightness curve selector for reuse."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": CURVE_CUBIC, "label": "Ease-In Strong (very gentle start)"},
                {"value": CURVE_QUADRATIC, "label": "Ease-In (gentle start)"},
                {"value": CURVE_LINEAR, "label": "Linear (even response)"},
                {"value": CURVE_SQRT, "label": "Ease-Out (quick start)"},
                {"value": CURVE_CBRT, "label": "Ease-Out Strong (very quick start)"},
            ]
        )
    )


def create_basic_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Create basic configuration schema with optional defaults."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, default=defaults.get(CONF_NAME, "")
            ): selector.TextSelector(),
            vol.Optional(
                CONF_STAGE_1_LIGHTS,
                default=defaults.get(CONF_STAGE_1_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_STAGE_2_LIGHTS,
                default=defaults.get(CONF_STAGE_2_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_STAGE_3_LIGHTS,
                default=defaults.get(CONF_STAGE_3_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_STAGE_4_LIGHTS,
                default=defaults.get(CONF_STAGE_4_LIGHTS, []),
            ): create_light_entity_selector(),
            vol.Optional(
                CONF_ENABLE_BACK_PROPAGATION,
                default=defaults.get(CONF_ENABLE_BACK_PROPAGATION, False),
            ): selector.BooleanSelector(),
        }
    )


def create_curve_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Create brightness curve configuration schema."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_STAGE_1_CURVE,
                default=defaults.get(CONF_STAGE_1_CURVE, DEFAULT_STAGE_1_CURVE),
            ): create_curve_selector(),
            vol.Required(
                CONF_STAGE_2_CURVE,
                default=defaults.get(CONF_STAGE_2_CURVE, DEFAULT_STAGE_2_CURVE),
            ): create_curve_selector(),
            vol.Required(
                CONF_STAGE_3_CURVE,
                default=defaults.get(CONF_STAGE_3_CURVE, DEFAULT_STAGE_3_CURVE),
            ): create_curve_selector(),
            vol.Required(
                CONF_STAGE_4_CURVE,
                default=defaults.get(CONF_STAGE_4_CURVE, DEFAULT_STAGE_4_CURVE),
            ): create_curve_selector(),
        }
    )


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

            # Proceed to curve configuration
            return await self.async_step_curves()

        # Use utility function to create schema
        data_schema = create_basic_schema()

        # Show the form to the user.
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Configure your light zones. Next step will allow customizing brightness curves."
            },
        )

    async def async_step_curves(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle brightness curve configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store curve configuration
            self._config_data.update(user_input)

            # Ensure default breakpoints are set
            if CONF_BREAKPOINTS not in self._config_data:
                self._config_data[CONF_BREAKPOINTS] = DEFAULT_BREAKPOINTS

            # Create the config entry
            return self.async_create_entry(
                title=self._config_data[CONF_NAME], data=self._config_data
            )

        # Use utility function to create schema
        data_schema = create_curve_schema()

        return self.async_show_form(
            step_id="curves",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Select brightness response curves for each stage. Linear is standard, Quadratic/Cubic give more precision at low brightness."
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

            # Proceed to curve configuration
            return await self.async_step_reconfigure_curves()

        # Use utility function to create schema with current values as defaults
        data_schema = create_basic_schema(config_entry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Update your light zones configuration. Next step will allow customizing brightness curves."
            },
        )

    async def async_step_reconfigure_curves(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of curves."""
        errors: dict[str, str] = {}

        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if config_entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            # Update config data
            self._config_data.update(user_input)

            # Ensure default breakpoints are set if missing
            if CONF_BREAKPOINTS not in self._config_data:
                self._config_data[CONF_BREAKPOINTS] = DEFAULT_BREAKPOINTS

            # Update the config entry
            return self.async_update_reload_and_abort(
                config_entry,
                data_updates=self._config_data,
                reason="reconfigure_successful",
            )

        # Use utility function to create schema with current values as defaults
        data_schema = create_curve_schema(config_entry.data)

        return self.async_show_form(
            step_id="reconfigure_curves",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "description": "Update brightness response curves for each stage."
            },
        )
