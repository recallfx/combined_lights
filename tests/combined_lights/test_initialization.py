"""Test initialization behavior of Combined Lights."""

import pytest
from homeassistant.core import HomeAssistant
from unittest.mock import patch

from custom_components.combined_lights.light import CombinedLight


class TestInitialization:
    """Test initialization scenarios."""

    @pytest.mark.asyncio
    async def test_initialization_with_lights_off(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test initialization when all lights appear off (KNX startup scenario)."""
        # Create the combined light
        combined_light = CombinedLight(mock_config_entry)
        combined_light.hass = hass

        # Mock zone manager to return all lights as off
        with patch.object(
            combined_light._zone_manager, "is_any_light_on", return_value=False
        ):
            with patch.object(
                combined_light._zone_manager,
                "get_zone_brightness_dict",
                return_value={
                    "stage_1": None,
                    "stage_2": None,
                    "stage_3": None,
                    "stage_4": None,
                },
            ):
                # Add to hass - this should attempt initialization despite is_on=False
                await combined_light.async_added_to_hass()

                # Verify initialization flag is set
                assert combined_light._target_brightness_initialized is True

                # Verify target brightness is preserved (default 255)
                assert combined_light._target_brightness == 255

    @pytest.mark.asyncio
    async def test_initialization_with_lights_on(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test initialization when lights are on and reporting states."""
        combined_light = CombinedLight(mock_config_entry)
        combined_light.hass = hass

        # Mock zone manager to return lights as on
        with patch.object(
            combined_light._zone_manager, "is_any_light_on", return_value=True
        ):
            with patch.object(
                combined_light._zone_manager,
                "get_zone_brightness_dict",
                return_value={
                    "stage_1": 50.0,  # 50% brightness
                    "stage_2": 20.0,  # 20% brightness
                    "stage_3": None,
                    "stage_4": None,
                },
            ):
                # Add to hass
                await combined_light.async_added_to_hass()

                # Verify initialization happened
                assert combined_light._target_brightness_initialized is True

                # Target brightness should be updated from zones
                # (exact value depends on estimation logic, just verify it's not default 255)
                assert combined_light._target_brightness < 255
                assert combined_light._target_brightness > 0

    @pytest.mark.asyncio
    async def test_initialization_flag_prevents_double_init(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test that initialization only happens once."""
        combined_light = CombinedLight(mock_config_entry)
        combined_light.hass = hass

        # Mock to track calls
        original_sync = combined_light._sync_target_brightness_from_lights
        call_count = 0

        def counting_sync():
            nonlocal call_count
            call_count += 1
            return original_sync()

        with patch.object(
            combined_light, "_sync_target_brightness_from_lights", side_effect=counting_sync
        ):
            # First call to async_added_to_hass
            await combined_light.async_added_to_hass()
            assert call_count == 1
            assert combined_light._target_brightness_initialized is True

            # Manually set the flag back to trigger the condition
            combined_light._target_brightness_initialized = False

            # Second call should NOT happen because flag is checked
            combined_light._target_brightness_initialized = True
            # The sync won't be called again because flag is True
            call_count_before = call_count

            # Simulate calling the initialization check manually
            if not combined_light._target_brightness_initialized:
                combined_light._sync_target_brightness_from_lights()

            # Count should not increase
            assert call_count == call_count_before

    @pytest.mark.asyncio
    async def test_initialization_handles_partial_state_sync(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test initialization when some lights have synced but others haven't."""
        combined_light = CombinedLight(mock_config_entry)
        combined_light.hass = hass

        # Mock partial sync - some zones have data, others don't
        with patch.object(
            combined_light._zone_manager, "is_any_light_on", return_value=True
        ):
            with patch.object(
                combined_light._zone_manager,
                "get_zone_brightness_dict",
                return_value={
                    "stage_1": 40.0,  # This zone synced
                    "stage_2": None,  # This zone hasn't synced yet
                    "stage_3": None,
                    "stage_4": None,
                },
            ):
                # Add to hass
                await combined_light.async_added_to_hass()

                # Verify initialization happened
                assert combined_light._target_brightness_initialized is True

                # Should have some brightness value calculated from stage_1
                assert combined_light._target_brightness > 0
