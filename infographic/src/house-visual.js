/**
 * House visualization component with 4 stage zones.
 */

import { LitElement, html, css, svg } from './lib.js';
import { getStageColor } from './calculations.js';

export class HouseVisual extends LitElement {
    static properties = {
        stages: { type: Array }
    };
    
    static styles = css`
        :host {
            display: block;
        }
        
        .house-container {
            position: relative;
            width: 100%;
            height: 300px;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            border: 1px solid #1e293b;
            overflow: hidden;
            display: flex;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            ring: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .stage-zone {
            flex: 1;
            position: relative;
            border-right: 1px solid rgba(30, 41, 59, 0.6);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            transition: all 0.5s;
        }
        
        .stage-zone:last-child {
            border-right: none;
        }
        
        .light-gradient {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            transition: opacity 0.15s;
            filter: blur(24px);
        }
        
        .light-beam {
            position: absolute;
            top: 40px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 50% 0%, rgba(251, 191, 36, 0.6) 0%, rgba(251, 191, 36, 0.1) 40%, transparent 70%);
            transform-origin: top center;
            pointer-events: none;
            mix-blend-mode: screen;
            transition: opacity 0.15s;
        }
        
        .fixture-icon {
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) scale(0.9);
            z-index: 10;
            transform-origin: top;
        }
        
        .room-content {
            position: relative;
            z-index: 10;
            padding: 16px;
            padding-bottom: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        
        .brightness-value {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 2px;
            font-variant-numeric: tabular-nums;
            color: white;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
            transition: opacity 0.2s;
        }
        
        .progress-track {
            margin-top: 12px;
            height: 4px;
            width: 100%;
            max-width: 60%;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 9999px;
            overflow: hidden;
            backdrop-filter: blur(4px);
        }
        
        .progress-fill {
            height: 100%;
            transition: width 0.1s linear;
            border-radius: 9999px;
        }
        
        .floor-reflection {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 40px;
            transition: opacity 0.2s;
        }
    `;
    
    constructor() {
        super();
        this.stages = [];
    }
    
    _renderFixtureIcon(type, opacity, color) {
        const isActive = opacity > 0;
        const stroke = isActive ? '#e2e8f0' : '#334155';
        const fill = isActive ? color : 'transparent';
        
        return svg`
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                ${type === 'strip' ? svg`
                    <rect x="4" y="2" width="16" height="4" rx="1" fill="${fill}" stroke="${stroke}" stroke-width="1.5" fill-opacity="0.8" />
                ` : ''}
                ${type === 'lamp' ? svg`
                    <path d="M8 2H16L18 10H6L8 2Z" fill="${fill}" stroke="${stroke}" stroke-width="1.5" fill-opacity="0.6" />
                    <line x1="12" y1="10" x2="12" y2="16" stroke="${stroke}" stroke-width="1.5" />
                    <path d="M9 16H15" stroke="${stroke}" stroke-width="1.5" />
                ` : ''}
                ${type === 'ceiling' ? svg`
                    <path d="M6 2C6 2 6 8 12 8C18 8 18 2 18 2" fill="${fill}" stroke="${stroke}" stroke-width="1.5" fill-opacity="0.8" />
                ` : ''}
                ${type === 'spot' ? svg`
                    <rect x="10" y="2" width="4" height="6" fill="${stroke}" />
                    <path d="M7 8H17L15 14H9L7 8Z" fill="${fill}" stroke="${stroke}" stroke-width="1.5" fill-opacity="0.6" />
                ` : ''}
            </svg>
        `;
    }
    
    render() {
        return html`
            <div class="house-container">
                ${this.stages.map(stage => {
                    const brightness = stage.localBrightness;
                    const brightnessDisplay = Math.round(brightness);
                    const color = getStageColor(stage.config.id);
                    const opacity = brightness / 100;
                    
                    return html`
                        <div class="stage-zone">
                            <!-- Light Source Gradient -->
                            <div 
                                class="light-gradient"
                                style="background: radial-gradient(circle at 50% 0%, ${color} 0%, transparent 70%); opacity: ${opacity * 0.7}"
                            ></div>
                            
                            <!-- Hard Beam Effect -->
                            <div 
                                class="light-beam"
                                style="opacity: ${opacity * 0.8}"
                            ></div>
                            
                            <!-- Light Fixture Icon -->
                            <div class="fixture-icon">
                                ${this._renderFixtureIcon(stage.config.icon, opacity, color)}
                            </div>
                            
                            <!-- Room Content -->
                            <div class="room-content">
                                <div class="brightness-value" style="opacity: ${Math.max(0.3, opacity)}">
                                    ${brightnessDisplay}%
                                </div>
                                
                                <div class="progress-track">
                                    <div 
                                        class="progress-fill"
                                        style="width: ${brightness}%; background-color: ${color}; box-shadow: 0 0 8px ${color}"
                                    ></div>
                                </div>
                            </div>
                            
                            <!-- Floor Reflection -->
                            <div 
                                class="floor-reflection"
                                style="background: linear-gradient(to top, ${color}33, transparent); opacity: ${opacity}"
                            ></div>
                        </div>
                    `;
                })}
            </div>
        `;
    }
}

customElements.define('house-visual', HouseVisual);
