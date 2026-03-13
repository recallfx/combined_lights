"""Light platform for Combined Lights integration."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
import uuid

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_DEBOUNCE_DELAY,
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_LIGHTS,
    CONF_WATCHDOG_DELAY,
    DEFAULT_DEBOUNCE_DELAY,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    DEFAULT_WATCHDOG_DELAY,
    DOMAIN,
    WATCHDOG_BRIGHTNESS_TOLERANCE,
    WATCHDOG_MAX_RETRIES,
)
from .helpers import (
    BrightnessCalculator,
    HACombinedLightsCoordinator,
    LightController,
    ManualChangeDetector,
)

_LOGGER = logging.getLogger(__name__)

# Load version from manifest.json to keep it in sync
_MANIFEST_PATH = Path(__file__).parent / "manifest.json"
_VERSION = json.loads(_MANIFEST_PATH.read_text()).get("version", "unknown")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Combined Lights light entity."""
    async_add_entities([CombinedLight(hass, entry)], True)


class CombinedLight(LightEntity, RestoreEntity):
    """Combined Light entity that controls multiple light zones."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the Combined Light."""
        self._entry = entry
        self._attr_name = entry.data.get("name", "Combined Lights")
        self._attr_unique_id = f"{entry.entry_id}_combined_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS

        # Device info for UI grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get("name", "Combined Lights"),
            manufacturer="Combined Lights",
            model="Virtual Light Controller",
            sw_version=_VERSION,
        )

        # Create the brightness calculator
        self._brightness_calc = BrightnessCalculator(entry)

        # Create the HA coordinator - uses same logic as simulation
        self._coordinator = HACombinedLightsCoordinator(
            hass, entry, self._brightness_calc
        )

        # Register lights with the coordinator
        self._register_lights_with_coordinator(entry)

        # Helper instances for HA-specific functionality
        self._light_controller = LightController(hass)
        self._manual_detector = ManualChangeDetector()

        # State tracking
        self._remove_listener = None
        self._target_brightness_initialized = False
        self._back_propagation_enabled = entry.data.get(
            CONF_ENABLE_BACK_PROPAGATION, DEFAULT_ENABLE_BACK_PROPAGATION
        )
        self._back_prop_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # Debounce state for collecting concurrent external changes
        self._pending_manual_changes: dict[str, dict] = {}
        self._debounce_task: asyncio.Task | None = None
        self._debounce_delay = entry.data.get(
            CONF_DEBOUNCE_DELAY, DEFAULT_DEBOUNCE_DELAY
        )

        # Post-command state verification watchdog
        self._watchdog_task: asyncio.Task | None = None
        self._watchdog_delay = entry.data.get(
            CONF_WATCHDOG_DELAY, DEFAULT_WATCHDOG_DELAY
        )

    def _register_lights_with_coordinator(self, entry: ConfigEntry) -> None:
        """Register all configured lights with the coordinator."""
        stage_configs = [
            (1, CONF_STAGE_1_LIGHTS),
            (2, CONF_STAGE_2_LIGHTS),
            (3, CONF_STAGE_3_LIGHTS),
            (4, CONF_STAGE_4_LIGHTS),
        ]
        for stage, conf_key in stage_configs:
            for entity_id in entry.data.get(conf_key, []):
                self._coordinator.register_light(entity_id, stage)

    async def async_added_to_hass(self) -> None:
        """Entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Restore previous state if available
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state == "on":
                self._attr_is_on = True
                if (brightness := last_state.attributes.get("brightness")) is not None:
                    self._coordinator._target_brightness = brightness
                    self._target_brightness_initialized = True
                    _LOGGER.debug("Restored brightness from last state: %s", brightness)

        # Update light controller with hass instance
        self._light_controller = LightController(self.hass)

        # Sync coordinator state from actual HA light states
        if not self._target_brightness_initialized:
            self._sync_coordinator_from_ha()
            self._target_brightness_initialized = True

        # Prepare integration context
        self._create_integration_context()

        # Listen for state changes of controlled lights
        all_lights = list(self._coordinator._lights.keys())

        @callback
        def light_state_changed(event: Event) -> None:
            """Handle controlled light state changes."""
            entity_id = event.data.get("entity_id")
            if entity_id not in all_lights:
                return

            # Check for manual intervention
            is_manual, reason = self._manual_detector.is_manual_change(entity_id, event)

            if is_manual:
                _LOGGER.debug(
                    "Manual intervention detected for %s: %s",
                    entity_id,
                    reason,
                )
                # Fire custom event for external change
                self.hass.bus.async_fire(
                    "combined_light.external_change",
                    {
                        "entity_id": entity_id,
                        "context_id": event.context.id if event.context else None,
                    },
                )

                # Collect manual change with debounce to handle concurrent events
                self._queue_manual_change(entity_id, event)

            self.async_schedule_update_ha_state()

        self._remove_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, light_state_changed
        )

    def _create_integration_context(self) -> Context:
        """Create a new context and register it with the manual change detector."""
        ctx = Context(id=str(uuid.uuid4()), user_id=None)
        self._manual_detector.add_integration_context(ctx)
        return ctx

    def _sync_coordinator_from_ha(self) -> None:
        """Sync coordinator state from actual HA light states."""
        self._coordinator.sync_all_lights_from_ha()

        # Update is_on from actual light states
        self._coordinator._is_on = any(
            lt.is_on for lt in self._coordinator._lights.values()
        )

        # Estimate overall brightness from current states
        if self._coordinator.is_on:
            overall_pct = self._coordinator._estimate_overall_from_current_lights()
            if overall_pct > 0:
                self._coordinator._target_brightness = max(
                    1, min(255, int(overall_pct / 100 * 255))
                )
                _LOGGER.debug(
                    "Synced target brightness from HA: %.1f%% (%d)",
                    overall_pct,
                    self._coordinator._target_brightness,
                )

    @callback
    def _queue_manual_change(self, entity_id: str, event: Event) -> None:
        """Queue a manual change for debounced processing.

        This collects concurrent external changes (e.g., KNX "all off")
        before processing to avoid race conditions.
        """
        new_state = event.data.get("new_state")
        if not new_state:
            return

        # Store the change with timestamp
        self._pending_manual_changes[entity_id] = {
            "state": new_state.state,
            "brightness": new_state.attributes.get("brightness"),
            "timestamp": event.time_fired,
        }

        _LOGGER.debug(
            "Queued manual change for %s (pending: %d)",
            entity_id.split(".")[-1],
            len(self._pending_manual_changes),
        )

        # Cancel existing debounce task and start a new one
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        self._debounce_task = self.hass.async_create_task(
            self._process_pending_manual_changes()
        )

    async def _process_pending_manual_changes(self) -> None:
        """Process pending manual changes after debounce delay.

        Handles all pending changes as a batch so that concurrent events
        (e.g., KNX "all off") are properly accounted for.
        """
        try:
            await asyncio.sleep(self._debounce_delay)
        except asyncio.CancelledError:
            # New changes came in, this task was replaced
            return

        if not self._pending_manual_changes:
            return

        # Take snapshot of pending changes and clear
        pending = dict(self._pending_manual_changes)
        self._pending_manual_changes.clear()

        _LOGGER.info(
            "Processing %d debounced manual changes: %s",
            len(pending),
            [eid.split(".")[-1] for eid in pending.keys()],
        )

        if not self.hass:
            return

        # Sync all lights from HA so coordinator knows current state
        self._coordinator.sync_all_lights_from_ha()

        # Classify changes by reading current HA state
        turn_off_stages: list[int] = []
        turn_on_entity: str | None = None
        turn_on_brightness: int = 0
        any_manual_turn_off = False
        changed_entities: set[str] = set()

        for eid in pending:
            state = self.hass.states.get(eid)
            if state is None or state.state in ("unavailable", "unknown"):
                continue

            light = self._coordinator.get_light(eid)
            if not light:
                continue

            changed_entities.add(eid)

            if state.state == "off":
                turn_off_stages.append(light.stage)
                any_manual_turn_off = True
            elif state.state == "on":
                raw_brightness = state.attributes.get("brightness")
                # Skip transitional on@0 states
                if raw_brightness is None or raw_brightness == 0:
                    continue
                if raw_brightness > turn_on_brightness:
                    turn_on_entity = eid
                    turn_on_brightness = raw_brightness

        if not changed_entities:
            return

        # Calculate new overall brightness from ALL changes
        if turn_off_stages:
            # For turn-offs: use the LOWEST activation point among all
            # turned-off stages. This respects the intent of concurrent turn-offs.
            min_overall = 100.0
            for stage in turn_off_stages:
                activation = (
                    self._coordinator._calculator.estimate_overall_from_single_light(
                        stage, 0.0
                    )
                )
                min_overall = min(min_overall, activation)

            any_on = any(lt.is_on for lt in self._coordinator._lights.values())
            self._coordinator._is_on = any_on

            if any_on and min_overall > 0:
                self._coordinator._target_brightness = max(
                    1, min(255, int(min_overall / 100 * 255))
                )

            _LOGGER.info(
                "  Batch turn-off: stages=%s → overall=%.1f%%",
                turn_off_stages,
                min_overall,
            )

        elif turn_on_entity:
            # For turn-ons: estimate from the brightest changed light
            light = self._coordinator.get_light(turn_on_entity)
            if light:
                brightness_pct = turn_on_brightness / 255.0 * 100
                overall_pct = (
                    self._coordinator._calculator.estimate_overall_from_single_light(
                        light.stage, brightness_pct
                    )
                )
                self._coordinator._is_on = True
                self._coordinator._target_brightness = max(
                    1, min(255, int(overall_pct / 100 * 255))
                )
                _LOGGER.info(
                    "  Batch turn-on: %s at %.1f%% → overall=%.1f%%",
                    turn_on_entity.split(".")[-1],
                    brightness_pct,
                    overall_pct,
                )
        else:
            return

        # Calculate back-propagation changes (excluding ALL manually changed entities)
        back_prop_changes = self._coordinator.apply_back_propagation(
            exclude_entity_id=changed_entities
        )

        # Log state
        lights_state = {
            eid.split(".")[-1]: f"{lt.is_on}@{lt.brightness}"
            for eid, lt in self._coordinator._lights.items()
        }
        _LOGGER.info("  Lights state: %s", lights_state)
        _LOGGER.info(
            "  Back-prop changes: %s (enabled=%s)",
            {k.split(".")[-1]: v for k, v in back_prop_changes.items()}
            if back_prop_changes
            else {},
            self._back_propagation_enabled,
        )

        # Filter back-propagation for turn-off intent
        if any_manual_turn_off and back_prop_changes:
            filtered = {}
            for eid, bri in back_prop_changes.items():
                if bri == 0:
                    # Turn-off is always allowed
                    filtered[eid] = bri
                else:
                    # Only adjust brightness of lights that are already on in HA
                    current = self.hass.states.get(eid)
                    if current and current.state == "on":
                        filtered[eid] = bri
                    # else: skip — would turn on a currently-off light

            removed = len(back_prop_changes) - len(filtered)
            if removed > 0:
                _LOGGER.info(
                    "  Filtered out %d turn-on changes for off lights", removed
                )
            back_prop_changes = filtered

        # Schedule back-propagation if enabled
        if self._back_propagation_enabled and back_prop_changes:
            _LOGGER.info(
                "  Scheduling back-propagation for %d lights",
                len(back_prop_changes),
            )
            self._schedule_back_propagation(back_prop_changes)

        self.async_schedule_update_ha_state()

    def _handle_manual_change(self, entity_id: str) -> None:
        """Handle a manual light change using the coordinator.

        Note: This method is kept for backward compatibility (used by tests).
        The main processing path is _process_pending_manual_changes which
        handles batch changes directly.
        """
        if not self.hass:
            return

        # Get the new brightness from HA state
        state = self.hass.states.get(entity_id)
        if state is None:
            return

        # Skip unavailable/unknown states — not a real turn-off
        if state.state in ("unavailable", "unknown"):
            _LOGGER.info(
                "SKIP manual change for %s: state is %s",
                entity_id.split(".")[-1],
                state.state,
            )
            return

        manual_turn_off = False
        if state.state == "on":
            raw_brightness = state.attributes.get("brightness")
            # Handle transitional on@0 state - skip processing
            if raw_brightness is None or raw_brightness == 0:
                _LOGGER.info(
                    "SKIP manual change for %s: transitional on@0 state",
                    entity_id.split(".")[-1],
                )
                return
            brightness = raw_brightness
        else:
            brightness = 0
            manual_turn_off = True

        _LOGGER.info(
            "HANDLE manual change: %s state=%s brightness=%d",
            entity_id.split(".")[-1],
            state.state,
            brightness,
        )

        # Sync all lights from HA first so coordinator knows current state
        # This is critical for correct estimation when a light is turned off
        self._coordinator.sync_all_lights_from_ha()

        # Log current state of all lights
        lights_state = {
            eid.split(".")[-1]: f"{lt.is_on}@{lt.brightness}"
            for eid, lt in self._coordinator._lights.items()
        }
        _LOGGER.info("  Lights state after sync: %s", lights_state)

        # Use coordinator to handle the change - same logic as simulation
        overall_pct, back_prop_changes = self._coordinator.handle_manual_light_change(
            entity_id, brightness
        )

        _LOGGER.info(
            "  Result: overall=%.1f%%, back_prop_enabled=%s, changes=%s",
            overall_pct,
            self._back_propagation_enabled,
            {k.split(".")[-1]: v for k, v in back_prop_changes.items()}
            if back_prop_changes
            else {},
        )

        # Filter back-propagation for turn-off intent: don't turn on currently-off
        # lights, but allow brightness adjustments for already-on lights
        if manual_turn_off and back_prop_changes:
            filtered_changes = {}
            for eid, bri in back_prop_changes.items():
                if bri == 0:
                    filtered_changes[eid] = bri  # Turn-off always allowed
                else:
                    current = self.hass.states.get(eid)
                    if current and current.state == "on":
                        filtered_changes[eid] = bri  # Adjust already-on light
                    # else: skip — would turn on a currently-off light
            removed = len(back_prop_changes) - len(filtered_changes)
            if removed > 0:
                _LOGGER.info(
                    "  Filtered out %d turn-on changes for off lights",
                    removed,
                )
            back_prop_changes = filtered_changes

        # Schedule back-propagation if enabled
        if self._back_propagation_enabled and back_prop_changes:
            _LOGGER.info(
                "  Scheduling back-propagation for %d lights", len(back_prop_changes)
            )
            self._schedule_back_propagation(back_prop_changes, entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from Home Assistant."""
        if self._remove_listener:
            self._remove_listener()
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        if self._back_prop_task and not self._back_prop_task.done():
            self._back_prop_task.cancel()
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return if entity is available (at least one member light is available)."""
        if not self.hass:
            return False
        for entity_id in self._coordinator._lights:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in ("unavailable", "unknown"):
                return True
        return False

    @property
    def is_on(self) -> bool:
        """Return true if any controlled light is on."""
        if not self.hass:
            return False
        for entity_id in self._coordinator._lights:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                return True
        return False

    @property
    def brightness(self) -> int | None:
        """Return the target brightness of the combined light."""
        if not self.is_on:
            return None
        return self._coordinator.target_brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the combined light."""
        if self._lock.locked():
            _LOGGER.debug("Waiting for lock in async_turn_on")

        async with self._lock:
            brightness = kwargs.get(ATTR_BRIGHTNESS)

            # Use coordinator to calculate changes - same logic as simulation
            changes = self._coordinator.turn_on(brightness)

            self._attr_is_on = True

            # Get or create context
            caller_ctx = getattr(self, "context", None) or Context(
                id=str(uuid.uuid4()), user_id=None
            )
            self._manual_detector.add_integration_context(caller_ctx)

            _LOGGER.info(
                "Combined light turn_on: target=%d (%.1f%%), stage=%d",
                self._coordinator.target_brightness,
                self._coordinator.target_brightness_pct,
                self._coordinator.current_stage,
            )

            # Apply changes to actual HA lights
            any_success = await self._apply_changes_to_ha(changes, caller_ctx)

            if not any_success:
                _LOGGER.warning(
                    "No lights were successfully controlled - state may be inaccurate"
                )
                self._attr_is_on = False

            # Schedule watchdog to verify lights reached expected state
            # Always schedule, even on failure — KNX may have partially delivered
            self._schedule_watchdog(changes)

            # Log zone brightnesses
            zone_brightness = self._coordinator.get_zone_brightness_for_ha()
            _LOGGER.info(
                "Zone brightnesses: %s",
                {k: f"{v:.1f}%" for k, v in zone_brightness.items()},
            )

            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the combined light."""
        if self._lock.locked():
            _LOGGER.debug("Waiting for lock in async_turn_off")

        async with self._lock:
            # Use coordinator to calculate changes - same logic as simulation
            changes = self._coordinator.turn_off()

            self._attr_is_on = False

            # Get or create context
            caller_ctx = getattr(self, "context", None) or Context(
                id=str(uuid.uuid4()), user_id=None
            )
            self._manual_detector.add_integration_context(caller_ctx)

            # Apply changes to actual HA lights
            await self._apply_changes_to_ha(changes, caller_ctx)

            # Schedule watchdog to verify lights turned off
            self._schedule_watchdog(changes)

            _LOGGER.info("Combined light turned off")
            self.async_write_ha_state()

    async def _apply_changes_to_ha(
        self, changes: dict[str, int], context: Context
    ) -> bool:
        """Apply brightness changes to actual HA lights.

        Args:
            changes: Dict mapping entity_id to brightness (0-255)
            context: HA context for the service calls

        Returns:
            True if at least one light was successfully controlled
        """
        self._manual_detector.set_updating_flag(True)
        any_success = False

        _LOGGER.info(
            "APPLY changes to HA: %s (context=%s)",
            {k.split(".")[-1]: v for k, v in changes.items()},
            context.id[:8],
        )

        try:
            # Group by brightness for efficient service calls
            lights_on: dict[int, list[str]] = {}
            lights_off: list[str] = []

            for entity_id, brightness in changes.items():
                if brightness > 0:
                    if brightness not in lights_on:
                        lights_on[brightness] = []
                    lights_on[brightness].append(entity_id)
                else:
                    lights_off.append(entity_id)

            # Turn on lights grouped by brightness
            for brightness, entities in lights_on.items():
                # Track expected states BEFORE service call
                for entity_id in entities:
                    self._manual_detector.track_expected_state(entity_id, brightness)

                try:
                    brightness_pct = brightness / 255.0 * 100
                    _LOGGER.info(
                        "  Calling turn_on for %s at %.1f%%",
                        [e.split(".")[-1] for e in entities],
                        brightness_pct,
                    )
                    result = await self._light_controller.turn_on_lights(
                        entities, brightness_pct, context
                    )
                    if result:
                        any_success = True
                except Exception as err:
                    _LOGGER.error("Failed to turn on lights %s: %s", entities, err)
                    for entity_id in entities:
                        self._manual_detector.cleanup_expected_state(entity_id)

            # Turn off lights
            if lights_off:
                for entity_id in lights_off:
                    self._manual_detector.track_expected_state(entity_id, 0)

                _LOGGER.info(
                    "  Calling turn_off for %s", [e.split(".")[-1] for e in lights_off]
                )

                try:
                    result = await self._light_controller.turn_off_lights(
                        lights_off, context
                    )
                    if result:
                        any_success = True
                except Exception as err:
                    _LOGGER.error("Failed to turn off lights %s: %s", lights_off, err)
                    for entity_id in lights_off:
                        self._manual_detector.cleanup_expected_state(entity_id)

        finally:
            self._manual_detector.set_updating_flag(False)

        return any_success

    def _schedule_back_propagation(
        self, changes: dict[str, int], exclude_entity_id: str | None = None
    ) -> None:
        """Schedule back-propagation to apply changes to HA lights."""
        if not self.hass:
            return

        if self._back_prop_task and not self._back_prop_task.done():
            self._back_prop_task.cancel()

        self._back_prop_task = self.hass.async_create_task(
            self._async_apply_back_propagation(changes, exclude_entity_id)
        )

    async def _async_apply_back_propagation(
        self, changes: dict[str, int], exclude_entity_id: str | None = None
    ) -> None:
        """Apply back-propagation changes to HA lights."""
        caller_ctx = self._create_integration_context()

        _LOGGER.info(
            "Back-propagation: applying changes %s (excluding %s)",
            {k: v for k, v in changes.items()},
            exclude_entity_id,
        )

        try:
            if self._lock.locked():
                _LOGGER.debug("Waiting for lock in back-propagation")

            async with self._lock:
                await self._apply_changes_to_ha(changes, caller_ctx)

            # Verify back-propagation results too
            self._schedule_watchdog(changes)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Failed to apply back-propagation")

    # ── Post-command state verification watchdog ──────────────────────

    def _schedule_watchdog(
        self, expected_states: dict[str, int], retry_count: int = 0
    ) -> None:
        """Schedule a delayed check to verify lights reached expected state.

        Args:
            expected_states: Dict mapping entity_id to expected brightness (0-255)
            retry_count: How many retries have already been attempted
        """
        if not self.hass:
            return

        # Cancel any existing watchdog — only the latest command matters
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()

        self._watchdog_task = self.hass.async_create_task(
            self._watchdog_verify(expected_states, retry_count)
        )

    async def _watchdog_verify(
        self, expected_states: dict[str, int], retry_count: int = 0
    ) -> None:
        """Verify lights reached expected state after a delay.

        If mismatches are found:
          - retry_count < MAX_RETRIES → retry the failed commands
          - retry_count >= MAX_RETRIES → re-sync coordinator from HA (accept reality)
        """
        try:
            await asyncio.sleep(self._watchdog_delay)
        except asyncio.CancelledError:
            return

        if not self.hass:
            return

        mismatches: dict[str, dict] = {}

        for entity_id, expected_brightness in expected_states.items():
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                # Can't verify — skip
                continue

            actual_on = state.state == "on"
            actual_brightness = state.attributes.get("brightness")
            expected_on = expected_brightness > 0

            if expected_on and not actual_on:
                # Should be on but is off
                mismatches[entity_id] = {
                    "expected": expected_brightness,
                    "actual": 0,
                    "issue": "expected_on_got_off",
                }
            elif not expected_on and actual_on:
                # Should be off but is on
                mismatches[entity_id] = {
                    "expected": 0,
                    "actual": actual_brightness or 0,
                    "issue": "expected_off_got_on",
                }
            elif expected_on and actual_on and actual_brightness is not None:
                diff = abs(actual_brightness - expected_brightness)
                if diff > WATCHDOG_BRIGHTNESS_TOLERANCE:
                    mismatches[entity_id] = {
                        "expected": expected_brightness,
                        "actual": actual_brightness,
                        "issue": f"brightness_drift_{diff}",
                    }

        if not mismatches:
            _LOGGER.debug("Watchdog: all %d lights verified OK", len(expected_states))
            return

        _LOGGER.warning(
            "Watchdog: %d/%d lights mismatched after %.1fs: %s",
            len(mismatches),
            len(expected_states),
            self._watchdog_delay,
            {
                eid.split(".")[
                    -1
                ]: f"expected={m['expected']} actual={m['actual']} ({m['issue']})"
                for eid, m in mismatches.items()
            },
        )

        if retry_count < WATCHDOG_MAX_RETRIES:
            # Retry only the mismatched commands
            retry_changes = {eid: m["expected"] for eid, m in mismatches.items()}
            _LOGGER.info(
                "Watchdog: retrying %d lights (attempt %d/%d)",
                len(retry_changes),
                retry_count + 1,
                WATCHDOG_MAX_RETRIES,
            )

            caller_ctx = self._create_integration_context()

            try:
                async with self._lock:
                    await self._apply_changes_to_ha(retry_changes, caller_ctx)
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOGGER.exception("Watchdog: retry failed")
                return

            # Schedule another verification after the retry
            self._schedule_watchdog(retry_changes, retry_count + 1)
        else:
            # Max retries reached — accept reality and re-sync
            _LOGGER.warning(
                "Watchdog: max retries reached, re-syncing coordinator from HA"
            )
            self._sync_coordinator_from_ha()
            self.async_schedule_update_ha_state()
