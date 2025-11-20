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

# Brightness curve configuration per stage
CONF_STAGE_1_CURVE = "stage_1_curve"
CONF_STAGE_2_CURVE = "stage_2_curve"
CONF_STAGE_3_CURVE = "stage_3_curve"
CONF_STAGE_4_CURVE = "stage_4_curve"

# Advanced configuration keys
CONF_BREAKPOINTS = "breakpoints"  # [30, 60, 85] - slider positions where zones activate

# Optional behavior switches
CONF_ENABLE_BACK_PROPAGATION = "enable_back_propagation"
DEFAULT_ENABLE_BACK_PROPAGATION = False

# Brightness curve types
CURVE_LINEAR = "linear"
CURVE_QUADRATIC = "quadratic"  # More precision at low brightness
CURVE_CUBIC = "cubic"  # Even more precision at low brightness

# Default curve - linear provides most predictable behavior
DEFAULT_BRIGHTNESS_CURVE = CURVE_LINEAR

# Default configuration
DEFAULT_BREAKPOINTS = [30, 60, 85]  # 1-30%, 31-60%, 61-85%, 86-100%

# Default curves for each stage
DEFAULT_STAGE_1_CURVE = CURVE_LINEAR
DEFAULT_STAGE_2_CURVE = CURVE_LINEAR
DEFAULT_STAGE_3_CURVE = CURVE_LINEAR
DEFAULT_STAGE_4_CURVE = CURVE_LINEAR
