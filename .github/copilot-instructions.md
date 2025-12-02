# Combined Lights - AI Agent Instructions

## Architecture overview

tbd

## Using uv

This project uses `uv` for Python environment and dependency management. Always prefix Python commands with `uv run` - never run `python`, `pytest`, or other Python tools directly. Examples:
- `uv run pytest tests/` - run tests
- `uv run python script.py` - run a script
- `uv run mypy .` - run type checking

## Running the infographic

The infographic is in the `infographic/` folder. It's a static site - serve it with:
```bash
cd infographic && python3 -m http.server 8080
```
Note: Use `python3`, not `python` (not available on this system).

## Running the simulation

Start the simulation server with:
```bash
uv run python simulation/run_server.py
```
Opens at http://localhost:8091 by default.

## Testing commands

Run tests with `uv run pytest tests/`. Tests use pytest-homeassistant-custom-component which provides fixtures like `hass` and `MockConfigEntry`.

For new test files, use `ConfigEntry` from `homeassistant.config_entries`, not a custom mock. Required parameters: version, minor_version, domain, title, data, options, entry_id, source, unique_id, discovery_keys.

Always call `coordinator.async_cleanup_listeners()` in test teardown to prevent lingering timer errors. The test framework checks for uncanceled timers.

## Extension patterns

Add new triggers by subclassing `TriggerHandler` (see `triggers.py` lines 19-100). Implement `async_setup()`, `is_active()`, and `get_info()`. Register with `trigger_manager.add_trigger(name, instance)`.

Add brightness logic by subclassing `BrightnessStrategy` and implementing `get_brightness(context)`. Context dict includes `is_house_active`, `is_dark_inside`, `motion_active`. Register with `light_controller.set_brightness_strategy()`.

Add manual detection logic by subclassing `ManualInterventionStrategy`. The base class provides `is_integration_context()`. Return tuple of (is_manual: bool, reason: str) from `is_manual_intervention()`.

## Config flow specifics

The config flow uses two steps: basic setup collects entities, advanced setup collects timeouts and brightness. Use `vol.All(cv.ensure_list, [cv.entity_id])` for multi-entity fields, not `vol.Any()`.

Entity validation happens in `_validate_input()` which checks for at least one light type. Don't validate entity existence - Home Assistant handles that.

Reconfiguration reuses the same flow with pre-filled data. Use `self.config_entry.data.get(key, default)` when building schemas.

## Common pitfalls

Don't use `timer.start_time` - it's private. Use `timer.end_time` or `timer.remaining_seconds` instead.

Don't import from `homeassistant.components.combined_lights` - this is a custom component, use `custom_components.combined_lights`.

Don't send command to the background when testing, for example simulation should  be run in the main thread.

## File organization

Tests mirror the source structure: `tests/combined_lights/test_*.py` corresponds to `custom_components/combined_lights/*.py`. Use `conftest.py` for shared fixtures.

Constants go in `const.py` using uppercase names. State strings use lowercase with hyphens (STATE_MOTION_AUTO = "motion-auto").

## Readme writing style

Write like a human, not an AI. Avoid flowery language, summary phrases, generic lists, vague statements, and common AI patterns. Use clear, accurate, and natural language with real-world detail and nuance.