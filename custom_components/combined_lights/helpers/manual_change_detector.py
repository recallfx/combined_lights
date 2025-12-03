"""Manual change detector helper."""

from __future__ import annotations

from homeassistant.core import Context, Event


class ManualChangeDetector:
    """Detects manual interventions in light states.

    Detection strategy:
    1. Context match: If the event context matches one we created, it's our change.
    2. Expected state: If context doesn't match but brightness matches expectation,
       it's likely our change propagated through another integration (e.g., KNX).
    3. Otherwise: It's a manual/external change.

    The key insight is that slow-responding lights (KNX, etc.) don't need timeouts.
    With blocking=True service calls, HA waits for state settlement. Any events
    during that time with our context are ours; events with external contexts
    but matching our expected brightness are also ours.
    """

    def __init__(self):
        """Initialize the manual change detector."""
        self._recent_contexts: list[str] = []
        self._max_recent_contexts = 10
        self._expected_states: dict[str, int] = {}  # entity_id -> expected brightness
        self._updating_lights = False
        self._brightness_tolerance = 5

    def add_integration_context(self, context: Context) -> None:
        """Add an integration context to the recent history."""
        if context.id not in self._recent_contexts:
            self._recent_contexts.append(context.id)
            # Keep only the last N contexts
            if len(self._recent_contexts) > self._max_recent_contexts:
                self._recent_contexts.pop(0)

    def set_updating_flag(self, updating: bool) -> None:
        """Set the updating flag."""
        self._updating_lights = updating

    def track_expected_state(self, entity_id: str, expected_brightness: int) -> None:
        """Track expected state for an entity."""
        self._expected_states[entity_id] = expected_brightness

    def is_manual_change(self, entity_id: str, event: Event) -> tuple[bool, str]:
        """Determine if a state change was manual intervention.

        Args:
            entity_id: Entity that changed
            event: State change event

        Returns:
            Tuple of (is_manual, reason)
        """
        new_state = event.data.get("new_state")
        actual_brightness = (
            new_state.attributes.get("brightness") if new_state else None
        )
        expected_brightness = self._expected_states.get(entity_id)
        is_our_context = (
            event.context and event.context.id in self._recent_contexts
        )

        # Priority 1: Context match - definitely our change
        if is_our_context:
            # Clear expectation since we got a response
            self._expected_states.pop(entity_id, None)
            return False, "recent_context_match"

        # Priority 2: Check expected state (for integrations that use their own context)
        if expected_brightness is not None:
            # Handle "off" state
            if new_state and new_state.state == "off":
                if expected_brightness == 0:
                    del self._expected_states[entity_id]
                    return False, "expected_off_state"
                else:
                    # Expected on, but got off - manual turn off
                    del self._expected_states[entity_id]
                    return True, "unexpected_off"

            # Check brightness match
            if actual_brightness is not None:
                brightness_diff = abs(actual_brightness - expected_brightness)
                if brightness_diff <= self._brightness_tolerance:
                    # Matches expectation - our change propagated
                    del self._expected_states[entity_id]
                    return False, "expected_brightness_match"
                else:
                    # Brightness mismatch - manual change
                    del self._expected_states[entity_id]
                    return True, "brightness_mismatch"

            # State is "on" but no brightness attribute - assume match if we expected on
            if new_state and new_state.state == "on" and expected_brightness > 0:
                del self._expected_states[entity_id]
                return False, "expected_on_state"

        # Priority 3: No expectation - check updating flag
        if self._updating_lights:
            # We're in the middle of updating, this might be a side effect
            return False, "integration_updating"

        # No expectation and not our context - manual change
        return True, "external_context"

    def cleanup_expected_state(self, entity_id: str) -> None:
        """Clean up expected state for an entity."""
        self._expected_states.pop(entity_id, None)
