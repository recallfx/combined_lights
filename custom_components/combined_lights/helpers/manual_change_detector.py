"""Manual change detector helper."""
from __future__ import annotations

from homeassistant.core import Context, Event


class ManualChangeDetector:
    """Detects manual interventions in light states."""

    def __init__(self):
        """Initialize the manual change detector."""
        self._recent_contexts: list[str] = []
        self._max_recent_contexts = 5
        self._expected_states: dict[str, int] = {}
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
        context_is_external = (
            event.context
            and event.context.id not in self._recent_contexts
        )

        # If the event comes from one of our recent contexts, it's not manual
        if event.context and event.context.id in self._recent_contexts:
            # Even if brightness doesn't match (e.g. race condition or ramp up),
            # we know this change was triggered by us.
            if expected_brightness is not None:
                del self._expected_states[entity_id]
            return False, "recent_context_match"

        # Check if we have an expectation for this entity
        if expected_brightness is not None:
            # Handle "off" state specially
            if new_state and new_state.state == "off" and expected_brightness == 0:
                del self._expected_states[entity_id]
                return False, "expected_off_state"

            # Check brightness match within tolerance
            if actual_brightness is not None:
                brightness_diff = abs(actual_brightness - expected_brightness)
                if brightness_diff <= self._brightness_tolerance:
                    # Matches expectation
                    del self._expected_states[entity_id]
                    return False, "expected_brightness_match"
                else:
                    # Brightness doesn't match - this is manual
                    del self._expected_states[entity_id]
                    return True, "brightness_mismatch"
            else:
                # No brightness attribute but we expected one
                del self._expected_states[entity_id]
                return True, "brightness_mismatch"

        # No expectation set - check if we're currently updating
        if self._updating_lights and not context_is_external:
            # Integration is updating but no expectation was tracked
            return False, "integration_updating"

        # Check context
        if context_is_external:
            return True, "external_context"

        # No expectation and not our context - likely manual
        return True, "no_expectation"

    def cleanup_expected_state(self, entity_id: str) -> None:
        """Clean up expected state for an entity."""
        self._expected_states.pop(entity_id, None)
