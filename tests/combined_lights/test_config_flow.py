"""Test the Combined Lights config flow."""

from uuid import uuid4

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.combined_lights.const import (
    CONF_BREAKPOINTS,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_CURVE,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_CURVE,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_CURVE,
    CONF_STAGE_4_LIGHTS,
    CURVE_QUADRATIC,
    DEFAULT_BREAKPOINTS,
    DEFAULT_STAGE_1_CURVE,
    DEFAULT_STAGE_2_CURVE,
    DEFAULT_STAGE_3_CURVE,
    DEFAULT_STAGE_4_CURVE,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    CONF_ENABLE_BACK_PROPAGATION,
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

    async def test_full_flow_with_defaults(self, hass: HomeAssistant) -> None:
        """Test full config flow with default curves."""
        # Start with user step
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Complete user step (assign lights)
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

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "curves"

        # Complete curves step with defaults
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_STAGE_1_CURVE: DEFAULT_STAGE_1_CURVE,
                CONF_STAGE_2_CURVE: DEFAULT_STAGE_2_CURVE,
                CONF_STAGE_3_CURVE: DEFAULT_STAGE_3_CURVE,
                CONF_STAGE_4_CURVE: DEFAULT_STAGE_4_CURVE,
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
            CONF_STAGE_1_CURVE: DEFAULT_STAGE_1_CURVE,
            CONF_STAGE_2_CURVE: DEFAULT_STAGE_2_CURVE,
            CONF_STAGE_3_CURVE: DEFAULT_STAGE_3_CURVE,
            CONF_STAGE_4_CURVE: DEFAULT_STAGE_4_CURVE,
            CONF_ENABLE_BACK_PROPAGATION: DEFAULT_ENABLE_BACK_PROPAGATION,
        }

    async def test_full_flow_custom_curves_and_advanced(
        self, hass: HomeAssistant
    ) -> None:
        """Test full config flow with custom curves."""
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

        # Complete curves step with custom curves
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_STAGE_1_CURVE: CURVE_QUADRATIC,
                CONF_STAGE_2_CURVE: "linear",
                CONF_STAGE_3_CURVE: "linear",
                CONF_STAGE_4_CURVE: "linear",
            },
        )

        assert result3["type"] is FlowResultType.CREATE_ENTRY
        assert result3["data"][CONF_STAGE_1_CURVE] == CURVE_QUADRATIC
        assert result3["data"][CONF_BREAKPOINTS] == DEFAULT_BREAKPOINTS

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
                CONF_STAGE_1_CURVE: DEFAULT_STAGE_1_CURVE,
                CONF_STAGE_2_CURVE: DEFAULT_STAGE_2_CURVE,
                CONF_STAGE_3_CURVE: DEFAULT_STAGE_3_CURVE,
                CONF_STAGE_4_CURVE: DEFAULT_STAGE_4_CURVE,
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

        # Complete reconfigure step (lights)
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Updated Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.new_stage1"],
                CONF_STAGE_2_LIGHTS: [],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: [],
            },
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reconfigure_curves"

        # Complete curves step
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_STAGE_1_CURVE: CURVE_QUADRATIC,
                CONF_STAGE_2_CURVE: DEFAULT_STAGE_2_CURVE,
                CONF_STAGE_3_CURVE: DEFAULT_STAGE_3_CURVE,
                CONF_STAGE_4_CURVE: DEFAULT_STAGE_4_CURVE,
            },
        )

        assert result3["type"] is FlowResultType.ABORT
        assert result3["reason"] == "reconfigure_successful"
        assert config_entry.data[CONF_STAGE_1_CURVE] == CURVE_QUADRATIC


class TestConfigFlowSchemas:
    """Test config flow schema creation."""

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
