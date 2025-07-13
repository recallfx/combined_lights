"""Constants for the Combined lights integration."""

DOMAIN = "combined_lights"

# Platforms to be set up.
NUMBER_PLATFORM = "number"

# Configuration keys used in the config flow.
CONF_NAME = "name"
CONF_BACKGROUND_LIGHTS = "background_lights"
CONF_FEATURE_LIGHTS = "feature_lights"
CONF_CEILING_LIGHTS = "ceiling_lights"

# Advanced configuration keys for breakpoints and brightness ranges
CONF_BREAKPOINTS = "breakpoints"  # [30, 60, 90] - slider positions where zones activate
CONF_BACKGROUND_BRIGHTNESS_RANGES = (
    "background_brightness_ranges"  # [[1,50], [51,70], [71,80], [81,100]]
)
CONF_FEATURE_BRIGHTNESS_RANGES = (
    "feature_brightness_ranges"  # [[1,50], [51,70], [71,100]]
)
CONF_CEILING_BRIGHTNESS_RANGES = "ceiling_brightness_ranges"  # [[1,50], [51,100]]

# Default configuration matching your original request
DEFAULT_BREAKPOINTS = [30, 60, 90]  # 1-30%, 31-60%, 61-90%, 91-100%

# Default brightness ranges for each zone at each stage
DEFAULT_BACKGROUND_BRIGHTNESS_RANGES = [
    [1, 50],  # Stage 1 (1-30%): background at 1-50%
    [51, 70],  # Stage 2 (31-60%): background at 51-70%
    [71, 80],  # Stage 3 (61-90%): background at 71-80%
    [81, 100],  # Stage 4 (91-100%): background at 81-100%
]

DEFAULT_FEATURE_BRIGHTNESS_RANGES = [
    [0, 0],  # Stage 1: feature lights off
    [1, 50],  # Stage 2 (31-60%): feature at 1-50%
    [51, 70],  # Stage 3 (61-90%): feature at 51-70%
    [71, 100],  # Stage 4 (91-100%): feature at 71-100%
]

DEFAULT_CEILING_BRIGHTNESS_RANGES = [
    [0, 0],  # Stage 1: ceiling lights off
    [0, 0],  # Stage 2: ceiling lights off
    [1, 50],  # Stage 3 (61-90%): ceiling at 1-50%
    [51, 100],  # Stage 4 (91-100%): ceiling at 51-100%
]
