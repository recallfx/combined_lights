/**
 * Curve types for brightness calculation.
 */
export const CurveType = {
    Linear: 'Linear',
    Quadratic: 'Quadratic',
    Cubic: 'Cubic',
    SquareRoot: 'SquareRoot',
    CubeRoot: 'CubeRoot'
};

/**
 * Curve options for UI dropdown.
 */
export const CURVE_OPTIONS = [
    { value: CurveType.Cubic, label: "Ease-In Strong" },
    { value: CurveType.Quadratic, label: "Ease-In" },
    { value: CurveType.Linear, label: "Linear" },
    { value: CurveType.SquareRoot, label: "Ease-Out" },
    { value: CurveType.CubeRoot, label: "Ease-Out Strong" },
];

/**
 * Default stage configuration.
 */
export const DEFAULT_STAGES = [
    {
        id: 1,
        name: "Stage 1 - Ambient",
        startPercentage: 0,
        curve: CurveType.Quadratic,
        description: "Active from 0%. Creates the base layer.",
        icon: "strip"
    },
    {
        id: 2,
        name: "Stage 2 - Task",
        startPercentage: 30,
        curve: CurveType.Linear,
        description: "Activates at 30%. Adds functional light.",
        icon: "lamp"
    },
    {
        id: 3,
        name: "Stage 3 - General",
        startPercentage: 60,
        curve: CurveType.Linear,
        description: "Activates at 60%. Fills the room.",
        icon: "ceiling"
    },
    {
        id: 4,
        name: "Stage 4 - Boost",
        startPercentage: 90,
        curve: CurveType.Linear,
        description: "Activates at 90%. Maximum brightness.",
        icon: "spot"
    }
];

/**
 * Calculates the local brightness for a specific stage based on global brightness.
 */
export function calculateStageBrightness(globalBrightness, stage) {
    const min = stage.startPercentage;
    const max = 100;
    
    if (globalBrightness <= min) {
        return 0;
    }

    const range = max - min;
    const progress = (globalBrightness - min) / range;
    const clampedProgress = Math.min(Math.max(progress, 0), 1);

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

    // Return raw value for smooth curves, round only for display
    return curvedValue * 100;
}

/**
 * Get stage color by ID.
 */
export function getStageColor(id) {
    switch(id) {
        case 1: return '#fbbf24'; // Amber-400
        case 2: return '#38bdf8'; // Sky-400
        case 3: return '#a78bfa'; // Violet-400
        case 4: return '#f472b6'; // Pink-400
        default: return '#94a3b8';
    }
}

/**
 * Generate chart data points.
 */
export function generateChartData(stages) {
    const points = [];
    // Use step of 0.5 for very smooth curves (201 points)
    for (let i = 0; i <= 100; i += 0.5) {
        const point = { global: i };
        stages.forEach(stage => {
            point[stage.id] = calculateStageBrightness(i, stage);
        });
        points.push(point);
    }
    return points;
}
