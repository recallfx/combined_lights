# Combined Lights

Combine and control multiple Home Assistant light entities as a single adaptive lighting group, with stage-based brightness and advanced configuration.

## Features
- Group multiple lights into stages (e.g., Stage 1, Stage 2, Stage 3)
- Control all grouped lights as one entity with intelligent staging
- Configure brightness breakpoints and ranges for each stage
- Four configurable lighting stages with stage-specific brightness control
- Advanced configuration via UI
- Supports reconfiguration without removing the integration

## How It Works: Lighting Stages

Combined Lights uses a **4-stage lighting system** that progressively activates different light stages based on the overall brightness level you set.

### Default Configuration
- **Breakpoints**: `[30, 60, 90]` (configurable)
- **Stages**:
  - **Stage 1**: 1% - 30% brightness (Ambient lighting)
  - **Stage 2**: 31% - 60% brightness (Feature lighting)
  - **Stage 3**: 61% - 90% brightness (Ceiling lighting)
  - **Stage 4**: 91% - 100% brightness (Full lighting)

### Stage Behavior by Brightness

| Stage | Description          | Brightness Range |
|-------|----------------------|------------------|
| **1** | Ambient lighting     | 1% - 30%         |
| **2** | Feature lighting     | 31% - 60%        |
| **3** | Ceiling lighting     | 61% - 90%        |
| **4** | Full lighting        | 91% - 100%       |

### Example Usage
- **Set to 25%**: Only Stage 1 lights active at ~40% brightness (cozy ambient lighting)
- **Set to 45%**: Stage 1 lights at ~60% + Stage 2 lights at ~30% (accent lighting)
- **Set to 75%**: All stages active - Stage 1 at ~75%, Stage 2 at ~60%, Stage 3 at ~25% (full room lighting)
- **Set to 95%**: Maximum lighting - all stages at high brightness (task lighting)

### Customization
Both **breakpoints** and **brightness ranges** are fully configurable:
- **Breakpoints**: Define when each stage activates (e.g., `[25, 50, 80]`)
- **Brightness Ranges**: Set min/max brightness for each stage
- **Stage Assignment**: Choose which lights belong to each stage
- **Brightness Curve**: Control how input brightness translates to stage brightness

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
At 1% brightness, the difference between 1% and 2% stage output is **100% brighter** - very noticeable!
At 60% brightness, the difference between 60% and 61% stage output is only **1.7% brighter** - barely perceptible.

Curves give you **more precision where it matters most** and **smoother control where fine-tuning is less critical**.

## Installation
1. Copy the `combined_lights` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the Combined Lights integration via Settings → Devices & Services.

## Configuration
1. **Basic Setup**: Use the UI to select lights for each stage (e.g., Stage 1, Stage 2, Stage 3)
2. **Advanced Setup**: Configure breakpoints, brightness ranges, and response curve:
   - **Breakpoints**: Define the percentage thresholds between stages (default: `[30, 60, 90]`)
   - **Brightness Curve**: Choose Linear, Quadratic (recommended), or Cubic response
   - **Brightness Ranges**: Set `[min, max]` brightness for each stage
3. **Reconfiguration**: Update settings anytime from the integration options without recreating

### Configuration Examples

**Conservative Lighting** (slower progression):
- Breakpoints: `[40, 70, 85]`
- Stage 1 stays active longer, Stage 3 activates later

**Aggressive Lighting** (faster progression):
- Breakpoints: `[20, 40, 70]`
- All stages activate quickly for maximum illumination

**Custom Brightness Ranges**:
```json
Stage 1: [[10,30], [40,60], [70,80], [85,100]]
Stage 2: [[0,0],   [20,40], [50,70], [80,100]]
Stage 3: [[0,0],   [0,0],   [30,50], [60,100]]
```

## Documentation
See [project documentation](https://github.com/recallfx/ha-combined-lights) for full details and examples.

## Issue Tracker
Report bugs or request features at [GitHub Issues](https://github.com/recallfx/ha-combined-lights/issues).

## Code Owners
- [@recallfx](https://github.com/recallfx)

## License
This project is licensed under the MIT License.
