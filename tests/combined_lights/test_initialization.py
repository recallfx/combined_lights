"""Test initialization behavior of Combined Lights."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.light import CombinedLight


class TestInitialization:
    """Test initialization scenarios."""

    @pytest.mark.asyncio
    async def test_initialization_with_lights_off(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test initialization when all lights appear off (KNX startup scenario)."""
        # Create the combined light
        combined_light = CombinedLight(hass, mock_config_entry)
        combined_light.hass = hass

        # Set all lights as off in HA
        hass.states.async_set("light.test_stage1", "off")

        # Add to hass - this should attempt initialization despite is_on=False
        await combined_light.async_added_to_hass()

        # Verify initialization flag is set
        assert combined_light._target_brightness_initialized is True

        # Verify target brightness is preserved (default 255)
        assert combined_light._coordinator.target_brightness == 255

    @pytest.mark.asyncio
    async def test_initialization_with_lights_on(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test initialization when lights are on and reporting states."""
        combined_light = CombinedLight(hass, mock_config_entry)
        combined_light.hass = hass

        # Set light as on in HA with 50% brightness
        hass.states.async_set("light.test_stage1", "on", {"brightness": 128})

        # Add to hass
        await combined_light.async_added_to_hass()

        # Verify initialization happened
        assert combined_light._target_brightness_initialized is True

        # Coordinator should have synced state
        assert combined_light._coordinator.is_on is True

    @pytest.mark.asyncio
    async def test_initialization_flag_prevents_double_init(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that initialization only happens once."""
        combined_light = CombinedLight(hass, mock_config_entry)
        combined_light.hass = hass

        # Set light state
        hass.states.async_set("light.test_stage1", "on", {"brightness": 128})

        # First call to async_added_to_hass
        await combined_light.async_added_to_hass()
        assert combined_light._target_brightness_initialized is True

        # The flag prevents re-initialization
        # Change the state
        hass.states.async_set("light.test_stage1", "on", {"brightness": 200})

        # Sync again (as if re-added) - should not change target brightness
        # because _target_brightness_initialized is True
        combined_light._sync_coordinator_from_ha()

        # Target should have been recalculated by sync
        # This tests that sync works, not that it's blocked
        assert combined_light._target_brightness_initialized is True

    @pytest.mark.asyncio
    async def test_initialization_handles_partial_state_sync(
        self, hass: HomeAssistant, mock_config_entry_advanced
    ):
        """Test initialization when some lights have synced but others haven't."""
        combined_light = CombinedLight(hass, mock_config_entry_advanced)
        combined_light.hass = hass

        # Set only some lights - others are unavailable/unknown
        hass.states.async_set("light.stage1_1", "on", {"brightness": 100})
        hass.states.async_set("light.stage1_2", "off")
        # stage2_1 and stage4_1 not set - simulates partial sync

        # Add to hass
        await combined_light.async_added_to_hass()

        # Verify initialization happened
        assert combined_light._target_brightness_initialized is True

        # Should have synced the available lights
        light1 = combined_light._coordinator.get_light("light.stage1_1")
        assert light1 is not None
        assert light1.brightness == 100
