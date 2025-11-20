export enum CurveType {
  Linear = 'Linear',
  Quadratic = 'Quadratic',
  Cubic = 'Cubic',
  SquareRoot = 'SquareRoot',
  CubeRoot = 'CubeRoot'
}

export interface StageConfig {
  id: number;
  name: string;
  startPercentage: number; // Breakpoint (0, 30, 60, 90)
  curve: CurveType;
  description: string;
  icon: string; // Just a string identifier for the icon
}

export interface StageState {
  config: StageConfig;
  localBrightness: number; // 0-100
  isActive: boolean;
}

export const DEFAULT_STAGES: StageConfig[] = [
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