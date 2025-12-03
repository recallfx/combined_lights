"""Test race condition handling in manual change detection."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, Event, HomeAssistant

from custom_components.combined_lights.helpers.manual_change_detector import (
    ManualChangeDetector,
)
from custom_components.combined_lights.light import CombinedLight


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_123"
    entry.data = {
        "name": "Test Combined Light",
        "stage_1_lights": ["light.stage1"],
        "stage_2_lights": ["light.stage2"],
        "stage_3_lights": ["light.stage3"],
        "stage_4_lights": ["light.stage4"],
        "breakpoints": [25, 50, 75],
        "brightness_curve": "linear",
        "enable_back_propagation": True,
    }
    return entry


@pytest.fixture
def combined_light(hass: HomeAssistant, mock_entry):
    """Create a CombinedLight instance."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    return light


@pytest.fixture
def detector():
    """Create a ManualChangeDetector instance."""
    return ManualChangeDetector()


def create_state_event(
    entity_id: str,
    old_state: str,
    old_brightness: int | None,
    new_state: str,
    new_brightness: int | None,
    context_id: str = "external_ctx",
) -> Event:
    """Create a mock state change event."""
    old = MagicMock()
    old.state = old_state
    old.attributes = {"brightness": old_brightness}

    new = MagicMock()
    new.state = new_state
    new.attributes = {"brightness": new_brightness}

    ctx = Context(id=context_id)

    event = MagicMock(spec=Event)
    event.data = {
        "entity_id": entity_id,
        "old_state": old,
        "new_state": new,
    }
    event.context = ctx
    event.time_fired = asyncio.get_event_loop().time()

    return event


class TestTransitionalOnState:
    """Test handling of transitional on@0 states."""

    def test_transitional_on_state_not_manual(self, detector: ManualChangeDetector):
        """Transitional on@0 state should not be detected as manual change."""
        event = create_state_event(
            "light.test",
            old_state="off",
            old_brightness=None,
            new_state="on",
            new_brightness=0,  # transitional state
        )

        is_manual, reason = detector.is_manual_change("light.test", event)

        assert not is_manual
        assert reason == "transitional_on_state"

    def test_transitional_on_state_none_brightness(self, detector: ManualChangeDetector):
        """Transitional state with None brightness should not be manual."""
        event = create_state_event(
            "light.test",
            old_state="off",
            old_brightness=None,
            new_state="on",
            new_brightness=None,  # brightness not yet reported
        )

        is_manual, reason = detector.is_manual_change("light.test", event)

        assert not is_manual
        assert reason == "transitional_on_state"

    def test_actual_brightness_is_manual(self, detector: ManualChangeDetector):
        """Actual brightness value should be detected as manual change."""
        event = create_state_event(
            "light.test",
            old_state="off",
            old_brightness=None,
            new_state="on",
            new_brightness=255,  # actual brightness
        )

        is_manual, reason = detector.is_manual_change("light.test", event)

        assert is_manual
        assert reason == "external_context"

    def test_brightness_change_not_transitional(self, detector: ManualChangeDetector):
        """Brightness change on already-on light is not transitional."""
        event = create_state_event(
            "light.test",
            old_state="on",
            old_brightness=128,
            new_state="on",
            new_brightness=0,  # dimming to 0
        )

        # This is not transitional (old state was already on)
        is_manual, reason = detector.is_manual_change("light.test", event)

        # Should be detected as manual since it's an external change
        assert is_manual
        assert reason == "external_context"

    def test_pending_brightness_confirmation(self, detector: ManualChangeDetector):
        """Brightness arriving after transitional on@0 should be manual."""
        # First event: transitional on@0
        event1 = create_state_event(
            "light.test",
            old_state="off",
            old_brightness=None,
            new_state="on",
            new_brightness=0,
        )

        is_manual, reason = detector.is_manual_change("light.test", event1)
        assert not is_manual
        assert reason == "transitional_on_state"
        assert "light.test" in detector._pending_brightness

        # Second event: actual brightness arrives
        event2 = create_state_event(
            "light.test",
            old_state="on",
            old_brightness=0,
            new_state="on",
            new_brightness=200,
        )

        is_manual, reason = detector.is_manual_change("light.test", event2)
        assert is_manual
        assert reason == "brightness_confirmation"
        assert "light.test" not in detector._pending_brightness

    def test_pending_brightness_expires(self, detector: ManualChangeDetector):
        """Pending brightness should expire after timeout."""
        import time

        # Set a very short timeout for testing
        detector._pending_brightness_timeout = 0.01

        # First event: transitional on@0
        event1 = create_state_event(
            "light.test",
            old_state="off",
            old_brightness=None,
            new_state="on",
            new_brightness=0,
        )

        detector.is_manual_change("light.test", event1)
        assert "light.test" in detector._pending_brightness

        # Wait for timeout
        time.sleep(0.02)

        # Second event: brightness arrives late
        event2 = create_state_event(
            "light.test",
            old_state="on",
            old_brightness=0,
            new_state="on",
            new_brightness=200,
        )

        is_manual, reason = detector.is_manual_change("light.test", event2)
        # Should still be manual (external context) but not as brightness_confirmation
        assert is_manual
        assert reason == "external_context"


