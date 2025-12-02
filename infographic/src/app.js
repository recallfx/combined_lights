/**
 * Combined Lights Infographic - Main App Component.
 * Lit-based version matching the original React UI.
 */

import { LitElement, html, css } from './lib.js';
import { DEFAULT_STAGES, calculateStageBrightness } from './calculations.js';
import './house-visual.js';
import './stage-chart.js';
import './curve-selector.js';

export class InfographicApp extends LitElement {
    static properties = {
        globalBrightness: { type: Number },
        stagesConfig: { type: Array }
    };
    
    static styles = css`
        :host {
            display: block;
            min-height: 100vh;
            background: #0f172a;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 24px;
        }
        
        .container {
            max-width: 1024px;
            margin: 0 auto;
        }
        
        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid rgba(30, 41, 59, 0.6);
            margin-bottom: 32px;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            padding: 8px;
            background: #1e293b;
            border-radius: 8px;
            box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .logo-icon svg {
            width: 20px;
            height: 20px;
            color: #fbbf24;
        }
        
        .header-title h1 {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            color: white;
        }
        
        .header-subtitle {
            font-size: 0.7rem;
            color: #64748b;
            font-weight: 500;
        }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .github-link {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            font-size: 0.75rem;
            font-weight: 500;
            color: #94a3b8;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
        }
        
        .github-link:hover {
            color: white;
            background: #1e293b;
        }
        
        .export-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.2);
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            color: rgba(253, 230, 138, 0.9);
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .export-btn:hover {
            background: rgba(245, 158, 11, 0.2);
            border-color: rgba(245, 158, 11, 0.3);
            color: #fef3c7;
        }
        
        /* Hero Control */
        .hero-control {
            background: rgba(30, 41, 59, 0.4);
            padding: 32px;
            border-radius: 16px;
            border: 1px solid rgba(51, 65, 85, 0.8);
            position: relative;
            overflow: hidden;
            margin-bottom: 32px;
        }
        
        .hero-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 32px;
        }
        
        .hero-label-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .hero-icon {
            padding: 8px;
            background: rgba(51, 65, 85, 0.5);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .hero-icon svg {
            width: 20px;
            height: 20px;
            color: #fbbf24;
        }
        
        .hero-label {
            font-size: 0.875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #e2e8f0;
            margin-bottom: 2px;
        }
        
        .hero-sublabel {
            font-size: 0.75rem;
            color: #64748b;
        }
        
        .hero-value {
            display: flex;
            align-items: baseline;
            gap: 4px;
        }
        
        .hero-value-number {
            font-size: 3rem;
            font-weight: 700;
            color: white;
            line-height: 1;
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.025em;
        }
        
        .hero-value-unit {
            font-size: 1.125rem;
            color: #64748b;
            font-weight: 500;
        }
        
        /* Slider */
        .slider-container {
            position: relative;
            height: 48px;
            display: flex;
            align-items: center;
            padding: 0 4px;
        }
        
        .slider-track-bg {
            position: absolute;
            left: 0;
            right: 0;
            height: 16px;
            background: rgba(51, 65, 85, 0.5);
            border-radius: 9999px;
            border: 1px solid rgba(71, 85, 105, 0.5);
            overflow: hidden;
        }
        
        .slider-track-fill {
            height: 100%;
            background: linear-gradient(to right, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.3));
            transition: width 0.075s ease-out;
        }
        
        .slider-progress {
            position: absolute;
            left: 4px;
            right: 4px;
            height: 8px;
            pointer-events: none;
        }
        
        .slider-progress-bar {
            height: 100%;
            background: linear-gradient(to right, #d97706, #f59e0b);
            border-radius: 9999px;
            box-shadow: 0 0 20px rgba(251, 191, 36, 0.4);
            transition: width 0.075s ease-out;
        }
        
        .slider-input {
            position: absolute;
            width: 100%;
            height: 48px;
            opacity: 0;
            cursor: pointer;
            z-index: 20;
        }
        
        .slider-thumb {
            position: absolute;
            width: 28px;
            height: 28px;
            background: #f1f5f9;
            border: 3px solid #f59e0b;
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            pointer-events: none;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: left 0.075s ease-out;
        }
        
        .slider-thumb-dot {
            width: 6px;
            height: 6px;
            background: #f59e0b;
            border-radius: 50%;
        }
        
        .slider-markers {
            position: relative;
            height: 24px;
            margin-top: 8px;
            font-size: 10px;
            font-weight: 500;
            color: #475569;
            font-family: ui-monospace, monospace;
            user-select: none;
        }
        
        .slider-marker {
            position: absolute;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            transform: translateX(-50%);
        }
        
        .slider-marker:first-child {
            transform: translateX(0);
        }
        
        .slider-marker:last-child {
            transform: translateX(-100%);
        }
        
        .slider-marker-tick {
            width: 1px;
            height: 6px;
            background: rgba(71, 85, 105, 0.5);
        }
        
        /* Grid Layout */
        .grid-2col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 32px;
        }
        
        @media (max-width: 1024px) {
            .grid-2col {
                grid-template-columns: 1fr;
            }
        }
        
        .grid-4col {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
        
        @media (max-width: 768px) {
            .grid-4col {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        /* Section Headers */
        .section {
            margin-bottom: 32px;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            padding-left: 4px;
        }
        
        .section-dot {
            width: 4px;
            height: 4px;
            border-radius: 50%;
        }
        
        .section-dot.amber { background: #f59e0b; }
        .section-dot.blue { background: #3b82f6; }
        .section-dot.purple { background: #a855f7; }
        
        .section-title {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
        }
        
        .section-line {
            flex: 1;
            height: 1px;
            background: rgba(51, 65, 85, 0.5);
            margin-left: 8px;
        }
        
        /* Chart Container */
        .chart-container {
            background: rgba(15, 23, 42, 0.2);
            border-radius: 12px;
            border: 1px solid rgba(51, 65, 85, 0.5);
            padding: 4px;
        }
        
        /* Footer */
        footer {
            padding-top: 32px;
            border-top: 1px solid rgba(51, 65, 85, 0.5);
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 24px;
            font-size: 0.75rem;
            color: #64748b;
        }
        
        .tip-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(15, 23, 42, 0.5);
            padding: 8px 12px;
            border-radius: 9999px;
            border: 1px solid #1e293b;
        }
        
        .tip-icon {
            color: rgba(245, 158, 11, 0.7);
        }
        
        .footer-links {
            display: flex;
            align-items: center;
            gap: 24px;
        }
        
        .footer-link {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #64748b;
            text-decoration: none;
            transition: color 0.2s;
        }
        
        .footer-link:hover {
            color: #fbbf24;
        }
        
        .footer-divider {
            color: #334155;
        }
    `;
    
