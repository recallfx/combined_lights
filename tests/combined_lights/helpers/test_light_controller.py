"""Tests for LightController helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from homeassistant.core import Context, HomeAssistant

from custom_components.combined_lights.helpers.light_controller import LightController


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def light_controller(mock_hass):
    """Create a LightController instance with mock hass."""
    return LightController(mock_hass)


@pytest.fixture
def context():
    """Create a test context."""
    return Context(id=str(uuid.uuid4()))


class TestLightControllerTurnOn:
    """Tests for turn_on_lights method."""

    async def test_turn_on_uses_blocking_true(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights uses blocking=True in service call."""
        entities = ["light.test1", "light.test2"]
        brightness_pct = 75.0

        await light_controller.turn_on_lights(entities, brightness_pct, context)

        mock_hass.services.async_call.assert_called_once()
        call_kwargs = mock_hass.services.async_call.call_args
        assert call_kwargs.kwargs.get("blocking") is True, (
            "Service call must use blocking=True to wait for lights to respond"
        )

    async def test_turn_on_batches_entities(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights sends all entities in a single call."""
        entities = ["light.test1", "light.test2", "light.test3"]
        brightness_pct = 50.0

        await light_controller.turn_on_lights(entities, brightness_pct, context)

        # Should only be one call, not three
        assert mock_hass.services.async_call.call_count == 1, (
            "Should batch all entities into a single service call"
        )

        # Verify all entities were included
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args.args[2]  # Third positional arg is service_data
        assert service_data["entity_id"] == entities

    async def test_turn_on_passes_context(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights passes context to service call."""
        entities = ["light.test1"]
        brightness_pct = 100.0

        await light_controller.turn_on_lights(entities, brightness_pct, context)

        call_kwargs = mock_hass.services.async_call.call_args.kwargs
        assert call_kwargs.get("context") is context

    async def test_turn_on_calculates_brightness_value(
        self, light_controller, mock_hass, context
    ):
        """Test that brightness percentage is converted to 0-255 value."""
        entities = ["light.test1"]

        # Test 100% = 255
        await light_controller.turn_on_lights(entities, 100.0, context)
        service_data = mock_hass.services.async_call.call_args.args[2]
        assert service_data["brightness"] == 255

        mock_hass.services.async_call.reset_mock()

        # Test 50% = 127
        await light_controller.turn_on_lights(entities, 50.0, context)
        service_data = mock_hass.services.async_call.call_args.args[2]
        assert service_data["brightness"] == 127

        mock_hass.services.async_call.reset_mock()

        # Test 0% = 0
        await light_controller.turn_on_lights(entities, 0.0, context)
        service_data = mock_hass.services.async_call.call_args.args[2]
        assert service_data["brightness"] == 0

    async def test_turn_on_returns_expected_states(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights returns expected state mapping."""
        entities = ["light.test1", "light.test2"]
        brightness_pct = 75.0
        expected_brightness = int(75.0 / 100.0 * 255)

        result = await light_controller.turn_on_lights(entities, brightness_pct, context)

        assert result == {
            "light.test1": expected_brightness,
            "light.test2": expected_brightness,
        }

    async def test_turn_on_empty_list_returns_empty(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights with empty list doesn't call service."""
        result = await light_controller.turn_on_lights([], 50.0, context)

        assert result == {}
        mock_hass.services.async_call.assert_not_called()

    async def test_turn_on_handles_service_error(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights handles service errors gracefully."""
        from homeassistant.exceptions import ServiceNotFound

        mock_hass.services.async_call.side_effect = ServiceNotFound(
            "light", "turn_on"
        )
        entities = ["light.test1"]

        result = await light_controller.turn_on_lights(entities, 50.0, context)

        # Should return empty dict on error
        assert result == {}


class TestLightControllerTurnOff:
    """Tests for turn_off_lights method."""

    async def test_turn_off_uses_blocking_true(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights uses blocking=True in service call."""
        entities = ["light.test1", "light.test2"]

        await light_controller.turn_off_lights(entities, context)

        mock_hass.services.async_call.assert_called_once()
        call_kwargs = mock_hass.services.async_call.call_args
        assert call_kwargs.kwargs.get("blocking") is True, (
            "Service call must use blocking=True to wait for lights to respond"
        )

    async def test_turn_off_batches_entities(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights sends all entities in a single call."""
        entities = ["light.test1", "light.test2", "light.test3"]

        await light_controller.turn_off_lights(entities, context)

        # Should only be one call, not three
        assert mock_hass.services.async_call.call_count == 1, (
            "Should batch all entities into a single service call"
        )

        # Verify all entities were included
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args.args[2]  # Third positional arg is service_data
        assert service_data["entity_id"] == entities

    async def test_turn_off_passes_context(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights passes context to service call."""
        entities = ["light.test1"]

        await light_controller.turn_off_lights(entities, context)

        call_kwargs = mock_hass.services.async_call.call_args.kwargs
        assert call_kwargs.get("context") is context

    async def test_turn_off_returns_zero_brightness(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights returns zero brightness for all entities."""
        entities = ["light.test1", "light.test2"]

        result = await light_controller.turn_off_lights(entities, context)

        assert result == {
            "light.test1": 0,
            "light.test2": 0,
        }

    async def test_turn_off_empty_list_returns_empty(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights with empty list doesn't call service."""
        result = await light_controller.turn_off_lights([], context)

        assert result == {}
        mock_hass.services.async_call.assert_not_called()

    async def test_turn_off_handles_service_error(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights handles service errors gracefully."""
        from homeassistant.exceptions import ServiceNotFound

        mock_hass.services.async_call.side_effect = ServiceNotFound(
            "light", "turn_off"
        )
        entities = ["light.test1"]

        result = await light_controller.turn_off_lights(entities, context)

        # Should return empty dict on error
        assert result == {}


class TestLightControllerServiceCalls:
    """Tests for service call correctness."""

    async def test_turn_on_calls_correct_service(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_on_lights calls light.turn_on service."""
        await light_controller.turn_on_lights(["light.test"], 50.0, context)

        call_args = mock_hass.services.async_call.call_args.args
        assert call_args[0] == "light"
        assert call_args[1] == "turn_on"

    async def test_turn_off_calls_correct_service(
        self, light_controller, mock_hass, context
    ):
        """Test that turn_off_lights calls light.turn_off service."""
        await light_controller.turn_off_lights(["light.test"], context)

        call_args = mock_hass.services.async_call.call_args.args
        assert call_args[0] == "light"
        assert call_args[1] == "turn_off"

