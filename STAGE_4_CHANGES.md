# Combined Lights Integration - Stage 4 Addition

## Summary

Successfully added a fourth stage to the Combined Lights integration, expanding from 3 stages to 4 stages with updated breakpoints and configuration.

## Changes Made

### 1. Constants (`const.py`)
- Added `CONF_STAGE_4_LIGHTS` and `CONF_STAGE_4_BRIGHTNESS_RANGES` configuration keys
- Updated default breakpoints from `[30, 60, 90]` to `[25, 50, 75]` for more even distribution
- Added `DEFAULT_STAGE_4_BRIGHTNESS_RANGES` with pattern `[[0, 0], [0, 0], [0, 0], [1, 100]]`
- Updated all other stage brightness ranges to work with 4 stages instead of 3

### 2. Configuration Flow (`config_flow.py`)
- Added Stage 4 light selection to the basic configuration schema
- Added Stage 4 brightness ranges to the advanced configuration schema
- Updated the merge function to handle Stage 4 configuration data
- Added proper imports for all Stage 4 constants

### 3. Light Platform (`light.py`)
- Updated `get_light_zones()` to include `stage_4` lights
- Updated `get_brightness_ranges()` to include `stage_4` brightness ranges
- Modified `_sync_target_brightness_from_lights()` to consider Stage 4 lights
- Updated `async_turn_on()` to control Stage 4 lights
- Added Stage 4 to the logging output for better debugging
- Fixed quadratic list summation issue in `_get_all_controlled_lights()`
- Added proper initialization of `_target_brightness_initialized` attribute

### 4. User Interface Strings (`strings.json`)
- Added Stage 4 light selection to all configuration steps (user, advanced, reconfigure, reconfigure_advanced)
- Updated descriptions to include Stage 4 (e.g., "task lighting")
- Updated breakpoint descriptions to reflect new `[25, 50, 75]` values

## New Stage Behavior

The integration now supports 4 stages with the following breakpoints:

1. **Stage 1**: 1-25% brightness
2. **Stage 2**: 26-50% brightness
3. **Stage 3**: 51-75% brightness
4. **Stage 4**: 76-100% brightness

### Default Brightness Ranges

- **Stage 1 Lights**: Active in all stages `[1,40]`, `[41,60]`, `[61,80]`, `[81,100]`
- **Stage 2 Lights**: Active from stage 2 `[0,0]`, `[1,40]`, `[41,60]`, `[61,100]`
- **Stage 3 Lights**: Active from stage 3 `[0,0]`, `[0,0]`, `[1,50]`, `[51,100]`
- **Stage 4 Lights**: Active only in stage 4 `[0,0]`, `[0,0]`, `[0,0]`, `[1,100]`

## Testing

All functionality has been verified with a comprehensive test suite that confirms:
- ✅ Stage 4 configuration is properly defined
- ✅ Stage calculation works correctly for all 4 stages
- ✅ Stage 4 brightness ranges follow the expected pattern
- ✅ No linting errors or runtime issues

## Migration

Existing configurations with 3 stages will continue to work. Users can optionally:
1. Add Stage 4 lights to their configuration
2. Update breakpoints if desired (defaults changed to more even distribution)
3. Customize Stage 4 brightness ranges through the advanced configuration

The integration maintains backward compatibility while providing the expanded functionality.
