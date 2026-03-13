"""Validation suite for back-propagation correctness.

These tests verify that back-propagation works correctly in realistic
Home Assistant scenarios, confirming that identified bugs are fixed.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, Event, HomeAssistant

from custom_components.combined_lights.helpers import (
    BrightnessCalculator,
    HACombinedLightsCoordinator,
)
from custom_components.combined_lights.helpers.manual_change_detector import (
    ManualChangeDetector,
)
from custom_components.combined_lights.light import CombinedLight


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backprop_entry():
    """Config entry with back-propagation enabled, default breakpoints [30, 60, 90]."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "backprop_test"
    entry.data = {
        "name": "Backprop Test",
        "stage_1_lights": ["light.stage1"],
        "stage_2_lights": ["light.stage2"],
        "stage_3_lights": ["light.stage3"],
        "stage_4_lights": ["light.stage4"],
        "breakpoints": [30, 60, 90],
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
        "enable_back_propagation": True,
        "debounce_delay": 0.0,
    }
    return entry


@pytest.fixture
def combined_light(hass: HomeAssistant, backprop_entry):
    """CombinedLight with back-propagation enabled and zero debounce."""
    light = CombinedLight(hass, backprop_entry)
    light.hass = hass
    # Stub out HA state writer — entity is not fully registered in test context
    light.async_schedule_update_ha_state = MagicMock()
    return light


def create_state_event(
    entity_id: str,
    old_state: str,
    old_brightness: int | None,
    new_state: str,
    new_brightness: int | None,
    context_id: str = "external_ctx",
) -> Event:
    """Create a mock state-change event."""
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


# ===========================================================================
# FIX 1 – _updating_lights flag no longer drops legitimate manual changes
# ===========================================================================


