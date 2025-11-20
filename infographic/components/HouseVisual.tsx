import React from 'react';
import { StageState } from '../types';
import { getStageColor } from '../utils/calculations';

interface HouseVisualProps {
  stages: StageState[];
}

export const HouseVisual: React.FC<HouseVisualProps> = ({ stages }) => {
  return (
    <div className="relative w-full h-64 sm:h-72 lg:h-[300px] bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden flex shadow-2xl ring-1 ring-white/5">
      {/* This represents a cross-section of a house with 4 distinct zones */}
      
      {stages.map((stage, index) => {
        const brightness = stage.localBrightness;
        const color = getStageColor(stage.config.id);
        const opacity = brightness / 100;
        
        return (
          <div key={stage.config.id} className="flex-1 relative border-r border-slate-800/60 last:border-r-0 flex flex-col justify-end group transition-all duration-500">
            {/* Light Source Gradient */}
            <div 
              className="absolute top-0 left-0 right-0 h-full transition-opacity duration-150"
              style={{
                background: `radial-gradient(circle at 50% 0%, ${color} 0%, transparent 70%)`,
                opacity: opacity * 0.7,
                filter: 'blur(24px)'
              }}
            />
            
            {/* Hard Beam Effect */}
            <div 
               className="absolute top-10 left-1/2 -translate-x-1/2 w-full h-full light-beam transition-opacity duration-150 mix-blend-screen"
               style={{ opacity: opacity * 0.8 }}
            />

            {/* Light Fixture Icon */}
            <div className="absolute top-5 left-1/2 -translate-x-1/2 z-10 transform scale-75 sm:scale-90 transition-transform origin-top">
               <LightFixtureIcon type={stage.config.icon} opacity={opacity} color={color} />
            </div>

            {/* Room Content (Silhouette) */}
            <div className="relative z-10 p-2 sm:p-4 pb-3 sm:pb-5 flex flex-col items-center w-full">
                <div className="text-xl sm:text-2xl font-bold mb-0.5 tabular-nums text-white drop-shadow-md" style={{ opacity: Math.max(0.3, opacity) }}>
                    {brightness}%
                </div>
                
                <div className="mt-3 h-1 w-full max-w-[60%] bg-slate-800/80 rounded-full overflow-hidden backdrop-blur-sm">
                    <div 
                        className="h-full transition-all duration-100 ease-linear shadow-[0_0_8px_currentColor]" 
                        style={{ width: `${brightness}%`, backgroundColor: color, color: color }} 
                    />
                </div>
            </div>
            
            {/* Floor Reflection */}
            <div 
                className="absolute bottom-0 left-0 right-0 h-8 sm:h-10 transition-opacity duration-200"
                style={{ 
                    background: `linear-gradient(to top, ${color}33, transparent)`,
                    opacity: opacity
                }}
            />
          </div>
        );
      })}
    </div>
  );
};

const LightFixtureIcon = ({ type, opacity, color }: { type: string, opacity: number, color: string }) => {
  const isActive = opacity > 0;
  
  // When active, use white stroke for contrast against the glow, else dark slate
  const stroke = isActive ? '#e2e8f0' : '#334155'; 
  const fill = isActive ? color : 'transparent';
  
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="transition-colors duration-300">
       {type === 'strip' && (
          <rect x="4" y="2" width="16" height="4" rx="1" fill={fill} stroke={stroke} strokeWidth="1.5" fillOpacity={0.8} />
       )}
       {type === 'lamp' && (
           <>
            <path d="M8 2H16L18 10H6L8 2Z" fill={fill} stroke={stroke} strokeWidth="1.5" fillOpacity={0.6} />
            <line x1="12" y1="10" x2="12" y2="16" stroke={stroke} strokeWidth="1.5" />
            <path d="M9 16H15" stroke={stroke} strokeWidth="1.5" />
           </>
       )}
       {type === 'ceiling' && (
           <path d="M6 2C6 2 6 8 12 8C18 8 18 2 18 2" fill={fill} stroke={stroke} strokeWidth="1.5" fillOpacity={0.8} />
       )}
       {type === 'spot' && (
           <>
            <rect x="10" y="2" width="4" height="6" fill={stroke} />
            <path d="M7 8H17L15 14H9L7 8Z" fill={fill} stroke={stroke} strokeWidth="1.5" fillOpacity={0.6} />
           </>
       )}
    </svg>
  )
}