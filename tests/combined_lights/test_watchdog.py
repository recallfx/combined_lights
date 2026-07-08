"""Tests for post-command watchdog behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.combined_lights.const import (
    WATCHDOG_BRIGHTNESS_TOLERANCE,
    WATCHDOG_MAX_RETRIES,
)
from custom_components.combined_lights.light import CombinedLight


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "watchdog_entry"
    entry.data = {
        "name": "Watchdog Test Light",
        "stage_1_lights": ["light.bulb_1"],
        "stage_2_lights": ["light.bulb_2"],
        "stage_3_lights": [],
        "stage_4_lights": [],
        "breakpoints": [25, 50, 75],
        "stage_1_curve": "linear",
        "stage_2_curve": "linear",
        "stage_3_curve": "linear",
        "stage_4_curve": "linear",
    }
    return entry


@pytest.fixture
def combined_light(hass: HomeAssistant, mock_entry):
    """Create a CombinedLight instance."""
    light = CombinedLight(hass, mock_entry)
    light.hass = hass
    light._watchdog_delay = 0
    light.async_schedule_update_ha_state = MagicMock()
    return light


async def test_watchdog_does_nothing_when_state_matches(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Watchdog should not retry when actual state matches expectation."""
    hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 128})
    combined_light._apply_changes_to_ha = AsyncMock()
    combined_light._schedule_watchdog = MagicMock()
    combined_light._sync_coordinator_from_ha = MagicMock()

    await combined_light._watchdog_verify({"light.bulb_1": 128})

    combined_light._apply_changes_to_ha.assert_not_called()
    combined_light._schedule_watchdog.assert_not_called()
    combined_light._sync_coordinator_from_ha.assert_not_called()


async def test_watchdog_tolerates_small_brightness_drift(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Brightness differences inside tolerance should not retry."""
    expected = 128
    hass.states.async_set(
        "light.bulb_1",
        STATE_ON,
        {"brightness": expected + WATCHDOG_BRIGHTNESS_TOLERANCE},
    )
    combined_light._apply_changes_to_ha = AsyncMock()
    combined_light._schedule_watchdog = MagicMock()

    await combined_light._watchdog_verify({"light.bulb_1": expected})

    combined_light._apply_changes_to_ha.assert_not_called()
    combined_light._schedule_watchdog.assert_not_called()


async def test_watchdog_retries_only_mismatched_lights(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Watchdog should retry only lights that missed their expected state."""
    hass.states.async_set("light.bulb_1", STATE_OFF)
    hass.states.async_set("light.bulb_2", STATE_ON, {"brightness": 64})
    combined_light._apply_changes_to_ha = AsyncMock(return_value=True)
    combined_light._schedule_watchdog = MagicMock()

    await combined_light._watchdog_verify({"light.bulb_1": 180, "light.bulb_2": 64})

    combined_light._apply_changes_to_ha.assert_awaited_once()
    retry_changes = combined_light._apply_changes_to_ha.await_args.args[0]
    assert retry_changes == {"light.bulb_1": 180}
    combined_light._schedule_watchdog.assert_called_once_with({"light.bulb_1": 180}, 1)


async def test_watchdog_resyncs_after_max_retries(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Watchdog should accept HA state after retry budget is exhausted."""
    hass.states.async_set("light.bulb_1", STATE_ON, {"brightness": 100})
    combined_light._apply_changes_to_ha = AsyncMock()
    combined_light._sync_coordinator_from_ha = MagicMock()

    await combined_light._watchdog_verify(
        {"light.bulb_1": 0}, retry_count=WATCHDOG_MAX_RETRIES
    )

    combined_light._apply_changes_to_ha.assert_not_called()
    combined_light._sync_coordinator_from_ha.assert_called_once()
    combined_light.async_schedule_update_ha_state.assert_called_once()


async def test_watchdog_skips_unverifiable_states(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Unavailable or unknown states should not trigger retries."""
    hass.states.async_set("light.bulb_1", STATE_UNAVAILABLE)
    combined_light._apply_changes_to_ha = AsyncMock()
    combined_light._schedule_watchdog = MagicMock()

    await combined_light._watchdog_verify({"light.bulb_1": 180})

    combined_light._apply_changes_to_ha.assert_not_called()
    combined_light._schedule_watchdog.assert_not_called()


async def test_watchdog_retry_failure_stops_retry_chain(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """A retry service failure should not schedule another watchdog."""
    hass.states.async_set("light.bulb_1", STATE_OFF)
    combined_light._apply_changes_to_ha = AsyncMock(side_effect=Exception("boom"))
    combined_light._schedule_watchdog = MagicMock()

    await combined_light._watchdog_verify({"light.bulb_1": 180})

    combined_light._apply_changes_to_ha.assert_awaited_once()
    combined_light._schedule_watchdog.assert_not_called()


async def test_scheduling_watchdog_cancels_previous_task(
    hass: HomeAssistant, combined_light: CombinedLight
):
    """Only the latest watchdog task should remain active."""
    combined_light._watchdog_delay = 60

    combined_light._schedule_watchdog({"light.bulb_1": 100})
    first_task = combined_light._watchdog_task

    combined_light._schedule_watchdog({"light.bulb_1": 200})
    second_task = combined_light._watchdog_task

    assert first_task is not second_task
    assert first_task.cancelling() > 0 or first_task.cancelled() or first_task.done()

    second_task.cancel()
    await asyncio.sleep(0)
