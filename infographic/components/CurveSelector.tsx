import React from 'react';
import { CurveType, StageConfig } from '../types';
import { getStageColor } from '../utils/calculations';
import { Lightbulb, Lamp, ArrowUpToLine, Sun } from 'lucide-react';

interface CurveSelectorProps {
  stage: StageConfig;
  onChange: (id: number, curve: CurveType) => void;
}

const CURVE_OPTIONS = [
  { value: CurveType.Cubic, label: "Ease-In Strong" },
  { value: CurveType.Quadratic, label: "Ease-In" },
  { value: CurveType.Linear, label: "Linear" },
  { value: CurveType.SquareRoot, label: "Ease-Out" },
  { value: CurveType.CubeRoot, label: "Ease-Out Strong" },
];

export const CurveSelector: React.FC<CurveSelectorProps> = ({ stage, onChange }) => {
  const color = getStageColor(stage.id);
  
  const Icon = () => {
    const props = { size: 16, color: color };
    switch (stage.icon) {
        case 'strip': return <ArrowUpToLine {...props} />;
        case 'lamp': return <Lamp {...props} />;
        case 'ceiling': return <Lightbulb {...props} />;
        case 'spot': return <Sun {...props} />;
        default: return <Lightbulb {...props} />;
    }
  };

  return (
    <div className="flex flex-col p-3 sm:p-4 bg-slate-900/50 rounded-xl border border-slate-800/50 hover:border-slate-700 transition-all duration-200 relative group overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full transition-opacity duration-200" style={{ backgroundColor: color, opacity: 0.6 }}></div>
      
      <div className="flex justify-between items-start mb-3 pl-2">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-slate-800/80 rounded-md ring-1 ring-slate-700/50">
             <Icon />
          </div>
          <div>
              <h3 className="font-semibold text-slate-200 text-xs sm:text-sm leading-none mb-1">{stage.name}</h3>
              <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wider leading-none">Starts @ {stage.startPercentage}%</p>
          </div>
        </div>
      </div>
      
      <div className="pl-2 mt-auto">
        <div className="relative group/select">
            <select 
            className="w-full bg-slate-950 text-[11px] sm:text-xs font-medium text-slate-300 border border-slate-700 rounded-lg pl-2 pr-6 py-1.5 appearance-none focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all cursor-pointer hover:border-slate-600"
            value={stage.curve}
            onChange={(e) => onChange(stage.id, e.target.value as CurveType)}
            >
            {CURVE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
            </select>
            <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-3 h-3 text-slate-600 group-hover/select:text-slate-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
        </div>
      </div>
    </div>
  );
};