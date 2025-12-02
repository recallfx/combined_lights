"""Test the Combined Lights light platform."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.components.light import ColorMode
from homeassistant.core import HomeAssistant, State

from custom_components.combined_lights.const import (
    CURVE_LINEAR,
    CURVE_QUADRATIC,
)
from custom_components.combined_lights.light import (
    CombinedLight,
    async_setup_entry,
)


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    async def test_async_setup_entry(
        self, hass: HomeAssistant, mock_config_entry
    ) -> None:
        """Test setting up the light platform."""
        mock_add_entities = Mock()

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Verify that one entity was added
        mock_add_entities.assert_called_once()
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], CombinedLight)


class TestCombinedLight:
    """Test CombinedLight entity."""

    @pytest.fixture
    def combined_light(self, mock_config_entry_advanced) -> CombinedLight:
        """Create a CombinedLight instance for testing."""
        return CombinedLight(mock_config_entry_advanced)

    def test_init(
        self, combined_light: CombinedLight, mock_config_entry_advanced
    ) -> None:
        """Test CombinedLight initialization."""
        assert combined_light._attr_name == "Advanced Test Combined Lights"
        assert (
            combined_light._attr_unique_id
            == f"{mock_config_entry_advanced.entry_id}_combined_light"
        )
        assert combined_light._attr_is_on is False
        assert combined_light._attr_brightness == 255
        assert combined_light._attr_supported_color_modes == {ColorMode.BRIGHTNESS}
        assert combined_light._attr_color_mode == ColorMode.BRIGHTNESS

    def test_available_with_available_lights(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test entity availability when member lights are available."""
        combined_light.hass = hass
        
        # Set up at least one available light
        hass.states.async_set("light.stage1_1", "on", {"brightness": 128})
        
        assert combined_light.available is True

    def test_available_with_all_unavailable_lights(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test entity availability when all member lights are unavailable."""
        combined_light.hass = hass
        
        # Set all lights to unavailable
        hass.states.async_set("light.stage1_1", "unavailable")
        hass.states.async_set("light.stage1_2", "unavailable")
        hass.states.async_set("light.stage2_1", "unavailable")
        hass.states.async_set("light.stage4_1", "unavailable")
        
        assert combined_light.available is False

    def test_available_without_hass(self, combined_light: CombinedLight) -> None:
        """Test entity availability when hass is not set."""
        combined_light.hass = None
        assert combined_light.available is False

    def test_device_info(self, combined_light: CombinedLight) -> None:
        """Test that device_info is properly set."""
        assert combined_light._attr_device_info is not None
        assert combined_light._attr_device_info["manufacturer"] == "Combined Lights"
        assert combined_light._attr_device_info["model"] == "Virtual Light Controller"

    def test_get_stage_from_brightness(self, combined_light: CombinedLight) -> None:
        """Test determining stage from brightness percentage."""

        # Test each stage using the brightness calculator
        brightness_calc = combined_light._brightness_calc
        # Breakpoints are [30, 60, 90] in advanced config
        assert brightness_calc.get_stage_from_brightness(10) == 0  # Stage 1
        assert brightness_calc.get_stage_from_brightness(30) == 0  # Stage 1
        assert brightness_calc.get_stage_from_brightness(35) == 1  # Stage 2
        assert brightness_calc.get_stage_from_brightness(60) == 1  # Stage 2
        assert brightness_calc.get_stage_from_brightness(65) == 2  # Stage 3
        assert brightness_calc.get_stage_from_brightness(90) == 2  # Stage 3
        assert brightness_calc.get_stage_from_brightness(95) == 3  # Stage 4
        assert brightness_calc.get_stage_from_brightness(100) == 3  # Stage 4

    def test_apply_brightness_curve_linear(self, combined_light: CombinedLight) -> None:
        """Test linear brightness curve."""
        brightness_calc = combined_light._brightness_calc
        # Linear curve should return input unchanged
        assert brightness_calc._apply_brightness_curve(0.0, CURVE_LINEAR) == 0.0
        assert brightness_calc._apply_brightness_curve(0.5, CURVE_LINEAR) == 0.5
        assert brightness_calc._apply_brightness_curve(1.0, CURVE_LINEAR) == 1.0

    def test_apply_brightness_curve_quadratic(
        self, combined_light: CombinedLight
    ) -> None:
        """Test quadratic brightness curve."""
        brightness_calc = combined_light._brightness_calc
        # Quadratic curve: y = x^2
        result = brightness_calc._apply_brightness_curve(0.5, CURVE_QUADRATIC)
        assert result == 0.25

    def test_calculate_zone_brightness_stage_1(
        self, combined_light: CombinedLight
    ) -> None:
        """Test zone brightness calculation for Stage 1."""
        brightness_calc = combined_light._brightness_calc
        # Stage 1 is active from 0 to 100% overall brightness
        # In advanced config, Stage 1 has Quadratic curve

        # At 0% overall, should be 0%
        assert brightness_calc.calculate_zone_brightness(0, "stage_1") == 0.0

        # At 15% overall (halfway to 30% breakpoint), progress is 15/100 = 0.15
        # Quadratic: 0.15^2 = 0.0225
        # Brightness: 1 + 0.0225 * 99 = 3.2275
        result = brightness_calc.calculate_zone_brightness(15, "stage_1")
        assert abs(result - 3.2275) < 0.1

        # At 100% overall, should be 100%
        assert brightness_calc.calculate_zone_brightness(100, "stage_1") == 100.0

    def test_calculate_zone_brightness_stage_2(
        self, combined_light: CombinedLight
    ) -> None:
        """Test zone brightness calculation for Stage 2."""
        brightness_calc = combined_light._brightness_calc
        # Stage 2 activates at 30% (breakpoint 1)
        # Curve is default (Linear)

        # Below 30%, should be 0
        assert brightness_calc.calculate_zone_brightness(20, "stage_2") == 0.0

        # At 30%, should be 0 (just activating)
        assert brightness_calc.calculate_zone_brightness(30, "stage_2") == 0.0

        # At 65% (midway between 30 and 100 is 65), progress = (65-30)/(100-30) = 35/70 = 0.5
        # Linear: 0.5
        # Brightness: 1 + 0.5 * 99 = 50.5
        result = brightness_calc.calculate_zone_brightness(65, "stage_2")
        assert abs(result - 50.5) < 0.1

        # At 100%, should be 100%
        assert brightness_calc.calculate_zone_brightness(100, "stage_2") == 100.0

    def test_get_all_controlled_lights(self, combined_light: CombinedLight) -> None:
        """Test getting all controlled light entity IDs."""
        zone_manager = combined_light._zone_manager
        lights = zone_manager.get_all_lights()
        expected = [
            "light.stage1_1",
            "light.stage1_2",
            "light.stage2_1",
            "light.stage4_1",
        ]
        assert sorted(lights) == sorted(expected)

    def test_get_average_brightness_mocked(self, combined_light: CombinedLight) -> None:
        """Test getting average brightness with mocked states."""
        # Mock the hass object and states
        combined_light.hass = Mock()

        def mock_get_state(entity_id):
            if entity_id == "light.test1":
                return Mock(state="on", attributes={"brightness": 100})
            elif entity_id == "light.test2":
                return Mock(state="on", attributes={"brightness": 200})
            return Mock(state="off")

        combined_light.hass.states.get = mock_get_state

        zone_manager = combined_light._zone_manager
        result = zone_manager.get_average_brightness(
            combined_light.hass, ["light.test1", "light.test2", "light.test3"]
        )
        assert result == 150  # (100 + 200) / 2

    def test_get_average_brightness_all_off_mocked(
        self, combined_light: CombinedLight
    ) -> None:
        """Test getting average brightness when all lights are off."""
        # Mock the hass object and states
        combined_light.hass = Mock()
        combined_light.hass.states.get = Mock(return_value=Mock(state="off"))

        zone_manager = combined_light._zone_manager
        result = zone_manager.get_average_brightness(
            combined_light.hass, ["light.test1", "light.test2"]
        )
        assert result is None

    def test_is_on_property_mocked(self, combined_light: CombinedLight) -> None:
        """Test is_on property with mocked states."""
        # Mock the hass object and states
        combined_light.hass = Mock()

        # Test when all lights are off
        combined_light.hass.states.get = Mock(return_value=Mock(state="off"))
        assert combined_light.is_on is False

        # Test when some lights are on
        def mock_get_state(entity_id):
            if entity_id == "light.stage1_1":
                return Mock(state="on")
            return Mock(state="off")

        combined_light.hass.states.get = mock_get_state
        assert combined_light.is_on is True

    def test_brightness_property(self, combined_light: CombinedLight) -> None:
        """Test brightness property."""
        # Mock is_on to control the property behavior
        combined_light.hass = Mock()
        combined_light.hass.states.get = Mock(return_value=Mock(state="off"))

        # When off, brightness should be None
        assert combined_light.brightness is None

        # When on, should return target brightness
        combined_light.hass.states.get = Mock(return_value=Mock(state="on"))
        combined_light._target_brightness = 128
        assert combined_light.brightness == 128

    def test_entity_state_snapshot(
        self, combined_light: CombinedLight, snapshot
    ) -> None:
        """Test entity state attributes with snapshot testing."""
        # Set up some specific state
        combined_light._target_brightness = 150
        combined_light._attr_is_on = True

        # Test that the entity attributes match snapshot (excluding dynamic unique_id)
        entity_attributes = {
            "name": combined_light._attr_name,
            "is_on": combined_light._attr_is_on,
            "brightness": combined_light._attr_brightness,
            "supported_color_modes": list(combined_light._attr_supported_color_modes),
            "color_mode": combined_light._attr_color_mode,
            "target_brightness": combined_light._target_brightness,
        }

        assert entity_attributes == snapshot


class TestBrightnessEdgeCases:
    """Test brightness behavior at edge cases and breakpoints."""

    @pytest.fixture
    def combined_light(self, mock_config_entry_advanced) -> CombinedLight:
        """Create a CombinedLight instance with default config."""
        return CombinedLight(mock_config_entry_advanced)

    @pytest.mark.asyncio
    async def test_brightness_at_zero_turns_off(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test that 0% brightness turns off the light."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Set up lights as on
        hass.states.async_set("light.stage1_1", "on", {"brightness": 128})
        
        # Mock the light controller
        combined_light._light_controller = AsyncMock()
        combined_light._light_controller.turn_on_lights = AsyncMock(return_value={})
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})
        
        await combined_light.async_turn_on(brightness=0)
        
        # With 0 brightness, turn_off should be called
        combined_light._light_controller.turn_off_lights.assert_called()

    @pytest.mark.asyncio
    async def test_brightness_at_breakpoint_1(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test brightness exactly at breakpoint 1 (30%)."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Breakpoint 1 is 30% = 76.5 brightness
        brightness_30_percent = int(255 * 0.30)  # 76
        
        # Mock the light controller
        combined_light._light_controller = AsyncMock()
        combined_light._light_controller.turn_on_lights = AsyncMock(return_value={})
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})
        
        await combined_light.async_turn_on(brightness=brightness_30_percent)
        
        # At 30%, stage 1 should be at 100%
        combined_light._light_controller.turn_on_lights.assert_called()

    @pytest.mark.asyncio
    async def test_brightness_at_breakpoint_2(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test brightness exactly at breakpoint 2 (60%)."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Breakpoint 2 is 60% = 153 brightness
        brightness_60_percent = int(255 * 0.60)  # 153
        
        # Mock the light controller
        combined_light._light_controller = AsyncMock()
        combined_light._light_controller.turn_on_lights = AsyncMock(return_value={})
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})
        
        await combined_light.async_turn_on(brightness=brightness_60_percent)
        
        # At 60%, stages 1-2 should be on
        combined_light._light_controller.turn_on_lights.assert_called()

    @pytest.mark.asyncio
    async def test_brightness_at_breakpoint_3(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test brightness exactly at breakpoint 3 (90%)."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Breakpoint 3 is 90% = 229.5 brightness
        brightness_90_percent = int(255 * 0.90)  # 229
        
        # Mock the light controller
        combined_light._light_controller = AsyncMock()
        combined_light._light_controller.turn_on_lights = AsyncMock(return_value={})
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})
        
        await combined_light.async_turn_on(brightness=brightness_90_percent)
        
        # At 90%, stages 1-3 should be on
        combined_light._light_controller.turn_on_lights.assert_called()

    @pytest.mark.asyncio
    async def test_brightness_at_100_percent(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test brightness at 100%."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Mock the light controller
        combined_light._light_controller = AsyncMock()
        combined_light._light_controller.turn_on_lights = AsyncMock(return_value={})
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})
        
        await combined_light.async_turn_on(brightness=255)
        
        # At 100%, all stages should be on
        combined_light._light_controller.turn_on_lights.assert_called()


class TestRestoreEntity:
    """Test RestoreEntity support for state persistence."""

    @pytest.fixture
    def combined_light(self, mock_config_entry_advanced) -> CombinedLight:
        """Create a CombinedLight instance for testing."""
        return CombinedLight(mock_config_entry_advanced)

    @pytest.mark.asyncio
    async def test_restore_state_on(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test restoring 'on' state with brightness from last state."""
        combined_light.hass = hass
        
        # Set up mock lights
        hass.states.async_set("light.stage1_1", "on", {"brightness": 128})
        hass.states.async_set("light.stage1_2", "on", {"brightness": 128})
        
        # Mock async_get_last_state to return a previous state
        last_state = State(
            "light.combined_light",
            "on",
            {"brightness": 200},
        )
        
        with patch.object(
            combined_light, "async_get_last_state", return_value=last_state
        ):
            await combined_light.async_added_to_hass()
        
        assert combined_light._attr_is_on is True
        assert combined_light._target_brightness == 200
        assert combined_light._target_brightness_initialized is True

    @pytest.mark.asyncio
    async def test_restore_state_off(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test restoring 'off' state - should not set is_on."""
        combined_light.hass = hass
        
        # Set up mock lights
        hass.states.async_set("light.stage1_1", "off")
        
        # Mock async_get_last_state to return a previous 'off' state
        last_state = State(
            "light.combined_light",
            "off",
            {"brightness": 150},
        )
        
        with patch.object(
            combined_light, "async_get_last_state", return_value=last_state
        ):
            await combined_light.async_added_to_hass()
        
        # Off state should not set is_on to True
        assert combined_light._attr_is_on is False

    @pytest.mark.asyncio
    async def test_restore_state_none(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test behavior when no previous state exists."""
        combined_light.hass = hass
        
        # Set up mock lights as on
        hass.states.async_set("light.stage1_1", "on", {"brightness": 128})
        
        # Mock async_get_last_state to return None (no previous state)
        with patch.object(
            combined_light, "async_get_last_state", return_value=None
        ):
            await combined_light.async_added_to_hass()
        
        # Should sync from lights instead
        assert combined_light._target_brightness_initialized is True

    @pytest.mark.asyncio
    async def test_restore_state_without_brightness(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test restoring state when brightness attribute is missing."""
        combined_light.hass = hass
        
        # Set up mock lights
        hass.states.async_set("light.stage1_1", "on", {"brightness": 100})
        
        # Mock async_get_last_state to return state without brightness
        last_state = State(
            "light.combined_light",
            "on",
            {},  # No brightness attribute
        )
        
        with patch.object(
            combined_light, "async_get_last_state", return_value=last_state
        ):
            await combined_light.async_added_to_hass()
        
        # Should be on but brightness not initialized from restore
        assert combined_light._attr_is_on is True
        # Brightness should fall back to sync from lights
        assert combined_light._target_brightness_initialized is True


class TestPartialZoneSuccess:
    """Test behavior when some zones succeed and others fail."""

    @pytest.fixture
    def combined_light(self, mock_config_entry_advanced) -> CombinedLight:
        """Create a CombinedLight instance for testing."""
        return CombinedLight(mock_config_entry_advanced)

    @pytest.mark.asyncio
    async def test_partial_zone_failure_still_turns_on(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test that partial zone failure still turns on the combined light."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Set up mock lights
        hass.states.async_set("light.stage1_1", "on", {"brightness": 128})
        
        # Mock light controller where one zone succeeds and one fails
        mock_controller = AsyncMock()
        
        async def mock_turn_on(lights, brightness, context):
            if "light.stage1_1" in lights:
                return {"light.stage1_1": 128}  # Success
            raise Exception("Zone failed")
        
        mock_controller.turn_on_lights = mock_turn_on
        mock_controller.turn_off_lights = AsyncMock(return_value={})
        combined_light._light_controller = mock_controller
        
        await combined_light.async_turn_on(brightness=255)
        
        # Should still be on since some zones succeeded
        assert combined_light._attr_is_on is True

    @pytest.mark.asyncio
    async def test_all_zones_fail_turns_off(
        self, combined_light: CombinedLight, hass: HomeAssistant
    ) -> None:
        """Test that if all zones fail, combined light stays off."""
        combined_light.hass = hass
        combined_light.async_write_ha_state = MagicMock()
        
        # Mock light controller that always fails
        mock_controller = AsyncMock()
        mock_controller.turn_on_lights = AsyncMock(side_effect=Exception("Failed"))
        mock_controller.turn_off_lights = AsyncMock(return_value={})
        combined_light._light_controller = mock_controller
        
        await combined_light.async_turn_on(brightness=128)
        
        # Should be off since no zones succeeded
        assert combined_light._attr_is_on is False
