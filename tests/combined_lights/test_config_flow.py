"""Test the Combined Lights config flow."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.combined_lights.const import (
    CONF_BREAKPOINTS,
    CONF_BRIGHTNESS_CURVE,
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_STAGE_1_BRIGHTNESS_RANGES,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_BRIGHTNESS_RANGES,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_BRIGHTNESS_RANGES,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_BRIGHTNESS_RANGES,
    CONF_STAGE_4_LIGHTS,
    CURVE_QUADRATIC,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
    DOMAIN,
)


class TestCombinedLightsConfigFlow:
    """Test the Combined Lights config flow."""

    async def test_form_user_step(self, hass: HomeAssistant) -> None:
        """Test we get the user form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}
        assert result["step_id"] == "user"

    async def test_form_user_step_with_lights(self, hass: HomeAssistant) -> None:
        """Test user step with light entities."""
        # Mock some light entities
        with patch("homeassistant.helpers.entity_registry.async_get") as mock_registry:
            mock_registry.return_value.async_get_entity_id.side_effect = [
                "light.stage1_1",
                "light.stage1_2",
                "light.stage2_1",
            ]

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_NAME: "Test Combined Lights",
                    CONF_STAGE_1_LIGHTS: ["light.stage1_1", "light.stage1_2"],
                    CONF_STAGE_2_LIGHTS: ["light.stage2_1"],
                    CONF_STAGE_3_LIGHTS: [],
                    CONF_STAGE_4_LIGHTS: [],
                },
            )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "advanced"
        assert result2["errors"] == {}

    async def test_form_advanced_step_with_defaults(self, hass: HomeAssistant) -> None:
        """Test advanced step with default configuration."""
        # Start with user step
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Complete user step
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Test Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.stage1"],
                CONF_STAGE_2_LIGHTS: [],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
            },
        )

        # Complete advanced step with defaults
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "advanced_config": {
                    CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
                    CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
                    CONF_STAGE_1_BRIGHTNESS_RANGES: [
                        "1, 40",
                        "41, 60",
                        "61, 80",
                        "81, 100",
                    ],
                    CONF_STAGE_2_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "1, 40",
                        "41, 60",
                        "61, 100",
                    ],
                    CONF_STAGE_3_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "0, 0",
                        "1, 50",
                        "51, 100",
                    ],
                    CONF_STAGE_4_BRIGHTNESS_RANGES: ["0, 0", "0, 0", "0, 0", "1, 100"],
                }
            },
        )

        assert result3["type"] is FlowResultType.CREATE_ENTRY
        assert result3["title"] == "Test Combined Lights"
        assert result3["data"] == {
            CONF_NAME: "Test Combined Lights",
            CONF_STAGE_1_LIGHTS: ["light.stage1"],
            CONF_STAGE_2_LIGHTS: [],
            CONF_STAGE_3_LIGHTS: [],
            CONF_STAGE_4_LIGHTS: [],
            CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
            CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
            CONF_STAGE_1_BRIGHTNESS_RANGES: DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
            CONF_STAGE_2_BRIGHTNESS_RANGES: DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
            CONF_STAGE_3_BRIGHTNESS_RANGES: DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
            CONF_STAGE_4_BRIGHTNESS_RANGES: DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
            CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
        }

    async def test_form_advanced_step_custom_config(self, hass: HomeAssistant) -> None:
        """Test advanced step with custom configuration."""
        # Start with user step
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Complete user step
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Custom Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.stage1"],
                CONF_STAGE_2_LIGHTS: ["light.stage2"],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
            },
        )

        # Complete advanced step with custom configuration
        custom_breakpoints = [30, 60, 90]
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "advanced_config": {
                    CONF_BREAKPOINTS: custom_breakpoints,
                    CONF_BRIGHTNESS_CURVE: CURVE_QUADRATIC,
                    CONF_STAGE_1_BRIGHTNESS_RANGES: [
                        "5, 30",
                        "35, 55",
                        "60, 80",
                        "85, 100",
                    ],
                    CONF_STAGE_2_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "10, 35",
                        "40, 65",
                        "70, 100",
                    ],
                    CONF_STAGE_3_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "0, 0",
                        "20, 50",
                        "55, 100",
                    ],
                    CONF_STAGE_4_BRIGHTNESS_RANGES: ["0, 0", "0, 0", "0, 0", "30, 100"],
                }
            },
        )

        assert result3["type"] is FlowResultType.CREATE_ENTRY
        assert result3["title"] == "Custom Combined Lights"
        assert result3["data"][CONF_BREAKPOINTS] == custom_breakpoints
        assert result3["data"][CONF_BRIGHTNESS_CURVE] == CURVE_QUADRATIC
        assert result3["data"][CONF_STAGE_1_BRIGHTNESS_RANGES] == [
            [5, 30],
            [35, 55],
            [60, 80],
            [85, 100],
        ]

    async def test_reconfigure_flow(self, hass: HomeAssistant) -> None:
        """Test the reconfigure flow."""
        # Create a mock config entry
        config_entry = ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Existing Combined Lights",
            data={
                CONF_NAME: "Existing Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.old_stage1"],
                CONF_STAGE_2_LIGHTS: [],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
                CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
                CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
                CONF_STAGE_1_BRIGHTNESS_RANGES: DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
                CONF_STAGE_2_BRIGHTNESS_RANGES: DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
                CONF_STAGE_3_BRIGHTNESS_RANGES: DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
                CONF_STAGE_4_BRIGHTNESS_RANGES: DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
                CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
            },
            options={},
            entry_id=str(uuid4()),
            source=config_entries.SOURCE_USER,
            unique_id=None,
            discovery_keys=set(),
        )

        # Add the config entry to Home Assistant
        hass.config_entries._entries[config_entry.entry_id] = config_entry

        # Start reconfigure flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": config_entry.entry_id,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

    async def test_reconfigure_flow_complete(self, hass: HomeAssistant) -> None:
        """Test complete reconfigure flow."""
        # Create a mock config entry
        config_entry = ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Existing Combined Lights",
            data={
                CONF_NAME: "Existing Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.old_stage1"],
                CONF_STAGE_2_LIGHTS: [],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
                CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
                CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
                CONF_STAGE_1_BRIGHTNESS_RANGES: DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
                CONF_STAGE_2_BRIGHTNESS_RANGES: DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
                CONF_STAGE_3_BRIGHTNESS_RANGES: DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
                CONF_STAGE_4_BRIGHTNESS_RANGES: DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
                CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
            },
            options={},
            entry_id=str(uuid4()),
            source=config_entries.SOURCE_USER,
            unique_id=None,
            discovery_keys=set(),
        )

        hass.config_entries._entries[config_entry.entry_id] = config_entry

        # Start reconfigure flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": config_entry.entry_id,
            },
        )

        # Complete basic reconfigure step
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Updated Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.new_stage1", "light.new_stage1_2"],
                CONF_STAGE_2_LIGHTS: ["light.new_stage2"],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
            },
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reconfigure_advanced"

        # Complete advanced reconfigure step
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "advanced_config": {
                    CONF_BREAKPOINTS: [20, 40, 80],
                    CONF_BRIGHTNESS_CURVE: CURVE_QUADRATIC,
                    CONF_STAGE_1_BRIGHTNESS_RANGES: [
                        "10, 50",
                        "55, 70",
                        "75, 85",
                        "90, 100",
                    ],
                    CONF_STAGE_2_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "15, 45",
                        "50, 75",
                        "80, 100",
                    ],
                    CONF_STAGE_3_BRIGHTNESS_RANGES: [
                        "0, 0",
                        "0, 0",
                        "25, 60",
                        "65, 100",
                    ],
                    CONF_STAGE_4_BRIGHTNESS_RANGES: ["0, 0", "0, 0", "0, 0", "40, 100"],
                }
            },
        )

        assert result3["type"] is FlowResultType.ABORT
        assert result3["reason"] == "reconfigure_successful"


