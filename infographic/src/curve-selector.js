/**
 * Curve selector card component.
 */

import { LitElement, html, css, svg } from './lib.js';
import { getStageColor, CURVE_OPTIONS } from './calculations.js';

export class CurveSelector extends LitElement {
    static properties = {
        stage: { type: Object }
    };
    
    static styles = css`
        :host {
            display: block;
        }
        
        .card {
            display: flex;
            flex-direction: column;
            padding: 16px;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 12px;
            border: 1px solid rgba(30, 41, 59, 0.5);
            position: relative;
            overflow: hidden;
            transition: all 0.2s;
        }
        
        .card:hover {
            border-color: #334155;
        }
        
        .indicator {
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            opacity: 0.6;
            transition: opacity 0.2s;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            padding-left: 8px;
        }
        
        .header-content {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .icon-box {
            padding: 6px;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: inset 0 0 0 1px rgba(51, 65, 85, 0.5);
        }
        
        .stage-info h3 {
            font-weight: 600;
            color: #e2e8f0;
            font-size: 0.875rem;
            line-height: 1;
            margin: 0 0 4px 0;
        }
        
        .stage-info p {
            font-size: 10px;
            color: #64748b;
            font-family: ui-monospace, monospace;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            line-height: 1;
            margin: 0;
        }
        
        .select-wrapper {
            position: relative;
            padding-left: 8px;
            margin-top: auto;
        }
        
        select {
            width: 100%;
            background: #0f172a;
            font-size: 11px;
            font-weight: 500;
            color: #cbd5e1;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 6px 24px 6px 8px;
            appearance: none;
            cursor: pointer;
            transition: all 0.15s;
        }
        
        select:hover {
            border-color: #475569;
        }
        
        select:focus {
            outline: none;
            border-color: rgba(245, 158, 11, 0.5);
            box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.1);
        }
        
        .select-arrow {
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            color: #475569;
            transition: color 0.15s;
        }
        
        .select-wrapper:hover .select-arrow {
            color: #64748b;
        }
    `;
    
    constructor() {
        super();
        this.stage = null;
    }
    
    _renderIcon(type, color) {
        const iconMap = {
            strip: svg`
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
                    <line x1="12" y1="19" x2="12" y2="5"></line>
                    <polyline points="5 12 12 5 19 12"></polyline>
                </svg>
            `,
            lamp: svg`
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
                    <path d="M8 2h8l2 10H6L8 2z"></path>
                    <line x1="12" y1="12" x2="12" y2="18"></line>
                    <line x1="8" y1="18" x2="16" y2="18"></line>
                </svg>
            `,
            ceiling: svg`
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
                    <path d="M9 18h6"></path>
                    <path d="M10 22h4"></path>
                    <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"></path>
                </svg>
            `,
            spot: svg`
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
                    <circle cx="12" cy="12" r="4"></circle>
                    <path d="M12 2v2"></path>
                    <path d="M12 20v2"></path>
                    <path d="m4.93 4.93 1.41 1.41"></path>
                    <path d="m17.66 17.66 1.41 1.41"></path>
                    <path d="M2 12h2"></path>
                    <path d="M20 12h2"></path>
                    <path d="m6.34 17.66-1.41 1.41"></path>
                    <path d="m19.07 4.93-1.41 1.41"></path>
                </svg>
            `
        };
        return iconMap[type] || iconMap.ceiling;
    }
    
    _handleChange(e) {
        this.dispatchEvent(new CustomEvent('curve-change', {
            detail: { id: this.stage.id, curve: e.target.value },
            bubbles: true,
            composed: true
        }));
    }
    
    render() {
        if (!this.stage) return html``;
        
        const color = getStageColor(this.stage.id);
        
        return html`
            <div class="card">
                <div class="indicator" style="background-color: ${color}"></div>
                
                <div class="header">
                    <div class="header-content">
                        <div class="icon-box">
                            ${this._renderIcon(this.stage.icon, color)}
                        </div>
                        <div class="stage-info">
                            <h3>${this.stage.name}</h3>
                            <p>Starts @ ${this.stage.startPercentage}%</p>
                        </div>
                    </div>
                </div>
                
                <div class="select-wrapper">
                    <select .value=${this.stage.curve} @change=${this._handleChange}>
                        ${CURVE_OPTIONS.map(opt => html`
                            <option value=${opt.value} ?selected=${this.stage.curve === opt.value}>
                                ${opt.label}
                            </option>
                        `)}
                    </select>
                    <div class="select-arrow">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M6 9l6 6 6-6"></path>
                        </svg>
                    </div>
                </div>
            </div>
        `;
    }
}

customElements.define('curve-selector', CurveSelector);