class TestUpdatingFlagFixed:
    """Verify that manual changes are NOT dropped when _updating_lights is True."""

    async def test_manual_change_processed_despite_updating_flag(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Manual changes should be processed even when _updating_lights is True."""
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            hass.states.async_set(eid, STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = 255

        # Even with updating flag on, manual change should be processed
        combined_light._manual_detector.set_updating_flag(True)

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 128})
        combined_light._handle_manual_change("light.stage1")

        target_after = combined_light._coordinator.target_brightness
        assert target_after != 255, (
            f"Manual change should be processed even with updating flag. "
            f"Got {target_after}"
        )

        combined_light._manual_detector.set_updating_flag(False)

    async def test_updating_flag_true_during_apply_changes(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """_updating_lights is True during service calls (for is_manual_change)."""
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            hass.states.async_set(eid, STATE_ON, {"brightness": 255})

        flag_was_true = False

        async def observing_turn_on(entities, brightness_pct, context):
            nonlocal flag_was_true
            if combined_light._manual_detector._updating_lights:
                flag_was_true = True
            return {e: int(brightness_pct / 100 * 255) for e in entities}

        combined_light._light_controller.turn_on_lights = observing_turn_on
        combined_light._light_controller.turn_off_lights = AsyncMock(return_value={})

        ctx = Context(id="test_ctx")
        await combined_light._apply_changes_to_ha({"light.stage1": 128}, ctx)

        assert flag_was_true, (
            "_updating_lights should be True during service calls "
            "(used by is_manual_change to filter our own events)"
        )
        assert not combined_light._manual_detector._updating_lights


# ===========================================================================
# FIX 2 – Coordinator state not corrupted when all lights off
# ===========================================================================


class TestCoordinatorStateFixed:
    """Verify that coordinator internal state stays consistent when all off."""

    def test_no_corruption_after_all_off(self):
        """After turning off the last light, internal states should all stay off."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "breakpoints": [30, 60, 90],
            "stage_1_curve": "linear",
            "stage_2_curve": "linear",
            "stage_3_curve": "linear",
            "stage_4_curve": "linear",
        }
        calc = BrightnessCalculator(entry)
        hass = MagicMock()
        coord = HACombinedLightsCoordinator(hass, entry, calc)

        coord.register_light("light.s1", 1)
        coord.register_light("light.s2", 2)
        coord.register_light("light.s3", 3)

        coord.turn_on(brightness=int(70 / 100 * 255))

        # Manually mark all lights as off
        for eid in ["light.s3", "light.s2", "light.s1"]:
            coord._lights[eid].is_on = False
            coord._lights[eid].brightness = 0

        coord.handle_manual_light_change("light.s1", 0)

        assert coord.is_on is False

        # FIX: no internal lights should be re-marked as on
        lights_on = [lt.entity_id for lt in coord.get_lights() if lt.is_on]
        assert lights_on == [], (
            f"All lights should be off internally, but got: {lights_on}"
        )

    def test_estimate_correct_after_all_off(self):
        """After all-off, _estimate_overall_from_current_lights returns 0."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "breakpoints": [30, 60, 90],
            "stage_1_curve": "linear",
            "stage_2_curve": "linear",
            "stage_3_curve": "linear",
            "stage_4_curve": "linear",
        }
        calc = BrightnessCalculator(entry)
        hass = MagicMock()
        coord = HACombinedLightsCoordinator(hass, entry, calc)

        coord.register_light("light.s1", 1)
        coord.register_light("light.s2", 2)

        coord.turn_on(brightness=int(50 / 100 * 255))

        coord._lights["light.s1"].is_on = False
        coord._lights["light.s1"].brightness = 0
        coord._lights["light.s2"].is_on = False
        coord._lights["light.s2"].brightness = 0

        coord.handle_manual_light_change("light.s2", 0)

        estimate = coord._estimate_overall_from_current_lights()
        assert estimate == 0.0, (
            f"All off → estimate should be 0, got {estimate}"
        )


# ===========================================================================
# FIX 3 – Batch processing handles simultaneous off correctly
# ===========================================================================


class TestBatchProcessingFixed:
    """Verify that simultaneous changes are all considered, not just one."""

    async def test_simultaneous_off_uses_lowest_activation(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """KNX "all off" for stage 2+3: overall should use the lowest activation."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 179})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 147})
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 66})
        hass.states.async_set("light.stage4", STATE_OFF)
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = int(70 / 100 * 255)

        # Both turn off
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)

        # Directly populate pending changes (avoids auto-task creation)
        for eid in ["light.stage3", "light.stage2"]:
            combined_light._pending_manual_changes[eid] = {
                "state": "off",
                "brightness": None,
                "timestamp": 0,
            }

        # Stub out back-prop scheduling and HA state update
        combined_light._schedule_back_propagation = MagicMock()

        await combined_light._process_pending_manual_changes()

        target_pct = combined_light._coordinator.target_brightness / 255 * 100

        # FIX: should be 30% (stage 2 activation), not 60% (stage 3 activation)
        assert abs(target_pct - 30.0) < 2.0, (
            f"Both stage 2+3 off → overall should be ~30%, got {target_pct:.1f}%"
        )

    async def test_simultaneous_off_order_independent(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Result should be the same regardless of queue insertion order."""
        def run_scenario(queue_order):
            hass.states.async_set("light.stage1", STATE_ON, {"brightness": 179})
            hass.states.async_set("light.stage2", STATE_OFF)
            hass.states.async_set("light.stage3", STATE_OFF)
            hass.states.async_set("light.stage4", STATE_OFF)
            combined_light._coordinator._is_on = True
            combined_light._coordinator._target_brightness = int(70 / 100 * 255)

            # Directly populate pending changes (avoids auto-task creation)
            combined_light._pending_manual_changes.clear()
            for eid in queue_order:
                combined_light._pending_manual_changes[eid] = {
                    "state": "off",
                    "brightness": None,
                    "timestamp": 0,
                }

        # Stub out back-prop scheduling
        combined_light._schedule_back_propagation = MagicMock()

        # Order A: stage2 first
        run_scenario(["light.stage2", "light.stage3"])
        await combined_light._process_pending_manual_changes()
        result_a = combined_light._coordinator.target_brightness / 255 * 100

        # Order B: stage3 first
        run_scenario(["light.stage3", "light.stage2"])
        await combined_light._process_pending_manual_changes()
        result_b = combined_light._coordinator.target_brightness / 255 * 100

        # FIX: both orders should give the same result
        assert abs(result_a - result_b) < 1.0, (
            f"Results should be order-independent: A={result_a:.1f}%, B={result_b:.1f}%"
        )

    async def test_correct_estimation_uses_all_light_states(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """_estimate_overall_from_current_lights works correctly after sync."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 179})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        combined_light._coordinator.sync_all_lights_from_ha()

        estimate = combined_light._coordinator._estimate_overall_from_current_lights()
        assert 65 < estimate < 75, (
            f"Stage 1 at 179 → estimate should be ~70%, got {estimate:.1f}%"
        )


# ===========================================================================
# FIX 4 – Turn-off filter allows brightness adjustments for on lights
# ===========================================================================


class TestTurnOffFilterFixed:
    """Verify the improved filter allows dimming already-on lights."""

    async def test_turn_off_allows_brightness_adjustment_for_on_lights(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Turning off stage 3 should adjust stage 1 and 2 brightness."""
        calc = combined_light._coordinator._calculator
        s1_at_80 = int(calc.calculate_zone_brightness(80, 1) / 100 * 255)
        s2_at_80 = int(calc.calculate_zone_brightness(80, 2) / 100 * 255)
        s3_at_80 = int(calc.calculate_zone_brightness(80, 3) / 100 * 255)

        combined_light._coordinator._target_brightness = int(80 / 100 * 255)
        combined_light._coordinator._is_on = True

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": s1_at_80})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": s2_at_80})
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": s3_at_80})
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled_changes = {}
        def capture(changes, exclude=None):
            scheduled_changes.update(changes)
        combined_light._schedule_back_propagation = capture

        # Manually turn off stage 3
        hass.states.async_set("light.stage3", STATE_OFF)
        combined_light._handle_manual_change("light.stage3")

        # FIX: stage 1 and 2 should get brightness adjustments
        has_stage1 = "light.stage1" in scheduled_changes and scheduled_changes["light.stage1"] > 0
        has_stage2 = "light.stage2" in scheduled_changes and scheduled_changes["light.stage2"] > 0

        assert has_stage1, (
            f"Stage 1 should get brightness adjustment, got {scheduled_changes}"
        )
        assert has_stage2, (
            f"Stage 2 should get brightness adjustment, got {scheduled_changes}"
        )

    async def test_turn_off_still_blocks_turning_on_off_lights(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Turn-off filter should still prevent turning on currently-off lights."""
        combined_light._coordinator._target_brightness = 255
        combined_light._coordinator._is_on = True

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 255})
        hass.states.async_set("light.stage4", STATE_OFF)  # already off

        scheduled_changes = {}
        def capture(changes, exclude=None):
            scheduled_changes.update(changes)
        combined_light._schedule_back_propagation = capture

        # Turn off stage 3
        hass.states.async_set("light.stage3", STATE_OFF)
        combined_light._handle_manual_change("light.stage3")

        # Stage 4 was off → should NOT be turned on
        if "light.stage4" in scheduled_changes:
            assert scheduled_changes["light.stage4"] == 0, (
                "Stage 4 was off, should not be turned on by back-prop"
            )


