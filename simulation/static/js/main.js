/**
 * Main entry point for Combined Lights simulation.
 */

import { appState } from './state.js';
import { WebSocketManager } from './websocket.js';
import './components/app.js';

let appElement = null;
let wsManager = null;

function init() {
    appElement = document.createElement('combined-lights-app');
    document.body.appendChild(appElement);
    
    // Wire up app events
    appElement.addEventListener('reset', () => wsManager.reset());
    
    appElement.addEventListener('set-brightness', (e) => {
        const { brightness } = e.detail;
        if (brightness === 0) {
            wsManager.turnOff();
        } else {
            wsManager.turnOn(brightness);
        }
    });
    
    appElement.addEventListener('update-config', (e) => {
        wsManager.updateConfig(e.detail.config);
    });
    
    appElement.addEventListener('set-light', (e) => {
        const { entityId, brightness } = e.detail;
        wsManager.setLight(entityId, brightness);
    });
    
    // Initialize WebSocket
    wsManager = new WebSocketManager(appState, {
        onConnect: () => {
            appElement.connected = true;
        },
        
        onDisconnect: () => {
            appElement.connected = false;
        },
        
        onInit: (state) => {
            appState.state = state;
            appElement.state = state;
        },
        
        onStateUpdate: (state) => {
            appState.state = state;
            appElement.state = state;
        },
    });
    
    wsManager.connect();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
