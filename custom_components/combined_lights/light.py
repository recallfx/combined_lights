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
    CONF_ENABLE_BACK_PROPAGATION,
    CONF_STAGE_1_LIGHTS,
    CONF_STAGE_2_LIGHTS,
    CONF_STAGE_3_LIGHTS,
    CONF_STAGE_4_LIGHTS,
    DEFAULT_ENABLE_BACK_PROPAGATION,
    DOMAIN,
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
        self._pending_manual_changes: dict[str, int] = {}  # entity_id -> brightness
        self._manual_change_window = 0.15  # seconds to collect grouped changes
        self._manual_change_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

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
        integration_context = Context(id=str(uuid.uuid4()), user_id=None)
        self._manual_detector.add_integration_context(integration_context)

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

                # Handle manual change using coordinator
                self._handle_manual_change(entity_id)

            self.async_schedule_update_ha_state()

        self._remove_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, light_state_changed
        )

    def _sync_coordinator_from_ha(self) -> None:
        """Sync coordinator state from actual HA light states."""
        self._coordinator.sync_all_lights_from_ha()

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

    def _handle_manual_change(self, entity_id: str) -> None:
        """Handle a manual light change using the coordinator.
        
        Collects manual changes within a short window to detect patterns like
        KNX "all off" button that sends off to multiple lights simultaneously.
        """
        if not self.hass:
            return

        # Skip if we're currently updating
        if self._manual_detector._updating_lights:
            _LOGGER.debug("Skipping manual change handling while updating")
            return

        # Get the current brightness for this entity
        state = self.hass.states.get(entity_id)
        if state is None:
            return
        
        if state.state == "on":
            brightness = state.attributes.get("brightness", 255) or 255
        else:
            brightness = 0

        # Track this manual change
        self._pending_manual_changes[entity_id] = brightness
        _LOGGER.debug(
            "Manual change queued: %s -> %d (pending: %d changes)",
            entity_id,
            brightness,
            len(self._pending_manual_changes),
        )

        # Cancel any pending processing - we'll restart the timer
        if self._manual_change_task and not self._manual_change_task.done():
            self._manual_change_task.cancel()

        # Schedule processing after the collection window
        self._manual_change_task = self.hass.async_create_task(
            self._async_process_manual_changes()
        )

    async def _async_process_manual_changes(self) -> None:
        """Process collected manual changes after the collection window.
        
        This allows us to detect patterns like "all lights turned off" which
        should result in turning off the combined light without back-propagation.
        """
        try:
            # Wait for more changes to arrive
            await asyncio.sleep(self._manual_change_window)
        except asyncio.CancelledError:
            # More changes came in, this task was cancelled
            return

        # Snapshot and clear pending changes
        changes = self._pending_manual_changes.copy()
        self._pending_manual_changes.clear()

        if not changes:
            return

        # Analyze the pattern of changes
        all_controlled_lights = set(self._coordinator._lights.keys())
        changed_lights = set(changes.keys())
        all_off = all(b == 0 for b in changes.values())
        
        _LOGGER.debug(
            "Processing %d manual changes: %s (all_off=%s)",
            len(changes),
            changes,
            all_off,
        )

        # Sync coordinator state from HA
        self._coordinator.sync_all_lights_from_ha()

        # Case 1: All controlled lights were turned off
        if all_off and changed_lights == all_controlled_lights:
            _LOGGER.info("Manual change: all lights turned off simultaneously")
            self._coordinator.turn_off()
            self.async_schedule_update_ha_state()
            return

        # Case 2: All lights are now off (even if only some were in this batch)
        if not self._coordinator.is_on:
            _LOGGER.info("Manual change: all lights now off")
            self._coordinator.turn_off()
            self.async_schedule_update_ha_state()
            return

        # Case 3: Some lights still on - estimate overall brightness
        overall_pct = self._coordinator._estimate_overall_from_current_lights()
        
        if overall_pct > 0:
            self._coordinator._target_brightness = max(
                1, min(255, int(overall_pct / 100 * 255))
            )
            self._coordinator._is_on = True

        _LOGGER.info(
            "Manual change settled: %d changes, new overall brightness %.1f%%",
            len(changes),
            overall_pct,
        )

        # Back-propagate if enabled
        if self._back_propagation_enabled:
            back_prop_changes = self._coordinator.apply_back_propagation()
            if back_prop_changes:
                self._schedule_back_propagation(back_prop_changes, None)

        self.async_schedule_update_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from Home Assistant."""
        if self._remove_listener:
            self._remove_listener()
        if self._back_prop_task and not self._back_prop_task.done():
            self._back_prop_task.cancel()
        if self._manual_change_task and not self._manual_change_task.done():
            self._manual_change_task.cancel()
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
        caller_ctx = Context(id=str(uuid.uuid4()), user_id=None)
        self._manual_detector.add_integration_context(caller_ctx)

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
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Failed to apply back-propagation")
