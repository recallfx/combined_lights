# Combined Lights

A Home Assistant custom component that creates a single unified light entity that intelligently controls multiple light zones based on brightness stages. Perfect for creating sophisticated lighting scenes that gradually expand throughout your home as you increase the brightness.

## Overview

Combined Lights transforms your collection of individual lights into a cohesive lighting system. Set one brightness level, and watch as different zones of lights activate and adjust their brightness based on your configured stages and ranges.

The integration creates stages based on brightness breakpoints (e.g., 1-25%, 26-50%, 51-75%, 76-100%) and allows you to define which lights are active in each stage and what brightness they should have.

## Key Features

- **Zone-based Control**: Organize lights into 4 configurable stages/zones
- **Progressive Activation**: Lights activate in stages as overall brightness increases
- **Bidirectional Sync**: Wall switch changes automatically update the combined light brightness
- **Configurable Back-Propagation**: Optionally push manual adjustments to every stage to keep the scene aligned
- **Flexible Brightness Mapping**: Each zone can have different brightness ranges for each stage
- **Multiple Curve Types**: Linear, quadratic, or cubic brightness curves for fine-tuned control
- **Smart Context Awareness**: Distinguishes between manual changes and automation-driven adjustments
- **Native Home Assistant Integration**: Uses config flow for easy setup and reconfiguration

## How It Works

The integration divides the brightness scale (0-100%) into configurable stages using breakpoints. For example, with breakpoints `[25, 50, 75]`:

- **Stage 1**: 1-25% overall brightness
- **Stage 2**: 26-50% overall brightness  
- **Stage 3**: 51-75% overall brightness
- **Stage 4**: 76-100% overall brightness

Each light zone (stage_1_lights, stage_2_lights, etc.) can be configured with brightness ranges that define how bright those lights should be during each stage.

### Bidirectional Control

Combined Lights works both ways:

1. **Combined Light → Individual Lights**: When you adjust the combined light's brightness slider (or via automation), it calculates and applies the appropriate brightness to each zone based on your configuration.

2. **Wall Switches → Combined Light**: When you use physical wall switches or other controls to change individual lights, Combined Lights detects the changes and updates its own brightness to reflect the new state. This means other automations see the combined light as the control point, not the individual switches.

#### Back-Propagation vs Indicator-Only Updates

- **Indicator-Only (default)**: Manual tweaks simply adjust the combined light's reported percentage based on how many stages are active. For example, turning on only a Stage 4 light will display roughly 25%, preventing the slider from jumping straight to 100%.
- **Back-Propagation Enabled**: Toggle the **“Sync Manual Changes”** option in the config flow if you want manual changes to immediately drive *all* relevant stages so the entire scene matches the inferred combined brightness.

This toggle provides the best of both worlds: calm indicator behavior by default and full scene correction when desired.

This bidirectional sync ensures your lighting state is always accurate, whether you control individual lights or use the combined entity.

### Example Configuration

```yaml
# Breakpoints: [25, 50, 75]
stage_1_lights:    # Always-on ambient lights
  - light.bedside_lamp
  - light.hallway_strip
  
stage_2_lights:    # Task lighting
  - light.desk_lamp
  - light.kitchen_under_cabinet
  
stage_3_lights:    # Room lighting
  - light.living_room_ceiling
  - light.bedroom_main
  
stage_4_lights:    # Full brightness/outdoor
  - light.outdoor_floodlights
  - light.garage_lights

# Brightness ranges for stage_1_lights:
# Stage 1 (1-25%):   lights at 5-20%
# Stage 2 (26-50%):  lights at 30-50% 
# Stage 3 (51-75%):  lights at 60-80%
# Stage 4 (76-100%): lights at 90-100%
```

When you set the combined light to 40% brightness:
- Stage 1 lights: On at 30-50% range
- Stage 2 lights: On at calculated brightness
- Stage 3 lights: Off (stage not reached)
- Stage 4 lights: Off (stage not reached)