class TestConfigFlowUtilities:
    """Test config flow utility functions."""

    def test_format_ranges_for_yaml(self) -> None:
        """Test formatting ranges for YAML display."""
        from custom_components.combined_lights.config_flow import format_ranges_for_yaml

        ranges = [[1, 40], [41, 60], [61, 80], [81, 100]]
        expected = ["1, 40", "41, 60", "61, 80", "81, 100"]
        result = format_ranges_for_yaml(ranges)
        assert result == expected

    def test_parse_ranges_from_yaml_string_format(self) -> None:
        """Test parsing ranges from string format."""
        from custom_components.combined_lights.config_flow import parse_ranges_from_yaml

        ranges_input = ["1, 40", "41, 60", "61, 80", "81, 100"]
        expected = [[1, 40], [41, 60], [61, 80], [81, 100]]
        result = parse_ranges_from_yaml(ranges_input)
        assert result == expected

    def test_parse_ranges_from_yaml_list_format(self) -> None:
        """Test parsing ranges from list format."""
        from custom_components.combined_lights.config_flow import parse_ranges_from_yaml

        ranges_input = [[1, 40], [41, 60], [61, 80], [81, 100]]
        expected = [[1, 40], [41, 60], [61, 80], [81, 100]]
        result = parse_ranges_from_yaml(ranges_input)
        assert result == expected

    def test_parse_ranges_from_yaml_empty(self) -> None:
        """Test parsing empty ranges."""
        from custom_components.combined_lights.config_flow import parse_ranges_from_yaml

        result = parse_ranges_from_yaml([])
        assert result == []

    def test_parse_ranges_from_yaml_invalid_string(self) -> None:
        """Test parsing invalid string format raises ValueError."""
        from custom_components.combined_lights.config_flow import parse_ranges_from_yaml

        with pytest.raises(ValueError, match="Invalid range format"):
            parse_ranges_from_yaml(["1, 40, 60"])  # Too many values

    def test_parse_ranges_from_yaml_invalid_list(self) -> None:
        """Test parsing invalid list format raises ValueError."""
        from custom_components.combined_lights.config_flow import parse_ranges_from_yaml

        with pytest.raises(ValueError, match="Invalid range format"):
            parse_ranges_from_yaml([[1, 40, 60]])  # Too many values

    def test_merge_config_with_defaults(self) -> None:
        """Test merging configuration with defaults."""
        from custom_components.combined_lights.config_flow import (
            merge_config_with_defaults,
        )

        config_data = {
            CONF_NAME: "Test",
            CONF_STAGE_1_LIGHTS: ["light.test"],
        }

        user_input = {
            "advanced_config": {
                CONF_BREAKPOINTS: [30, 60, 90],
                CONF_BRIGHTNESS_CURVE: CURVE_QUADRATIC,
                CONF_STAGE_1_BRIGHTNESS_RANGES: ["5, 30", "35, 55"],
                CONF_STAGE_2_BRIGHTNESS_RANGES: ["0, 0", "10, 35"],
                CONF_STAGE_3_BRIGHTNESS_RANGES: ["0, 0", "0, 0"],
                CONF_STAGE_4_BRIGHTNESS_RANGES: ["0, 0", "0, 0"],
            }
        }

        result = merge_config_with_defaults(config_data, user_input)

        assert result[CONF_NAME] == "Test"
        assert result[CONF_STAGE_1_LIGHTS] == ["light.test"]
        assert result[CONF_BREAKPOINTS] == [30, 60, 90]
        assert result[CONF_BRIGHTNESS_CURVE] == CURVE_QUADRATIC
        assert result[CONF_STAGE_1_BRIGHTNESS_RANGES] == [[5, 30], [35, 55]]


