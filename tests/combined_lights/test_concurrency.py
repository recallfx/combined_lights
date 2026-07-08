"""Tests for concurrency handling in Combined Lights."""

import asyncio
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.light import CombinedLight
from custom_components.combined_lights.const import CONF_ENABLE_BACK_PROPAGATION


def make_state_event(state: str, brightness: int | None = None):
    """Create a minimal state-change event."""
    new_state = MagicMock()
    new_state.state = state
    new_state.attributes = {"brightness": brightness}

    event = MagicMock()
    event.data = {"new_state": new_state}
    event.time_fired = None
    return event


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "name": "Test Light",
        CONF_ENABLE_BACK_PROPAGATION: False,
        "breakpoints": [25, 50, 75],
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
        "stage_1_lights": ["light.bulb_1"],
        "stage_2_lights": [],
        "stage_3_lights": [],
        "stage_4_lights": [],
    }
    return entry


class TestExpectedStateTracking:
    """Tests for expected state pre-tracking to prevent race conditions."""

    @pytest.mark.asyncio
    async def test_expected_states_tracked_before_service_call(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are tracked BEFORE awaiting the service call.

        This is critical to prevent the race condition where a state change event
        arrives before the expectation is set.
        """
        light = CombinedLight(hass, mock_entry)
        light.hass = hass

        # Track the order of operations
        operation_order = []

        # Mock the manual detector to record when track_expected_state is called
        original_track = light._manual_detector.track_expected_state

        def tracking_track_expected_state(entity_id, brightness):
            operation_order.append(("track", entity_id, brightness))
            return original_track(entity_id, brightness)

        light._manual_detector.track_expected_state = tracking_track_expected_state

        # Mock the light controller to record when turn_on_lights is called
        async def mock_turn_on_lights(lights, brightness, context):
            operation_order.append(("service_call", lights[0] if lights else None))
            return {entity: int(brightness / 100.0 * 255) for entity in lights}

        light._light_controller.turn_on_lights = mock_turn_on_lights

        light.async_write_ha_state = MagicMock()

        # Execute turn_on
        await light.async_turn_on(brightness=128)

        # Verify that track was called BEFORE service_call
        track_idx = None
        service_idx = None
        for i, op in enumerate(operation_order):
            if op[0] == "track" and op[1] == "light.bulb_1":
                track_idx = i
            if op[0] == "service_call" and op[1] == "light.bulb_1":
                service_idx = i

        assert track_idx is not None, "Expected state was not tracked"
        assert service_idx is not None, "Service call was not made"
        assert track_idx < service_idx, (
            f"Expected state must be tracked BEFORE service call. "
            f"Track at index {track_idx}, service at {service_idx}. "
            f"Order: {operation_order}"
        )

    @pytest.mark.asyncio
    async def test_expected_states_cleaned_on_failure(
        self, hass: HomeAssistant, mock_entry
    ):
        """Test that expected states are cleaned up when a zone fails."""
        # Add stage 2 with a light
        mock_entry.data["stage_2_lights"] = ["light.bulb_2"]

        light = CombinedLight(hass, mock_entry)
        light.hass = hass

        # Mock controller to fail for bulb_2
        async def failing_turn_on(lights, brightness, context):
            if "light.bulb_2" in lights:
                raise Exception("Light unavailable")
            return {entity: int(brightness / 100.0 * 255) for entity in lights}

        light._light_controller.turn_on_lights = failing_turn_on
        light.async_write_ha_state = MagicMock()

        # Execute turn_on
        await light.async_turn_on(brightness=255)

        # Verify that expected state for failed light was cleaned up
        assert "light.bulb_2" not in light._manual_detector._expected_states


@pytest.mark.asyncio
async def test_async_turn_on_concurrency(hass: HomeAssistant, mock_entry):
    """Test that async_turn_on is serialized."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass

    # Track _apply_changes_to_ha calls
    call_count = 0
    original_apply = light._apply_changes_to_ha

    async def slow_apply(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return await original_apply(*args, **kwargs)

    light._apply_changes_to_ha = slow_apply
    light.async_write_ha_state = MagicMock()

    # Start two turn_on calls concurrently
    task1 = asyncio.create_task(light.async_turn_on(brightness=100))
    task2 = asyncio.create_task(light.async_turn_on(brightness=200))

    await asyncio.gather(task1, task2)

    # Verify that _apply_changes_to_ha was called twice (serialized)
    assert call_count == 2


@pytest.mark.asyncio
async def test_lock_acquisition(hass: HomeAssistant, mock_entry):
    """Test that lock is acquired during operations."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    light.async_write_ha_state = MagicMock()

    # Track lock usage
    lock_acquired = False
    original_lock = light._lock

    class TrackingLock:
        async def __aenter__(self):
            nonlocal lock_acquired
            lock_acquired = True
            await original_lock.__aenter__()
            return self

        async def __aexit__(self, *args):
            await original_lock.__aexit__(*args)

        def locked(self):
            return original_lock.locked()

    light._lock = TrackingLock()

    await light.async_turn_on(brightness=100)

    # Verify lock was acquired
    assert lock_acquired is True


@pytest.mark.asyncio
async def test_back_propagation_concurrency(hass: HomeAssistant, mock_entry):
    """Test that back propagation respects the lock."""
    mock_entry.data[CONF_ENABLE_BACK_PROPAGATION] = True

    light = CombinedLight(hass, mock_entry)
    light.hass = hass

    # Track lock usage
    lock_acquired = False
    original_lock = light._lock

    class TrackingLock:
        async def __aenter__(self):
            nonlocal lock_acquired
            lock_acquired = True
            await original_lock.__aenter__()
            return self

        async def __aexit__(self, *args):
            await original_lock.__aexit__(*args)

        def locked(self):
            return original_lock.locked()

    light._lock = TrackingLock()

    # Manually test back propagation with some changes
    await light._async_apply_back_propagation({"light.bulb_1": 128}, "light.test")

    # Verify lock was acquired
    assert lock_acquired is True


@pytest.mark.asyncio
async def test_manual_batch_processing_respects_lock(
    hass: HomeAssistant, mock_entry
):
    """Test that debounced manual processing uses the operation lock."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    light.async_schedule_update_ha_state = MagicMock()
    light._debounce_delay = 0
    light._pending_manual_changes = {
        "light.bulb_1": {
            "state": "on",
            "brightness": 128,
            "timestamp": None,
        }
    }
    hass.states.async_set("light.bulb_1", "on", {"brightness": 128})

    lock_acquired = False
    original_lock = light._lock

    class TrackingLock:
        async def __aenter__(self):
            nonlocal lock_acquired
            lock_acquired = True
            await original_lock.__aenter__()
            return self

        async def __aexit__(self, *args):
            await original_lock.__aexit__(*args)

        def locked(self):
            return original_lock.locked()

    light._lock = TrackingLock()

    await light._process_pending_manual_changes()

    assert lock_acquired is True


@pytest.mark.asyncio
async def test_manual_event_during_processing_gets_followup_batch(
    hass: HomeAssistant, mock_entry
):
    """Manual events queued during processing should not be dropped."""
    mock_entry.data["stage_2_lights"] = ["light.bulb_2"]
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    light._debounce_delay = 0
    light._process_manual_change_batch = MagicMock()

    await light._lock.acquire()
    try:
        light._queue_manual_change("light.bulb_1", make_state_event("on", 128))
        first_task = light._debounce_task

        for _ in range(10):
            await asyncio.sleep(0)
            if not light._manual_change_debounce_sleeping:
                break

        assert first_task is not None
        assert not light._manual_change_debounce_sleeping
        assert not first_task.done()

        light._queue_manual_change("light.bulb_2", make_state_event("on", 200))

        assert first_task.cancelling() == 0
        assert "light.bulb_2" in light._pending_manual_changes
    finally:
        light._lock.release()

    await first_task
    followup_task = light._debounce_task
    if followup_task is not first_task:
        await followup_task

    processed_batches = [
        set(call.args[0])
        for call in light._process_manual_change_batch.call_args_list
    ]
    assert {"light.bulb_1"} in processed_batches
    assert {"light.bulb_2"} in processed_batches
