"""Tests for ConfigValidator helper."""
from custom_components.combined_lights.helpers import ConfigValidator

def test_validate_brightness_ranges_valid():
    """Test valid brightness ranges."""
    assert ConfigValidator.validate_brightness_ranges([[0, 100]])
    assert ConfigValidator.validate_brightness_ranges([[0, 0], [1, 50]])
    assert ConfigValidator.validate_brightness_ranges([])
    assert ConfigValidator.validate_brightness_ranges([[10, 20], [30, 40]])

def test_validate_brightness_ranges_invalid():
    """Test invalid brightness ranges."""
    # Invalid format
    assert not ConfigValidator.validate_brightness_ranges([[0]])
    assert not ConfigValidator.validate_brightness_ranges([[0, 1, 2]])
    
    # Out of bounds
    assert not ConfigValidator.validate_brightness_ranges([[-1, 50]])
    assert not ConfigValidator.validate_brightness_ranges([[0, 101]])
    
    # Min > Max (unless 0,0)
    assert not ConfigValidator.validate_brightness_ranges([[50, 40]])
    
    # 0,0 is valid (off)
    assert ConfigValidator.validate_brightness_ranges([[0, 0]])

def test_validate_breakpoints_valid():
    """Test valid breakpoints."""
    assert ConfigValidator.validate_breakpoints([25, 50, 75])
    assert ConfigValidator.validate_breakpoints([1, 2, 3])
    assert ConfigValidator.validate_breakpoints([97, 98, 99])

def test_validate_breakpoints_invalid():
    """Test invalid breakpoints."""
    # Wrong length
    assert not ConfigValidator.validate_breakpoints([50])
    assert not ConfigValidator.validate_breakpoints([25, 50])
    assert not ConfigValidator.validate_breakpoints([25, 50, 75, 90])
    
    # Not sorted
    assert not ConfigValidator.validate_breakpoints([50, 25, 75])
    
    # Out of bounds
    assert not ConfigValidator.validate_breakpoints([0, 50, 75])
    assert not ConfigValidator.validate_breakpoints([25, 50, 100])
    assert not ConfigValidator.validate_breakpoints([-1, 50, 75])
