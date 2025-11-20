"""Light platform for Combined Lights integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import uuid

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE_BACK_PROPAGATION, DEFAULT_ENABLE_BACK_PROPAGATION
from .helpers import (
    BrightnessCalculator,
    LightController,
    ManualChangeDetector,
    ZoneManager,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Combined Lights light entity."""
    # Create a single combined light entity
    async_add_entities([CombinedLight(entry)], True)


class CombinedLight(LightEntity):
    """Combined Light entity that controls multiple light zones."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Combined Light."""
        self._entry = entry
        self._attr_name = entry.data.get("name", "Combined Lights")
        self._attr_unique_id = f"{entry.entry_id}_combined_light"
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS

        # Helper instances
        self._brightness_calc = BrightnessCalculator(entry)
        self._light_controller = LightController(
            None
        )  # Will be set in async_added_to_hass
        self._manual_detector = ManualChangeDetector()
        self._zone_manager = ZoneManager(entry)

        # State tracking
        self._remove_listener = None
        self._target_brightness = 255
        self._target_brightness_initialized = False
        self._back_propagation_enabled = entry.data.get(
            CONF_ENABLE_BACK_PROPAGATION, DEFAULT_ENABLE_BACK_PROPAGATION
        )
        self._back_prop_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def async_added_to_hass(self) -> None:
        """Entity added to Home Assistant."""
        await super().async_added_to_hass()

        # Initialize light controller with hass instance
        self._light_controller = LightController(self.hass)

        # Initialize target brightness based on current state
        # Always attempt sync, even if lights appear off (handles KNX/slow integration startup delay)
        if not self._target_brightness_initialized:
            self._sync_target_brightness_from_lights()
            self._target_brightness_initialized = True

        # Prepare integration context
        integration_context = Context(id=str(uuid.uuid4()), user_id=None)
        self._manual_detector.add_integration_context(integration_context)

        # Listen for state changes of controlled lights
        all_lights = self._zone_manager.get_all_lights()

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

                # Update target brightness based on child light changes
                # Only update for manual changes - integration-initiated changes already have correct target
                self._update_target_brightness_from_children(
                    manual_update=True, changed_entity_id=entity_id
                )

            self.async_schedule_update_ha_state()

        self._remove_listener = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, light_state_changed
        )

    def _sync_target_brightness_from_lights(self) -> None:
        """Sync target brightness from actual light states (used during initialization)."""
        # Use the new bidirectional sync method
        self._update_target_brightness_from_children()

        # If still at default, try a fallback calculation
        if self._target_brightness == 255:
            light_zones = self._zone_manager.get_light_zones()

            # Get average brightness from each zone
            zone_brightness = {
                zone: self._zone_manager.get_average_brightness(self.hass, lights)
                for zone, lights in light_zones.items()
            }

            # Simple heuristic: use the highest brightness from active zones
            max_brightness = 0
            breakpoints = self._brightness_calc._get_breakpoints()

            if zone_brightness["stage_4"]:
                max_brightness = max(
                    max_brightness,
                    breakpoints[2] * 255 // 100 + zone_brightness["stage_4"] // 2,
                )
            elif zone_brightness["stage_3"]:
                max_brightness = max(
                    max_brightness,
                    breakpoints[1] * 255 // 100 + zone_brightness["stage_3"] // 2,
                )
            elif zone_brightness["stage_2"]:
                max_brightness = max(
                    max_brightness,
                    breakpoints[0] * 255 // 100 + zone_brightness["stage_2"] // 2,
                )
            elif zone_brightness["stage_1"]:
                max_brightness = max(max_brightness, zone_brightness["stage_1"])

            if max_brightness > 0:
                self._target_brightness = min(255, max_brightness)

    def _build_zone_brightness_map(
        self, brightness_pct: float, light_zones: dict[str, list[str]]
    ) -> dict[str, float]:
        """Calculate per-zone brightness targets for a given overall percentage."""

        return {
            zone_name: self._brightness_calc.calculate_zone_brightness(
                brightness_pct, zone_name
            )
            for zone_name in light_zones.keys()
        }

    def _update_target_brightness_from_children(
        self, *, manual_update: bool = False, changed_entity_id: str | None = None
    ) -> None:
        """Update target brightness based on current child light states."""

        if not self.hass:
            return

        # Skip updates while we are in the middle of applying our own changes.
        if self._manual_detector._updating_lights and not manual_update:
            _LOGGER.debug("Skipping sync while integration is updating lights")
            return

        zone_brightness = self._zone_manager.get_zone_brightness_dict(self.hass)
        all_off = all(
            brightness is None or brightness == 0
            for brightness in zone_brightness.values()
        )

        if all_off:
            _LOGGER.debug("All child lights off, preserving previous target")
            return

        if manual_update and not self._back_propagation_enabled:
            estimated_brightness_pct = (
                self._brightness_calc.estimate_manual_indicator_from_zones(
                    zone_brightness
                )
            )
        else:
            estimated_brightness_pct = (
                self._brightness_calc.estimate_overall_brightness_from_zones(
                    zone_brightness
                )
            )

        new_target = int((estimated_brightness_pct / 100.0) * 255)
        new_target = max(1, min(255, new_target))

        if abs(new_target - self._target_brightness) > 5:
            old_target = self._target_brightness
            self._target_brightness = new_target
            _LOGGER.info(
                "Target brightness updated from child light changes: %s -> %s (%.1f%%)",
                old_target,
                new_target,
                estimated_brightness_pct,
            )
        else:
            _LOGGER.debug(
                "Target brightness sync skipped (change too small): current=%s, estimated=%s",
                self._target_brightness,
                new_target,
            )

        if manual_update and self._back_propagation_enabled:
            self._schedule_back_propagation(estimated_brightness_pct, changed_entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Entity removed from Home Assistant."""
        if self._remove_listener:
            self._remove_listener()
        if self._back_prop_task and not self._back_prop_task.done():
            self._back_prop_task.cancel()
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if any controlled light is on."""
        return self._zone_manager.is_any_light_on(self.hass)

    @property
    def brightness(self) -> int | None:
        """Return the target brightness of the combined light."""
        if not self.is_on:
            return None
        return self._target_brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the combined light."""
        # Acquire lock to prevent concurrent updates
        if self._lock.locked():
            _LOGGER.debug("Waiting for lock in async_turn_on")

        async with self._lock:
            if ATTR_BRIGHTNESS in kwargs:
                self._target_brightness = kwargs[ATTR_BRIGHTNESS]

            self._attr_is_on = True

            # Get or create context
            caller_ctx = getattr(self, "context", None) or Context(
                id=str(uuid.uuid4()), user_id=None
            )
            self._manual_detector.add_integration_context(caller_ctx)

            # Convert brightness to percentage (0-100)
            brightness_pct = (self._target_brightness / 255.0) * 100

            _LOGGER.info(
                "Combined light async_turn_on called with target brightness %d (%.1f%%)",
                self._target_brightness,
                brightness_pct,
            )

            # Calculate zone brightnesses using helper
            light_zones = self._zone_manager.get_light_zones()
            zone_brightness = self._build_zone_brightness_map(
                brightness_pct, light_zones
            )

            _LOGGER.info(
                "Calculated zone brightnesses: %s",
                {k: f"{v:.1f}%" for k, v in zone_brightness.items()},
            )

            # Control all zones
            await self._control_all_zones(light_zones, zone_brightness, caller_ctx)

            # Log the operation
            stage = self._brightness_calc.get_stage_from_brightness(brightness_pct)
            _LOGGER.info(
                "Combined light turned on - overall: %s%% (stage %s) | stage_1: %s%% | stage_2: %s%% | stage_3: %s%% | stage_4: %s%%",
                int(brightness_pct),
                stage + 1,
                int(zone_brightness.get("stage_1", 0))
                if zone_brightness.get("stage_1", 0) > 0
                else 0,
                int(zone_brightness.get("stage_2", 0))
                if zone_brightness.get("stage_2", 0) > 0
                else 0,
                int(zone_brightness.get("stage_3", 0))
                if zone_brightness.get("stage_3", 0) > 0
                else 0,
                int(zone_brightness.get("stage_4", 0))
                if zone_brightness.get("stage_4", 0) > 0
                else 0,
            )

            self.async_write_ha_state()

    async def _control_all_zones(
        self,
        light_zones: dict[str, list[str]],
        zone_brightness: dict[str, float],
        context: Context,
    ) -> None:
        """Control all light zones based on calculated brightness values."""
        # Set updating flag to prevent feedback loops
        self._manual_detector.set_updating_flag(True)

        try:
            for zone_name, lights in light_zones.items():
                if not lights:
                    _LOGGER.debug("Skipping zone %s - no lights", zone_name)
                    continue

                brightness = zone_brightness[zone_name]
                _LOGGER.debug(
                    "Processing zone %s with lights %s at brightness %d",
                    zone_name,
                    lights,
                    brightness,
                )
                try:
                    if brightness > 0:
                        expected_states = await self._light_controller.turn_on_lights(
                            lights, brightness, context
                        )
                        _LOGGER.debug(
                            "Zone %s turned on with expected states: %s",
                            zone_name,
                            expected_states,
                        )
                        # Track expected states
                        for entity_id, brightness_val in expected_states.items():
                            self._manual_detector.track_expected_state(
                                entity_id, brightness_val
                            )
                    else:
                        expected_states = await self._light_controller.turn_off_lights(
                            lights, context
                        )
                        # Track expected states
                        for entity_id, brightness_val in expected_states.items():
                            self._manual_detector.track_expected_state(
                                entity_id, brightness_val
                            )
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error("Failed to control zone %s: %s", zone_name, err)
        finally:
            self._manual_detector.set_updating_flag(False)

    def _schedule_back_propagation(
        self, overall_pct: float, changed_entity_id: str | None = None
    ) -> None:
        """Schedule an asynchronous back-propagation run."""

        if not self.hass:
            return

        if self._back_prop_task and not self._back_prop_task.done():
            self._back_prop_task.cancel()

        self._back_prop_task = self.hass.async_create_task(
            self._async_apply_back_propagation(overall_pct, changed_entity_id)
        )

    async def _async_apply_back_propagation(
        self, overall_pct: float, changed_entity_id: str | None = None
    ) -> None:
        """Drive all zones to match the inferred overall brightness.

        Args:
            overall_pct: Target overall brightness percentage
            changed_entity_id: Entity that was manually changed (will be excluded)
        """

        light_zones = self._zone_manager.get_light_zones()
        zone_brightness = self._build_zone_brightness_map(overall_pct, light_zones)

        caller_ctx = Context(id=str(uuid.uuid4()), user_id=None)
        self._manual_detector.add_integration_context(caller_ctx)

        # Filter out the manually changed entity from each zone
        if changed_entity_id:
            filtered_zones = {
                zone: [light for light in lights if light != changed_entity_id]
                for zone, lights in light_zones.items()
            }
            _LOGGER.info(
                "Back-propagation excluding %s from zones. Original: %s, Filtered: %s",
                changed_entity_id,
                light_zones,
                filtered_zones,
            )
        else:
            filtered_zones = light_zones

        _LOGGER.info(
            "Back-propagation applying overall_pct=%.1f%% to zones with brightnesses: %s",
            overall_pct,
            zone_brightness,
        )

        try:
            # Acquire lock to prevent concurrent updates
            if self._lock.locked():
                _LOGGER.debug("Waiting for lock in back-propagation")

            async with self._lock:
                await self._control_all_zones(
                    filtered_zones, zone_brightness, caller_ctx
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to back-propagate manual change to all stages")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the combined light."""
        # Acquire lock to prevent concurrent updates
        if self._lock.locked():
            _LOGGER.debug("Waiting for lock in async_turn_off")

        async with self._lock:
            self._attr_is_on = False

            # Get or create context
            caller_ctx = getattr(self, "context", None) or Context(
                id=str(uuid.uuid4()), user_id=None
            )
            self._manual_detector.add_integration_context(caller_ctx)

            # Turn off all configured lights
            all_lights = self._zone_manager.get_all_lights()

            if all_lights:
                # Set updating flag to prevent feedback loops
                self._manual_detector.set_updating_flag(True)
                try:
                    expected_states = await self._light_controller.turn_off_lights(
                        all_lights, caller_ctx
                    )
                    # Track expected states
                    for entity_id, brightness_val in expected_states.items():
                        self._manual_detector.track_expected_state(
                            entity_id, brightness_val
                        )
                finally:
                    self._manual_detector.set_updating_flag(False)

            _LOGGER.info("Combined light turned off - all configured lights turned off")
            self.async_write_ha_state()
