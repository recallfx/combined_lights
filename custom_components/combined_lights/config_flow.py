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
    CONF_BRIGHTNESS_CURVE,
    CONF_STAGE_1_BRIGHTNESS_RANGES,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_BRIGHTNESS_RANGES,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_BRIGHTNESS_RANGES,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_BRIGHTNESS_RANGES,
    CONF_STAGE_4_LIGHTS,
    CURVE_CUBIC,
    CURVE_LINEAR,
    CURVE_QUADRATIC,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
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
        }
    )


def create_curve_selector() -> selector.SelectSelector:
    """Create brightness curve selector for reuse."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": CURVE_LINEAR, "label": "Linear (even response)"},
                {
                    "value": CURVE_QUADRATIC,
                    "label": "Quadratic (more precision at low brightness)",
                },
                {
                    "value": CURVE_CUBIC,
                    "label": "Cubic (maximum precision at low brightness)",
                },
            ]
        )
    )


def create_advanced_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Create advanced configuration schema using YAML editor."""
    defaults = defaults or {}

    # Create the default YAML configuration with simplified range format
    default_config = {
        CONF_BREAKPOINTS: defaults.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS),
        CONF_BRIGHTNESS_CURVE: defaults.get(
            CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE
        ),
        CONF_STAGE_1_BRIGHTNESS_RANGES: format_ranges_for_yaml(
            defaults.get(
                CONF_STAGE_1_BRIGHTNESS_RANGES, DEFAULT_STAGE_1_BRIGHTNESS_RANGES
            )
        ),
        CONF_STAGE_2_BRIGHTNESS_RANGES: format_ranges_for_yaml(
            defaults.get(
                CONF_STAGE_2_BRIGHTNESS_RANGES, DEFAULT_STAGE_2_BRIGHTNESS_RANGES
            )
        ),
        CONF_STAGE_3_BRIGHTNESS_RANGES: format_ranges_for_yaml(
            defaults.get(
                CONF_STAGE_3_BRIGHTNESS_RANGES, DEFAULT_STAGE_3_BRIGHTNESS_RANGES
            )
        ),
        CONF_STAGE_4_BRIGHTNESS_RANGES: format_ranges_for_yaml(
            defaults.get(
                CONF_STAGE_4_BRIGHTNESS_RANGES, DEFAULT_STAGE_4_BRIGHTNESS_RANGES
            )
        ),
    }

    return vol.Schema(
        {
            vol.Required(
                "advanced_config",
                default=default_config,
                description="Advanced configuration in YAML format",
            ): selector.ObjectSelector(),
        }
    )


def merge_config_with_defaults(
    config_data: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    """Merge configuration data with defaults for missing values."""
    # Extract the advanced config from the YAML input
    advanced_config = user_input.get("advanced_config", {})

    # Parse brightness ranges from simplified format
    stage_1_ranges = parse_ranges_from_yaml(
        advanced_config.get(
            CONF_STAGE_1_BRIGHTNESS_RANGES,
            format_ranges_for_yaml(DEFAULT_STAGE_1_BRIGHTNESS_RANGES),
        )
    )
    stage_2_ranges = parse_ranges_from_yaml(
        advanced_config.get(
            CONF_STAGE_2_BRIGHTNESS_RANGES,
            format_ranges_for_yaml(DEFAULT_STAGE_2_BRIGHTNESS_RANGES),
        )
    )
    stage_3_ranges = parse_ranges_from_yaml(
        advanced_config.get(
            CONF_STAGE_3_BRIGHTNESS_RANGES,
            format_ranges_for_yaml(DEFAULT_STAGE_3_BRIGHTNESS_RANGES),
        )
    )
    stage_4_ranges = parse_ranges_from_yaml(
        advanced_config.get(
            CONF_STAGE_4_BRIGHTNESS_RANGES,
            format_ranges_for_yaml(DEFAULT_STAGE_4_BRIGHTNESS_RANGES),
        )
    )

    return {
        **config_data,
        CONF_BREAKPOINTS: advanced_config.get(CONF_BREAKPOINTS, DEFAULT_BREAKPOINTS),
        CONF_BRIGHTNESS_CURVE: advanced_config.get(
            CONF_BRIGHTNESS_CURVE, DEFAULT_BRIGHTNESS_CURVE
        ),
        CONF_STAGE_1_BRIGHTNESS_RANGES: stage_1_ranges,
        CONF_STAGE_2_BRIGHTNESS_RANGES: stage_2_ranges,
        CONF_STAGE_3_BRIGHTNESS_RANGES: stage_3_ranges,
        CONF_STAGE_4_BRIGHTNESS_RANGES: stage_4_ranges,
    }


def format_ranges_for_yaml(ranges: list[list[int]]) -> list[str]:
    """Convert [[min, max], [min, max], ...] to ['min, max', 'min, max', ...] for better YAML display."""
    return [f"{range_pair[0]}, {range_pair[1]}" for range_pair in ranges]


def parse_ranges_from_yaml(
    ranges_input: list[str] | list[list[int]],
) -> list[list[int]]:
    """Parse ranges from either 'min, max' strings or [[min, max]] format."""
    if not ranges_input:
        return []

    result = []
    for item in ranges_input:
        if isinstance(item, str):
            # Parse "min, max" format
            parts = [int(x.strip()) for x in item.split(",")]
            if len(parts) != 2:
                raise ValueError(f"Invalid range format: {item}")
            result.append(parts)
        elif isinstance(item, list) and len(item) == 2:
            # Already in [[min, max]] format
            result.append([int(item[0]), int(item[1])])
        else:
            raise ValueError(f"Invalid range format: {item}")

    return result


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
                    "Advanced: Configure breakpoints and brightness ranges using YAML.\n\n"
                    "Example configuration:\n"
                    "- breakpoints: [30, 60, 90] (creates stages 1-30%, 31-60%, 61-90%, 91-100%)\n"
                    "- brightness_curve: linear (or quadratic, cubic)\n"
                    "- brightness ranges: use simplified format like:\n"
                    "  stage_1_brightness_ranges:\n"
                    "    - '5, 20'   # Stage 1: min 5%, max 20%\n"
                    "    - '10, 40'  # Stage 2: min 10%, max 40%\n"
                    "    - '20, 70'  # Stage 3: min 20%, max 70%\n"
                    "    - '50, 100' # Stage 4: min 50%, max 100%\n"
                    "- Use '0, 0' to turn lights off in that stage"
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
                    "Advanced: Update breakpoints and brightness ranges using YAML.\n\n"
                    "Example configuration:\n"
                    "- breakpoints: [30, 60, 90] (creates stages 1-30%, 31-60%, 61-90%, 91-100%)\n"
                    "- brightness_curve: linear (or quadratic, cubic)\n"
                    "- brightness ranges: use simplified format like:\n"
                    "  stage_1_brightness_ranges:\n"
                    "    - '5, 20'   # Stage 1: min 5%, max 20%\n"
                    "    - '10, 40'  # Stage 2: min 10%, max 40%\n"
                    "    - '20, 70'  # Stage 3: min 20%, max 70%\n"
                    "    - '50, 100' # Stage 4: min 50%, max 100%\n"
                    "- Use '0, 0' to turn lights off in that stage"
                )
            },
        )