## Installation

### HACS (Recommended)

1. Ensure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS
3. Search for "Combined Lights" and install
4. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/combined_lights` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

### Basic Setup

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration** and search for "Combined Lights"
3. Configure your light zones:
   - **Name**: Display name for your combined light entity
   - **Stage 1 Lights**: Always-on ambient lights (optional)
   - **Stage 2 Lights**: Secondary zone lights (optional)
   - **Stage 3 Lights**: Main room lights (optional)  
   - **Stage 4 Lights**: Full brightness/outdoor lights (optional)

### Advanced Configuration

The second step allows you to customize:

- **Breakpoints**: Where stages transition (default: [25, 50, 75])
- **Brightness Curve**: Linear, quadratic, or cubic response
- **Brightness Ranges**: Min/max brightness for each light zone in each stage

#### Brightness Ranges Format

Use the simplified format in the YAML editor:

```yaml
stage_1_brightness_ranges:
  - "5, 20"    # Stage 1: 5-20% brightness
  - "30, 50"   # Stage 2: 30-50% brightness  
  - "60, 80"   # Stage 3: 60-80% brightness
  - "90, 100"  # Stage 4: 90-100% brightness

stage_2_brightness_ranges:
  - "0, 0"     # Stage 1: off
  - "10, 40"   # Stage 2: 10-40% brightness
  - "50, 70"   # Stage 3: 50-70% brightness
  - "80, 100"  # Stage 4: 80-100% brightness
```

Use `"0, 0"` to keep lights off during specific stages.

### Brightness Curves

- **Linear**: Even brightness distribution across the range
- **Quadratic**: More precision at lower brightness levels
- **Cubic**: Maximum precision at low brightness, good for fine ambient control

## Understanding Bidirectional Sync

One of Combined Lights' most powerful features is its ability to sync in both directions. This creates a seamless experience whether you're using digital controls or physical wall switches.

### How It Works

When you flip a wall switch or use a physical dimmer to adjust individual lights:

1. **Detection**: Combined Lights monitors all configured light entities for state changes
2. **Calculation**: It performs a reverse calculation to determine what overall brightness percentage would produce the current state
3. **Update**: The combined light entity updates its brightness to match
4. **Transparency**: Other automations and components see this as a normal combined light adjustment

### Benefits

- **Single Source of Truth**: Automations can monitor just the combined light, not individual switches
- **No Manual Flags**: Other components don't need special logic to detect "manual" vs "automated" changes
- **Physical Controls Work**: Users can use familiar wall switches without breaking automation logic
- **Always Accurate**: The combined light brightness always reflects the actual state of your lights

### Example Scenario

You have an automation that turns on accent lighting when the combined light is below 30%:

```yaml
automation:
  - trigger:
      platform: numeric_state
      entity_id: light.combined_lights
      below: 30
    action:
      - service: light.turn_on
        target:
          entity_id: light.accent_lights
```

Without bidirectional sync, this automation would need to monitor multiple individual lights and handle manual intervention. With bidirectional sync, it just works—whether someone adjusts the combined light slider or flips a wall switch, the automation responds correctly.

## Usage Examples

### Progressive Home Lighting

```yaml
# Living room that expands from accent to full lighting
stage_1_lights: ["light.accent_strips"]
stage_2_lights: ["light.table_lamps"] 
stage_3_lights: ["light.ceiling_main"]
stage_4_lights: ["light.outdoor_patio"]

# Breakpoints: [30, 60, 90] for smooth transitions
```

### Office/Workspace Setup

```yaml
# Desk area that scales from monitor bias to full room
stage_1_lights: ["light.monitor_backlight"]
stage_2_lights: ["light.desk_lamp"]
stage_3_lights: ["light.office_ceiling"]
stage_4_lights: ["light.closet", "light.storage_room"]
```

### Bedroom Nighttime Routine

```yaml
# Gentle progression from night light to morning brightness
stage_1_lights: ["light.bedside_dim"]
stage_2_lights: ["light.dresser_lamp"]
stage_3_lights: ["light.bedroom_main"]
stage_4_lights: ["light.walk_in_closet"]

