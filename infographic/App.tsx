import React, { useState, useCallback, useRef } from 'react';
import { toPng } from 'html-to-image';
import { StageConfig, DEFAULT_STAGES, StageState, CurveType } from './types';
import { calculateStageBrightness } from './utils/calculations';
import { HouseVisual } from './components/HouseVisual';
import { StageChart } from './components/StageChart';
import { CurveSelector } from './components/CurveSelector';
import { Download, Lightbulb, Info, Sliders, Github } from 'lucide-react';

function App() {
  const [globalBrightness, setGlobalBrightness] = useState<number>(45);
  const [stagesConfig, setStagesConfig] = useState<StageConfig[]>(DEFAULT_STAGES);
  const captureRef = useRef<HTMLDivElement>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Calculate current state of all stages
  const currentStages: StageState[] = stagesConfig.map(config => ({
    config,
    isActive: globalBrightness > config.startPercentage,
    localBrightness: calculateStageBrightness(globalBrightness, config)
  }));

  const handleCurveChange = (id: number, curve: CurveType) => {
    setStagesConfig(prev => prev.map(s => s.id === id ? { ...s, curve } : s));
  };

  const handleExport = useCallback(async () => {
    if (captureRef.current === null) return;
    
    setIsExporting(true);
    try {
        const dataUrl = await toPng(captureRef.current, { 
            cacheBust: true, 
            backgroundColor: '#020617', // slate-950
            pixelRatio: 2 
        });
        const link = document.createElement('a');
        link.download = 'combined-lights-config.png';
        link.href = dataUrl;
        link.click();
    } catch (err) {
        console.error('Failed to export image', err);
    } finally {
        setIsExporting(false);
    }
  }, [captureRef]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 sm:p-6 font-sans selection:bg-amber-500/30 selection:text-amber-200">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex justify-between items-center pb-6 border-b border-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-900 rounded-lg ring-1 ring-white/10 shadow-lg">
                <Lightbulb className="w-5 h-5 text-amber-400" />
            </div>
            <div>
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white">Combined Lights</h1>
                <p className="text-slate-500 text-xs font-medium">Integration Helper</p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
             <a 
              href="https://github.com/recallfx/combined_lights"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-900 rounded-lg transition-all"
             >
               <Github className="w-4 h-4" />
               <span>GitHub</span>
             </a>
             <a 
              href="https://github.com/recallfx/combined_lights"
              target="_blank"
              rel="noopener noreferrer"
              className="sm:hidden p-2 text-slate-400 hover:text-white"
             >
               <Github className="w-5 h-5" />
             </a>

            <button 
                onClick={handleExport}
                disabled={isExporting}
                className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 hover:border-amber-500/30 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed text-amber-200/90 hover:text-amber-100"
            >
                <Download className="w-3.5 h-3.5" />
                {isExporting ? 'Saving...' : 'Export'}
            </button>
          </div>
        </header>

        {/* Main Content Area */}
        <div ref={captureRef} className="space-y-8">
            
            {/* Hero Control: Global Brightness */}
            <div className="bg-slate-900/40 p-6 sm:p-8 rounded-2xl border border-slate-800/80 shadow-sm backdrop-blur-sm relative overflow-hidden group">
                
                <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-800/50 rounded-lg">
                            <Sliders className="w-5 h-5 text-amber-400" />
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-slate-200 uppercase tracking-wide mb-0.5">Master Brightness</label>
                            <div className="text-xs text-slate-500">Control the global input level</div>
                        </div>
                    </div>
                    <div className="flex items-baseline gap-1">
                        <span className="text-5xl font-bold text-white tabular-nums tracking-tight leading-none">{globalBrightness}</span>
                        <span className="text-lg text-slate-500 font-medium">%</span>
                    </div>
                </div>
                
                <div className="relative h-12 w-full flex items-center px-1">
                    {/* Track Background */}
                    <div className="absolute inset-x-0 h-4 bg-slate-800/50 rounded-full overflow-hidden border border-slate-700/50">
                       <div 
                            className="h-full bg-gradient-to-r from-amber-900/20 to-amber-500/20 transition-all duration-75 ease-out origin-left"
                            style={{ width: `${globalBrightness}%` }}
                       />
                    </div>
                    
                    {/* Progress Fill */}
                    <div 
                        className="absolute inset-x-0 mx-1 h-2 top-1/2 -translate-y-1/2 pointer-events-none"
                    >
                        <div 
                            className="h-full bg-gradient-to-r from-amber-600 to-amber-400 rounded-full shadow-[0_0_20px_rgba(251,191,36,0.4)] transition-all duration-75 ease-out"
                            style={{ width: `${globalBrightness}%` }}
                        />
                    </div>

                    {/* Slider Input */}
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={globalBrightness}
                        onChange={(e) => setGlobalBrightness(parseInt(e.target.value))}
                        className="absolute w-full opacity-0 cursor-pointer h-12 z-20"
                        aria-label="Global brightness slider"
                    />

                    {/* Thumb */}
                    <div 
                         className="absolute w-7 h-7 bg-slate-100 border-[3px] border-amber-500 rounded-full shadow-xl pointer-events-none z-10 transition-all duration-75 ease-out flex items-center justify-center"
                         style={{ left: `calc(${globalBrightness}% - 14px)` }}
                    >
                        <div className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
                    </div>
                </div>

                {/* Scale Markers */}
                <div className="flex justify-between text-[10px] font-medium text-slate-600 mt-2 font-mono px-2 select-none">
                    {[0, 30, 60, 90, 100].map(mark => (
                        <span key={mark} className="relative flex flex-col items-center gap-1">
                            <span className="w-px h-1.5 bg-slate-700/50"></span>
                            {mark}%
                        </span>
                    ))}
                </div>
            </div>

            {/* Visualization & Chart Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
                {/* House Visualization */}
                <div className="space-y-4">
                    <div className="flex items-center gap-2 px-1">
                        <div className="h-1 w-1 rounded-full bg-amber-500"></div>
                        <h2 className="text-xs uppercase tracking-wider font-bold text-slate-400">Zone Visualizer</h2>
                    </div>
                    <HouseVisual stages={currentStages} />
                </div>

                {/* Chart */}
                <div className="space-y-4 flex flex-col">
                    <div className="flex items-center gap-2 px-1">
                        <div className="h-1 w-1 rounded-full bg-blue-500"></div>
                        <h2 className="text-xs uppercase tracking-wider font-bold text-slate-400">Response Curves</h2>
                    </div>
                    <div className="flex-1 min-h-[300px] bg-slate-900/20 rounded-xl border border-slate-800/50 p-1">
                        <StageChart currentGlobalBrightness={globalBrightness} stages={stagesConfig} />
                    </div>
                </div>
            </div>

             {/* Configuration Cards */}
             <div className="pt-4">
                <div className="flex items-center gap-2 mb-6 px-1">
                    <div className="h-1 w-1 rounded-full bg-purple-500"></div>
                    <h2 className="text-xs uppercase tracking-wider font-bold text-slate-400">Stage Configuration</h2>
                    <div className="h-px flex-1 bg-slate-800/50 ml-2"></div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {stagesConfig.map(stage => (
                        <CurveSelector 
                        key={stage.id} 
                        stage={stage} 
                        onChange={handleCurveChange} 
                        />
                    ))}
                </div>
            </div>
        </div>
        
        {/* Footer */}
        <footer className="pt-8 border-t border-slate-800/50 flex flex-col md:flex-row justify-between items-center gap-6 text-slate-500 text-xs pb-8">
            <div className="flex items-center gap-2 bg-slate-900/50 px-3 py-2 rounded-full border border-slate-800">
                <Info className="w-3.5 h-3.5 text-amber-500/70" />
                <span>Tip: Quadratic curves provide smoother transitions for low-light scenes.</span>
            </div>
            
            <div className="flex items-center gap-6">
                <a href="https://github.com/recallfx/combined_lights" target="_blank" rel="noopener noreferrer" className="hover:text-amber-400 transition-colors flex items-center gap-1.5">
                    <Github className="w-3.5 h-3.5" />
                    <span>View Integration on GitHub</span>
                </a>
                <span className="text-slate-700">•</span>
                <p>© {new Date().getFullYear()} Combined Lights</p>
            </div>
        </footer>
      </div>
    </div>
  );
}

export default App;