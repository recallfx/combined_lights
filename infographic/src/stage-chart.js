/**
 * Stage chart component using SVG (no external charting library).
 */

import { LitElement, html, css, svg } from './lib.js';
import { getStageColor, generateChartData } from './calculations.js';

export class StageChart extends LitElement {
    static properties = {
        stages: { type: Array },
        currentGlobalBrightness: { type: Number }
    };
    
    static styles = css`
        :host {
            display: block;
            width: 100%;
        }
        
        .chart-container {
            width: 100%;
            height: 260px;
            padding: 16px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }
        
        @media (min-width: 1025px) {
            .chart-container {
                height: 300px;
            }
        }
        
        @media (max-width: 640px) {
            .chart-container {
                height: 200px;
                padding: 12px;
            }
        }
        
        .chart-area {
            flex: 1;
            display: flex;
            min-height: 0;
        }
        
        .y-axis-labels {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding-right: 8px;
            padding-top: 4px;
            padding-bottom: 4px;
        }
        
        .y-label {
            font-size: 11px;
            color: #64748b;
            font-family: ui-monospace, monospace;
            text-align: right;
            line-height: 1;
        }
        
        .chart-wrapper {
            flex: 1;
            position: relative;
            min-height: 0;
            display: flex;
            flex-direction: column;
        }
        
        .svg-wrapper {
            flex: 1;
            min-height: 0;
        }
        
        svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        
        .x-axis-labels {
            position: relative;
            height: 20px;
            padding-top: 6px;
        }
        
        .x-label {
            position: absolute;
            font-size: 11px;
            color: #64748b;
            font-family: ui-monospace, monospace;
            transform: translateX(-50%);
        }
        
        .axis-line {
            stroke: #334155;
            stroke-width: 1;
            vector-effect: non-scaling-stroke;
        }
        
        .grid-line {
            stroke: #1e293b;
            stroke-width: 1;
            stroke-dasharray: 4 4;
            stroke-opacity: 0.5;
            vector-effect: non-scaling-stroke;
        }
        
        .breakpoint-line {
            stroke: #1e293b;
            stroke-width: 1;
            stroke-dasharray: 3 3;
            vector-effect: non-scaling-stroke;
        }
        
        .current-line {
            stroke: #cbd5e1;
            stroke-width: 1;
            stroke-dasharray: 2 2;
            opacity: 0.5;
            vector-effect: non-scaling-stroke;
        }
        
        .stage-path {
            fill: none;
            stroke-width: 2;
            shape-rendering: geometricPrecision;
            vector-effect: non-scaling-stroke;
        }
        
        .legend {
            display: flex;
            gap: 16px;
            justify-content: center;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: #94a3b8;
        }
        
        .legend-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
    `;
    
    constructor() {
        super();
        this.stages = [];
        this.currentGlobalBrightness = 0;
    }
    
    _generatePath(data, stageId) {
        const points = data.map((d) => {
            const x = (d.global / 100) * 100;
            const y = 100 - (d[stageId] / 100) * 100;
            return x + ',' + y;
        });
        
        return 'M ' + points.join(' L ');
    }
    
    render() {
        const data = generateChartData(this.stages);
        
        const xLabels = [0, 30, 60, 90, 100];
        const yLabels = [100, 75, 50, 25, 0];
        const breakpoints = [30, 60, 90];
        const currentXPct = this.currentGlobalBrightness;
        
        return html`
            <div class="chart-container">
                <div class="chart-area">
                    <div class="y-axis-labels">
                        ${yLabels.map(y => html`<span class="y-label">${y}</span>`)}
                    </div>
                    
                    <div class="chart-wrapper">
                        <div class="svg-wrapper">
                            <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                                ${[25, 50, 75, 100].map(y => {
                                    const yPos = 100 - y;
                                    return svg`<line class="grid-line" x1="0" y1="${yPos}" x2="100" y2="${yPos}" />`;
                                })}
                                
                                ${breakpoints.map(bp => svg`<line class="breakpoint-line" x1="${bp}" y1="0" x2="${bp}" y2="100" />`)}
                                
                                <line class="current-line" x1="${currentXPct}" y1="0" x2="${currentXPct}" y2="100" />
                                
                                <line class="axis-line" x1="0" y1="100" x2="100" y2="100" />
                                <line class="axis-line" x1="0" y1="0" x2="0" y2="100" />
                                
                                ${this.stages.map(stage => svg`
                                    <path 
                                        class="stage-path" 
                                        d="${this._generatePath(data, stage.id)}"
                                        stroke="${getStageColor(stage.id)}"
                                    />
                                `)}
                            </svg>
                        </div>
                        
                        <div class="x-axis-labels">
                            ${xLabels.map(x => html`<span class="x-label" style="left: ${x}%">${x}</span>`)}
                        </div>
                    </div>
                </div>
                
                <div class="legend">
                    ${this.stages.map(stage => html`
                        <div class="legend-item">
                            <span class="legend-dot" style="background: ${getStageColor(stage.id)}"></span>
                            <span>${stage.name.split(' - ')[1] || stage.name}</span>
                        </div>
                    `)}
                </div>
            </div>
        `;
    }
}

customElements.define('stage-chart', StageChart);
