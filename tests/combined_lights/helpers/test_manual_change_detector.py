"""Tests for ManualChangeDetector helper."""

from homeassistant.const import STATE_ON
from homeassistant.core import Context, State

from custom_components.combined_lights.helpers import ManualChangeDetector


class TestManualChangeDetector:
    """Tests for manual override detection logic."""

    def _make_state(self, brightness: int) -> State:
        return State("light.demo", STATE_ON, {"brightness": brightness})

    def test_manual_detected_during_update(self):
        detector = ManualChangeDetector()
        detector.add_integration_context(Context(id="integration"))
        detector.set_updating_flag(True)
        detector.track_expected_state("light.demo", 255)

        event = type("Evt", (), {})()
        event.data = {"new_state": self._make_state(180)}
        event.context = Context(id="manual")

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is True
        assert reason == "brightness_mismatch"
        assert "light.demo" not in detector._expected_states

    def test_integration_change_respected_during_update(self):
        detector = ManualChangeDetector()
        integration_ctx = Context(id="integration")
        detector.add_integration_context(integration_ctx)
        detector.set_updating_flag(True)
        detector.track_expected_state("light.demo", 200)

        event = type("Evt", (), {})()
        event.data = {"new_state": self._make_state(200)}
        event.context = integration_ctx

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is False
        assert reason == "recent_context_match"
