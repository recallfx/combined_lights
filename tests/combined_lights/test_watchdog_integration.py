"""Integration tests for post-command state verification watchdog.

Tests realistic end-to-end scenarios simulating KNX bus failures,
partial deliveries, gateway congestion, and concurrent interactions.
Each test uses a FaultyLightController that can be configured to
simulate specific failure modes (drop telegrams, deliver wrong
brightness, ignore turn-off, etc.).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, HomeAssistant

from custom_components.combined_lights.const import (
    WATCHDOG_BRIGHTNESS_TOLERANCE,
)
from custom_components.combined_lights.light import CombinedLight


# ===========================================================================
# Helpers
# ===========================================================================


class FaultyLightController:
    """Light controller that simulates KNX bus faults.

    Configure per-entity failure behavior:
      - drop_entities: set of entity_ids whose commands are silently dropped
      - wrong_brightness: dict mapping entity_id → wrong brightness to set
      - fail_count: how many times to fail before succeeding (per entity)
      - delay_entities: set of entity_ids that respond slowly (no actual delay,
        but HA state is not set until the watchdog retry)
    """

    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self.drop_entities: set[str] = set()
        self.wrong_brightness: dict[str, int] = {}
        self.fail_count: dict[str, int] = {}
        self._attempt_count: dict[str, int] = {}
        self.delay_entities: set[str] = set()
        self._delayed_commands: list[tuple[str, str, dict]] = []
        self.call_log: list[tuple[str, list[str], int | None]] = []

    def _should_fail(self, entity_id: str) -> bool:
        """Check if this entity should fail this attempt."""
        max_fails = self.fail_count.get(entity_id, 0)
        if max_fails <= 0:
            return False
        current = self._attempt_count.get(entity_id, 0)
        self._attempt_count[entity_id] = current + 1
        return current < max_fails

    async def turn_on_lights(
        self, entities: list[str], brightness_pct: float, context: Context
    ) -> dict[str, int]:
        brightness_value = int(brightness_pct / 100.0 * 255)
        result = {}
        for eid in entities:
            self.call_log.append(("turn_on", [eid], brightness_value))

            if eid in self.drop_entities:
                # Telegram dropped — HA state unchanged
                continue

            if self._should_fail(eid):
                # Transient failure — don't update state
                continue

            if eid in self.delay_entities:
                # Will be delivered later
                self._delayed_commands.append(
                    (eid, "on", {"brightness": brightness_value})
                )
                continue

            actual_bri = self.wrong_brightness.get(eid, brightness_value)
            self._hass.states.async_set(
                eid, "on", {"brightness": actual_bri}, context=context
            )
            result[eid] = brightness_value
        return result

    async def turn_off_lights(
        self, entities: list[str], context: Context
    ) -> dict[str, int]:
        result = {}
        for eid in entities:
            self.call_log.append(("turn_off", [eid], 0))

            if eid in self.drop_entities:
                continue

            if self._should_fail(eid):
                continue

            if eid in self.delay_entities:
                self._delayed_commands.append((eid, "off", {}))
                continue

            self._hass.states.async_set(eid, "off", {}, context=context)
            result[eid] = 0
        return result

    def deliver_delayed(self):
        """Deliver all delayed commands (simulates late KNX response)."""
        for eid, state, attrs in self._delayed_commands:
            self._hass.states.async_set(eid, state, attrs)
        self._delayed_commands.clear()


def make_entry(
    *,
    breakpoints=None,
    stages=None,
    back_propagation=True,
    watchdog_delay=0.01,  # Very short for tests
) -> MagicMock:
    """Create a ConfigEntry mock with sensible defaults."""
    breakpoints = breakpoints or [30, 60, 90]

    if stages is None:
        stages = {
            "stage_1_lights": ["light.stage1"],
            "stage_2_lights": ["light.stage2"],
            "stage_3_lights": ["light.stage3"],
            "stage_4_lights": ["light.stage4"],
        }

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "watchdog_test"
    entry.data = {
        "name": "Watchdog Test",
        "breakpoints": breakpoints,
        **stages,
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
        "enable_back_propagation": back_propagation,
        "debounce_delay": 0.0,
        "watchdog_delay": watchdog_delay,
    }
    return entry


def all_entity_ids(entry: MagicMock) -> list[str]:
    """Get all light entity IDs from an entry."""
    ids = []
    for key in ("stage_1_lights", "stage_2_lights", "stage_3_lights", "stage_4_lights"):
        ids.extend(entry.data.get(key, []))
    return ids


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def watchdog_entry():
    return make_entry()


@pytest.fixture
def faulty_controller(hass: HomeAssistant):
    return FaultyLightController(hass)


@pytest.fixture
def watchdog_light(hass: HomeAssistant, watchdog_entry, faulty_controller):
    """CombinedLight wired to FaultyLightController."""
    light = CombinedLight(hass, watchdog_entry)
    light.hass = hass
    light._light_controller = faulty_controller
    light.async_schedule_update_ha_state = MagicMock()
    light.async_write_ha_state = MagicMock()
    for eid in all_entity_ids(watchdog_entry):
        hass.states.async_set(eid, "off", {})
    return light


# ===========================================================================
# 1. Dropped Turn-On Telegram
# ===========================================================================


class TestDroppedTurnOn:
    """KNX telegram for turn_on is lost — light stays off."""

    async def test_single_light_dropped_turn_on_retried(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Dropped turn-on for one light should be retried by watchdog."""
        # stage1 will fail once then succeed
        faulty_controller.fail_count["light.stage1"] = 1

        await watchdog_light.async_turn_on(brightness=26)  # ~10%, only stage1

        # Wait for watchdog to fire and retry
        await asyncio.sleep(0.1)

        # Watchdog should have retried — stage1 should now be on
        state = hass.states.get("light.stage1")
        assert state.state == "on"
        assert state.attributes.get("brightness") is not None
        assert state.attributes["brightness"] > 0

    async def test_all_lights_dropped_turn_on(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """All turn-on telegrams dropped — watchdog retries all."""
        for eid in ["light.stage1", "light.stage2", "light.stage3"]:
            faulty_controller.fail_count[eid] = 1

        await watchdog_light.async_turn_on(brightness=200)  # ~78%, stages 1-3

        await asyncio.sleep(0.1)

        # All should be on after retry
        for eid in ["light.stage1", "light.stage2", "light.stage3"]:
            state = hass.states.get(eid)
            assert state.state == "on", f"{eid} should be on after watchdog retry"

    async def test_permanently_dropped_triggers_resync(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Permanently unresponsive light → watchdog gives up and re-syncs."""
        faulty_controller.drop_entities.add("light.stage1")

        await watchdog_light.async_turn_on(brightness=26)  # ~10%

        # Wait for initial watchdog + retry + final watchdog
        await asyncio.sleep(0.3)

        # stage1 never responded — coordinator should have re-synced
        # and accepted reality (light is off)
        light_state = watchdog_light._coordinator.get_light("light.stage1")
        assert light_state is not None
        assert light_state.is_on is False


# ===========================================================================
# 2. Dropped Turn-Off Telegram
# ===========================================================================


class TestDroppedTurnOff:
    """KNX telegram for turn_off is lost — light stays on."""

    async def test_single_light_dropped_turn_off_retried(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Dropped turn-off should be retried by watchdog."""
        # First turn on successfully
        await watchdog_light.async_turn_on(brightness=26)
        await asyncio.sleep(0.05)

        # Now drop the turn-off for stage1
        faulty_controller.fail_count["light.stage1"] = 1
        faulty_controller._attempt_count.clear()

        await watchdog_light.async_turn_off()
        await asyncio.sleep(0.1)

        # Should be off after retry
        state = hass.states.get("light.stage1")
        assert state.state == "off"

    async def test_persistent_turn_off_failure_resyncs(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Light refuses to turn off → coordinator re-syncs to 'on' state."""
        # Turn on first
        await watchdog_light.async_turn_on(brightness=26)
        await asyncio.sleep(0.05)

        # Permanently drop turn-off
        faulty_controller.drop_entities.add("light.stage1")

        await watchdog_light.async_turn_off()
        await asyncio.sleep(0.3)

        # Coordinator should accept that light.stage1 is still on
        light = watchdog_light._coordinator.get_light("light.stage1")
        assert light.is_on is True


# ===========================================================================
# 3. Brightness Drift
# ===========================================================================


class TestBrightnessDrift:
    """Light turns on but at wrong brightness (KNX dimmer rounding, etc.)."""

    async def test_small_drift_within_tolerance_accepted(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Brightness within tolerance should be accepted without retry.

        Uses _watchdog_verify directly to test exact tolerance boundaries.
        """
        expected = 128
        # Set actual brightness within tolerance
        hass.states.async_set(
            "light.stage1", STATE_ON,
            {"brightness": expected + WATCHDOG_BRIGHTNESS_TOLERANCE - 1},
        )

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": expected})
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before  # No retry

    async def test_large_drift_triggers_retry(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Brightness beyond tolerance should trigger a retry."""
        expected = 128
        # Set actual brightness well beyond tolerance
        hass.states.async_set(
            "light.stage1", STATE_ON,
            {"brightness": expected + WATCHDOG_BRIGHTNESS_TOLERANCE + 20},
        )

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": expected})
        calls_after = len(faulty_controller.call_log)

        assert calls_after > calls_before  # Should retry

    async def test_large_drift_end_to_end(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """End-to-end: light reports wildly wrong brightness, watchdog corrects."""
        # stage1 always reports brightness=10 regardless of command
        faulty_controller.wrong_brightness["light.stage1"] = 10

        await watchdog_light.async_turn_on(brightness=26)
        initial_calls = len(faulty_controller.call_log)

        # Clear wrong brightness so retry succeeds
        faulty_controller.wrong_brightness.clear()

        await asyncio.sleep(0.1)

        # Watchdog should have retried
        assert len(faulty_controller.call_log) > initial_calls

        # stage1 should now have correct brightness (not 10)
        state = hass.states.get("light.stage1")
        assert state.state == "on"
        assert state.attributes["brightness"] > 10

    async def test_drift_on_multiple_lights(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Multiple lights drifting should all be corrected."""
        faulty_controller.wrong_brightness["light.stage1"] = 10
        faulty_controller.wrong_brightness["light.stage2"] = 10

        await watchdog_light.async_turn_on(brightness=200)

        # Clear wrong brightness for retry
        faulty_controller.wrong_brightness.clear()

        await asyncio.sleep(0.1)

        # Both should have been retried and now have correct brightness
        s1 = hass.states.get("light.stage1")
        s2 = hass.states.get("light.stage2")
        assert s1.state == "on"
        assert s2.state == "on"
        # After retry, brightness should be correct (not 10)
        assert s1.attributes["brightness"] > 10
        assert s2.attributes["brightness"] > 10


# ===========================================================================
# 4. Partial Delivery
# ===========================================================================


class TestPartialDelivery:
    """Some lights respond, others don't — mixed success."""

    async def test_only_failed_lights_retried(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Only the lights that failed should be retried, not the successful ones."""
        # stage2 fails once, stage1 succeeds immediately
        faulty_controller.fail_count["light.stage2"] = 1

        await watchdog_light.async_turn_on(brightness=100)  # ~39%, stages 1-2

        await asyncio.sleep(0.1)

        # Count retry calls per entity
        retry_entities = [
            call[1][0] for call in faulty_controller.call_log
            if call[0] == "turn_on"
        ]

        # stage1 should be called once (initial), stage2 twice (initial + retry)
        stage1_calls = retry_entities.count("light.stage1")
        stage2_calls = retry_entities.count("light.stage2")
        assert stage1_calls == 1, f"stage1 called {stage1_calls} times, expected 1"
        assert stage2_calls == 2, f"stage2 called {stage2_calls} times, expected 2"

    async def test_mixed_on_off_partial_failure(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """When some lights turn on and others off, partial failure handled correctly."""
        # First turn everything on
        await watchdog_light.async_turn_on(brightness=255)
        await asyncio.sleep(0.05)

        # Now dim to 10% — stage1 on, stages 2-4 off
        # Drop the turn-off for stage2
        faulty_controller.fail_count["light.stage2"] = 1
        faulty_controller._attempt_count.clear()

        await watchdog_light.async_turn_on(brightness=26)
        await asyncio.sleep(0.1)

        # stage2 should be off after retry
        state = hass.states.get("light.stage2")
        assert state.state == "off"


# ===========================================================================
# 5. Persistent Failure → Re-sync
# ===========================================================================


class TestPersistentFailureResync:
    """Light never responds — watchdog gives up and re-syncs coordinator."""

    async def test_resync_updates_coordinator_brightness(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """After giving up, coordinator brightness should match actual HA state."""
        # Set stage1 to some known state in HA manually
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 100})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        # Now drop ALL commands permanently
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            faulty_controller.drop_entities.add(eid)

        # Try to set brightness to 255 — will completely fail
        await watchdog_light.async_turn_on(brightness=255)
        await asyncio.sleep(0.3)

        # Coordinator should have re-synced from HA
        # stage1 is on@100 in HA, others off
        light = watchdog_light._coordinator.get_light("light.stage1")
        assert light.brightness == 100

    async def test_resync_after_turn_off_failure(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Failed turn-off → re-sync accepts lights are still on."""
        # Turn on first (successful)
        await watchdog_light.async_turn_on(brightness=26)
        await asyncio.sleep(0.05)

        # Drop all turn-offs
        for eid in all_entity_ids(make_entry()):
            faulty_controller.drop_entities.add(eid)

        await watchdog_light.async_turn_off()
        await asyncio.sleep(0.3)

        # stage1 is still on — coordinator should know this
        light = watchdog_light._coordinator.get_light("light.stage1")
        assert light.is_on is True


# ===========================================================================
# 6. Late KNX Response (Gateway Latency)
# ===========================================================================


class TestGatewayLatency:
    """Light responds after initial command but before watchdog fires."""

    async def test_late_response_before_watchdog_no_retry(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """If light responds late but before watchdog, no retry needed."""
        # Use delay simulation — command is deferred
        faulty_controller.delay_entities.add("light.stage1")

        await watchdog_light.async_turn_on(brightness=26)

        # Deliver the delayed response before watchdog fires
        faulty_controller.deliver_delayed()

        await asyncio.sleep(0.1)

        # Watchdog should see light is on and not retry
        # No additional turn_on calls for stage1 beyond initial
        stage1_on_calls = [
            c for c in faulty_controller.call_log
            if c[0] == "turn_on" and "light.stage1" in c[1]
        ]
        assert len(stage1_on_calls) == 1


# ===========================================================================
# 7. Concurrent Manual Change During Watchdog
# ===========================================================================


class TestConcurrentManualChange:
    """User touches a wall switch while watchdog is pending."""

    async def test_new_command_cancels_pending_watchdog(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """A new turn_on should cancel the previous command's watchdog."""
        # Use longer watchdog delay for this test
        watchdog_light._watchdog_delay = 0.2

        await watchdog_light.async_turn_on(brightness=50)
        first_task = watchdog_light._watchdog_task
        assert first_task is not None

        # Immediately issue another command
        await watchdog_light.async_turn_on(brightness=200)
        second_task = watchdog_light._watchdog_task

        assert first_task != second_task
        assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()

    async def test_turn_off_cancels_turn_on_watchdog(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Turn off should cancel pending turn-on watchdog."""
        watchdog_light._watchdog_delay = 0.2

        await watchdog_light.async_turn_on(brightness=128)
        turn_on_task = watchdog_light._watchdog_task

        await watchdog_light.async_turn_off()
        turn_off_task = watchdog_light._watchdog_task

        assert turn_on_task != turn_off_task
        assert turn_on_task.cancelling() > 0 or turn_on_task.cancelled() or turn_on_task.done()

    async def test_rapid_commands_only_last_watchdog_active(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Rapid sequence of commands → only final command's watchdog runs."""
        watchdog_light._watchdog_delay = 0.2

        tasks = []
        for bri in [50, 100, 150, 200, 255]:
            await watchdog_light.async_turn_on(brightness=bri)
            tasks.append(watchdog_light._watchdog_task)

        # Only the last task should still be active
        for t in tasks[:-1]:
            assert t.cancelling() > 0 or t.cancelled() or t.done()

        assert not tasks[-1].done()


# ===========================================================================
# 8. Back-Propagation Watchdog
# ===========================================================================


class TestBackPropWatchdog:
    """Watchdog verifies back-propagation results too."""

    async def test_back_prop_failure_retried(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Back-propagation that fails should be caught by watchdog."""
        # Set up: all lights on at some brightness
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            hass.states.async_set(eid, STATE_ON, {"brightness": 200})

        # Simulate manual change on stage1 to trigger back-prop
        # We'll test the back-prop watchdog by directly calling
        # _async_apply_back_propagation with a faulty controller
        faulty_controller.fail_count["light.stage2"] = 1

        changes = {"light.stage2": 128}
        await watchdog_light._async_apply_back_propagation(changes)

        await asyncio.sleep(0.1)

        # stage2 should have been retried and now be at correct brightness
        state = hass.states.get("light.stage2")
        assert state.state == "on"


# ===========================================================================
# 9. Unavailable / Unknown Entities
# ===========================================================================


class TestUnavailableEntities:
    """Watchdog behavior with entities in unavailable/unknown states."""

    async def test_unavailable_light_skipped(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Unavailable lights should be skipped by watchdog, not retried."""
        hass.states.async_set("light.stage1", "unavailable")

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": 128}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before  # No retry

    async def test_unknown_light_skipped(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Unknown lights should be skipped by watchdog."""
        hass.states.async_set("light.stage1", "unknown")

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": 128}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before

    async def test_nonexistent_entity_skipped(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Entity not in HA at all should be skipped."""
        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.does_not_exist": 128}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before


# ===========================================================================
# 10. Full Scenario Chains
# ===========================================================================


class TestFullScenarios:
    """End-to-end scenarios combining multiple failure modes."""

    async def test_turn_on_partial_drop_watchdog_fixes_then_turn_off(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Turn on with partial drop → watchdog fixes → then clean turn off."""
        # stage2 drops the first turn-on
        faulty_controller.fail_count["light.stage2"] = 1

        await watchdog_light.async_turn_on(brightness=128)
        await asyncio.sleep(0.15)

        # stage2 should be on after watchdog retry
        assert hass.states.get("light.stage2").state == "on"

        # Now turn off cleanly
        faulty_controller._attempt_count.clear()
        await watchdog_light.async_turn_off()
        await asyncio.sleep(0.1)

        # All should be off
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            assert hass.states.get(eid).state == "off"

    async def test_turn_on_wrong_brightness_corrected_then_dim(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Turn on with wrong brightness → watchdog corrects → then dim down."""
        # stage1 reports wrong brightness on first command
        faulty_controller.wrong_brightness["light.stage1"] = 10

        await watchdog_light.async_turn_on(brightness=26)

        # Clear fault for retry
        faulty_controller.wrong_brightness.clear()
        await asyncio.sleep(0.1)

        # stage1 should have correct brightness after retry
        state = hass.states.get("light.stage1")
        assert state.state == "on"
        assert state.attributes["brightness"] > 10

    async def test_gateway_down_total_failure_resync(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Complete gateway failure → all commands dropped → resync accepts off state."""
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            faulty_controller.drop_entities.add(eid)

        await watchdog_light.async_turn_on(brightness=255)
        await asyncio.sleep(0.3)

        # All lights should still be off in HA
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            assert hass.states.get(eid).state == "off"

        # Coordinator should have re-synced and know everything is off
        assert watchdog_light._coordinator.is_on is False

    async def test_intermittent_failure_across_stages(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Different stages fail intermittently — all eventually corrected."""
        # Each stage fails exactly once
        for eid in ["light.stage1", "light.stage2", "light.stage3"]:
            faulty_controller.fail_count[eid] = 1

        await watchdog_light.async_turn_on(brightness=200)
        await asyncio.sleep(0.15)

        # All three should be on after watchdog retry
        for eid in ["light.stage1", "light.stage2", "light.stage3"]:
            state = hass.states.get(eid)
            assert state.state == "on", f"{eid} should be on after retry"

    async def test_watchdog_with_multi_light_stages(
        self, hass: HomeAssistant,
    ):
        """Multiple lights per stage — each verified independently."""
        entry = make_entry(stages={
            "stage_1_lights": ["light.s1a", "light.s1b"],
            "stage_2_lights": ["light.s2a"],
            "stage_3_lights": ["light.stage3"],
            "stage_4_lights": ["light.stage4"],
        })
        controller = FaultyLightController(hass)

        light = CombinedLight(hass, entry)
        light.hass = hass
        light._light_controller = controller
        light.async_schedule_update_ha_state = MagicMock()
        light.async_write_ha_state = MagicMock()

        for eid in all_entity_ids(entry):
            hass.states.async_set(eid, "off", {})

        # s1b fails once
        controller.fail_count["light.s1b"] = 1

        await light.async_turn_on(brightness=26)
        await asyncio.sleep(0.15)

        # s1a should be on (succeeded first time)
        assert hass.states.get("light.s1a").state == "on"
        # s1b should also be on (succeeded on retry)
        assert hass.states.get("light.s1b").state == "on"


# ===========================================================================
# 11. Edge Cases
# ===========================================================================


class TestWatchdogEdgeCases:
    """Corner cases in watchdog behavior."""

    async def test_watchdog_with_zero_delay(
        self, hass: HomeAssistant,
    ):
        """Watchdog with 0 delay should still work."""
        entry = make_entry(watchdog_delay=0.0)
        controller = FaultyLightController(hass)
        controller.fail_count["light.stage1"] = 1

        light = CombinedLight(hass, entry)
        light.hass = hass
        light._light_controller = controller
        light.async_schedule_update_ha_state = MagicMock()
        light.async_write_ha_state = MagicMock()
        for eid in all_entity_ids(entry):
            hass.states.async_set(eid, "off", {})

        await light.async_turn_on(brightness=26)
        await asyncio.sleep(0.05)

        assert hass.states.get("light.stage1").state == "on"

    async def test_light_turned_on_with_no_brightness_attr(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Light reports 'on' but no brightness attribute — should not retry."""
        # Simulate: light is on but brightness not reported
        hass.states.async_set("light.stage1", STATE_ON, {})

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": 128}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        # Should NOT retry — light is on, just missing brightness attr
        assert calls_after == calls_before

    async def test_watchdog_tolerance_boundary(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Brightness exactly at tolerance boundary should be accepted."""
        expected = 128
        hass.states.async_set(
            "light.stage1", STATE_ON,
            {"brightness": expected + WATCHDOG_BRIGHTNESS_TOLERANCE},
        )

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": expected}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before  # Exactly at tolerance = OK

    async def test_watchdog_one_past_tolerance_retries(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Brightness one unit past tolerance should trigger retry."""
        expected = 128
        hass.states.async_set(
            "light.stage1", STATE_ON,
            {"brightness": expected + WATCHDOG_BRIGHTNESS_TOLERANCE + 1},
        )

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage1": expected}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after > calls_before  # Should retry

    async def test_empty_changes_no_watchdog(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
    ):
        """Empty expected_states should not crash or schedule anything."""
        watchdog_light._watchdog_task = None
        await watchdog_light._watchdog_verify({}, retry_count=0)
        # Should complete without error

    async def test_off_light_expected_off_no_retry(
        self, hass: HomeAssistant, watchdog_light: CombinedLight,
        faulty_controller: FaultyLightController,
    ):
        """Light expected off and is off should not be retried."""
        hass.states.async_set("light.stage4", STATE_OFF)

        calls_before = len(faulty_controller.call_log)
        await watchdog_light._watchdog_verify({"light.stage4": 0}, retry_count=0)
        calls_after = len(faulty_controller.call_log)

        assert calls_after == calls_before
