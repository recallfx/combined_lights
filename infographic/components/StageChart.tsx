import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea
} from 'recharts';
import { StageConfig } from '../types';
import { calculateStageBrightness, getStageColor } from '../utils/calculations';

interface StageChartProps {
  currentGlobalBrightness: number;
  stages: StageConfig[];
}

export const StageChart: React.FC<StageChartProps> = ({ currentGlobalBrightness, stages }) => {
  
  // Generate data points for the chart
  const data = useMemo(() => {
    const points = [];
    for (let i = 0; i <= 100; i += 2) {
      const point: any = { global: i };
      stages.forEach(stage => {
        point[stage.id] = calculateStageBrightness(i, stage);
      });
      points.push(point);
    }
    return points;
  }, [stages]);

  return (
    <div className="w-full h-full p-2 sm:p-4 text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 10, bottom: 5, left: -15 }}>
          <CartesianGrid strokeDasharray="5 5" stroke="#1e293b" vertical={false} strokeOpacity={0.5} />
          <XAxis 
            dataKey="global" 
            stroke="#475569" 
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#334155' }}
            minTickGap={20}
          />
          <YAxis 
            stroke="#475569"
            tick={{ fontSize: 10, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            width={30}
          />
          <Tooltip 
            contentStyle={{ 
                backgroundColor: '#0f172a', 
                borderColor: '#1e293b', 
                borderRadius: '8px', 
                color: '#f8fafc', 
                fontSize: '12px', 
                padding: '8px 12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)' 
            }}
            itemStyle={{ padding: 0, paddingBottom: 2 }}
            cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4', opacity: 0.5 }}
          />
          
          {/* Breakpoint Reference Lines */}
          {[30, 60, 90].map(bp => (
            <ReferenceLine key={bp} x={bp} stroke="#1e293b" strokeDasharray="4 4" />
          ))}

          {/* Current Global Position Indicator */}
          <ReferenceLine x={currentGlobalBrightness} stroke="#cbd5e1" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />
          <ReferenceArea x1={currentGlobalBrightness-1} x2={currentGlobalBrightness+1} fill="#fff" opacity={0.03} />

          {/* Stage Lines */}
          {stages.map(stage => (
            <Line 
              key={stage.id}
              type="monotone"
              dataKey={stage.id}
              stroke={getStageColor(stage.id)}
              strokeWidth={2}
              dot={false}
              name={stage.name}
              animationDuration={300}
              activeDot={{ r: 4, strokeWidth: 0, fill: getStageColor(stage.id) }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};