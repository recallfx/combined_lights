"""Manual change detector helper."""

from __future__ import annotations

import logging

from homeassistant.core import Context, Event

_LOGGER = logging.getLogger(__name__)


class ManualChangeDetector:
    """Detects manual interventions in light states."""

    def __init__(self):
        """Initialize the manual change detector."""
        self._recent_contexts: list[str] = []
        self._max_recent_contexts = 5
        self._expected_states: dict[str, int] = {}
        self._updating_lights = False
        self._brightness_tolerance = 5
        # Track entities waiting for brightness confirmation after on@0 state
        self._pending_brightness: dict[str, float] = {}  # entity_id -> timestamp
        self._pending_brightness_timeout = 2.0  # seconds to wait for brightness

    def add_integration_context(self, context: Context) -> None:
        """Add an integration context to the recent history."""
        if context.id not in self._recent_contexts:
            self._recent_contexts.append(context.id)
            _LOGGER.debug("Added context %s (total: %d)", context.id[:8], len(self._recent_contexts))
            # Keep only the last N contexts
            if len(self._recent_contexts) > self._max_recent_contexts:
                self._recent_contexts.pop(0)

    def set_updating_flag(self, updating: bool) -> None:
        """Set the updating flag."""
        self._updating_lights = updating
        _LOGGER.debug("Updating flag set to %s", updating)

    def track_expected_state(self, entity_id: str, expected_brightness: int) -> None:
        """Track expected state for an entity."""
        self._expected_states[entity_id] = expected_brightness
        _LOGGER.debug("Tracking expected state: %s -> %d", entity_id, expected_brightness)

    def is_manual_change(self, entity_id: str, event: Event) -> tuple[bool, str]:
        """Determine if a state change was manual intervention.

        Args:
            entity_id: Entity that changed
            event: State change event

        Returns:
            Tuple of (is_manual, reason)
        """
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        actual_brightness = (
            new_state.attributes.get("brightness") if new_state else None
        )
        expected_brightness = self._expected_states.get(entity_id)
        event_context_id = event.context.id if event.context else "none"
        context_is_ours = event.context and event.context.id in self._recent_contexts
        
        # Log the incoming event details
        old_state_str = f"{old_state.state}@{old_state.attributes.get('brightness')}" if old_state else "none"
        new_state_str = f"{new_state.state}@{actual_brightness}" if new_state else "none"
        _LOGGER.info(
            "StateChange %s: %s -> %s | ctx=%s ours=%s | expected=%s | updating=%s",
            entity_id.split(".")[-1],
            old_state_str,
            new_state_str,
            event_context_id[:8] if event_context_id != "none" else "none",
            context_is_ours,
            expected_brightness,
            self._updating_lights,
        )

        # Detect transitional on@0 state (light turning on but brightness not yet reported)
        # Skip processing these - wait for actual brightness value
        if (new_state and new_state.state == "on" and 
            (actual_brightness is None or actual_brightness == 0) and
            old_state and old_state.state == "off"):
            # Track this entity as pending brightness confirmation
            import time
            self._pending_brightness[entity_id] = time.time()
            _LOGGER.info("  -> NOT manual (transitional_on_state, waiting for brightness)")
            return False, "transitional_on_state"

        # Check if this is a brightness confirmation for a pending transitional state
        if entity_id in self._pending_brightness:
            import time
            pending_time = self._pending_brightness[entity_id]
            elapsed = time.time() - pending_time
            del self._pending_brightness[entity_id]
            
            if elapsed <= self._pending_brightness_timeout:
                # This is the actual brightness arriving after on@0
                # It's still a manual/external change that should be processed
                _LOGGER.info(
                    "  -> MANUAL (brightness_confirmation after %.2fs, brightness=%s)",
                    elapsed,
                    actual_brightness,
                )
                return True, "brightness_confirmation"
            else:
                _LOGGER.info(
                    "  -> Pending brightness expired (%.2fs > %.2fs)",
                    elapsed,
                    self._pending_brightness_timeout,
                )

        # If the event comes from one of our recent contexts, it's not manual
        if context_is_ours:
            # Even if brightness doesn't match (e.g. race condition or ramp up),
            # we know this change was triggered by us.
            if expected_brightness is not None:
                del self._expected_states[entity_id]
            _LOGGER.info("  -> NOT manual (recent_context_match)")
            return False, "recent_context_match"

        # Check if we have an expectation for this entity
        if expected_brightness is not None:
            # Handle "off" state specially
            if new_state and new_state.state == "off" and expected_brightness == 0:
                del self._expected_states[entity_id]
                _LOGGER.info("  -> NOT manual (expected_off_state)")
                return False, "expected_off_state"

            # Check brightness match within tolerance
            if actual_brightness is not None:
                brightness_diff = abs(actual_brightness - expected_brightness)
                if brightness_diff <= self._brightness_tolerance:
                    # Matches expectation
                    del self._expected_states[entity_id]
                    _LOGGER.info("  -> NOT manual (expected_brightness_match, diff=%d)", brightness_diff)
                    return False, "expected_brightness_match"
                else:
                    # Brightness doesn't match - this is manual
                    del self._expected_states[entity_id]
                    _LOGGER.info("  -> MANUAL (brightness_mismatch, expected=%d got=%d diff=%d)", 
                                expected_brightness, actual_brightness, brightness_diff)
                    return True, "brightness_mismatch"
            else:
                # No brightness attribute but we expected one
                del self._expected_states[entity_id]
                _LOGGER.info("  -> MANUAL (brightness_mismatch, no brightness attr)")
                return True, "brightness_mismatch"

        # No expectation set - check if we're currently updating
        if self._updating_lights:
            # Integration is updating but no expectation was tracked
            _LOGGER.info("  -> NOT manual (integration_updating)")
            return False, "integration_updating"

        # External context with no expectation - manual
        _LOGGER.info("  -> MANUAL (external_context, no expectation)")
        return True, "external_context"

    def cleanup_expected_state(self, entity_id: str) -> None:
        """Clean up expected state for an entity."""
        if entity_id in self._expected_states:
            _LOGGER.debug("Cleaned up expected state for %s", entity_id)
        self._expected_states.pop(entity_id, None)
