"""Constants for the Combined lights integration."""

DOMAIN = "combined_lights"

# Platforms to be set up.
NUMBER_PLATFORM = "number"

# Configuration keys used in the config flow.
CONF_NAME = "name"

# Configuration keys updated to use stage-based terminology
CONF_STAGE_1_LIGHTS = "stage_1_lights"
CONF_STAGE_2_LIGHTS = "stage_2_lights"
CONF_STAGE_3_LIGHTS = "stage_3_lights"
CONF_STAGE_4_LIGHTS = "stage_4_lights"

# Advanced configuration keys for breakpoints and brightness ranges
CONF_BREAKPOINTS = "breakpoints"  # [25, 50, 75] - slider positions where zones activate
CONF_STAGE_1_BRIGHTNESS_RANGES = (
    "stage_1_brightness_ranges"  # [[1,40], [41,60], [61,80], [81,100]]
)
CONF_STAGE_2_BRIGHTNESS_RANGES = (
    "stage_2_brightness_ranges"  # [[0,0], [1,40], [41,60], [61,100]]
)
CONF_STAGE_3_BRIGHTNESS_RANGES = (
    "stage_3_brightness_ranges"  # [[0,0], [0,0], [1,50], [51,100]]
)
CONF_STAGE_4_BRIGHTNESS_RANGES = (
    "stage_4_brightness_ranges"  # [[0,0], [0,0], [0,0], [1,100]]
)

# Brightness curve configuration
CONF_BRIGHTNESS_CURVE = "brightness_curve"  # "linear", "quadratic", or "cubic"

# Brightness curve types
CURVE_LINEAR = "linear"
CURVE_QUADRATIC = "quadratic"  # More precision at low brightness
CURVE_CUBIC = "cubic"  # Even more precision at low brightness

# Default curve - linear provides most predictable behavior
DEFAULT_BRIGHTNESS_CURVE = CURVE_LINEAR

# Default configuration matching your original request
DEFAULT_BREAKPOINTS = [25, 50, 75]  # 1-25%, 26-50%, 51-75%, 76-100%

# Default brightness ranges for each zone at each stage (4 stages now instead of 4)
DEFAULT_STAGE_1_BRIGHTNESS_RANGES = [
    [1, 40],  # Stage 1 (1-25%): lights at 1-40%
    [41, 60],  # Stage 2 (26-50%): lights at 41-60%
    [61, 80],  # Stage 3 (51-75%): lights at 61-80%
    [81, 100],  # Stage 4 (76-100%): lights at 81-100%
]

DEFAULT_STAGE_2_BRIGHTNESS_RANGES = [
    [0, 0],  # Stage 1: lights off
    [1, 40],  # Stage 2 (26-50%): lights at 1-40%
    [41, 60],  # Stage 3 (51-75%): lights at 41-60%
    [61, 100],  # Stage 4 (76-100%): lights at 61-100%
]

DEFAULT_STAGE_3_BRIGHTNESS_RANGES = [
    [0, 0],  # Stage 1: lights off
    [0, 0],  # Stage 2: lights off
    [1, 50],  # Stage 3 (51-75%): lights at 1-50%
    [51, 100],  # Stage 4 (76-100%): lights at 51-100%
]

DEFAULT_STAGE_4_BRIGHTNESS_RANGES = [
    [0, 0],  # Stage 1: lights off
    [0, 0],  # Stage 2: lights off
    [0, 0],  # Stage 3: lights off
    [1, 100],  # Stage 4 (76-100%): lights at 1-100%
]
