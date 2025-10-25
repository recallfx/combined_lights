"""Test the Combined Lights integration setup and teardown."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.combined_lights import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.combined_lights.const import (
    CONF_STAGE_1_LIGHTS,
    DEFAULT_BREAKPOINTS,
    DEFAULT_BRIGHTNESS_CURVE,
    DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
    DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
    DOMAIN,
)


class TestCombinedLightsIntegration:
    """Test Combined Lights integration setup and teardown."""

    @pytest.fixture
    def mock_config_entry(self) -> ConfigEntry:
        """Create a mock config entry for testing."""
        return ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Test Combined Lights",
            data={
                CONF_NAME: "Test Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.test_stage1"],
                "stage_2_lights": [],
                "stage_3_lights": [],
                "stage_4_lights": [],
                "breakpoints": DEFAULT_BREAKPOINTS,
                "brightness_curve": DEFAULT_BRIGHTNESS_CURVE,
                "stage_1_brightness_ranges": DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
                "stage_2_brightness_ranges": DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
                "stage_3_brightness_ranges": DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
                "stage_4_brightness_ranges": DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
            },
            options={},
            entry_id=str(uuid4()),
            source="user",
            unique_id=None,
            discovery_keys=set(),
        )

    async def test_platforms_constant(self) -> None:
        """Test that PLATFORMS constant is correctly defined."""
        assert PLATFORMS == ["light"]
        assert isinstance(PLATFORMS, list)
        assert len(PLATFORMS) == 1

    async def test_async_setup_entry_success(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test successful setup of config entry."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward:
            mock_forward.return_value = None

            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_async_setup_entry_forward_called_with_correct_platforms(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test that setup forwards to correct platforms."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward:
            mock_forward.return_value = None

            await async_setup_entry(hass, mock_config_entry)

            # Verify the correct platforms are forwarded
            call_args = mock_forward.call_args
            assert call_args[0][0] == mock_config_entry
            assert call_args[0][1] == ["light"]

    async def test_async_unload_entry_success(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test successful unload of config entry."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
        ) as mock_unload:
            mock_unload.return_value = True

            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True
            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_async_unload_entry_failure(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test failed unload of config entry."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
        ) as mock_unload:
            mock_unload.return_value = False

            result = await async_unload_entry(hass, mock_config_entry)

            assert result is False
            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_async_unload_entry_forward_called_with_correct_platforms(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test that unload uses correct platforms."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
        ) as mock_unload:
            mock_unload.return_value = True

            await async_unload_entry(hass, mock_config_entry)

            # Verify the correct platforms are unloaded
            call_args = mock_unload.call_args
            assert call_args[0][0] == mock_config_entry
            assert call_args[0][1] == ["light"]

    async def test_setup_and_unload_cycle(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test complete setup and unload cycle."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward, patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
        ) as mock_unload:
            mock_forward.return_value = None
            mock_unload.return_value = True

            # Test setup
            setup_result = await async_setup_entry(hass, mock_config_entry)
            assert setup_result is True

            # Test unload
            unload_result = await async_unload_entry(hass, mock_config_entry)
            assert unload_result is True

            # Verify calls
            mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)
            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)