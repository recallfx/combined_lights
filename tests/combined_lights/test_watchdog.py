"""Tests for post-command state verification watchdog."""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Context, HomeAssistant

from custom_components.combined_lights.const import (
    WATCHDOG_BRIGHTNESS_TOLERANCE,
    WATCHDOG_MAX_RETRIES,
)
from custom_components.combined_lights.light import CombinedLight


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_watchdog_entry"
    entry.data = {
        "name": "Test Watchdog Light",
        "stage_1_lights": ["light.stage1"],
        "stage_2_lights": ["light.stage2"],
        "stage_3_lights": ["light.stage3"],
        "stage_4_lights": ["light.stage4"],
        "breakpoints": [25, 50, 75],
        "brightness_curve": "linear",
        "enable_back_propagation": True,
        "watchdog_delay": 0.05,  # Very short for tests
    }
    return entry


@pytest.fixture
def combined_light(hass: HomeAssistant, mock_entry):
    """Create a CombinedLight instance with watchdog enabled."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    light.async_schedule_update_ha_state = MagicMock()
    return light


class TestWatchdogScheduling:
    """Test watchdog task lifecycle."""

    def test_schedule_watchdog_creates_task(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Scheduling watchdog should create a task."""
        combined_light._schedule_watchdog({"light.stage1": 128})
        assert combined_light._watchdog_task is not None
        assert not combined_light._watchdog_task.done()

    def test_schedule_watchdog_cancels_previous(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """New watchdog should cancel previous one."""
        combined_light._schedule_watchdog({"light.stage1": 128})
        first_task = combined_light._watchdog_task

        combined_light._schedule_watchdog({"light.stage2": 200})
        second_task = combined_light._watchdog_task

        assert first_task != second_task
        assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()

    def test_no_watchdog_without_hass(self, combined_light: CombinedLight):
        """Watchdog should not be created if hass is None."""
        combined_light.hass = None
        combined_light._schedule_watchdog({"light.stage1": 128})
        assert combined_light._watchdog_task is None


class TestWatchdogVerification:
    """Test state verification logic."""

    async def test_all_lights_match_no_action(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should do nothing when all lights match expected state."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 128})
        hass.states.async_set("light.stage2", STATE_OFF)

        expected = {"light.stage1": 128, "light.stage2": 0}

        # Run watchdog directly (skip the sleep)
        await combined_light._watchdog_verify(expected)

        # No retry should be scheduled
        # (task is the one running this, so it's done, no new one)

    async def test_detects_light_not_turned_on(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should detect light that failed to turn on."""
        # Light should be on at 128 but is actually off (KNX dropped telegram)
        hass.states.async_set("light.stage1", STATE_OFF)

        # Mock _apply_changes_to_ha to track retry
        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            # Simulate success on retry
            hass.states.async_set("light.stage1", STATE_ON, {"brightness": 128})
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 128}, retry_count=0)

        assert "light.stage1" in retried
        assert retried["light.stage1"] == 128

    async def test_detects_light_not_turned_off(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should detect light that failed to turn off."""
        # Light should be off but is still on
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 200})

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            hass.states.async_set("light.stage1", STATE_OFF)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 0}, retry_count=0)

        assert "light.stage1" in retried
        assert retried["light.stage1"] == 0

    async def test_detects_brightness_drift(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should detect brightness that drifted beyond tolerance."""
        # Expected 200 but actual is 150 (drift of 50, well above tolerance of 10)
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 150})

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            hass.states.async_set("light.stage1", STATE_ON, {"brightness": 200})
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 200}, retry_count=0)

        assert "light.stage1" in retried
        assert retried["light.stage1"] == 200

    async def test_ignores_brightness_within_tolerance(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should accept brightness within tolerance."""
        # Expected 200, actual 205 — within WATCHDOG_BRIGHTNESS_TOLERANCE (10)
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 205})

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 200}, retry_count=0)

        # Should NOT retry since difference is within tolerance
        assert "light.stage1" not in retried

    async def test_skips_unavailable_lights(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should skip lights with unavailable/unknown state."""
        hass.states.async_set("light.stage1", "unavailable")

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 128}, retry_count=0)

        assert "light.stage1" not in retried

    async def test_skips_unknown_entities(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should skip entities that don't exist in HA."""
        # Don't set any state — entity doesn't exist
        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.nonexistent": 128}, retry_count=0)

        assert len(retried) == 0


class TestWatchdogRetryLogic:
    """Test retry and re-sync behavior."""

    async def test_retries_up_to_max(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should retry up to WATCHDOG_MAX_RETRIES times."""
        # Light stays off despite commands (persistent failure)
        hass.states.async_set("light.stage1", STATE_OFF)

        apply_count = 0

        async def mock_apply(changes, ctx):
            nonlocal apply_count
            apply_count += 1
            # Light still doesn't respond
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify(
            {"light.stage1": 128}, retry_count=0
        )

        # Should have retried once
        assert apply_count == 1

    async def test_max_retries_triggers_resync(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """After max retries, watchdog should re-sync coordinator from HA."""
        # Set up HA state that differs from what we commanded
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 100})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        # Run watchdog at max retries (should re-sync instead of retrying)
        await combined_light._watchdog_verify(
            {"light.stage1": 200}, retry_count=WATCHDOG_MAX_RETRIES
        )

        # Coordinator should have been re-synced to accept the actual HA state
        light = combined_light._coordinator.get_light("light.stage1")
        assert light is not None
        assert light.brightness == 100

    async def test_partial_mismatch_only_retries_failed(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should only retry lights that didn't match."""
        # stage1 is correct, stage2 failed to turn on
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.stage2", STATE_OFF)  # Should be on at 150

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            hass.states.async_set("light.stage2", STATE_ON, {"brightness": 150})
            return True

        combined_light._apply_changes_to_ha = mock_apply

        expected = {"light.stage1": 200, "light.stage2": 150}
        await combined_light._watchdog_verify(expected, retry_count=0)

        # Only stage2 should be retried
        assert "light.stage1" not in retried
        assert "light.stage2" in retried
        assert retried["light.stage2"] == 150

    async def test_retry_exception_does_not_crash(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog should handle exceptions during retry gracefully."""
        hass.states.async_set("light.stage1", STATE_OFF)

        async def mock_apply(changes, ctx):
            raise RuntimeError("KNX gateway unreachable")

        combined_light._apply_changes_to_ha = mock_apply

        # Should not raise
        await combined_light._watchdog_verify(
            {"light.stage1": 128}, retry_count=0
        )


class TestWatchdogIntegration:
    """Test watchdog integration with turn_on/turn_off flow."""

    async def test_turn_on_schedules_watchdog(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """async_turn_on should schedule a watchdog task."""
        # Set up HA states for all stages
        hass.states.async_set("light.stage1", STATE_OFF)
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        # Mock light controller to simulate success
        async def mock_turn_on(entities, brightness_pct, ctx):
            for eid in entities:
                bri = int(brightness_pct / 100 * 255)
                hass.states.async_set(eid, STATE_ON, {"brightness": bri})
            return {eid: int(brightness_pct / 100 * 255) for eid in entities}

        async def mock_turn_off(entities, ctx):
            for eid in entities:
                hass.states.async_set(eid, STATE_OFF)
            return {eid: 0 for eid in entities}

        combined_light._light_controller.turn_on_lights = mock_turn_on
        combined_light._light_controller.turn_off_lights = mock_turn_off
        combined_light.async_write_ha_state = MagicMock()

        await combined_light.async_turn_on(brightness=128)

        # Watchdog should be scheduled
        assert combined_light._watchdog_task is not None

    async def test_turn_off_schedules_watchdog(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """async_turn_off should schedule a watchdog task."""
        hass.states.async_set("light.stage1", STATE_ON, {"brightness": 200})
        hass.states.async_set("light.stage2", STATE_OFF)
        hass.states.async_set("light.stage3", STATE_OFF)
        hass.states.async_set("light.stage4", STATE_OFF)

        async def mock_turn_off(entities, ctx):
            for eid in entities:
                hass.states.async_set(eid, STATE_OFF)
            return {eid: 0 for eid in entities}

        async def mock_turn_on(entities, brightness_pct, ctx):
            return {}

        combined_light._light_controller.turn_on_lights = mock_turn_on
        combined_light._light_controller.turn_off_lights = mock_turn_off
        combined_light._coordinator._is_on = True
        combined_light.async_write_ha_state = MagicMock()

        await combined_light.async_turn_off()

        assert combined_light._watchdog_task is not None

    async def test_cleanup_cancels_watchdog(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Removing entity should cancel watchdog task."""
        combined_light._schedule_watchdog({"light.stage1": 128})
        assert combined_light._watchdog_task is not None

        await combined_light.async_will_remove_from_hass()

        # Task should have been cancelled
        task = combined_light._watchdog_task
        assert task.cancelling() > 0 or task.cancelled() or task.done()


class TestWatchdogEdgeCases:
    """Test edge cases and race conditions."""

    async def test_watchdog_cancelled_by_new_command(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """New command should cancel pending watchdog from previous command."""
        # First command schedules watchdog
        combined_light._schedule_watchdog({"light.stage1": 128})
        first_task = combined_light._watchdog_task

        # Second command schedules new watchdog
        combined_light._schedule_watchdog({"light.stage1": 200})
        second_task = combined_light._watchdog_task

        assert first_task != second_task
        assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()

    async def test_watchdog_with_empty_expected_states(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Watchdog with empty expected states should do nothing."""
        await combined_light._watchdog_verify({}, retry_count=0)
        # Should complete without error

    async def test_multiple_mismatches_all_retried(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """All mismatched lights should be retried in one batch."""
        hass.states.async_set("light.stage1", STATE_OFF)  # Should be on
        hass.states.async_set("light.stage2", STATE_ON, {"brightness": 50})  # Should be 200

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        expected = {"light.stage1": 128, "light.stage2": 200}
        await combined_light._watchdog_verify(expected, retry_count=0)

        assert retried == {"light.stage1": 128, "light.stage2": 200}

    async def test_on_light_with_none_brightness_accepted(
        self, hass: HomeAssistant, combined_light: CombinedLight
    ):
        """Light that is on but has no brightness attribute should not trigger drift detection."""
        # Light is on but brightness not reported yet (transitional)
        hass.states.async_set("light.stage1", STATE_ON, {})

        retried = {}

        async def mock_apply(changes, ctx):
            retried.update(changes)
            return True

        combined_light._apply_changes_to_ha = mock_apply

        await combined_light._watchdog_verify({"light.stage1": 128}, retry_count=0)

        # Should NOT retry — light is on, brightness just not reported
        assert "light.stage1" not in retried
