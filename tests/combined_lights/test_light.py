"""Test the Combined Lights light platform."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.const import (
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
from custom_components.combined_lights.light import (
    CombinedLight,
    async_setup_entry,
    get_brightness_ranges,
    get_config_value,
    get_light_zones,
)


class TestLightPlatformUtilities:
    """Test utility functions for the light platform."""

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
                CONF_STAGE_1_LIGHTS: ["light.stage1_1", "light.stage1_2"],
                CONF_STAGE_2_LIGHTS: ["light.stage2_1"],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: ["light.stage4_1"],
                CONF_BREAKPOINTS: [30, 60, 90],
                CONF_BRIGHTNESS_CURVE: CURVE_QUADRATIC,
                CONF_STAGE_1_BRIGHTNESS_RANGES: [[10, 40], [50, 70], [80, 90], [95, 100]],
                CONF_STAGE_2_BRIGHTNESS_RANGES: [[0, 0], [20, 50], [60, 80], [85, 100]],
                CONF_STAGE_3_BRIGHTNESS_RANGES: [[0, 0], [0, 0], [30, 60], [70, 100]],
                CONF_STAGE_4_BRIGHTNESS_RANGES: [[0, 0], [0, 0], [0, 0], [40, 100]],
            },
            options={},
            entry_id=str(uuid4()),
            source="user",
            unique_id=None,
            discovery_keys=set(),
        )

    def test_get_config_value(self, mock_config_entry: ConfigEntry) -> None:
        """Test getting configuration value with default fallback."""
        # Test existing value
        result = get_config_value(mock_config_entry, CONF_NAME, "Default Name")
        assert result == "Test Combined Lights"

        # Test default fallback
        result = get_config_value(mock_config_entry, "non_existent", "Default Value")
        assert result == "Default Value"

    def test_get_light_zones(self, mock_config_entry: ConfigEntry) -> None:
        """Test getting light zones from configuration."""
        zones = get_light_zones(mock_config_entry)
        
        expected = {
            "stage_1": ["light.stage1_1", "light.stage1_2"],
            "stage_2": ["light.stage2_1"],
            "stage_3": [],
            "stage_4": ["light.stage4_1"],
        }
        assert zones == expected

    def test_get_brightness_ranges(self, mock_config_entry: ConfigEntry) -> None:
        """Test getting brightness ranges from configuration."""
        ranges = get_brightness_ranges(mock_config_entry)
        
        assert ranges["stage_1"] == [[10, 40], [50, 70], [80, 90], [95, 100]]
        assert ranges["stage_2"] == [[0, 0], [20, 50], [60, 80], [85, 100]]
        assert ranges["stage_3"] == [[0, 0], [0, 0], [30, 60], [70, 100]]
        assert ranges["stage_4"] == [[0, 0], [0, 0], [0, 0], [40, 100]]

    def test_get_brightness_ranges_with_defaults(self) -> None:
        """Test getting brightness ranges with default values."""
        # Config entry with minimal data
        entry = ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Minimal",
            data={CONF_NAME: "Minimal"},
            options={},
            entry_id=str(uuid4()),
            source="user",
            unique_id=None,
            discovery_keys=set(),
        )
        
        ranges = get_brightness_ranges(entry)
        
        assert ranges["stage_1"] == DEFAULT_STAGE_1_BRIGHTNESS_RANGES
        assert ranges["stage_2"] == DEFAULT_STAGE_2_BRIGHTNESS_RANGES
        assert ranges["stage_3"] == DEFAULT_STAGE_3_BRIGHTNESS_RANGES
        assert ranges["stage_4"] == DEFAULT_STAGE_4_BRIGHTNESS_RANGES


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.fixture
    def mock_config_entry(self) -> ConfigEntry:
        """Create a mock config entry for testing."""
        return ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Test Combined Lights",
            data={CONF_NAME: "Test Combined Lights"},
            options={},
            entry_id=str(uuid4()),
            source="user",
            unique_id=None,
            discovery_keys=set(),
        )

    async def test_async_setup_entry(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
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
    def mock_config_entry(self) -> ConfigEntry:
        """Create a mock config entry for testing."""
        return ConfigEntry(
            version=1,
            minor_version=0,
            domain=DOMAIN,
            title="Test Combined Lights",
            data={
                CONF_NAME: "Test Combined Lights",
                CONF_STAGE_1_LIGHTS: ["light.stage1_1", "light.stage1_2"],
                CONF_STAGE_2_LIGHTS: ["light.stage2_1"],
                CONF_STAGE_3_LIGHTS: [],
                CONF_STAGE_4_LIGHTS: ["light.stage4_1"],
                CONF_BREAKPOINTS: DEFAULT_BREAKPOINTS,
                CONF_BRIGHTNESS_CURVE: DEFAULT_BRIGHTNESS_CURVE,
                CONF_STAGE_1_BRIGHTNESS_RANGES: DEFAULT_STAGE_1_BRIGHTNESS_RANGES,
                CONF_STAGE_2_BRIGHTNESS_RANGES: DEFAULT_STAGE_2_BRIGHTNESS_RANGES,
                CONF_STAGE_3_BRIGHTNESS_RANGES: DEFAULT_STAGE_3_BRIGHTNESS_RANGES,
                CONF_STAGE_4_BRIGHTNESS_RANGES: DEFAULT_STAGE_4_BRIGHTNESS_RANGES,
            },
            options={},
            entry_id=str(uuid4()),
            source="user",
            unique_id=None,
            discovery_keys=set(),
        )

    @pytest.fixture
    def combined_light(self, mock_config_entry: ConfigEntry) -> CombinedLight:
        """Create a CombinedLight instance for testing."""
        return CombinedLight(mock_config_entry)

    def test_init(self, combined_light: CombinedLight, mock_config_entry: ConfigEntry) -> None:
        """Test CombinedLight initialization."""
        assert combined_light._attr_name == "Test Combined Lights"
        assert combined_light._attr_unique_id == f"{mock_config_entry.entry_id}_combined_light"
        assert combined_light._attr_is_on is False
        assert combined_light._attr_brightness == 255
        assert combined_light._attr_supported_color_modes == {ColorMode.BRIGHTNESS}
        assert combined_light._attr_color_mode == ColorMode.BRIGHTNESS

    def test_available(self, combined_light: CombinedLight) -> None:
        """Test entity availability."""
        assert combined_light.available is True

    def test_get_stage_from_brightness(self, combined_light: CombinedLight) -> None:
        """Test determining stage from brightness percentage."""
        breakpoints = DEFAULT_BREAKPOINTS  # [25, 50, 75]
        
        # Test each stage
        assert combined_light._get_stage_from_brightness(10, breakpoints) == 0  # Stage 1
        assert combined_light._get_stage_from_brightness(25, breakpoints) == 0  # Stage 1
        assert combined_light._get_stage_from_brightness(30, breakpoints) == 1  # Stage 2
        assert combined_light._get_stage_from_brightness(50, breakpoints) == 1  # Stage 2
        assert combined_light._get_stage_from_brightness(60, breakpoints) == 2  # Stage 3
        assert combined_light._get_stage_from_brightness(75, breakpoints) == 2  # Stage 3
        assert combined_light._get_stage_from_brightness(80, breakpoints) == 3  # Stage 4
        assert combined_light._get_stage_from_brightness(100, breakpoints) == 3  # Stage 4

    def test_apply_brightness_curve_linear(self, combined_light: CombinedLight) -> None:
        """Test linear brightness curve."""
        # Linear curve should return input unchanged
        assert combined_light._apply_brightness_curve(0.0, CURVE_LINEAR) == 0.0
        assert combined_light._apply_brightness_curve(0.5, CURVE_LINEAR) == 0.5
        assert combined_light._apply_brightness_curve(1.0, CURVE_LINEAR) == 1.0

    def test_apply_brightness_curve_quadratic(self, combined_light: CombinedLight) -> None:
        """Test quadratic brightness curve."""
        # Quadratic curve should be different from linear for mid-range values
        result = combined_light._apply_brightness_curve(0.5, CURVE_QUADRATIC)
        assert result != 0.5  # Should be different from linear
        assert 0.0 <= result <= 1.0  # Should be within valid range

    def test_calculate_zone_brightness_off_range(self, combined_light: CombinedLight) -> None:
        """Test zone brightness calculation for off range [0, 0]."""
        # Zone should be off when range is [0, 0]
        result = combined_light._calculate_zone_brightness_from_config(
            50.0,  # overall_pct
            1,     # stage
            [[0, 0], [0, 0], [0, 0], [0, 0]],  # zone_ranges (all off)
            DEFAULT_BREAKPOINTS
        )
        assert result == 0.0

    def test_calculate_zone_brightness_active_range(self, combined_light: CombinedLight) -> None:
        """Test zone brightness calculation for active range."""
        # Zone should have brightness when range is not [0, 0]
        result = combined_light._calculate_zone_brightness_from_config(
            50.0,  # overall_pct (exactly at breakpoint[1])
            1,     # stage 2
            [[0, 0], [10, 50], [60, 80], [90, 100]],  # zone_ranges
            DEFAULT_BREAKPOINTS  # [25, 50, 75]
        )
        # Should be maximum of stage 2 range since we're at the upper boundary
        assert result == 50.0

    def test_get_all_controlled_lights(self, combined_light: CombinedLight) -> None:
        """Test getting all controlled light entity IDs."""
        lights = combined_light._get_all_controlled_lights()
        expected = ["light.stage1_1", "light.stage1_2", "light.stage2_1", "light.stage4_1"]
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

        result = combined_light._get_average_brightness(["light.test1", "light.test2", "light.test3"])
        assert result == 150  # (100 + 200) / 2

    def test_get_average_brightness_all_off_mocked(self, combined_light: CombinedLight) -> None:
        """Test getting average brightness when all lights are off."""
        # Mock the hass object and states
        combined_light.hass = Mock()
        combined_light.hass.states.get = Mock(return_value=Mock(state="off"))

        result = combined_light._get_average_brightness(["light.test1", "light.test2"])
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