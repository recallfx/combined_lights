"""Web server for Combined Lights simulation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import WSMsgType, web

from .sim_coordinator import SimCombinedLightsCoordinator, SimConfig

if TYPE_CHECKING:
    from aiohttp.web import Application, Request, WebSocketResponse

_LOGGER = logging.getLogger(__name__)

# Global state
coordinator: SimCombinedLightsCoordinator | None = None
clients: set[WebSocketResponse] = set()


async def websocket_handler(request: Request) -> WebSocketResponse:
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    clients.add(ws)

    _LOGGER.info("WebSocket client connected. Total: %d", len(clients))

    # Send initial state
    await ws.send_json(
        {
            "type": "init",
            "state": coordinator.get_simulation_state(),
        }
    )

    # Register for coordinator updates
    async def on_update() -> None:
        if not ws.closed:
            try:
                await ws.send_json(
                    {
                        "type": "state_update",
                        "state": coordinator.get_simulation_state(),
                    }
                )
            except Exception as e:
                _LOGGER.debug("Failed to send update: %s", e)

    remove_listener = coordinator.async_add_listener(on_update)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await handle_message(data, ws)
                except json.JSONDecodeError:
                    _LOGGER.warning("Invalid JSON: %s", msg.data)
            elif msg.type == WSMsgType.ERROR:
                _LOGGER.error("WebSocket error: %s", ws.exception())
    finally:
        remove_listener()
        clients.discard(ws)
        _LOGGER.info("WebSocket client disconnected. Total: %d", len(clients))

    return ws


async def handle_message(data: dict, ws: WebSocketResponse) -> None:
    """Handle incoming WebSocket message."""
    msg_type = data.get("type")

    if msg_type == "turn_on":
        brightness = data.get("brightness")
        await coordinator.async_turn_on(brightness)

    elif msg_type == "turn_off":
        await coordinator.async_turn_off()

    elif msg_type == "set_brightness":
        brightness = data.get("brightness")
        if brightness is not None:
            await coordinator.async_turn_on(int(brightness))

    elif msg_type == "set_light":
        entity_id = data.get("entity_id")
        brightness = data.get("brightness", 0)
        if entity_id:
            await coordinator.async_set_light_brightness(entity_id, brightness)

    elif msg_type == "reset":
        coordinator.reset()

    elif msg_type == "update_config":
        config = data.get("config", {})
        coordinator.update_config(config)

    elif msg_type == "get_history":
        await ws.send_json(
            {
                "type": "history",
                "history": coordinator.get_history(),
            }
        )

    else:
        _LOGGER.warning("Unknown message type: %s", msg_type)


async def index_handler(request: Request) -> web.FileResponse:
    """Serve index.html."""
    static_path = Path(__file__).parent / "static" / "index.html"
    return web.FileResponse(static_path)


def create_app(config: SimConfig | None = None) -> Application:
    """Create and configure the aiohttp application."""
    global coordinator

    coordinator = SimCombinedLightsCoordinator(config)

    app = web.Application()

    # Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", websocket_handler)

    # Static files
    static_path = Path(__file__).parent / "static"
    app.router.add_static("/static", static_path)

    return app


def run_server(
    host: str = "0.0.0.0", port: int = 8091, config: SimConfig | None = None
) -> None:
    """Run the simulation server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = create_app(config)

    _LOGGER.info("Starting Combined Lights Simulation at http://%s:%d", host, port)
    web.run_app(app, host=host, port=port, print=None)


if __name__ == "__main__":
    run_server()
