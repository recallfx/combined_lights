/**
 * Combined Lights simulation UI.
 * Styled to match the infographic visualizer (dark slate + amber).
 */

import { LitElement, html, css } from '../lib.js';

// Stage colors matching infographic
const STAGE_COLORS = ['#f59e0b', '#3b82f6', '#a855f7', '#22c55e'];

export class CombinedLightsApp extends LitElement {
    static properties = {
        connected: { type: Boolean },
        state: { type: Object },
        _selectedLight: { type: Object, state: true },
        _dialogBrightness: { type: Number, state: true },
    };
    
    static styles = css`
        :host {
            display: block;
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
        }
        
        /* Header */
        header {
            background: transparent;
            border-bottom: 1px solid rgba(51, 65, 85, 0.6);
            padding: 1.25rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .logo-icon {
            width: 36px;
            height: 36px;
            background: #1e293b;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 0 0 1px rgba(255,255,255,0.1);
        }
        
        .header-title {
            display: flex;
            flex-direction: column;
        }
        
        h1 { 
            margin: 0; 
            font-size: 1.125rem; 
            font-weight: 700; 
            color: white;
            letter-spacing: -0.025em;
        }
        
        .header-subtitle {
            font-size: 0.7rem;
            color: #64748b;
            font-weight: 500;
        }
        
        .header-right {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }
        
        .status-badge {
            padding: 0.375rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.7rem;
            font-weight: 500;
        }
        .status-badge.connected { 
            background: rgba(34, 197, 94, 0.1); 
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .status-badge.disconnected { 
            background: rgba(239, 68, 68, 0.1); 
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        /* Main Content */
        main {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            padding: 2rem 1.5rem;
            max-width: 900px;
            margin: 0 auto;
        }
        
        /* Hero Section - Master Brightness */
        .hero-control {
            background: rgba(30, 41, 59, 0.4);
            border-radius: 16px;
            border: 1px solid rgba(51, 65, 85, 0.8);
            padding: 1.5rem 2rem;
            position: relative;
            overflow: hidden;
        }
        
        .hero-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 1.5rem;
        }
        
        .hero-label-group {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .hero-icon {
            width: 36px;
            height: 36px;
            background: rgba(51, 65, 85, 0.5);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }
        
        .hero-label {
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #e2e8f0;
        }
        
        .hero-sublabel {
            font-size: 0.7rem;
            color: #64748b;
            margin-top: 0.125rem;
        }
        
        .hero-value {
            display: flex;
            align-items: baseline;
            gap: 0.25rem;
        }
        
        .hero-value-number {
            font-size: 3rem;
            font-weight: 700;
            color: white;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }
        
        .hero-value-unit {
            font-size: 1.125rem;
            color: #64748b;
            font-weight: 500;
        }
        
        /* Custom Slider */
        .slider-track-container {
            position: relative;
            height: 48px;
            display: flex;
            align-items: center;
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
            transition: width 0.1s ease-out;
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
            box-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
            transition: width 0.1s ease-out;
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
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            pointer-events: none;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: left 0.1s ease-out;
        }
        
        .slider-thumb-dot {
            width: 6px;
            height: 6px;
            background: #f59e0b;
            border-radius: 50%;
        }
        
        .slider-markers {
            position: relative;
            height: 20px;
            margin-top: 0.5rem;
            font-size: 0.625rem;
            font-weight: 500;
            color: #475569;
            font-family: ui-monospace, monospace;
        }
        
        .slider-marker {
            position: absolute;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.25rem;
            transform: translateX(-50%);
        }
        
        .slider-marker-tick {
            width: 1px;
            height: 6px;
            background: rgba(71, 85, 105, 0.5);
        }
        
        /* Section Header */
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
            padding-left: 0.25rem;
        }
        
        .section-dot {
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: #f59e0b;
        }
        
        .section-title {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
        }
        
        /* Stage Cards */
        .lights-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }
        
        .light-card {
            background: rgba(30, 41, 59, 0.6);
            border-radius: 12px;
            border: 1px solid rgba(51, 65, 85, 0.5);
            padding: 1rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            overflow: hidden;
        }
        
        .light-card:hover { 
            border-color: rgba(71, 85, 105, 0.8);
            transform: translateY(-2px);
        }
        
        .light-card.active { 
            border-color: var(--stage-color);
            box-shadow: 0 0 20px rgba(var(--stage-color-rgb), 0.2);
        }
        
        .light-card-indicator {
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            opacity: 0.6;
        }
        
        .light-glow {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            background: radial-gradient(circle at 50% 0%, var(--stage-color) 0%, transparent 70%);
            opacity: 0;
            filter: blur(20px);
            transition: opacity 0.3s;
            pointer-events: none;
        }
        
        .light-card.active .light-glow {
            opacity: 0.3;
        }
        
        .light-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.25rem;
            position: relative;
            z-index: 1;
            font-variant-numeric: tabular-nums;
            opacity: 0.3;
            transition: opacity 0.2s;
        }
        
        .light-card.active .light-value {
            opacity: 1;
            text-shadow: 0 0 20px var(--stage-color);
        }
        
        .light-label { 
            font-weight: 600; 
            color: #e2e8f0;
            font-size: 0.85rem;
            position: relative;
            z-index: 1;
        }
        
        .light-status { 
            color: #64748b;
            font-size: 0.75rem;
            margin-top: 0.25rem;
            position: relative;
            z-index: 1;
        }
        
        .light-bar {
            margin-top: 0.75rem;
            height: 4px;
            background: rgba(51, 65, 85, 0.8);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
            z-index: 1;
        }
        
        .light-bar-fill {
            height: 100%;
            border-radius: 2px;
            transition: width 0.2s;
            box-shadow: 0 0 8px currentColor;
        }
        
        /* Activity Log */
        .activity-log {
            background: rgba(30, 41, 59, 0.4);
            border-radius: 12px;
            border: 1px solid rgba(51, 65, 85, 0.5);
            padding: 1rem;
        }
        
        .log-container {
            max-height: 180px;
            overflow-y: auto;
            font-family: ui-monospace, monospace;
            font-size: 0.7rem;
            background: #0f172a;
            color: #94a3b8;
            border-radius: 8px;
            padding: 0.75rem;
            border: 1px solid rgba(51, 65, 85, 0.3);
        }
        
        .log-entry {
            padding: 0.2rem 0;
            border-bottom: 1px solid rgba(51, 65, 85, 0.3);
        }
        
        .log-entry:last-child { border-bottom: none; }
        
        .log-entry.manual { color: #fbbf24; }
        .log-entry.auto { color: #4ade80; }
        .log-entry.backprop { color: #60a5fa; }
        
        /* Buttons */
        button {
            padding: 0.5rem 0.875rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        button.primary { 
            background: rgba(245, 158, 11, 0.1);
            color: #fcd34d;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }
        button.primary:hover { 
            background: rgba(245, 158, 11, 0.2);
            border-color: rgba(245, 158, 11, 0.3);
        }
        
        button.secondary { 
            background: rgba(51, 65, 85, 0.5);
            color: #e2e8f0;
            border: 1px solid rgba(71, 85, 105, 0.5);
        }
        button.secondary:hover { 
            background: rgba(71, 85, 105, 0.5);
        }
        
        button.ghost {
            background: transparent;
            color: #94a3b8;
            border: 1px solid rgba(71, 85, 105, 0.5);
        }
        button.ghost:hover {
            background: rgba(51, 65, 85, 0.3);
            color: #e2e8f0;
        }
        
        /* Checkbox */
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
            font-size: 0.8rem;
            color: #94a3b8;
            padding: 0.375rem 0.75rem;
            border-radius: 8px;
            border: 1px solid rgba(71, 85, 105, 0.3);
            transition: all 0.2s;
        }
        
        .checkbox-label:hover {
            border-color: rgba(71, 85, 105, 0.5);
            color: #e2e8f0;
        }
        
        .checkbox-label input { 
            margin: 0;
            accent-color: #f59e0b;
        }
        
        /* Dialog */
        .dialog-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .dialog-overlay.open { display: flex; }
        
        .dialog {
            background: #1e293b;
            border-radius: 16px;
            border: 1px solid rgba(51, 65, 85, 0.8);
            padding: 1.5rem;
            min-width: 300px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        
        .dialog h2 { 
            margin: 0 0 1.25rem 0; 
            font-size: 1rem;
            font-weight: 600;
            color: white;
        }
        
        .dialog input[type="range"] {
            width: 100%;
            height: 8px;
            -webkit-appearance: none;
            background: #334155;
            border-radius: 4px;
            margin: 0.5rem 0;
        }
        
        .dialog input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            background: #f59e0b;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
        }
        
        .dialog-value {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            color: white;
            margin: 0.75rem 0;
            font-variant-numeric: tabular-nums;
        }
        
        .dialog-buttons {
            display: flex;
            gap: 0.5rem;
            justify-content: flex-end;
            margin-top: 1.25rem;
        }
    `;
    
