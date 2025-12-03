"""Tests for ManualChangeDetector helper."""

from homeassistant.const import STATE_ON
from homeassistant.core import Context, State

from custom_components.combined_lights.helpers import ManualChangeDetector


class TestManualChangeDetector:
    """Tests for manual override detection logic."""

    def _make_state(self, brightness: int) -> State:
        return State("light.demo", STATE_ON, {"brightness": brightness})

    def test_manual_detected_brightness_mismatch(self):
        """Test that brightness mismatch with external context is detected as manual."""
        detector = ManualChangeDetector()
        detector.add_integration_context(Context(id="integration"))
        detector.track_expected_state("light.demo", 255)

        # External context with wrong brightness = manual change
        event = type("Evt", (), {})()
        event.data = {"new_state": self._make_state(180)}
        event.context = Context(id="external")

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is True
        assert reason == "brightness_mismatch"
        assert "light.demo" not in detector._expected_states

    def test_integration_change_respected_with_context(self):
        detector = ManualChangeDetector()
        integration_ctx = Context(id="integration")
        detector.add_integration_context(integration_ctx)
        detector.track_expected_state("light.demo", 200)

        event = type("Evt", (), {})()
        event.data = {"new_state": self._make_state(200)}
        event.context = integration_ctx

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is False
        assert reason == "recent_context_match"

    def test_external_context_with_matching_brightness_not_manual(self):
        """KNX lights may fire events with their own context, but matching brightness."""
        detector = ManualChangeDetector()
        detector.add_integration_context(Context(id="integration"))
        detector.track_expected_state("light.demo", 200)

        # KNX fires its own event, but brightness matches what we commanded
        event = type("Evt", (), {})()
        event.data = {"new_state": self._make_state(200)}
        event.context = Context(id="knx_internal")

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is False
        assert reason == "expected_brightness_match"

    def test_knx_button_off_is_manual(self):
        """KNX button press turning off lights should be detected as manual."""
        detector = ManualChangeDetector()
        detector.add_integration_context(Context(id="integration"))
        # We expected light to be ON at 255
        detector.track_expected_state("light.demo", 255)

        # KNX button turns it off - external context, unexpected state
        event = type("Evt", (), {})()
        event.data = {"new_state": State("light.demo", "off", {})}
        event.context = Context(id="knx_button")

        is_manual, reason = detector.is_manual_change("light.demo", event)

        assert is_manual is True
        assert reason == "unexpected_off"