# ===========================================================================
# FIX 5 – Context buffer increased, fewer false positives
# ===========================================================================


class TestContextBufferFixed:
    """Verify the increased context buffer prevents false manual detection."""

    def test_context_buffer_holds_20(self):
        """Buffer should hold 20 contexts (up from 5)."""
        detector = ManualChangeDetector()
        assert detector._max_recent_contexts == 20

        # Add 20 contexts — all should survive
        contexts = []
        for i in range(20):
            ctx = Context(id=f"ctx_{i}")
            detector.add_integration_context(ctx)
            contexts.append(ctx)

        for ctx in contexts:
            assert ctx.id in detector._recent_contexts

    def test_21st_context_evicts_first(self):
        """The 21st context should evict the first."""
        detector = ManualChangeDetector()

        contexts = []
        for i in range(21):
            ctx = Context(id=f"ctx_{i}")
            detector.add_integration_context(ctx)
            contexts.append(ctx)

        assert contexts[0].id not in detector._recent_contexts
        for ctx in contexts[1:]:
            assert ctx.id in detector._recent_contexts

    def test_6_contexts_no_longer_causes_eviction(self):
        """6 contexts should all be preserved (was the old limit)."""
        detector = ManualChangeDetector()

        first_ctx = Context(id="first_context")
        detector.add_integration_context(first_ctx)
        for i in range(5):
            detector.add_integration_context(Context(id=f"filler_{i}"))

        # FIX: first context should NOT be evicted with 6 additions
        assert first_ctx.id in detector._recent_contexts

        event = create_state_event(
            "light.test", "off", None, "on", 128,
            context_id=first_ctx.id,
        )

        is_manual, reason = detector.is_manual_change("light.test", event)
        assert is_manual is False, (
            f"Event with our context should NOT be manual. reason={reason}"
        )


