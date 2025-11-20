import { CurveType, StageConfig } from '../types';

/**
 * Calculates the local brightness for a specific stage based on global brightness.
 * 
 * Logic based on Combined Lights documentation:
 * - Stage 1 (Start 0): Maps Global 0-100 to Local 0-100.
 * - Stage 2 (Start 30): Maps Global 30-100 to Local 0-100.
 * - etc.
 */
export const calculateStageBrightness = (
  globalBrightness: number, // 0-100
  stage: StageConfig
): number => {
  const min = stage.startPercentage;
  const max = 100;
  
  // If global brightness is below the activation threshold, the light is off
  if (globalBrightness <= min) {
    return 0;
  }

  // Calculate linear progress within the active range (0.0 to 1.0)
  // Example: Breakpoint 30, Global 65. Range 70. Progress 35. Ratio 0.5.
  const range = max - min;
  const progress = (globalBrightness - min) / range;
  
  // Clamp just in case
  const clampedProgress = Math.min(Math.max(progress, 0), 1);

  // Apply Curve
  let curvedValue = clampedProgress;
  
  switch (stage.curve) {
    case CurveType.Quadratic:
      curvedValue = Math.pow(clampedProgress, 2);
      break;
    case CurveType.Cubic:
      curvedValue = Math.pow(clampedProgress, 3);
      break;
    case CurveType.SquareRoot:
      curvedValue = Math.sqrt(clampedProgress);
      break;
    case CurveType.CubeRoot:
      curvedValue = Math.cbrt(clampedProgress);
      break;
    case CurveType.Linear:
    default:
      curvedValue = clampedProgress;
      break;
  }

  // Convert back to 0-100 integer for display/usage
  return Math.round(curvedValue * 100);
};

export const getStageColor = (id: number): string => {
    switch(id) {
        case 1: return '#fbbf24'; // Amber-400
        case 2: return '#38bdf8'; // Sky-400
        case 3: return '#a78bfa'; // Violet-400
        case 4: return '#f472b6'; // Pink-400
        default: return '#94a3b8';
    }
}