    constructor() {
        super();
        this.connected = false;
        this.state = null;
        this._selectedLight = null;
        this._dialogBrightness = 0;
    }
    
    render() {
        const isOn = this.state?.is_on || false;
        const brightnessPct = isOn ? (this.state?.brightness_pct || 0) : 0;
        const currentStage = this.state?.current_stage || 0;
        const breakpoints = this.state?.config?.breakpoints || [30, 60, 90];
        const lights = this.state?.lights || [];
        
        return html`
            <header>
                <div class="header-left">
                    <div class="logo-icon">💡</div>
                    <div class="header-title">
                        <h1>Combined Lights</h1>
                        <span class="header-subtitle">Simulation</span>
                    </div>
                </div>
                <div class="header-right">
                    <label class="checkbox-label">
                        <input 
                            type="checkbox" 
                            .checked=${this.state?.config?.back_propagation || false}
                            @change=${(e) => this._setBackPropagation(e.target.checked)}
                        />
                        Back-propagation
                    </label>
                    <span class="status-badge ${this.connected ? 'connected' : 'disconnected'}">
                        ${this.connected ? '● Connected' : '○ Disconnected'}
                    </span>
                    <button class="ghost" @click=${this._onReset}>Reset</button>
                </div>
            </header>
            
            <main>
                <!-- Hero Control -->
                <div class="hero-control">
                    <div class="hero-header">
                        <div class="hero-label-group">
                            <div class="hero-icon">🎚️</div>
                            <div>
                                <div class="hero-label">Master Brightness</div>
                                <div class="hero-sublabel">${isOn ? `Stage ${currentStage} active` : 'All lights off'}</div>
                            </div>
                        </div>
                        <div class="hero-value">
                            <span class="hero-value-number">${Math.round(brightnessPct)}</span>
                            <span class="hero-value-unit">%</span>
                        </div>
                    </div>
                    
                    <div class="slider-track-container">
                        <div class="slider-track-bg">
                            <div class="slider-track-fill" style="width: ${brightnessPct}%"></div>
                        </div>
                        <div class="slider-progress">
                            <div class="slider-progress-bar" style="width: ${brightnessPct}%"></div>
                        </div>
                        <input 
                            type="range"
                            class="slider-input"
                            min="0" 
                            max="100" 
                            .value=${Math.round(brightnessPct)}
                            @change=${this._onSliderChange}
                        />
                        <div class="slider-thumb" style="left: calc(${brightnessPct}% - 14px)">
                            <div class="slider-thumb-dot"></div>
                        </div>
                    </div>
                    
                    <div class="slider-markers">
                        ${[0, ...breakpoints, 100].map(mark => html`
                            <div class="slider-marker" style="left: ${mark}%">
                                <div class="slider-marker-tick"></div>
                                <span>${mark}%</span>
                            </div>
                        `)}
                    </div>
                </div>
                
                <!-- Stage Cards -->
                <div>
                    <div class="section-header">
                        <div class="section-dot"></div>
                        <span class="section-title">Zone Visualizer</span>
                    </div>
                    <div class="lights-row">
                        ${lights.map((light, i) => {
                            const color = STAGE_COLORS[i] || STAGE_COLORS[0];
                            const isActive = light.state === 'on';
                            const pct = isActive ? light.brightness_pct : 0;
                            return html`
                                <div 
                                    class="light-card ${isActive ? 'active' : ''}"
                                    style="--stage-color: ${color}; --stage-color-rgb: ${this._hexToRgb(color)}"
                                    @click=${() => this._openLightDialog(light)}
                                >
                                    <div class="light-card-indicator" style="background: ${color}"></div>
                                    <div class="light-glow" style="--stage-color: ${color}"></div>
                                    <div class="light-value">${isActive ? pct : '—'}</div>
                                    <div class="light-label">Stage ${i + 1}</div>
                                    <div class="light-status">${isActive ? `${pct}%` : 'OFF'}</div>
                                    <div class="light-bar">
                                        <div 
                                            class="light-bar-fill" 
                                            style="width: ${pct}%; background: ${color}; color: ${color}"
                                        ></div>
                                    </div>
                                </div>
                            `;
                        })}
                    </div>
                </div>
                
                <!-- Activity Log -->
                <div class="activity-log">
                    <div class="section-header">
                        <div class="section-dot" style="background: #3b82f6"></div>
                        <span class="section-title">Activity Log</span>
                    </div>
                    <div class="log-container">
                        ${(this.state?.history || []).slice().reverse().map(h => html`
                            <div class="log-entry ${h.event_type}">${h.description}</div>
                        `)}
                    </div>
                </div>
            </main>
            
            <!-- Dialog -->
            <div class="dialog-overlay ${this._selectedLight ? 'open' : ''}" @click=${this._closeDialog}>
                <div class="dialog" @click=${(e) => e.stopPropagation()}>
                    ${this._selectedLight ? html`
                        <h2>💡 Stage ${this._selectedLight.stage}</h2>
                        <input 
                            type="range" 
                            min="0" 
                            max="255" 
                            .value=${this._dialogBrightness}
                            @input=${(e) => this._dialogBrightness = parseInt(e.target.value)}
                        />
                        <div class="dialog-value">${Math.round(this._dialogBrightness / 255 * 100)}%</div>
                        <div class="dialog-buttons">
                            <button class="ghost" @click=${this._closeDialog}>Cancel</button>
                            <button class="secondary" @click=${() => this._applyLightBrightness(0)}>Off</button>
                            <button class="primary" @click=${() => this._applyLightBrightness(this._dialogBrightness)}>Apply</button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    _hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result 
            ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
            : '245, 158, 11';
    }
    
    _onSliderChange(e) {
        this._setBrightness(parseInt(e.target.value));
    }
    
    _onReset() {
        this.dispatchEvent(new CustomEvent('reset'));
    }
    
    _setBrightness(pct) {
        const brightness = Math.round((pct / 100) * 255);
        this.dispatchEvent(new CustomEvent('set-brightness', { detail: { brightness } }));
    }
    
    _setBackPropagation(enabled) {
        this.dispatchEvent(new CustomEvent('update-config', { 
            detail: { config: { enable_back_propagation: enabled } } 
        }));
    }
    
    _openLightDialog(light) {
        this._selectedLight = light;
        this._dialogBrightness = light.brightness || 0;
    }
    
    _closeDialog() {
        this._selectedLight = null;
    }
    
    _applyLightBrightness(brightness) {
        if (this._selectedLight) {
            this.dispatchEvent(new CustomEvent('set-light', {
                detail: { entityId: this._selectedLight.entity_id, brightness }
            }));
        }
        this._closeDialog();
    }
}

customElements.define('combined-lights-app', CombinedLightsApp);