class TestDebounceQueueing:
    """Test the debounce mechanism for concurrent changes."""

    async def test_queue_manual_change_adds_to_pending(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual changes should be queued for debounced processing."""
        event = create_state_event(
            "light.stage1",
            old_state="on",
            old_brightness=255,
            new_state="off",
            new_brightness=None,
        )

        combined_light._queue_manual_change("light.stage1", event)

        assert "light.stage1" in combined_light._pending_manual_changes
        assert combined_light._pending_manual_changes["light.stage1"]["state"] == "off"

    async def test_multiple_changes_collected_before_processing(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Multiple concurrent changes should be collected before processing."""
        # Set up initial states - all lights on
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4", STATE_ON, {"brightness": 255})

        # Queue multiple off events (simulating KNX "all off")
        for entity_id in ["light.stage1", "light.stage2", "light.stage3"]:
            event = create_state_event(
                entity_id,
                old_state="on",
                old_brightness=255,
                new_state="off",
                new_brightness=None,
            )
            combined_light._queue_manual_change(entity_id, event)

        # All should be pending
        assert len(combined_light._pending_manual_changes) == 3
        assert all(
            change["state"] == "off"
            for change in combined_light._pending_manual_changes.values()
        )

    async def test_debounce_cancels_previous_task(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """New changes should cancel previous debounce task."""
        event1 = create_state_event(
            "light.stage1", "on", 255, "off", None
        )
        combined_light._queue_manual_change("light.stage1", event1)
        first_task = combined_light._debounce_task

        event2 = create_state_event(
            "light.stage2", "on", 255, "off", None
        )
        combined_light._queue_manual_change("light.stage2", event2)
        second_task = combined_light._debounce_task

        # Tasks should be different
        assert first_task != second_task
        # First task should be in cancelling state (cancel() was called)
        # Note: cancelled() returns False until the task actually finishes
        assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()


class TestConcurrentTurnOffPattern:
    """Test detection of concurrent turn-off patterns (KNX "all off")."""

    async def test_all_off_pattern_detected(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Concurrent turn-off should be detected and handled specially."""
        # Set up initial states - all lights on
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4", STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = 255

        # Simulate KNX "all off" - update HA states to off
        hass.states.async_set("light.stage1", STATE_OFF)
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        # Queue all off events
        for entity_id in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            event = create_state_event(
                entity_id, "on", 255, "off", None
            )
            combined_light._queue_manual_change(entity_id, event)

        # Process immediately (skip debounce delay for test)
        combined_light._debounce_delay = 0
        await combined_light._process_pending_manual_changes()

        # Should recognize all-off pattern and not trigger back-propagation
        # that would turn lights back on
        assert combined_light._coordinator._is_on is False


class TestHandleManualChangeSkipsTransitional:
    """Test that _handle_manual_change skips transitional states."""

    async def test_skip_transitional_on_zero(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual change should be skipped for transitional on@0 state."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 0})

        initial_brightness = combined_light._coordinator.target_brightness

        # This should be skipped
        combined_light._handle_manual_change("light.stage1")

        # Target brightness should not change
        assert combined_light._coordinator.target_brightness == initial_brightness

    async def test_skip_transitional_on_none(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual change should be skipped for transitional on with no brightness."""
        hass.states.async_set("light.stage1", STATE_ON, {})  # no brightness attr

        initial_brightness = combined_light._coordinator.target_brightness

        # This should be skipped
        combined_light._handle_manual_change("light.stage1")

        # Target brightness should not change
        assert combined_light._coordinator.target_brightness == initial_brightness

    async def test_process_actual_brightness(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual change should process actual brightness values."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        combined_light._handle_manual_change("light.stage1")

        # Should have updated coordinator state
        assert combined_light._coordinator.is_on is True
        # Target brightness should reflect the 50% brightness on stage 1
        assert combined_light._coordinator.target_brightness > 0


class TestHACoordinatorTransitionalState:
    """Test HA coordinator handling of transitional states."""

    async def test_sync_transitional_state_preserves_brightness(
        self, hass: HomeAssistant, mock_entry
    ):
        """Syncing transitional on@0 should preserve existing brightness."""
        from custom_components.combined_lights.helpers import (
            BrightnessCalculator,
            HACombinedLightsCoordinator,
        )

        calc = BrightnessCalculator(mock_entry)
        coordinator = HACombinedLightsCoordinator(hass, mock_entry, calc)

        # Register and set initial state
        coordinator.register_light("light.stage1", 1)
        light = coordinator._lights["light.stage1"]
        light.is_on = True
        light.brightness = 200

        # HA reports transitional on@0 state
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 0})

        # Sync should preserve existing brightness
        coordinator.sync_light_state_from_ha("light.stage1")

        assert light.is_on is True
        assert light.brightness == 200  # preserved, not changed to 1

    async def test_sync_new_light_transitional_gets_minimum(
        self, hass: HomeAssistant, mock_entry
    ):
        """Syncing transitional state for new light should get minimum brightness."""
        from custom_components.combined_lights.helpers import (
            BrightnessCalculator,
            HACombinedLightsCoordinator,
        )

        calc = BrightnessCalculator(mock_entry)
        coordinator = HACombinedLightsCoordinator(hass, mock_entry, calc)

        # Register light (starts with is_on=False, brightness=0)
        coordinator.register_light("light.stage1", 1)
        light = coordinator._lights["light.stage1"]

        # HA reports transitional on@0 state
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 0})

        # Sync should set minimum brightness, not 255
        coordinator.sync_light_state_from_ha("light.stage1")

        assert light.is_on is True
        assert light.brightness == 1  # minimum, not 255

    async def test_sync_actual_brightness(
        self, hass: HomeAssistant, mock_entry
    ):
        """Syncing actual brightness should work normally."""
        from custom_components.combined_lights.helpers import (
            BrightnessCalculator,
            HACombinedLightsCoordinator,
        )

        calc = BrightnessCalculator(mock_entry)
        coordinator = HACombinedLightsCoordinator(hass, mock_entry, calc)

        coordinator.register_light("light.stage1", 1)
        light = coordinator._lights["light.stage1"]

        # HA reports actual brightness
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 180})

        coordinator.sync_light_state_from_ha("light.stage1")

        assert light.is_on is True
        assert light.brightness == 180