# Use cubic curve for very gentle low-light progression
brightness_curve: "cubic"
```

## Automation Integration

The combined light entity works seamlessly with all Home Assistant automations and controls:

```yaml
# Simple brightness control
service: light.turn_on
target:
  entity_id: light.combined_lights
data:
  brightness_pct: 45

# Morning routine
automation:
  - trigger:
      platform: sun
      event: sunrise
    action:
      - service: light.turn_on
        target:
          entity_id: light.combined_lights
        data:
          brightness_pct: 75
```

### Working with Wall Switches

When users control individual lights via wall switches or physical controls:

- Combined Lights automatically updates its brightness to match
- Other automations see the change as if the combined light was adjusted
- No "manual intervention" flags for other components to worry about

This makes Combined Lights the single source of truth for your lighting state, whether controlled digitally or physically.

## Events

The integration fires custom events for monitoring and debugging:

```yaml
# Listen for external changes (useful for debugging)
automation:
  - trigger:
      platform: event
      event_type: combined_light.external_change
    action:
      - service: notify.mobile_app
        data:
          message: "Light {{ trigger.event.data.entity_id }} detected external change"
```

Note: With bidirectional sync enabled, most wall switch changes will update the combined light's brightness rather than triggering external change events. External change events are primarily useful for debugging unexpected state changes.

## Troubleshooting

### Lights Not Responding

1. Verify all light entities exist and are controllable
2. Check Home Assistant logs for errors
3. Ensure lights are not controlled by conflicting automations

### Combined Light Brightness Not Updating from Wall Switches

1. Check that the lights are properly configured in their respective zones
2. Verify the lights support brightness reporting (check `brightness` attribute)
3. Look for log messages about brightness sync in Home Assistant logs
4. Ensure the change is significant enough (threshold is 5/255)

### Unexpected Brightness

1. Review your brightness ranges configuration
2. Check which stage the overall brightness falls into
3. Verify breakpoints align with your expected behavior
4. Test with different brightness curves (linear/quadratic/cubic)

### Performance Issues

1. Avoid controlling too many lights in a single zone
2. Use appropriate timeouts for slow-responding lights
3. Consider splitting complex setups into multiple combined light entities
4. Check for feedback loops if using multiple automation layers

## Advanced Usage

### Custom Breakpoints

Adjust breakpoints to match your usage patterns:

```yaml
# Fine control at low levels, big jumps at high levels
breakpoints: [15, 30, 80]

# Even distribution
breakpoints: [25, 50, 75]

# Most control in middle range
breakpoints: [10, 40, 90]
```

### Zone-Specific Behavior

Different zones can have completely different brightness patterns:

```yaml
# Ambient lights: Always on, gentle increases
stage_1_brightness_ranges:
  - "10, 15"   # Barely visible
  - "20, 30"   # Gentle glow
  - "35, 50"   # Noticeable but soft
  - "60, 80"   # Full ambient

# Task lights: Off until needed, then strong
stage_2_brightness_ranges:
  - "0, 0"     # Off
  - "60, 80"   # Immediate useful brightness
  - "80, 90"   # High task lighting
  - "90, 100"  # Maximum brightness
```

## Contributing

Contributions are welcome! Please check the [issues page](https://github.com/recallfx/combined_lights/issues) for known issues or feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/recallfx/combined_lights/issues)
- **Discussions**: [Home Assistant Community](https://community.home-assistant.io/)

## Version History

- **2.2.0**: Added bidirectional brightness synchronization - wall switches now update combined light brightness
- **2.1.0**: Zone-based configuration and advanced brightness control
- **2.0.0**: Major rewrite with improved architecture and config flow
- **1.x**: Initial releases with basic functionality