"""Test the Combined Lights integration setup and teardown."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.combined_lights import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)


class TestCombinedLightsIntegration:
    """Test Combined Lights integration setup and teardown."""

    async def test_platforms_constant(self) -> None:
        """Test that PLATFORMS constant is correctly defined."""
        assert PLATFORMS == ["light"]
        assert isinstance(PLATFORMS, list)
        assert len(PLATFORMS) == 1

    async def test_async_setup_entry_success(
        self, hass: HomeAssistant, mock_config_entry
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
        self, hass: HomeAssistant, mock_config_entry
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
        self, hass: HomeAssistant, mock_config_entry
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
        self, hass: HomeAssistant, mock_config_entry
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
        self, hass: HomeAssistant, mock_config_entry
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
        self, hass: HomeAssistant, mock_config_entry
    ) -> None:
        """Test complete setup and unload cycle."""
        with (
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
            ) as mock_forward,
            patch(
                "homeassistant.config_entries.ConfigEntries.async_unload_platforms"
            ) as mock_unload,
        ):
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
