
import pytest
from unittest.mock import MagicMock
from homeassistant.core import Context, Event, State
from custom_components.combined_lights.helpers.manual_change_detector import ManualChangeDetector


class TestManualChangeDetectorTransition:
    """Tests for KNX and slow-light scenarios."""

    def test_our_context_always_trusted(self):
        """Events with our context are never manual, regardless of brightness."""
        detector = ManualChangeDetector()
        entity_id = "light.test"
        our_ctx = Context(id="our_context")
        detector.add_integration_context(our_ctx)
        
        # Expect OFF (0)
        detector.track_expected_state(entity_id, 0)
        
        # Event comes back with our context but intermediate brightness
        # (e.g., KNX light ramping down)
        event = MagicMock(spec=Event)
        event.context = our_ctx
        event.data = {
            "entity_id": entity_id,
            "new_state": State(entity_id, "on", {"brightness": 128})
        }
        
        is_manual, reason = detector.is_manual_change(entity_id, event)
        
        # Our context = not manual, even with mismatched brightness
        assert is_manual is False
        assert reason == "recent_context_match"
        
    def test_external_context_with_expected_brightness_not_manual(self):
        """External context but matching brightness is not manual (KNX echo)."""
        detector = ManualChangeDetector()
        entity_id = "light.test"
        detector.add_integration_context(Context(id="our_context"))
        
        # We commanded brightness 200
        detector.track_expected_state(entity_id, 200)
        
        # KNX fires its own event with different context, but correct brightness
        event = MagicMock(spec=Event)
        event.context = Context(id="knx_internal")
        event.data = {
            "entity_id": entity_id,
            "new_state": State(entity_id, "on", {"brightness": 200})
        }
        
        is_manual, reason = detector.is_manual_change(entity_id, event)
        
        assert is_manual is False
        assert reason == "expected_brightness_match"
        assert entity_id not in detector._expected_states

    def test_knx_button_different_brightness_is_manual(self):
        """KNX button changing brightness is detected as manual."""
        detector = ManualChangeDetector()
        entity_id = "light.test"
        detector.add_integration_context(Context(id="our_context"))
        
        # We expected brightness 255
        detector.track_expected_state(entity_id, 255)
        
        # KNX button dims to 50%
        event = MagicMock(spec=Event)
        event.context = Context(id="knx_button")
        event.data = {
            "entity_id": entity_id,
            "new_state": State(entity_id, "on", {"brightness": 128})
        }
        
        is_manual, reason = detector.is_manual_change(entity_id, event)
        
        assert is_manual is True
        assert reason == "brightness_mismatch"
        assert entity_id not in detector._expected_states

    def test_match_clears_expectation(self):
        """Test that a match clears the expectation immediately."""
        detector = ManualChangeDetector()
        entity_id = "light.test"
        
        # Expect OFF (0)
        detector.track_expected_state(entity_id, 0)
        
        # Simulate event: Light is OFF
        event = MagicMock(spec=Event)
        event.context = Context()
        event.data = {
            "entity_id": entity_id,
            "new_state": State(entity_id, "off", {"brightness": 0})
        }
        
        is_manual, reason = detector.is_manual_change(entity_id, event)
        
        assert is_manual is False
        assert reason == "expected_off_state"
        
        # Expectation should be removed
        assert entity_id not in detector._expected_states