    constructor() {
        super();
        this.globalBrightness = 45;
        this.stagesConfig = [...DEFAULT_STAGES];
    }
    
    get currentStages() {
        return this.stagesConfig.map(config => ({
            config,
            isActive: this.globalBrightness > config.startPercentage,
            localBrightness: calculateStageBrightness(this.globalBrightness, config)
        }));
    }
    
    _handleSliderChange(e) {
        this.globalBrightness = parseInt(e.target.value);
    }
    
    _handleCurveChange(e) {
        const { id, curve } = e.detail;
        this.stagesConfig = this.stagesConfig.map(s => 
            s.id === id ? { ...s, curve } : s
        );
    }
    
    _handleExport() {
        // Simple export - just log for now
        console.log('Export requested');
        alert('Export feature coming soon!');
    }
    
    render() {
        const markers = [0, 30, 60, 90, 100];
        
        return html`
            <div class="container">
                <!-- Header -->
                <header>
                    <div class="header-left">
                        <div class="logo-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M9 18h6"></path>
                                <path d="M10 22h4"></path>
                                <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"></path>
                            </svg>
                        </div>
                        <div class="header-title">
                            <h1>Combined Lights</h1>
                            <span class="header-subtitle">Integration Helper</span>
                        </div>
                    </div>
                    <div class="header-actions">
                        <a href="https://github.com/recallfx/ha-combined-lights" target="_blank" class="github-link">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                            <span>GitHub</span>
                        </a>
                        <button class="export-btn" @click=${this._handleExport}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Export
                        </button>
                    </div>
                </header>
                
                <!-- Hero Control: Master Brightness -->
                <div class="hero-control">
                    <div class="hero-header">
                        <div class="hero-label-group">
                            <div class="hero-icon">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="4" y1="21" x2="4" y2="14"></line>
                                    <line x1="4" y1="10" x2="4" y2="3"></line>
                                    <line x1="12" y1="21" x2="12" y2="12"></line>
                                    <line x1="12" y1="8" x2="12" y2="3"></line>
                                    <line x1="20" y1="21" x2="20" y2="16"></line>
                                    <line x1="20" y1="12" x2="20" y2="3"></line>
                                    <line x1="1" y1="14" x2="7" y2="14"></line>
                                    <line x1="9" y1="8" x2="15" y2="8"></line>
                                    <line x1="17" y1="16" x2="23" y2="16"></line>
                                </svg>
                            </div>
                            <div>
                                <div class="hero-label">Master Brightness</div>
                                <div class="hero-sublabel">Control the global input level</div>
                            </div>
                        </div>
                        <div class="hero-value">
                            <span class="hero-value-number">${this.globalBrightness}</span>
                            <span class="hero-value-unit">%</span>
                        </div>
                    </div>
                    
                    <div class="slider-container">
                        <div class="slider-track-bg">
                            <div class="slider-track-fill" style="width: ${this.globalBrightness}%"></div>
                        </div>
                        <div class="slider-progress">
                            <div class="slider-progress-bar" style="width: ${this.globalBrightness}%"></div>
                        </div>
                        <input 
                            type="range"
                            class="slider-input"
                            min="0" 
                            max="100" 
                            .value=${this.globalBrightness}
                            @input=${this._handleSliderChange}
                        />
                        <div class="slider-thumb" style="left: calc(${this.globalBrightness}% - 14px)">
                            <div class="slider-thumb-dot"></div>
                        </div>
                    </div>
                    
                    <div class="slider-markers">
                        ${markers.map(mark => html`
                            <div class="slider-marker" style="left: ${mark}%">
                                <div class="slider-marker-tick"></div>
                                <span>${mark}%</span>
                            </div>
                        `)}
                    </div>
                </div>
                
                <!-- Visualization Grid -->
                <div class="grid-2col">
                    <!-- House Visual -->
                    <div class="section">
                        <div class="section-header">
                            <div class="section-dot amber"></div>
                            <span class="section-title">Zone Visualizer</span>
                        </div>
                        <house-visual .stages=${this.currentStages}></house-visual>
                    </div>
                    
                    <!-- Chart -->
                    <div class="section">
                        <div class="section-header">
                            <div class="section-dot blue"></div>
                            <span class="section-title">Response Curves</span>
                        </div>
                        <div class="chart-container">
                            <stage-chart 
                                .stages=${this.stagesConfig}
                                .currentGlobalBrightness=${this.globalBrightness}
                            ></stage-chart>
                        </div>
                    </div>
                </div>
                
                <!-- Stage Configuration -->
                <div class="section">
                    <div class="section-header">
                        <div class="section-dot purple"></div>
                        <span class="section-title">Stage Configuration</span>
                        <div class="section-line"></div>
                    </div>
                    <div class="grid-4col" @curve-change=${this._handleCurveChange}>
                        ${this.stagesConfig.map(stage => html`
                            <curve-selector .stage=${stage}></curve-selector>
                        `)}
                    </div>
                </div>
                
                <!-- Footer -->
                <footer>
                    <div class="tip-badge">
                        <svg class="tip-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                        <span>Tip: Quadratic curves provide smoother transitions for low-light scenes.</span>
                    </div>
                    
                    <div class="footer-links">
                        <a href="https://github.com/recallfx/ha-combined-lights" target="_blank" class="footer-link">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                            <span>View Integration on GitHub</span>
                        </a>
                        <span class="footer-divider">•</span>
                        <span>© ${new Date().getFullYear()} Combined Lights</span>
                    </div>
                </footer>
            </div>
        `;
    }
}

customElements.define('infographic-app', InfographicApp);