# ===========================================================================
# FIX 6 – Multiple lights per stage uses average
# ===========================================================================


class TestMultiLightSameStageFixed:
    """Verify same-stage lights are averaged in estimation."""

    def test_average_brightness_used_for_estimation(self):
        """Two lights in stage 1 should be averaged."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "breakpoints": [30, 60, 90],
            "stage_1_curve": "linear",
            "stage_2_curve": "linear",
            "stage_3_curve": "linear",
            "stage_4_curve": "linear",
        }
        calc = BrightnessCalculator(entry)
        hass = MagicMock()
        coord = HACombinedLightsCoordinator(hass, entry, calc)

        coord.register_light("light.s1a", 1)
        coord.register_light("light.s1b", 1)

        # Light A at ~50%, Light B at 100%
        coord._lights["light.s1a"].is_on = True
        coord._lights["light.s1a"].brightness = 128  # ~50.2%
        coord._lights["light.s1b"].is_on = True
        coord._lights["light.s1b"].brightness = 255  # 100%

        estimate = coord._estimate_overall_from_current_lights()

        # Average: (50.2 + 100) / 2 ≈ 75.1% → overall ≈ 75%
        assert 70 < estimate < 80, (
            f"Average of 50% and 100% should give ~75% overall, got {estimate:.1f}%"
        )


# ===========================================================================
# NEW: Verify unavailable/unknown states are not treated as turn-offs
# ===========================================================================


class TestUnavailableStateHandling:
    """Verify unavailable/unknown states are ignored by _handle_manual_change."""

    async def test_unavailable_state_skipped(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Light going unavailable should not trigger back-propagation."""
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            hass.states.async_set(eid, STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = 255

        initial_target = combined_light._coordinator.target_brightness

        # Light becomes unavailable
        hass.states.async_set("light.stage3", "unavailable")
        combined_light._handle_manual_change("light.stage3")

        # Target should be unchanged
        assert combined_light._coordinator.target_brightness == initial_target

    async def test_unknown_state_skipped(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Light going unknown should not trigger back-propagation."""
        for eid in ["light.stage1", "light.stage2", "light.stage3", "light.stage4"]:
            hass.states.async_set(eid, STATE_ON, {"brightness": 255})
        combined_light._coordinator._is_on = True
        combined_light._coordinator._target_brightness = 255

        initial_target = combined_light._coordinator.target_brightness

        hass.states.async_set("light.stage3", "unknown")
        combined_light._handle_manual_change("light.stage3")

        assert combined_light._coordinator.target_brightness == initial_target


# ===========================================================================
# NEW: Verify debounce task cleanup on removal
# ===========================================================================


class TestCleanupOnRemoval:
    """Verify all async tasks are cancelled when entity is removed."""

    async def test_debounce_task_cancelled(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """_debounce_task should be cancelled on removal."""
        # Create a debounce task
        event = create_state_event("light.stage1", "on", 255, "off", None)
        combined_light._debounce_delay = 10.0  # long delay so it's still pending
        combined_light._queue_manual_change("light.stage1", event)

        assert combined_light._debounce_task is not None
        assert not combined_light._debounce_task.done()

        # Remove entity
        await combined_light.async_will_remove_from_hass()

        # Task should be cancelled (or in cancelling state pending next event loop tick)
        task = combined_light._debounce_task
        assert task.cancelling() > 0 or task.cancelled() or task.done()


# ===========================================================================
# End-to-end back-propagation scenarios
# ===========================================================================


class TestEndToEndBackPropagation:
    """End-to-end scenarios verifying back-propagation correctness."""

    async def test_wall_switch_dim_stage1_backpropagates_to_stage2(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """User dims stage 1 via wall switch → stage 2 should adjust."""
        calc = combined_light._coordinator._calculator

        combined_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        s1_target = int(calc.calculate_zone_brightness(50, 1) / 100 * 255)
        s2_target = int(calc.calculate_zone_brightness(50, 2) / 100 * 255)

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": s1_target})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": s2_target})
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled_changes = {}
        def capture(changes, exclude=None):
            scheduled_changes.update(changes)
        combined_light._schedule_back_propagation = capture

        new_s1 = int(30 / 100 * 255)
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": new_s1})
        combined_light._handle_manual_change("light.stage1")

        new_overall = combined_light._coordinator.target_brightness / 255 * 100
        assert 25 < new_overall < 35, f"Overall should be ~29%, got {new_overall:.1f}%"

    async def test_turn_on_stage3_backpropagates(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """User turns on stage 3 → stage 1 and 2 increase."""
        calc = combined_light._coordinator._calculator
        combined_light._coordinator.turn_on(brightness=int(40 / 100 * 255))

        s1_at_40 = int(calc.calculate_zone_brightness(40, 1) / 100 * 255)
        s2_at_40 = int(calc.calculate_zone_brightness(40, 2) / 100 * 255)

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": s1_at_40})
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": s2_at_40})
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled_changes = {}
        def capture(changes, exclude=None):
            scheduled_changes.update(changes)
        combined_light._schedule_back_propagation = capture

        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 128})
        combined_light._handle_manual_change("light.stage3")

        new_overall = combined_light._coordinator.target_brightness / 255 * 100
        assert new_overall > 60, f"Overall should be >60%, got {new_overall:.1f}%"

        assert "light.stage1" in scheduled_changes
        assert scheduled_changes["light.stage1"] > s1_at_40

    async def test_backprop_roundtrip_consistency(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Setting overall to X% then reading back should give ~X%."""
        calc = combined_light._coordinator._calculator

        for pct in [10, 25, 30, 35, 50, 60, 65, 80, 90, 95, 100]:
            target = max(1, int(pct / 100 * 255))
            combined_light._coordinator.turn_on(brightness=target)

            zone_brightness: dict[int, float | None] = {}
            for light in combined_light._coordinator.get_lights():
                if light.is_on and light.brightness > 0:
                    zone_brightness[light.stage] = light.brightness_pct
                else:
                    zone_brightness[light.stage] = None

            estimated = calc.estimate_overall_from_zones(zone_brightness)
            actual_pct = target / 255 * 100

            assert abs(estimated - actual_pct) < 3.0, (
                f"At {pct}%: estimate={estimated:.1f}% vs actual={actual_pct:.1f}%"
            )


# ===========================================================================
# Estimation method comparison
# ===========================================================================


class TestEstimationMethodComparison:
    """Compare single-light vs all-lights estimation methods."""

    def test_single_vs_all_lights_agree_for_simple_case(self):
        """When only one light changed, both methods should agree closely."""
        entry = MagicMock(spec=ConfigEntry)
        entry.data = {
            "breakpoints": [30, 60, 90],
            "stage_1_curve": "linear",
            "stage_2_curve": "linear",
            "stage_3_curve": "linear",
            "stage_4_curve": "linear",
        }
        calc = BrightnessCalculator(entry)
        hass = MagicMock()
        coord = HACombinedLightsCoordinator(hass, entry, calc)

        coord.register_light("light.s1", 1)
        coord.register_light("light.s2", 2)
        coord.register_light("light.s3", 3)

        coord.turn_on(brightness=int(70 / 100 * 255))

        # Turn off stage 3
        coord._lights["light.s3"].is_on = False
        coord._lights["light.s3"].brightness = 0

        single = calc.estimate_overall_from_single_light(3, 0.0)
        all_est = coord._estimate_overall_from_current_lights()

        # Single-light returns 60% (activation point)
        assert abs(single - 60.0) < 0.1

        # All-lights uses highest active stage (stage 2, still at 70% brightness)
        # These methods intentionally give different results for different use cases
        assert all_est > single
