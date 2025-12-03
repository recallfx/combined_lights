"""Home Assistant based simulation server.

This module runs a real Home Assistant instance with the actual
HACombinedLightsCoordinator, providing accurate simulation without
code duplication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from aiohttp import WSMsgType, web

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from custom_components.combined_lights.const import (
    CONF_BREAKPOINTS,
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_NAME,
    CONF_STAGE_1_CURVE,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_CURVE,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_CURVE,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_CURVE,
    CONF_STAGE_4_LIGHTS,
    CURVE_LINEAR,
    DEFAULT_BREAKPOINTS,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    DOMAIN,
)
from custom_components.combined_lights.helpers import (
    BrightnessCalculator,
    HACombinedLightsCoordinator,
)

_LOGGER = logging.getLogger(__name__)


# Default simulation configuration
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

    def to_config_entry_data(self) -> dict[str, Any]:
        """Convert to ConfigEntry data format."""
        return {
            CONF_NAME: "Simulation",
            CONF_STAGE_1_LIGHTS: ["light.stage_1"],
            CONF_STAGE_2_LIGHTS: ["light.stage_2"],
            CONF_STAGE_3_LIGHTS: ["light.stage_3"],
            CONF_STAGE_4_LIGHTS: ["light.stage_4"],
            CONF_BREAKPOINTS: self.breakpoints,
            CONF_STAGE_1_CURVE: self.stage_1_curve,
            CONF_STAGE_2_CURVE: self.stage_2_curve,
            CONF_STAGE_3_CURVE: self.stage_3_curve,
            CONF_STAGE_4_CURVE: self.stage_4_curve,
            CONF_ENABLE_BACK_PROPAGATION: self.enable_back_propagation,
        }


class HASimulationServer:
    """Simulation server using real Home Assistant instance."""

    def __init__(
        self, host: str = "localhost", port: int = 8091, config: SimConfig | None = None
    ):
        """Initialize the simulation server."""
        self.host = host
        self.port = port
        self._config = config or SimConfig.default()
        self.hass: HomeAssistant | None = None
        self.coordinator: HACombinedLightsCoordinator | None = None
        self.config_entry: ConfigEntry | None = None
        self._websockets: list[web.WebSocketResponse] = []
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._event_log: list[dict] = []
        self._max_log_entries = 50
        self._listeners: list[Callable] = []

    async def start(self) -> None:
        """Start the simulation server."""
        # Initialize Home Assistant
        await self._init_hass()

        # Set up web server
        self._app = web.Application()
        self._app.router.add_get("/ws", self._websocket_handler)
        self._app.router.add_get("/", self._index_handler)
        # Serve static files
        static_path = Path(__file__).parent / "static"
        self._app.router.add_static("/static", static_path)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()

        print("\n🏠 Combined Lights HA-Based Simulation Server")
        print(f"   Open http://{self.host}:{self.port} in your browser\n")

    async def stop(self) -> None:
        """Stop the simulation server."""
        # Close WebSocket connections
        for ws in self._websockets:
            await ws.close()

        # Stop Home Assistant
        if self.hass:
            await self.hass.async_stop()

        # Stop web server
        if self._runner:
            await self._runner.cleanup()

    async def _init_hass(self) -> None:
        """Initialize Home Assistant instance."""
        # Create Home Assistant instance
        self.hass = HomeAssistant("/tmp/ha_combined_lights_sim")
        await self.hass.async_start()

        # Set up mock services
        await self._setup_mock_services()

        # Set up mock entities
        await self._setup_mock_entities()

        # Create config entry
        self.config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Simulation",
            data=self._config.to_config_entry_data(),
            options={},
            entry_id="sim_entry",
            source="user",
            unique_id="sim_unique",
            discovery_keys={},
        )

        # Create brightness calculator
        brightness_calc = BrightnessCalculator(self.config_entry)

        # Create coordinator
        self.coordinator = HACombinedLightsCoordinator(
            self.hass, self.config_entry, brightness_calc
        )

        # Register lights with coordinator
        self.coordinator.register_light("light.stage_1", 1)
        self.coordinator.register_light("light.stage_2", 2)
        self.coordinator.register_light("light.stage_3", 3)
        self.coordinator.register_light("light.stage_4", 4)

        # Subscribe to state changes for broadcasting
        self.hass.bus.async_listen("state_changed", self._on_state_changed)

        _LOGGER.info("Home Assistant simulation initialized")

    async def _setup_mock_services(self) -> None:
        """Register mock services for light control."""

        async def handle_light_turn_on(call):
            """Handle light.turn_on service call."""
            entity_ids = call.data.get("entity_id", [])
            if isinstance(entity_ids, str):
                entity_ids = [entity_ids]

            brightness = call.data.get("brightness", 255)
            brightness_pct = call.data.get("brightness_pct")
            if brightness_pct is not None:
                brightness = int(brightness_pct * 255 / 100)

            # Preserve the context from the service call
            context = call.context

            for entity_id in entity_ids:
                if entity_id.startswith("light.stage_"):
                    current = self.hass.states.get(entity_id)
                    attrs = dict(current.attributes) if current else {}
                    attrs["brightness"] = brightness
                    attrs["supported_color_modes"] = ["brightness"]
                    self.hass.states.async_set(entity_id, "on", attrs, context=context)
                    _LOGGER.debug(
                        "Mock turn_on: %s brightness=%d context=%s",
                        entity_id,
                        brightness,
                        context.id if context else None,
                    )

        async def handle_light_turn_off(call):
            """Handle light.turn_off service call."""
            entity_ids = call.data.get("entity_id", [])
            if isinstance(entity_ids, str):
                entity_ids = [entity_ids]

            # Preserve the context from the service call
            context = call.context

            for entity_id in entity_ids:
                if entity_id.startswith("light.stage_"):
                    current = self.hass.states.get(entity_id)
                    attrs = dict(current.attributes) if current else {}
                    attrs["brightness"] = 0
                    attrs["supported_color_modes"] = ["brightness"]
                    self.hass.states.async_set(entity_id, "off", attrs, context=context)
                    _LOGGER.debug(
                        "Mock turn_off: %s context=%s",
                        entity_id,
                        context.id if context else None,
                    )

        # Register mock light services
        self.hass.services.async_register("light", "turn_on", handle_light_turn_on)
        self.hass.services.async_register("light", "turn_off", handle_light_turn_off)

    async def _setup_mock_entities(self) -> None:
        """Set up mock entities for simulation."""
        # Create 4 lights, one per stage
        for stage in range(1, 5):
            entity_id = f"light.stage_{stage}"
            self.hass.states.async_set(
                entity_id,
                "off",
                {
                    "friendly_name": f"Stage {stage} Light",
                    "brightness": 0,
                    "supported_color_modes": ["brightness"],
                },
            )

    @callback
    def _on_state_changed(self, event) -> None:
        """Handle state change events."""
        entity_id = event.data.get("entity_id", "")
        if entity_id.startswith("light.stage_"):
            # Sync coordinator state from HA
            self.coordinator.sync_light_state_from_ha(entity_id)
            # Broadcast to all WebSocket clients
            asyncio.create_task(self._broadcast_state())

    async def _index_handler(self, request: web.Request) -> web.FileResponse:
        """Serve index.html."""
        return web.FileResponse(Path(__file__).parent / "static" / "index.html")

    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._websockets.append(ws)
        _LOGGER.info("WebSocket client connected (%d total)", len(self._websockets))

        # Send initial state
        await ws.send_json({"type": "init", "state": self._get_state()})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(ws, json.loads(msg.data))
                elif msg.type == WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", ws.exception())
        finally:
            self._websockets.remove(ws)
            _LOGGER.info(
                "WebSocket client disconnected (%d remaining)", len(self._websockets)
            )

        return ws

    async def _handle_message(self, ws: web.WebSocketResponse, message: dict) -> None:
        """Handle incoming WebSocket message."""
        msg_type = message.get("type")
        _LOGGER.debug("Received message: %s", message)

        try:
            if msg_type == "turn_on":
                brightness = message.get("brightness")
                await self._turn_on(brightness)

            elif msg_type == "turn_off":
                await self._turn_off()

            elif msg_type == "set_brightness":
                brightness = message.get("brightness")
                if brightness is not None:
                    await self._turn_on(int(brightness))

            elif msg_type == "set_light":
                entity_id = message.get("entity_id")
                brightness = message.get("brightness", 0)
                if entity_id:
                    await self._set_light_brightness(entity_id, brightness)

            elif msg_type == "reset":
                await self._reset_simulation()

            elif msg_type == "update_config":
                config = message.get("config", {})
                self._update_config(config)

            elif msg_type == "get_history":
                await ws.send_json(
                    {
                        "type": "history",
                        "history": self._event_log,
                    }
                )

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

        except Exception as e:
            _LOGGER.exception("Error handling message: %s", e)
            await ws.send_json({"error": str(e)})

        # Broadcast updated state
        await self._broadcast_state()

    async def _turn_on(self, brightness: int | None = None) -> None:
        """Turn on the combined light."""
        # Calculate changes using coordinator
        changes = self.coordinator.turn_on(brightness)
        brightness_pct = self.coordinator.target_brightness_pct

        self._log_event(f"🔆 ON at {brightness_pct:.0f}%", "auto")

        # Apply changes to HA lights via services
        for entity_id, new_brightness in changes.items():
            if new_brightness > 0:
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": entity_id, "brightness": new_brightness},
                )
            else:
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {"entity_id": entity_id},
                )

            light = self.coordinator.get_light(entity_id)
            if light and new_brightness > 0:
                pct = new_brightness / 255 * 100
                self._log_event(f"  Stage {light.stage}: {pct:.0f}%", "auto")

    async def _turn_off(self) -> None:
        """Turn off the combined light."""
        changes = self.coordinator.turn_off()

        # Apply changes to HA lights
        for entity_id in changes:
            await self.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": entity_id},
            )

        self._log_event("🔅 OFF", "auto")

    async def _set_light_brightness(self, entity_id: str, brightness: int) -> None:
        """Manually set a single light's brightness."""
        light = self.coordinator.get_light(entity_id)
        if not light:
            return

        old_brightness = light.brightness
        old_pct = old_brightness / 255 * 100 if old_brightness > 0 else 0
        new_pct = brightness / 255 * 100 if brightness > 0 else 0

        # Update HA state directly (simulating manual control - no context)
        if brightness > 0:
            self.hass.states.async_set(
                entity_id,
                "on",
                {"brightness": brightness, "supported_color_modes": ["brightness"]},
            )
        else:
            self.hass.states.async_set(
                entity_id,
                "off",
                {"brightness": 0, "supported_color_modes": ["brightness"]},
            )

        # Sync coordinator from HA
        self.coordinator.sync_all_lights_from_ha()

        # Handle manual change using coordinator
        overall_pct, back_prop_changes = self.coordinator.handle_manual_light_change(
            entity_id, brightness
        )

        # Record manual change
        stage = light.stage
        if brightness > 0:
            self._log_event(
                f"✋ Stage {stage}: {old_pct:.0f}% → {new_pct:.0f}%", "manual"
            )
        else:
            self._log_event(f"✋ Stage {stage}: OFF", "manual")
        self._log_event(f"  → Overall: {overall_pct:.0f}%", "manual")

        # Apply back-propagation changes if enabled
        if self._config.enable_back_propagation and back_prop_changes:
            for bp_entity_id, bp_brightness in back_prop_changes.items():
                bp_light = self.coordinator.get_light(bp_entity_id)
                if not bp_light:
                    continue

                if bp_brightness > 0:
                    await self.hass.services.async_call(
                        "light",
                        "turn_on",
                        {"entity_id": bp_entity_id, "brightness": bp_brightness},
                    )
                    bp_pct = bp_brightness / 255 * 100
                    self._log_event(
                        f"↩️ Stage {bp_light.stage}: {bp_pct:.0f}%", "backprop"
                    )
                else:
                    await self.hass.services.async_call(
                        "light",
                        "turn_off",
                        {"entity_id": bp_entity_id},
                    )
                    self._log_event(f"↩️ Stage {bp_light.stage}: OFF", "backprop")

    async def _reset_simulation(self) -> None:
        """Reset simulation to initial state."""
        # Turn off all lights
        for stage in range(1, 5):
            entity_id = f"light.stage_{stage}"
            self.hass.states.async_set(
                entity_id,
                "off",
                {"brightness": 0, "supported_color_modes": ["brightness"]},
            )

        # Reset coordinator state
        self.coordinator.reset()

        self._event_log.clear()
        self._log_event("Simulation reset", "system")

    def _update_config(self, config_updates: dict) -> None:
        """Update simulation configuration."""
        if "breakpoints" in config_updates:
            self._config.breakpoints = config_updates["breakpoints"]
        if "enable_back_propagation" in config_updates:
            self._config.enable_back_propagation = config_updates[
                "enable_back_propagation"
            ]
        if "stage_1_curve" in config_updates:
            self._config.stage_1_curve = config_updates["stage_1_curve"]
        if "stage_2_curve" in config_updates:
            self._config.stage_2_curve = config_updates["stage_2_curve"]
        if "stage_3_curve" in config_updates:
            self._config.stage_3_curve = config_updates["stage_3_curve"]
        if "stage_4_curve" in config_updates:
            self._config.stage_4_curve = config_updates["stage_4_curve"]

        # Recreate config entry and coordinator with new config
        self.config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Simulation",
            data=self._config.to_config_entry_data(),
            options={},
            entry_id="sim_entry",
            source="user",
            unique_id="sim_unique",
            discovery_keys={},
        )

        brightness_calc = BrightnessCalculator(self.config_entry)
        self.coordinator = HACombinedLightsCoordinator(
            self.hass, self.config_entry, brightness_calc
        )

        # Re-register lights
        self.coordinator.register_light("light.stage_1", 1)
        self.coordinator.register_light("light.stage_2", 2)
        self.coordinator.register_light("light.stage_3", 3)
        self.coordinator.register_light("light.stage_4", 4)

        # Sync from HA
        self.coordinator.sync_all_lights_from_ha()

        # Recalculate if on
        if self.coordinator.is_on:
            changes = self.coordinator.apply_brightness_to_lights()
            asyncio.create_task(self._apply_changes_async(changes))

        self._log_event("Config updated", "system")

    async def _apply_changes_async(self, changes: dict[str, int]) -> None:
        """Apply changes to HA lights asynchronously."""
        for entity_id, brightness in changes.items():
            if brightness > 0:
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": entity_id, "brightness": brightness},
                )
            else:
                await self.hass.services.async_call(
                    "light",
                    "turn_off",
                    {"entity_id": entity_id},
                )

    def _get_state(self) -> dict[str, Any]:
        """Get current simulation state."""
        if not self.hass or not self.coordinator:
            return {"error": "Not initialized"}

        # Sync from HA to ensure current state
        self.coordinator.sync_all_lights_from_ha()

        return {
            "is_on": self.coordinator.is_on,
            "brightness_pct": self.coordinator.target_brightness_pct,
            "current_stage": self.coordinator.current_stage,
            "lights": [light.to_dict() for light in self.coordinator.get_lights()],
            "config": {
                "breakpoints": self._config.breakpoints,
                "back_propagation": self._config.enable_back_propagation,
                "stage_1_curve": self._config.stage_1_curve,
                "stage_2_curve": self._config.stage_2_curve,
                "stage_3_curve": self._config.stage_3_curve,
                "stage_4_curve": self._config.stage_4_curve,
            },
            "history": self._event_log[-20:],
            "timestamp": time.time(),
        }

    async def _broadcast_state(self) -> None:
        """Broadcast state to all WebSocket clients."""
        message = {"type": "state_update", "state": self._get_state()}
        for ws in self._websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                _LOGGER.error("Error broadcasting to client: %s", e)

    def _log_event(self, message: str, event_type: str = "info") -> None:
        """Log an event."""
        entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "description": message,
        }
        self._event_log.append(entry)
        if len(self._event_log) > self._max_log_entries:
            self._event_log.pop(0)
        _LOGGER.info(message)


async def run_ha_simulation(
    host: str = "0.0.0.0", port: int = 8091, config: SimConfig | None = None
):
    """Run the HA-based simulation server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    server = HASimulationServer(host=host, port=port, config=config)
    await server.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await server.stop()


def run_server(
    host: str | None = None, port: int | None = None, config: SimConfig | None = None
) -> None:
    """Entry point for the HA simulation server."""
    import argparse

    parser = argparse.ArgumentParser(description="Combined Lights Simulation Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8091, help="Port to bind to")
    parser.add_argument(
        "--breakpoints", default="30,60,90", help="Comma-separated breakpoints"
    )
    args = parser.parse_args()

    # CLI args override function params
    host = host or args.host
    port = port or args.port

    if config is None:
        breakpoints = [int(x.strip()) for x in args.breakpoints.split(",")]
        config = SimConfig(breakpoints=breakpoints)

    asyncio.run(run_ha_simulation(host=host, port=port, config=config))
