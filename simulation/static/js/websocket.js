/**
 * WebSocket connection management for Combined Lights simulation.
 */

export class WebSocketManager {
    constructor(appState, handlers) {
        this.appState = appState;
        this.handlers = handlers;
        this.ws = null;
        this.reconnectDelay = 2000;
    }
    
    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws`;
        
        console.log('Connecting to WebSocket:', url);
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.handlers.onConnect?.();
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._handleMessage(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            this.handlers.onDisconnect?.();
            setTimeout(() => this.connect(), this.reconnectDelay);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    _handleMessage(data) {
        switch (data.type) {
            case 'init':
                this.handlers.onInit?.(data.state);
                break;
                
            case 'state_update':
                this.handlers.onStateUpdate?.(data.state);
                break;
                
            case 'log':
                this.handlers.onLog?.(data.level, data.message, data.name);
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    send(type, payload = {}) {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, ...payload }));
        }
    }
    
    turnOn(brightness = null) {
        this.send('turn_on', brightness !== null ? { brightness } : {});
    }
    
    turnOff() {
        this.send('turn_off');
    }
    
    setLight(entityId, brightness) {
        this.send('set_light', { entity_id: entityId, brightness });
    }
    
    reset() {
        this.send('reset');
    }
    
    updateConfig(config) {
        this.send('update_config', { config });
    }
}
