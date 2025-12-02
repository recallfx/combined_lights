/**
 * Centralized state container for Combined Lights simulation.
 * Single source of truth for all application state.
 */

class AppState {
    constructor() {
        // Static data from server (set on init, doesn't change often)
        this.layout = null;
        
        // Dynamic coordinator state (updated via WebSocket)
        this.state = null;
        
        // Frontend-only state
        this.selectedLight = null;
        this.isDragging = false;
        this.sliderValue = 255;
        
        // Component references
        this.ws = null;
        this.canvasElement = null;
        this.appElement = null;
    }
    
    /**
     * Get all lights from layout
     */
    getLights() {
        return this.layout?.lights || [];
    }
    
    /**
     * Get all zones from layout
     */
    getZones() {
        return this.layout?.zones || [];
    }
    
    /**
     * Get light state by ID
     */
    getLightState(lightId) {
        if (!this.state?.zones) return null;
        
        for (const zone of Object.values(this.state.zones)) {
            const light = zone.lights?.find(l => l.entity_id === lightId);
            if (light) return light;
        }
        return null;
    }
    
    /**
     * Get zone state by ID
     */
    getZoneState(zoneId) {
        return this.state?.zones?.[zoneId] || null;
    }
}

// Global singleton
export const appState = new AppState();