class TestConfigFlowSchemas:
    """Test config flow schema creation."""

    def test_create_basic_schema_no_defaults(self) -> None:
        """Test creating basic schema without defaults."""
        from custom_components.combined_lights.config_flow import create_basic_schema

        schema = create_basic_schema()

        # Check that schema has all required fields
        schema_keys = list(schema.schema.keys())
        assert any(key.schema == CONF_NAME for key in schema_keys)
        assert any(key.schema == CONF_STAGE_1_LIGHTS for key in schema_keys)
        assert any(key.schema == CONF_STAGE_2_LIGHTS for key in schema_keys)
        assert any(key.schema == CONF_STAGE_3_LIGHTS for key in schema_keys)
        assert any(key.schema == CONF_STAGE_4_LIGHTS for key in schema_keys)

    def test_create_basic_schema_with_defaults(self) -> None:
        """Test creating basic schema with defaults."""
        from custom_components.combined_lights.config_flow import create_basic_schema

        defaults = {
            CONF_NAME: "Test Name",
            CONF_STAGE_1_LIGHTS: ["light.test1"],
            CONF_STAGE_2_LIGHTS: ["light.test2"],
        }

        schema = create_basic_schema(defaults)

        # Schema should be created successfully with defaults
        assert schema is not None

    def test_create_advanced_schema(self) -> None:
        """Test creating advanced schema."""
        from custom_components.combined_lights.config_flow import create_advanced_schema

        schema = create_advanced_schema()

        # Check that schema has advanced_config field
        schema_keys = list(schema.schema.keys())
        assert any(key.schema == "advanced_config" for key in schema_keys)

    def test_create_light_entity_selector(self) -> None:
        """Test creating light entity selector."""
        from custom_components.combined_lights.config_flow import (
            create_light_entity_selector,
        )
        from homeassistant.helpers import selector

        selector_obj = create_light_entity_selector()

        # Should be an EntitySelector
        assert isinstance(selector_obj, selector.EntitySelector)

    def test_create_curve_selector(self) -> None:
        """Test creating curve selector."""
        from custom_components.combined_lights.config_flow import create_curve_selector
        from homeassistant.helpers import selector

        selector_obj = create_curve_selector()

        # Should be a SelectSelector
        assert isinstance(selector_obj, selector.SelectSelector)
