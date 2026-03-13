"""Full integration pipeline testing suite.

Tests realistic end-to-end scenarios that simulate what happens on a real
Home Assistant instance: forward brightness distribution, reverse
back-propagation, concurrent KNX events, state transitions, curve roundtrips,
multi-light stages, filter logic, context tracking, state restoration,
and error resilience.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, Event, HomeAssistant, State

from custom_components.combined_lights.helpers import (
    BrightnessCalculator,
    HACombinedLightsCoordinator,
)
from custom_components.combined_lights.helpers.manual_change_detector import (
    ManualChangeDetector,
)
from custom_components.combined_lights.light import CombinedLight


# ===========================================================================
# Helpers
# ===========================================================================


class SimulatedLightController:
    """Light controller that actually updates HA states.

    When service calls are made, this writes back to hass.states so the
    coordinator can read them — creating a closed-loop simulation.
    """

    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    async def turn_on_lights(
        self, entities: list[str], brightness_pct: float, context: Context
    ) -> dict[str, int]:
        brightness_value = int(brightness_pct / 100.0 * 255)
        for eid in entities:
            self._hass.states.async_set(
                eid, "on", {"brightness": brightness_value}, context=context
            )
        return {eid: brightness_value for eid in entities}

    async def turn_off_lights(
        self, entities: list[str], context: Context
    ) -> dict[str, int]:
        for eid in entities:
            self._hass.states.async_set(eid, "off", {}, context=context)
        return {eid: 0 for eid in entities}


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
    event.data = {"entity_id": entity_id, "old_state": old, "new_state": new}
    event.context = ctx
    event.time_fired = 0
    return event


def make_entry(
    *,
    breakpoints=None,
    curves=None,
    stages=None,
    back_propagation=True,
    debounce_delay=0.0,
) -> MagicMock:
    """Create a ConfigEntry mock with sensible defaults."""
    breakpoints = breakpoints or [30, 60, 90]
    default_curves = {"stage_1_curve": "linear", "stage_2_curve": "linear",
                      "stage_3_curve": "linear", "stage_4_curve": "linear"}
    curve_data = {**default_curves, **(curves or {})}

    if stages is None:
        stages = {
            "stage_1_lights": ["light.stage1"],
            "stage_2_lights": ["light.stage2"],
            "stage_3_lights": ["light.stage3"],
            "stage_4_lights": ["light.stage4"],
        }

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "pipeline_test"
    entry.data = {
        "name": "Pipeline Test",
        "breakpoints": breakpoints,
        **stages,
        **curve_data,
        "enable_back_propagation": back_propagation,
        "debounce_delay": debounce_delay,
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
def pipeline_entry():
    """Config entry: 4 stages, 1 light each, linear, back-prop on, no debounce."""
    return make_entry()


@pytest.fixture
def multi_light_entry():
    """Config entry with multiple lights per stage."""
    return make_entry(stages={
        "stage_1_lights": ["light.s1a", "light.s1b"],
        "stage_2_lights": ["light.s2a", "light.s2b"],
        "stage_3_lights": ["light.stage3"],
        "stage_4_lights": ["light.stage4"],
    })


@pytest.fixture
def pipeline_light(hass: HomeAssistant, pipeline_entry):
    """CombinedLight wired to SimulatedLightController for closed-loop testing."""
    light = CombinedLight(hass, pipeline_entry)
    light.hass = hass
    light._light_controller = SimulatedLightController(hass)
    light.async_schedule_update_ha_state = MagicMock()
    # Initialize all HA states to off
    for eid in all_entity_ids(pipeline_entry):
        hass.states.async_set(eid, "off", {})
    return light


@pytest.fixture
def multi_light(hass: HomeAssistant, multi_light_entry):
    """CombinedLight with multiple lights per stage."""
    light = CombinedLight(hass, multi_light_entry)
    light.hass = hass
    light._light_controller = SimulatedLightController(hass)
    light.async_schedule_update_ha_state = MagicMock()
    for eid in all_entity_ids(multi_light_entry):
        hass.states.async_set(eid, "off", {})
    return light


# ===========================================================================
# 1. Forward Pipeline
# ===========================================================================


class TestForwardPipeline:
    """User sets combined brightness → stages get correct individual brightness."""

    async def test_turn_on_at_10_pct_only_stage1_active(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At 10%, only stage 1 should be on."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(10 / 100 * 255))
        assert changes["light.stage1"] > 0
        assert changes["light.stage2"] == 0
        assert changes["light.stage3"] == 0
        assert changes["light.stage4"] == 0

    async def test_turn_on_at_30_pct_breakpoint_stage2_still_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At exactly 30% (breakpoint), stage 2 is NOT yet active (exclusive boundary)."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(30 / 100 * 255))
        assert changes["light.stage1"] > 0
        assert changes["light.stage2"] == 0

    async def test_turn_on_at_31_pct_stage2_activates(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Just above breakpoint, stage 2 turns on."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(31 / 100 * 255))
        assert changes["light.stage1"] > 0
        assert changes["light.stage2"] > 0
        assert changes["light.stage3"] == 0

    async def test_turn_on_at_50_pct_stages_1_and_2_active(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At 50%, stages 1 and 2 on, 3 and 4 off."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        assert changes["light.stage1"] > 0
        assert changes["light.stage2"] > 0
        assert changes["light.stage3"] == 0
        assert changes["light.stage4"] == 0

    async def test_turn_on_at_60_pct_breakpoint_stage3_still_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At exactly 60%, stage 3 not yet active."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(60 / 100 * 255))
        assert changes["light.stage3"] == 0

    async def test_turn_on_at_61_pct_stage3_activates(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Above breakpoint, stage 3 turns on."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(61 / 100 * 255))
        assert changes["light.stage3"] > 0
        assert changes["light.stage4"] == 0

    async def test_turn_on_at_90_pct_breakpoint_stage4_still_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At exactly 90%, stage 4 not yet active."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(90 / 100 * 255))
        assert changes["light.stage4"] == 0

    async def test_turn_on_at_91_pct_all_stages_active(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Above 90%, all 4 stages active."""
        changes = pipeline_light._coordinator.turn_on(brightness=int(91 / 100 * 255))
        for eid in ("light.stage1", "light.stage2", "light.stage3", "light.stage4"):
            assert changes[eid] > 0, f"{eid} should be on at 91%"

    async def test_turn_on_at_100_pct_all_stages_full(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At 100%, all stages at full brightness."""
        changes = pipeline_light._coordinator.turn_on(brightness=255)
        for eid in ("light.stage1", "light.stage2", "light.stage3", "light.stage4"):
            assert changes[eid] == 255, f"{eid} should be at 255"

    async def test_turn_on_at_1_pct_minimum(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """At 1%, stage 1 on with very low brightness."""
        changes = pipeline_light._coordinator.turn_on(brightness=max(1, int(1 / 100 * 255)))
        assert 0 < changes["light.stage1"] <= 10
        assert changes["light.stage2"] == 0

    async def test_turn_on_then_change_brightness(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Change brightness from 50% to 80%: stage 3 newly activates."""
        pipeline_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        assert pipeline_light._coordinator._lights["light.stage3"].is_on is False

        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        assert pipeline_light._coordinator._lights["light.stage3"].is_on is True

    async def test_turn_on_then_turn_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn on at 100%, then off. All brightness = 0."""
        pipeline_light._coordinator.turn_on(brightness=255)
        changes = pipeline_light._coordinator.turn_off()
        for eid, bri in changes.items():
            assert bri == 0

    async def test_forward_brightness_monotonicity(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Sweep 1-100%: each stage brightness is monotonically non-decreasing."""
        calc = pipeline_light._coordinator._calculator
        prev = {s: 0.0 for s in range(1, 5)}
        for pct in range(1, 101):
            for stage in range(1, 5):
                bri = calc.calculate_zone_brightness(pct, stage)
                assert bri >= prev[stage], (
                    f"Stage {stage} brightness decreased at {pct}%: {bri} < {prev[stage]}"
                )
                prev[stage] = bri

    async def test_forward_stage_activation_order(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Stages activate in order: 1 first, then 2, then 3, then 4."""
        calc = pipeline_light._coordinator._calculator
        first_on = {}
        for pct in range(1, 101):
            for stage in range(1, 5):
                bri = calc.calculate_zone_brightness(pct, stage)
                if bri > 0 and stage not in first_on:
                    first_on[stage] = pct

        for s in range(1, 4):
            assert first_on[s] <= first_on.get(s + 1, 101), (
                f"Stage {s} activated at {first_on[s]}% but stage {s+1} at {first_on.get(s+1)}"
            )


# ===========================================================================
# 2. Reverse Pipeline (Back-Propagation)
# ===========================================================================


class TestReversePipeline:
    """Wall switch changes individual light → combined recalculates → others adjust."""

    def _setup_at(self, hass, light, pct):
        """Set up combined light at given percentage."""
        light._coordinator.turn_on(brightness=max(1, int(pct / 100 * 255)))
        for lt in light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

    async def test_wall_switch_turns_off_stage4(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off stage 4 → combined drops to 90%."""
        self._setup_at(hass, pipeline_light, 100)
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage4")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 90.0) < 2.0, f"Expected ~90%, got {target_pct:.1f}%"

    async def test_wall_switch_turns_off_stage3(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off stage 3 → combined drops to 60%."""
        self._setup_at(hass, pipeline_light, 80)
        hass.states.async_set("light.stage3", STATE_OFF)

        pipeline_light._schedule_back_propagation = lambda c, e=None: None
        pipeline_light._handle_manual_change("light.stage3")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 60.0) < 2.0, f"Expected ~60%, got {target_pct:.1f}%"

    async def test_wall_switch_turns_off_stage2(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off stage 2 → combined drops to 30%."""
        self._setup_at(hass, pipeline_light, 50)
        hass.states.async_set("light.stage2", STATE_OFF)

        pipeline_light._schedule_back_propagation = lambda c, e=None: None
        pipeline_light._handle_manual_change("light.stage2")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 30.0) < 2.0, f"Expected ~30%, got {target_pct:.1f}%"

    async def test_wall_switch_turns_off_stage1_all_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off only remaining stage 1 → combined off."""
        self._setup_at(hass, pipeline_light, 20)
        hass.states.async_set("light.stage1", STATE_OFF)

        pipeline_light._schedule_back_propagation = lambda c, e=None: None
        pipeline_light._handle_manual_change("light.stage1")

        assert pipeline_light._coordinator.is_on is False

    async def test_wall_switch_turns_on_stage3(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn on stage 3 → combined jumps above 60%."""
        self._setup_at(hass, pipeline_light, 40)
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 128})

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage3")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert target_pct > 60, f"Expected >60%, got {target_pct:.1f}%"

    async def test_wall_switch_dims_stage1(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Dim stage 1 → combined recalculates lower, stage 2 adjusts."""
        self._setup_at(hass, pipeline_light, 50)
        new_bri = int(30 / 100 * 255)
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": new_bri})

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage1")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert target_pct < 50, f"Expected < 50%, got {target_pct:.1f}%"

    async def test_backprop_excludes_manual_entity(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Back-propagation changes should not include the manually changed entity."""
        self._setup_at(hass, pipeline_light, 100)
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage4")

        assert "light.stage4" not in scheduled

    async def test_backprop_disabled_no_changes(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """With back-propagation disabled, no changes scheduled."""
        pipeline_light._back_propagation_enabled = False
        self._setup_at(hass, pipeline_light, 100)
        hass.states.async_set("light.stage4", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage4")

        assert scheduled == {}


# ===========================================================================
# 3. Roundtrip Consistency
# ===========================================================================


class TestRoundtripConsistency:
    """Forward then reverse should return to original value."""

    @pytest.mark.parametrize("curve", ["linear", "quadratic", "cubic", "sqrt", "cbrt"])
    def test_forward_reverse_roundtrip(self, curve: str):
        """Set combined → read stages → reverse estimate → should match."""
        entry = make_entry(curves={
            "stage_1_curve": curve, "stage_2_curve": curve,
            "stage_3_curve": curve, "stage_4_curve": curve,
        })
        calc = BrightnessCalculator(entry)

        for pct in range(5, 101, 5):
            zone_brightness: dict[int, float | None] = {}
            for stage in range(1, 5):
                b = calc.calculate_zone_brightness(pct, stage)
                zone_brightness[stage] = b if b > 0 else None

            estimated = calc.estimate_overall_from_zones(zone_brightness)
            assert abs(estimated - pct) < 3.0, (
                f"[{curve}] At {pct}%: roundtrip gave {estimated:.1f}%"
            )

    def test_roundtrip_at_exact_breakpoints(self):
        """At breakpoints, roundtrip still works."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)

        for bp in [30, 60, 90]:
            zone_brightness: dict[int, float | None] = {}
            for stage in range(1, 5):
                b = calc.calculate_zone_brightness(bp, stage)
                zone_brightness[stage] = b if b > 0 else None
            estimated = calc.estimate_overall_from_zones(zone_brightness)
            assert abs(estimated - bp) < 3.0, f"Breakpoint {bp}: got {estimated:.1f}%"

    def test_roundtrip_at_boundary_values(self):
        """0%, 1%, 99%, 100% — no crashes, correct values."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)

        for pct in [1, 99, 100]:
            zone_brightness: dict[int, float | None] = {}
            for stage in range(1, 5):
                b = calc.calculate_zone_brightness(pct, stage)
                zone_brightness[stage] = b if b > 0 else None
            estimated = calc.estimate_overall_from_zones(zone_brightness)
            assert abs(estimated - pct) < 3.0, f"At {pct}%: got {estimated:.1f}%"

    @pytest.mark.parametrize("curve", ["linear", "quadratic", "cubic", "sqrt", "cbrt"])
    def test_single_light_reverse_then_forward(self, curve: str):
        """Set zone brightness, reverse to overall, forward to zone — matches."""
        entry = make_entry(curves={
            "stage_1_curve": curve, "stage_2_curve": curve,
            "stage_3_curve": curve, "stage_4_curve": curve,
        })
        calc = BrightnessCalculator(entry)

        for stage in range(1, 5):
            for zone_pct in [10, 25, 50, 75, 100]:
                overall = calc._reverse_stage_brightness(stage, zone_pct)
                roundtrip = calc.calculate_zone_brightness(overall, stage)
                assert abs(roundtrip - zone_pct) < 2.0, (
                    f"[{curve}] Stage {stage}, zone {zone_pct}%: "
                    f"overall={overall:.1f}%, roundtrip={roundtrip:.1f}%"
                )


# ===========================================================================
# 4. Concurrent KNX Events
# ===========================================================================


class TestConcurrentKNXEvents:
    """Multiple state changes within debounce window get batched correctly."""

    async def test_simultaneous_off_all_four(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """All 4 lights off → combined off, no back-prop."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for eid in ("light.stage1", "light.stage2", "light.stage3", "light.stage4"):
            hass.states.async_set(eid, STATE_OFF)
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        assert pipeline_light._coordinator.is_on is False

    async def test_simultaneous_off_stages_2_and_3(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Stages 2+3 off → combined drops to 30% (lower activation)."""
        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        for eid in ("light.stage2", "light.stage3"):
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 30.0) < 2.0, f"Expected ~30%, got {target_pct:.1f}%"

    async def test_simultaneous_off_stages_3_and_4(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Stages 3+4 off → combined drops to 60%."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)
        for eid in ("light.stage3", "light.stage4"):
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 60.0) < 2.0, f"Expected ~60%, got {target_pct:.1f}%"

    @pytest.mark.parametrize("order_a,order_b", [
        (["light.stage2", "light.stage3"], ["light.stage3", "light.stage2"]),
        (["light.stage3", "light.stage4"], ["light.stage4", "light.stage3"]),
    ])
    async def test_simultaneous_off_order_independent(
        self, hass: HomeAssistant, pipeline_light: CombinedLight,
        order_a: list[str], order_b: list[str],
    ):
        """Result is the same regardless of dict insertion order."""
        pipeline_light._schedule_back_propagation = MagicMock()

        results = []
        for order in (order_a, order_b):
            pipeline_light._coordinator.turn_on(brightness=255)
            for lt in pipeline_light._coordinator.get_lights():
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

            for eid in order:
                hass.states.async_set(eid, STATE_OFF)
            pipeline_light._pending_manual_changes.clear()
            for eid in order:
                pipeline_light._pending_manual_changes[eid] = {
                    "state": "off", "brightness": None, "timestamp": 0,
                }
            await pipeline_light._process_pending_manual_changes()
            results.append(pipeline_light._coordinator.target_brightness)

        assert abs(results[0] - results[1]) < 2, (
            f"Order dependence: {results[0]} vs {results[1]}"
        )

    @pytest.mark.parametrize("off_stages,expected_pct", [
        ([2, 3], 30.0),  # min(30%, 60%)
        ([2, 4], 30.0),  # min(30%, 90%)
        ([3, 4], 60.0),  # min(60%, 90%)
    ])
    async def test_simultaneous_off_uses_lowest_activation(
        self, hass: HomeAssistant, pipeline_light: CombinedLight,
        off_stages: list[int], expected_pct: float,
    ):
        """Batch off uses the lowest activation point among turned-off stages."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        pipeline_light._pending_manual_changes.clear()
        for s in off_stages:
            eid = f"light.stage{s}"
            hass.states.async_set(eid, STATE_OFF)
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - expected_pct) < 2.0

    async def test_stage1_off_with_others_on_target_unchanged(
        self, hass: HomeAssistant, pipeline_light: CombinedLight,
    ):
        """Stage 1 off (activation=0%) doesn't update target when others are on.

        Stage 1 is always active at any overall > 0%. Turning it off is an
        override that the filter logic handles, not a brightness recalculation.
        """
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        hass.states.async_set("light.stage1", STATE_OFF)
        pipeline_light._pending_manual_changes["light.stage1"] = {
            "state": "off", "brightness": None, "timestamp": 0,
        }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        # Target stays at 255 since activation point is 0% and min_overall > 0 check fails
        assert pipeline_light._coordinator.target_brightness == 255

    async def test_debounce_replaces_same_entity(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Second change for same entity replaces first in pending dict."""
        pipeline_light._pending_manual_changes["light.stage1"] = {
            "state": "off", "brightness": None, "timestamp": 0,
        }
        pipeline_light._pending_manual_changes["light.stage1"] = {
            "state": "on", "brightness": 128, "timestamp": 1,
        }
        assert pipeline_light._pending_manual_changes["light.stage1"]["brightness"] == 128

    async def test_debounce_task_cancellation(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Second queued change cancels first debounce task."""
        pipeline_light._debounce_delay = 10.0  # long delay

        event1 = create_state_event("light.stage1", "on", 255, "off", None)
        pipeline_light._queue_manual_change("light.stage1", event1)
        first_task = pipeline_light._debounce_task

        event2 = create_state_event("light.stage2", "on", 255, "off", None)
        pipeline_light._queue_manual_change("light.stage2", event2)
        second_task = pipeline_light._debounce_task

        assert first_task != second_task
        assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()


# ===========================================================================
# 5. State Transitions
# ===========================================================================


class TestStateTransitions:
    """Tests specific on/off transitions and transitional states."""

    async def test_off_to_on_via_combined(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn on combined light → appropriate stages get brightness."""
        ctx = Context(id="test_turn_on")
        pipeline_light._manual_detector.add_integration_context(ctx)
        changes = pipeline_light._coordinator.turn_on(brightness=int(50 / 100 * 255))

        on_entities = [eid for eid, bri in changes.items() if bri > 0]
        off_entities = [eid for eid, bri in changes.items() if bri == 0]

        assert "light.stage1" in on_entities
        assert "light.stage2" in on_entities
        assert "light.stage3" in off_entities
        assert "light.stage4" in off_entities

    async def test_on_to_off_via_combined(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off combined light → all stages 0."""
        pipeline_light._coordinator.turn_on(brightness=255)
        changes = pipeline_light._coordinator.turn_off()
        assert all(bri == 0 for bri in changes.values())

    async def test_on_to_on_brightness_increase(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Increase from 30% to 80%: stage 3 newly activates."""
        pipeline_light._coordinator.turn_on(brightness=int(30 / 100 * 255))
        s3_before = pipeline_light._coordinator._lights["light.stage3"].is_on
        assert s3_before is False

        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        assert pipeline_light._coordinator._lights["light.stage3"].is_on is True

    async def test_on_to_on_brightness_decrease(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Decrease from 80% to 50%: stage 3 deactivates."""
        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        assert pipeline_light._coordinator._lights["light.stage3"].is_on is True

        pipeline_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        assert pipeline_light._coordinator._lights["light.stage3"].is_on is False

    async def test_transitional_on_at_0_skipped(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Transitional on@0 state is skipped by _handle_manual_change."""
        pipeline_light._coordinator._target_brightness = 255
        pipeline_light._coordinator._is_on = True

        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 0})
        initial = pipeline_light._coordinator.target_brightness

        pipeline_light._handle_manual_change("light.stage1")
        assert pipeline_light._coordinator.target_brightness == initial

    async def test_transitional_on_none_brightness_skipped(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """on with no brightness attribute is skipped."""
        pipeline_light._coordinator._target_brightness = 255
        pipeline_light._coordinator._is_on = True

        hass.states.async_set("light.stage1", STATE_ON, {})
        initial = pipeline_light._coordinator.target_brightness

        pipeline_light._handle_manual_change("light.stage1")
        assert pipeline_light._coordinator.target_brightness == initial

    async def test_transitional_on_0_skipped_in_batch(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Transitional state in batch processing is skipped."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        # Stage 3 reports on@0 (transitional)
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 0})
        pipeline_light._pending_manual_changes["light.stage3"] = {
            "state": "on", "brightness": 0, "timestamp": 0,
        }

        pipeline_light._schedule_back_propagation = MagicMock()
        initial = pipeline_light._coordinator.target_brightness
        await pipeline_light._process_pending_manual_changes()

        # Transitional entity skipped → no change
        assert pipeline_light._coordinator.target_brightness == initial

    async def test_last_light_off_combined_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Last remaining light off → combined off, no back-propagation."""
        pipeline_light._coordinator.turn_on(brightness=int(20 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        # Only stage 1 should be on
        hass.states.async_set("light.stage1", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage1")

        assert pipeline_light._coordinator.is_on is False
        assert scheduled == {}  # No back-prop when all off


# ===========================================================================
# 6. Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Boundary conditions, degenerate configurations, unusual scenarios."""

    async def test_brightness_clamped_to_1_minimum(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """turn_on(brightness=0) clamps to 1."""
        pipeline_light._coordinator.turn_on(brightness=0)
        assert pipeline_light._coordinator.target_brightness == 1

    async def test_brightness_clamped_to_255_maximum(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """turn_on(brightness=300) clamps to 255."""
        pipeline_light._coordinator.turn_on(brightness=300)
        assert pipeline_light._coordinator.target_brightness == 255

    async def test_single_light_stages_off_one_by_one(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn off stages one by one from 100% — consistent at each step."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        pipeline_light._schedule_back_propagation = lambda c, e=None: None

        expected_pcts = [90.0, 60.0, 30.0, 0.0]
        for i, stage in enumerate([4, 3, 2, 1]):
            hass.states.async_set(f"light.stage{stage}", STATE_OFF)
            pipeline_light._handle_manual_change(f"light.stage{stage}")
            target_pct = pipeline_light._coordinator.target_brightness / 255 * 100

            if expected_pcts[i] == 0:
                assert pipeline_light._coordinator.is_on is False
            else:
                assert abs(target_pct - expected_pcts[i]) < 2.0, (
                    f"After turning off stage {stage}: "
                    f"expected ~{expected_pcts[i]}%, got {target_pct:.1f}%"
                )

    def test_coordinator_reset_clears_all(self):
        """reset() clears everything."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        coord = HACombinedLightsCoordinator(MagicMock(), entry, calc)
        coord.register_light("light.s1", 1)
        coord.turn_on(brightness=200)
        assert coord.is_on is True

        coord.reset()
        assert coord.is_on is False
        assert coord.target_brightness == 255
        assert all(not lt.is_on for lt in coord.get_lights())

    def test_none_state_entity_skipped_in_sync(self, hass: HomeAssistant):
        """Entity not in hass.states is skipped without error."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        coord = HACombinedLightsCoordinator(hass, entry, calc)
        coord.register_light("light.nonexistent", 1)
        # No crash
        coord.sync_light_state_from_ha("light.nonexistent")
        assert coord._lights["light.nonexistent"].is_on is False

    def test_zero_range_span_degenerate_breakpoints(self):
        """Degenerate breakpoints [100, 100, 100] — no division by zero."""
        entry = make_entry(breakpoints=[100, 100, 100])
        calc = BrightnessCalculator(entry)

        # At 99%: only stage 1 should be on (all others activate at 100%)
        b1 = calc.calculate_zone_brightness(99, 1)
        b2 = calc.calculate_zone_brightness(99, 2)
        assert b1 > 0
        assert b2 == 0

        # At 100%: overall_pct <= activation_point (100 <= 100) → zone is off
        # Stage 2 never activates because boundary is exclusive
        b2_at_100 = calc.calculate_zone_brightness(100, 2)
        assert b2_at_100 == 0.0

    async def test_empty_stages_only_stage1(
        self, hass: HomeAssistant,
    ):
        """Only stage 1 configured — no crash, only stage 1 controlled."""
        entry = make_entry(stages={
            "stage_1_lights": ["light.only"],
            "stage_2_lights": [],
            "stage_3_lights": [],
            "stage_4_lights": [],
        })
        light = CombinedLight(hass, entry)
        light.hass = hass
        light.async_schedule_update_ha_state = MagicMock()
        hass.states.async_set("light.only", "off", {})

        changes = light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        assert "light.only" in changes
        assert changes["light.only"] > 0
        assert len(changes) == 1


# ===========================================================================
# 7. Curve Types
# ===========================================================================


class TestCurveTypes:
    """All 5 brightness curves produce correct results."""

    def test_linear_identity(self):
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        for x in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert calc._apply_brightness_curve(x, "linear") == x

    def test_quadratic_characteristic(self):
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        # At 50% progress: quadratic gives 25%
        assert abs(calc._apply_brightness_curve(0.5, "quadratic") - 0.25) < 0.001

    def test_cubic_characteristic(self):
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        # At 50% progress: cubic gives 12.5%
        assert abs(calc._apply_brightness_curve(0.5, "cubic") - 0.125) < 0.001

    def test_sqrt_characteristic(self):
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        # At 50% progress: sqrt gives ~70.7%
        assert abs(calc._apply_brightness_curve(0.5, "sqrt") - 0.7071) < 0.001

    def test_cbrt_characteristic(self):
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        # At 50% progress: cbrt gives ~79.4%
        assert abs(calc._apply_brightness_curve(0.5, "cbrt") - 0.7937) < 0.001

    @pytest.mark.parametrize("curve", ["linear", "quadratic", "cubic", "sqrt", "cbrt"])
    def test_curve_monotonicity(self, curve: str):
        """Curves should be monotonically non-decreasing."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        prev = 0.0
        for i in range(101):
            x = i / 100
            y = calc._apply_brightness_curve(x, curve)
            assert y >= prev - 1e-10, (
                f"[{curve}] Not monotonic at x={x}: {y} < {prev}"
            )
            prev = y

    @pytest.mark.parametrize("curve", ["linear", "quadratic", "cubic", "sqrt", "cbrt"])
    def test_curve_forward_reverse_identity(self, curve: str):
        """apply(x) then reverse(result) should give back x."""
        entry = make_entry()
        calc = BrightnessCalculator(entry)
        for i in range(1, 100):
            x = i / 100
            forward = calc._apply_brightness_curve(x, curve)
            reverse = calc._reverse_brightness_curve(forward, curve)
            assert abs(reverse - x) < 1e-6, (
                f"[{curve}] x={x}: forward={forward}, reverse={reverse}"
            )

    def test_mixed_curves_per_stage(self):
        """Different curve per stage — roundtrip works for each."""
        entry = make_entry(curves={
            "stage_1_curve": "quadratic",
            "stage_2_curve": "sqrt",
            "stage_3_curve": "cubic",
            "stage_4_curve": "cbrt",
        })
        calc = BrightnessCalculator(entry)

        # At 95%, all stages are on
        for stage in range(1, 5):
            zone = calc.calculate_zone_brightness(95, stage)
            assert zone > 0

            overall = calc._reverse_stage_brightness(stage, zone)
            assert abs(overall - 95) < 2.0, (
                f"Stage {stage}: zone={zone:.1f}%, roundtrip={overall:.1f}%"
            )


# ===========================================================================
# 8. Multi-Light Stages
# ===========================================================================


class TestMultiLightStages:
    """Multiple physical lights in the same stage."""

    async def test_same_stage_get_same_brightness(
        self, hass: HomeAssistant, multi_light: CombinedLight
    ):
        """Two lights in stage 1 get identical brightness."""
        changes = multi_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        assert changes["light.s1a"] == changes["light.s1b"]
        assert changes["light.s2a"] == changes["light.s2b"]

    async def test_multi_light_averaging(
        self, hass: HomeAssistant, multi_light: CombinedLight
    ):
        """Estimation averages same-stage lights."""
        # Only stage 1 lights on, others off
        multi_light._coordinator._lights["light.s1a"].is_on = True
        multi_light._coordinator._lights["light.s1a"].brightness = 128  # ~50.2%
        multi_light._coordinator._lights["light.s1b"].is_on = True
        multi_light._coordinator._lights["light.s1b"].brightness = 255  # 100%
        multi_light._coordinator._lights["light.s2a"].is_on = False
        multi_light._coordinator._lights["light.s2a"].brightness = 0
        multi_light._coordinator._lights["light.s2b"].is_on = False
        multi_light._coordinator._lights["light.s2b"].brightness = 0
        multi_light._coordinator._lights["light.stage3"].is_on = False
        multi_light._coordinator._lights["light.stage3"].brightness = 0
        multi_light._coordinator._lights["light.stage4"].is_on = False
        multi_light._coordinator._lights["light.stage4"].brightness = 0

        estimate = multi_light._coordinator._estimate_overall_from_current_lights()
        # Average of ~50.2% and 100% = ~75.1% stage 1 brightness
        # Stage 1 at 75% brightness → overall ~75%
        assert 70 < estimate < 80, f"Expected ~75%, got {estimate:.1f}%"

    async def test_backprop_excludes_only_changed_light(
        self, hass: HomeAssistant, multi_light: CombinedLight
    ):
        """Light A changes → back-prop includes light B (same stage) but not A."""
        multi_light._coordinator.turn_on(brightness=255)
        for lt in multi_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        hass.states.async_set("light.s1a", STATE_ON, {"brightness": 128})

        scheduled = {}
        multi_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        multi_light._handle_manual_change("light.s1a")

        assert "light.s1a" not in scheduled
        assert "light.s1b" in scheduled

    async def test_multi_light_one_unavailable(
        self, hass: HomeAssistant, multi_light: CombinedLight
    ):
        """One light unavailable — sync skips it, other still works."""
        multi_light._coordinator.turn_on(brightness=int(50 / 100 * 255))
        hass.states.async_set("light.s1a", "unavailable")
        hass.states.async_set("light.s1b", STATE_ON, {"brightness": 128})

        multi_light._coordinator.sync_all_lights_from_ha()

        s1b = multi_light._coordinator._lights["light.s1b"]
        # s1a should keep whatever state it had before (sync skips unavailable)
        assert s1b.is_on is True
        assert s1b.brightness == 128


# ===========================================================================
# 9. Turn-Off Filter Logic
# ===========================================================================


class TestTurnOffFilterLogic:
    """Filter prevents turning on currently-off lights during turn-off events."""

    async def test_filter_blocks_turning_on_off_light(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Back-prop should NOT turn on a light that is currently off in HA."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        # Stage 4 is already off in HA
        hass.states.async_set("light.stage4", STATE_OFF)
        # Stage 3 manually turned off
        hass.states.async_set("light.stage3", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage3")

        # Stage 4 was off → should NOT be turned on
        if "light.stage4" in scheduled:
            assert scheduled["light.stage4"] == 0

    async def test_filter_allows_dimming_on_light(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Back-prop should allow brightness adjustment of already-on lights."""
        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        # Turn off stage 3
        hass.states.async_set("light.stage3", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage3")

        # Stage 1 and 2 are on → should get brightness adjustments
        assert "light.stage1" in scheduled and scheduled["light.stage1"] > 0
        assert "light.stage2" in scheduled and scheduled["light.stage2"] > 0

    async def test_turn_on_event_no_filter(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """When user turns on a light, no turn-off filter is applied."""
        pipeline_light._coordinator.turn_on(brightness=int(40 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        # Turn ON stage 3 (was off)
        hass.states.async_set("light.stage3", STATE_ON, {"brightness": 128})

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage3")

        # No filter applied — other lights should get brightness adjustments
        assert "light.stage1" in scheduled
        assert "light.stage2" in scheduled

    async def test_batch_filter_in_process_pending(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Batch processing applies filter: off lights not turned on."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        # Stage 4 already off, stage 3 turning off
        hass.states.async_set("light.stage4", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        pipeline_light._pending_manual_changes["light.stage3"] = {
            "state": "off", "brightness": None, "timestamp": 0,
        }

        captured = {}
        pipeline_light._schedule_back_propagation = lambda c: captured.update(c)
        await pipeline_light._process_pending_manual_changes()

        # Stage 4 was off → should not be turned on
        if "light.stage4" in captured:
            assert captured["light.stage4"] == 0, (
                f"Stage 4 was off, got brightness {captured['light.stage4']}"
            )

    async def test_filter_preserves_turn_off_commands(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """brightness=0 in back-prop is always allowed through the filter."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        # Turn off stage 2 from 100% → drops to 30%, stages 3 and 4 should turn off
        hass.states.async_set("light.stage2", STATE_OFF)

        scheduled = {}
        pipeline_light._schedule_back_propagation = lambda c, e=None: scheduled.update(c)
        pipeline_light._handle_manual_change("light.stage2")

        # Stages 3 and 4 should be told to turn off (brightness=0)
        for eid in ("light.stage3", "light.stage4"):
            if eid in scheduled:
                assert scheduled[eid] == 0, (
                    f"{eid} should be turned off, got {scheduled[eid]}"
                )


# ===========================================================================
# 10. Context Tracking
# ===========================================================================


class TestContextTracking:
    """Integration's own changes are not detected as manual."""

    def test_our_context_not_manual(self):
        """Events with our context are not manual."""
        det = ManualChangeDetector()
        ctx = Context(id="our_ctx")
        det.add_integration_context(ctx)

        event = create_state_event(
            "light.test", "off", None, "on", 128, context_id="our_ctx"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert not is_manual
        assert reason == "recent_context_match"

    def test_external_context_is_manual(self):
        """Events with unknown context are manual."""
        det = ManualChangeDetector()
        ctx = Context(id="our_ctx")
        det.add_integration_context(ctx)

        event = create_state_event(
            "light.test", "off", None, "on", 128, context_id="foreign_ctx"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert is_manual

    def test_expected_brightness_match_not_manual(self):
        """Event matching expected brightness is not manual."""
        det = ManualChangeDetector()
        det.track_expected_state("light.test", 128)

        event = create_state_event(
            "light.test", "off", None, "on", 130, context_id="ext"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert not is_manual
        assert reason == "expected_brightness_match"

    def test_expected_brightness_mismatch_is_manual(self):
        """Event NOT matching expected brightness is manual."""
        det = ManualChangeDetector()
        det.track_expected_state("light.test", 128)

        event = create_state_event(
            "light.test", "off", None, "on", 200, context_id="ext"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert is_manual
        assert reason == "brightness_mismatch"

    def test_context_buffer_holds_20(self):
        """Buffer survives 20 contexts."""
        det = ManualChangeDetector()
        for i in range(20):
            det.add_integration_context(Context(id=f"ctx_{i}"))

        # All 20 should be in buffer
        for i in range(20):
            assert f"ctx_{i}" in det._recent_contexts

    def test_context_buffer_evicts_at_21(self):
        """21st context evicts the first."""
        det = ManualChangeDetector()
        for i in range(21):
            det.add_integration_context(Context(id=f"ctx_{i}"))

        assert "ctx_0" not in det._recent_contexts
        assert "ctx_20" in det._recent_contexts

    def test_updating_flag_blocks_external_detection(self):
        """Events during updating flag are not manual."""
        det = ManualChangeDetector()
        det.set_updating_flag(True)

        event = create_state_event(
            "light.test", "off", None, "on", 128, context_id="ext"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert not is_manual
        assert reason == "integration_updating"

        det.set_updating_flag(False)

    async def test_updating_flag_true_during_apply_false_after(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """_updating_lights is True during service calls, False after."""
        for eid in all_entity_ids(make_entry()):
            hass.states.async_set(eid, STATE_ON, {"brightness": 255})

        flag_during = []
        original_turn_on = pipeline_light._light_controller.turn_on_lights

        async def observe_turn_on(entities, brightness_pct, context):
            flag_during.append(pipeline_light._manual_detector._updating_lights)
            return await original_turn_on(entities, brightness_pct, context)

        pipeline_light._light_controller.turn_on_lights = observe_turn_on

        ctx = Context(id="test")
        pipeline_light._manual_detector.add_integration_context(ctx)
        await pipeline_light._apply_changes_to_ha({"light.stage1": 128}, ctx)

        assert any(flag_during), "Flag should have been True during call"
        assert not pipeline_light._manual_detector._updating_lights


# ===========================================================================
# 11. State Restoration
# ===========================================================================


class TestStateRestoration:
    """RestoreEntity behavior on HA restart."""

    async def test_restore_on_with_brightness(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Restored on-state with brightness sets coordinator target."""
        last = State("light.pipeline_test", "on", {"brightness": 200})

        with patch.object(pipeline_light, "async_get_last_state", return_value=last):
            pipeline_light._target_brightness_initialized = False
            await pipeline_light.async_added_to_hass()

        assert pipeline_light._coordinator.target_brightness == 200

    async def test_restore_off_state(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Restored off-state leaves is_on False."""
        last = State("light.pipeline_test", "off", {})

        with patch.object(pipeline_light, "async_get_last_state", return_value=last):
            pipeline_light._target_brightness_initialized = False
            await pipeline_light.async_added_to_hass()

        assert pipeline_light._attr_is_on is False

    async def test_restore_none_syncs_from_ha(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """No last state → syncs from current HA states."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        with patch.object(pipeline_light, "async_get_last_state", return_value=None):
            pipeline_light._target_brightness_initialized = False
            await pipeline_light.async_added_to_hass()

        assert pipeline_light._coordinator.is_on is True
        assert pipeline_light._coordinator.target_brightness > 0

    async def test_listener_registered_after_restore(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Event listener is registered after async_added_to_hass."""
        with patch.object(pipeline_light, "async_get_last_state", return_value=None):
            pipeline_light._target_brightness_initialized = False
            await pipeline_light.async_added_to_hass()

        assert pipeline_light._remove_listener is not None


# ===========================================================================
# 12. Error Resilience
# ===========================================================================


class TestErrorResilience:
    """Graceful handling of failures and unusual states."""

    async def test_unavailable_state_skipped_in_sync(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Unavailable lights are skipped during sync."""
        pipeline_light._coordinator.turn_on(brightness=255)
        hass.states.async_set("light.stage1", "unavailable")
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        pipeline_light._coordinator.sync_all_lights_from_ha()
        # stage1 keeps its internal state (not overwritten by unavailable)
        s1 = pipeline_light._coordinator._lights["light.stage1"]
        assert s1.brightness == 255  # Kept from turn_on

    async def test_unknown_state_skipped_in_sync(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Unknown lights are skipped during sync."""
        pipeline_light._coordinator.turn_on(brightness=255)
        hass.states.async_set("light.stage2", "unknown")
        pipeline_light._coordinator.sync_light_state_from_ha("light.stage2")

        s2 = pipeline_light._coordinator._lights["light.stage2"]
        assert s2.brightness == 255  # Kept from turn_on

    async def test_unavailable_in_handle_manual(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Unavailable entity skipped by _handle_manual_change."""
        pipeline_light._coordinator._target_brightness = 255
        hass.states.async_set("light.stage3", "unavailable")

        initial = pipeline_light._coordinator.target_brightness
        pipeline_light._handle_manual_change("light.stage3")
        assert pipeline_light._coordinator.target_brightness == initial

    async def test_missing_entity_in_handle_manual(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """None state skipped by _handle_manual_change."""
        # Don't set any state → hass.states.get returns None
        initial = pipeline_light._coordinator.target_brightness
        pipeline_light._handle_manual_change("light.nonexistent")
        assert pipeline_light._coordinator.target_brightness == initial

    async def test_debounce_task_cancelled_on_removal(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Debounce task cancelled when entity removed."""
        pipeline_light._debounce_delay = 10.0
        event = create_state_event("light.stage1", "on", 255, "off", None)
        pipeline_light._queue_manual_change("light.stage1", event)
        assert pipeline_light._debounce_task is not None

        await pipeline_light.async_will_remove_from_hass()

        task = pipeline_light._debounce_task
        assert task.cancelling() > 0 or task.cancelled() or task.done()

    async def test_backprop_task_cancelled_on_removal(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Back-prop task cancelled when entity removed."""
        # Create a long-running back-prop task
        async def slow_backprop():
            await asyncio.sleep(100)

        pipeline_light._back_prop_task = hass.async_create_task(slow_backprop())
        assert not pipeline_light._back_prop_task.done()

        await pipeline_light.async_will_remove_from_hass()

        task = pipeline_light._back_prop_task
        assert task.cancelling() > 0 or task.cancelled() or task.done()

    async def test_available_false_when_all_unavailable(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """available property returns False when all lights unavailable."""
        for eid in all_entity_ids(make_entry()):
            hass.states.async_set(eid, "unavailable")
        assert pipeline_light.available is False

    async def test_available_true_when_one_available(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """available returns True if at least one light is available."""
        for eid in all_entity_ids(make_entry()):
            hass.states.async_set(eid, "unavailable")
        hass.states.async_set("light.stage1", STATE_OFF)
        assert pipeline_light.available is True

    async def test_expected_off_state_not_manual(self):
        """Expected off state is correctly classified."""
        det = ManualChangeDetector()
        det.track_expected_state("light.test", 0)

        event = create_state_event(
            "light.test", "on", 128, "off", None, context_id="ext"
        )
        is_manual, reason = det.is_manual_change("light.test", event)
        assert not is_manual
        assert reason == "expected_off_state"


# ===========================================================================
# 13. Full Scenario Chains
# ===========================================================================


class TestFullScenarioChains:
    """Multi-step scenarios simulating real-world usage."""

    async def test_scenario_evening_dimming(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Turn on at 80% → wall switch turns off stage 3 → dims stage 2."""
        pipeline_light._schedule_back_propagation = lambda c, e=None: None

        # Step 1: Turn on at 80%
        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        assert pipeline_light._coordinator._lights["light.stage3"].is_on is True

        # Step 2: Wall switch turns off stage 3
        hass.states.async_set("light.stage3", STATE_OFF)
        pipeline_light._handle_manual_change("light.stage3")

        target_after_s3_off = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_after_s3_off - 60.0) < 2.0

        # Step 3: Wall switch dims stage 2 to 50%
        new_s2_bri = int(50 / 100 * 255)
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": new_s2_bri})
        pipeline_light._handle_manual_change("light.stage2")

        # Combined should have changed
        final = pipeline_light._coordinator.target_brightness / 255 * 100
        assert final != target_after_s3_off

    async def test_scenario_knx_all_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Start at 100%, KNX sends all 4 lights off. Combined → 0%."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        # All off via KNX
        for eid in ("light.stage1", "light.stage2", "light.stage3", "light.stage4"):
            hass.states.async_set(eid, STATE_OFF)
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        assert pipeline_light._coordinator.is_on is False

    async def test_scenario_knx_partial_off(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Start at 100%, KNX turns off stages 3+4. Combined → 30%."""
        pipeline_light._coordinator.turn_on(brightness=255)
        for lt in pipeline_light._coordinator.get_lights():
            hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})

        for eid in ("light.stage3", "light.stage4"):
            hass.states.async_set(eid, STATE_OFF)
            pipeline_light._pending_manual_changes[eid] = {
                "state": "off", "brightness": None, "timestamp": 0,
            }

        # Wait, stages 3+4 off means min activation of (60%, 90%) = 60%
        # but stage 2 is still on, so we should get 60%
        pipeline_light._schedule_back_propagation = MagicMock()
        await pipeline_light._process_pending_manual_changes()

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 60.0) < 2.0, f"Expected ~60%, got {target_pct:.1f}%"

    async def test_scenario_wall_switch_then_combined_override(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Wall switch dims → then user sets combined to 100%. Full override."""
        pipeline_light._schedule_back_propagation = lambda c, e=None: None

        # Start at 80%
        pipeline_light._coordinator.turn_on(brightness=int(80 / 100 * 255))
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        # Wall switch dims stage 1
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 64})
        pipeline_light._handle_manual_change("light.stage1")

        assert pipeline_light._coordinator.target_brightness < int(80 / 100 * 255)

        # User overrides to 100% via combined
        changes = pipeline_light._coordinator.turn_on(brightness=255)
        assert pipeline_light._coordinator.target_brightness == 255
        for eid in ("light.stage1", "light.stage2", "light.stage3", "light.stage4"):
            assert changes[eid] == 255

    async def test_scenario_rapid_brightness_changes(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Rapid changes: final state should be correct."""
        for pct in [20, 40, 60, 80, 100]:
            pipeline_light._coordinator.turn_on(brightness=int(pct / 100 * 255))

        assert pipeline_light._coordinator.target_brightness == 255
        assert all(
            lt.is_on for lt in pipeline_light._coordinator.get_lights()
        )

    async def test_scenario_off_on_off_on_cycle(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """on/off cycle: state consistent at each step."""
        for _ in range(3):
            pipeline_light._coordinator.turn_on(brightness=128)
            assert pipeline_light._coordinator.is_on is True
            assert all(lt.is_on or lt.brightness == 0
                       for lt in pipeline_light._coordinator.get_lights())

            pipeline_light._coordinator.turn_off()
            assert pipeline_light._coordinator.is_on is False
            assert all(lt.brightness == 0
                       for lt in pipeline_light._coordinator.get_lights())

    async def test_scenario_stage_by_stage_activation(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Sweep 0→100%: verify stages activate at correct breakpoints."""
        calc = pipeline_light._coordinator._calculator
        expected_activation = {1: 1, 2: 31, 3: 61, 4: 91}

        actual_activation = {}
        for pct in range(1, 101):
            for stage in range(1, 5):
                b = calc.calculate_zone_brightness(pct, stage)
                if b > 0 and stage not in actual_activation:
                    actual_activation[stage] = pct

        for stage in range(1, 5):
            assert actual_activation[stage] == expected_activation[stage], (
                f"Stage {stage}: activated at {actual_activation[stage]}%, "
                f"expected {expected_activation[stage]}%"
            )

    async def test_scenario_restore_then_manual_change(
        self, hass: HomeAssistant, pipeline_light: CombinedLight
    ):
        """Restore state at 60%, then wall switch turns off stage 2."""
        # Simulate restore
        pipeline_light._coordinator._target_brightness = int(60 / 100 * 255)
        pipeline_light._coordinator._is_on = True
        pipeline_light._coordinator.apply_brightness_to_lights()
        for lt in pipeline_light._coordinator.get_lights():
            if lt.is_on:
                hass.states.async_set(lt.entity_id, "on", {"brightness": lt.brightness})
            else:
                hass.states.async_set(lt.entity_id, "off", {})

        # Wall switch turns off stage 2
        hass.states.async_set("light.stage2", STATE_OFF)
        pipeline_light._schedule_back_propagation = lambda c, e=None: None
        pipeline_light._handle_manual_change("light.stage2")

        target_pct = pipeline_light._coordinator.target_brightness / 255 * 100
        assert abs(target_pct - 30.0) < 2.0, f"Expected ~30%, got {target_pct:.1f}%"
