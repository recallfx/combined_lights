# Combined Lights

A Home Assistant custom component that creates a single unified light entity that intelligently controls multiple light zones based on brightness stages. Perfect for creating sophisticated lighting scenes that gradually expand throughout your home as you increase the brightness.

## Overview

Combined Lights transforms your collection of individual lights into a cohesive lighting system. Set one brightness level, and watch as different zones of lights activate and adjust their brightness based on your configured stages and ranges.

The integration creates stages based on brightness breakpoints (e.g., 1-25%, 26-50%, 51-75%, 76-100%) and allows you to define which lights are active in each stage and what brightness they should have.

## Key Features

- **Zone-based Control**: Organize lights into 4 configurable stages/zones
- **Progressive Activation**: Lights activate in stages as overall brightness increases
- **Flexible Brightness Mapping**: Each zone can have different brightness ranges for each stage
- **Multiple Curve Types**: Linear, quadratic, or cubic brightness curves for fine-tuned control
- **Manual Intervention Detection**: Detects when lights are manually changed outside the integration
- **Native Home Assistant Integration**: Uses config flow for easy setup and reconfiguration

## How It Works

The integration divides the brightness scale (0-100%) into configurable stages using breakpoints. For example, with breakpoints `[25, 50, 75]`:

- **Stage 1**: 1-25% overall brightness
- **Stage 2**: 26-50% overall brightness  
- **Stage 3**: 51-75% overall brightness
- **Stage 4**: 76-100% overall brightness

Each light zone (stage_1_lights, stage_2_lights, etc.) can be configured with brightness ranges that define how bright those lights should be during each stage.

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

The combined light entity works with all standard Home Assistant light controls:

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

## Events

The integration fires custom events when manual changes are detected:

```yaml
# Listen for external changes
automation:
  - trigger:
      platform: event
      event_type: combined_light.external_change
    action:
      - service: notify.mobile_app
        data:
          message: "Light {{ trigger.event.data.entity_id }} was manually changed"
```

## Troubleshooting

### Lights Not Responding

1. Verify all light entities exist and are controllable
2. Check Home Assistant logs for errors
3. Ensure lights are not controlled by other automations simultaneously

### Unexpected Brightness

1. Review your brightness ranges configuration
2. Check if manual intervention detection is working correctly
3. Verify breakpoints align with your expected behavior

### Performance Issues

1. Avoid controlling too many lights in a single zone
2. Use appropriate timeouts for slow-responding lights
3. Consider splitting complex setups into multiple combined light entities

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

- **2.1.0**: Current version with zone-based configuration and advanced brightness control
- **2.0.0**: Major rewrite with improved architecture and config flow
- **1.x**: Initial releases with basic functionality