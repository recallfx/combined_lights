"""Simulation coordinator for Combined Lights.

Uses the base coordinator from the component for accurate behavior.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from custom_components.combined_lights.const import (
    CURVE_LINEAR,
    DEFAULT_BREAKPOINTS,
    DEFAULT_ENABLE_BACK_PROPAGATION,
)
from custom_components.combined_lights.helpers.base_coordinator import (
    BaseBrightnessCalculator,
    BaseCombinedLightsCoordinator,
    LightState,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SimConfig:
    """Configuration for simulation."""

    breakpoints: list[int] = field(default_factory=lambda: list(DEFAULT_BREAKPOINTS))
    enable_back_propagation: bool = DEFAULT_ENABLE_BACK_PROPAGATION
    stage_1_curve: str = CURVE_LINEAR
    stage_2_curve: str = CURVE_LINEAR
    stage_3_curve: str = CURVE_LINEAR
    stage_4_curve: str = CURVE_LINEAR

    @classmethod
    def default(cls) -> "SimConfig":
        return cls()


class SimBrightnessCalculator(BaseBrightnessCalculator):
    """Brightness calculator for simulation using in-memory config."""

    def __init__(self, config: SimConfig):
        """Initialize with simulation config."""
        self._config = config

    def get_breakpoints(self) -> list[int]:
        """Get breakpoints from simulation config."""
        return self._config.breakpoints

    def get_stage_curve(self, stage_idx: int) -> str:
        """Get brightness curve for a specific stage."""
        if stage_idx == 0:
            return self._config.stage_1_curve
        if stage_idx == 1:
            return self._config.stage_2_curve
        if stage_idx == 2:
            return self._config.stage_3_curve
        if stage_idx == 3:
            return self._config.stage_4_curve
        return "linear"


class SimCombinedLightsCoordinator(BaseCombinedLightsCoordinator):
    """Simulation coordinator extending the base coordinator.
    
    Adds async interface and event history for the simulation UI.
    """

    def __init__(self, config: SimConfig | None = None):
        self._config = config or SimConfig.default()
        calculator = SimBrightnessCalculator(self._config)
        super().__init__(calculator)
        
        self._listeners: list[Callable] = []
        self._history: list[dict] = []
        
        # Create 4 lights, one per stage
        for i in range(1, 5):
            entity_id = f"light.stage_{i}"
            self._lights[entity_id] = LightState(entity_id=entity_id, stage=i)

    def async_add_listener(self, callback: Callable) -> Callable:
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        for callback in self._listeners:
            asyncio.create_task(callback())

    def _record_event(self, event_type: str, description: str) -> None:
        self._history.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "description": description,
        })
        if len(self._history) > 50:
            self._history.pop(0)

    async def async_turn_on(self, brightness: int | None = None) -> None:
        """Async wrapper for turn_on."""
        changes = self.turn_on(brightness)
        brightness_pct = self.target_brightness_pct
        self._record_event("auto", f"🔆 ON at {brightness_pct:.0f}%")
        
        # Log individual light changes
        for entity_id, new_brightness in changes.items():
            stage = self._lights[entity_id].stage
            pct = new_brightness / 255 * 100 if new_brightness > 0 else 0
            if new_brightness > 0:
                self._record_event("auto", f"  Stage {stage}: {pct:.0f}%")
        
        self._notify_listeners()

    async def async_turn_off(self) -> None:
        """Async wrapper for turn_off."""
        self.turn_off()
        self._record_event("auto", "🔅 OFF")
        self._notify_listeners()

    async def async_set_light_brightness(self, entity_id: str, brightness: int) -> None:
        """Manually set a single light's brightness."""
        light = self._lights.get(entity_id)
        if not light:
            return
        
        old_brightness = light.brightness
        old_pct = old_brightness / 255 * 100 if old_brightness > 0 else 0
        new_pct = brightness / 255 * 100 if brightness > 0 else 0
        
        # Use base class method
        _, overall_pct = self.set_light_brightness(entity_id, brightness)
        
        # Record manual change
        stage = light.stage
        if brightness > 0:
            self._record_event("manual", f"✋ Stage {stage}: {old_pct:.0f}% → {new_pct:.0f}%")
        else:
            self._record_event("manual", f"✋ Stage {stage}: OFF")
        self._record_event("manual", f"  → Overall: {overall_pct:.0f}%")
        
        # Back-propagation: update other lights
        if self._config.enable_back_propagation and self._is_on:
            back_prop_changes = self.apply_back_propagation(exclude_entity_id=entity_id)
            
            # Log back-propagation changes
            if back_prop_changes:
                for bp_entity_id, bp_brightness in back_prop_changes.items():
                    bp_light = self._lights[bp_entity_id]
                    bp_pct = bp_brightness / 255 * 100 if bp_brightness > 0 else 0
                    if bp_brightness > 0:
                        self._record_event("backprop", f"↩️ Stage {bp_light.stage}: {bp_pct:.0f}%")
                    else:
                        self._record_event("backprop", f"↩️ Stage {bp_light.stage}: OFF")
        
        self._notify_listeners()

    def get_simulation_state(self) -> dict[str, Any]:
        return {
            "is_on": self._is_on,
            "brightness_pct": self.target_brightness_pct,
            "current_stage": self.current_stage,
            "lights": [light.to_dict() for light in self._lights.values()],
            "config": {
                "breakpoints": self._config.breakpoints,
                "back_propagation": self._config.enable_back_propagation,
                "stage_1_curve": self._config.stage_1_curve,
                "stage_2_curve": self._config.stage_2_curve,
                "stage_3_curve": self._config.stage_3_curve,
                "stage_4_curve": self._config.stage_4_curve,
            },
            "history": self._history[-20:],
            "timestamp": time.time(),
        }

    def get_history(self) -> list[dict]:
        return self._history

    def reset(self) -> None:
        """Reset to initial state."""
        super().reset()
        self._history.clear()
        self._notify_listeners()

    def update_config(self, config_updates: dict) -> None:
        if "breakpoints" in config_updates:
            self._config.breakpoints = config_updates["breakpoints"]
        if "enable_back_propagation" in config_updates:
            self._config.enable_back_propagation = config_updates["enable_back_propagation"]
        if "stage_1_curve" in config_updates:
            self._config.stage_1_curve = config_updates["stage_1_curve"]
        if "stage_2_curve" in config_updates:
            self._config.stage_2_curve = config_updates["stage_2_curve"]
        if "stage_3_curve" in config_updates:
            self._config.stage_3_curve = config_updates["stage_3_curve"]
        if "stage_4_curve" in config_updates:
            self._config.stage_4_curve = config_updates["stage_4_curve"]
        
        # Recreate calculator with new config
        self._calculator = SimBrightnessCalculator(self._config)
        
        # Recalculate if on
        if self._is_on:
            self.apply_brightness_to_lights()
        
        self._notify_listeners()
