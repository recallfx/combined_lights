# Combined Lights

Combine and control multiple Home Assistant light entities as a single adaptive lighting group, with zone-based brightness and advanced configuration.

## Features
- Group multiple lights into zones (background, feature, ceiling)
- Control all grouped lights as one entity with intelligent staging
- Configure brightness breakpoints and ranges for each zone
- Four configurable lighting stages with zone-specific brightness control
- Advanced configuration via UI
- Supports reconfiguration without removing the integration

## How It Works: Lighting Stages

Combined Lights uses a **4-stage lighting system** that progressively activates different light zones based on the overall brightness level you set.

### Default Configuration
- **Breakpoints**: `[30, 60, 90]` (configurable)
- **Stages**:
  - **Stage 1**: 1% - 30% brightness
  - **Stage 2**: 31% - 60% brightness  
  - **Stage 3**: 61% - 90% brightness
  - **Stage 4**: 91% - 100% brightness

### Zone Behavior by Stage

| Stage | Background Lights | Feature Lights | Ceiling Lights |
|-------|------------------|----------------|----------------|
| **1** (1-30%) | ✅ Active (1-50%) | ❌ Off | ❌ Off |
| **2** (31-60%) | ✅ Active (51-70%) | ✅ Active (1-50%) | ❌ Off |
| **3** (61-90%) | ✅ Active (71-80%) | ✅ Active (51-70%) | ✅ Active (1-50%) |
| **4** (91-100%) | ✅ Active (81-100%) | ✅ Active (71-100%) | ✅ Active (51-100%) |

### Example Usage
- **Set to 25%**: Only background lights at ~40% brightness (cozy ambient lighting)
- **Set to 45%**: Background lights at ~60% + feature lights at ~30% (accent lighting)
- **Set to 75%**: All zones active - background at ~75%, feature at ~60%, ceiling at ~25% (full room lighting)
- **Set to 95%**: Maximum lighting - all zones at high brightness (task lighting)

### Customization
Both **breakpoints** and **brightness ranges** are fully configurable:
- **Breakpoints**: Define when each stage activates (e.g., `[25, 50, 80]`)
- **Brightness Ranges**: Set min/max brightness for each zone in each stage
- **Zone Assignment**: Choose which lights belong to background, feature, or ceiling zones
- **Brightness Curve**: Control how input brightness translates to zone brightness

### Brightness Response Curves

The integration offers three brightness curve options for more natural lighting control:

#### **Linear** (Even Response)
- **1% input → 1% output**: Direct 1:1 mapping
- **50% input → 50% output**: Consistent across all levels
- **Best for**: Users who prefer predictable, even response

#### **Quadratic** (Recommended: Balanced Precision) 
- **1% input → ~1% output**: Nearly direct at very low levels
- **5% input → ~3% output**: Gentle curve begins
- **25% input → ~35% output**: More responsive in mid-range
- **Best for**: Most users - natural feel with good low-end control

#### **Cubic** (Maximum Low-End Precision)
- **1% input → ~1% output**: Direct mapping at very low levels
- **5% input → ~8% output**: Curve becomes more pronounced
- **15% input → ~25% output**: Significant mid-range boost
- **Best for**: Fine ambient lighting control and accent scenarios

### Why Curves Matter
At 1% brightness, the difference between 1% and 2% zone output is **100% brighter** - very noticeable!
At 60% brightness, the difference between 60% and 61% zone output is only **1.7% brighter** - barely perceptible.

Curves give you **more precision where it matters most** and **smoother control where fine-tuning is less critical**.

## Installation
1. Copy the `combined_lights` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the Combined Lights integration via Settings → Devices & Services.

## Configuration
1. **Basic Setup**: Use the UI to select lights for each zone (background, feature, ceiling)
2. **Advanced Setup**: Configure breakpoints, brightness ranges, and response curve:
   - **Breakpoints**: Define the percentage thresholds between stages (default: `[30, 60, 90]`)
   - **Brightness Curve**: Choose Linear, Quadratic (recommended), or Cubic response
   - **Brightness Ranges**: Set `[min, max]` brightness for each zone in each stage
3. **Reconfiguration**: Update settings anytime from the integration options without recreating

### Configuration Examples

**Conservative Lighting** (slower progression):
- Breakpoints: `[40, 70, 85]`
- Background stays active longer, ceiling activates later

**Aggressive Lighting** (faster progression):  
- Breakpoints: `[20, 40, 70]`
- All zones activate quickly for maximum illumination

**Custom Brightness Ranges**:
```json
Background: [[10,30], [40,60], [70,80], [85,100]]
Feature:    [[0,0],   [20,40], [50,70], [80,100]]  
Ceiling:    [[0,0],   [0,0],   [30,50], [60,100]]
```

## Documentation
See [project documentation](https://github.com/recallfx/ha-combined-lights) for full details and examples.

## Issue Tracker
Report bugs or request features at [GitHub Issues](https://github.com/recallfx/ha-combined-lights/issues).

## Code Owners
- [@recallfx](https://github.com/recallfx)

## License
This project is licensed under the MIT License.
