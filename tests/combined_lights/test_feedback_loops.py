"""Test feedback loops and potential interference in Combined Lights."""

import asyncio

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Context, HomeAssistant

from custom_components.combined_lights.const import CONF_ENABLE_BACK_PROPAGATION

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def mock_light_entities(hass):
    """Create mock light entities."""
    hass.states.async_set("light.stage_1_1", STATE_OFF)
    hass.states.async_set("light.stage_2_1", STATE_OFF)
    return ["light.stage_1_1", "light.stage_2_1"]


async def _setup_combined_light(hass: HomeAssistant, *, watchdog_delay: float = 5.0):
    """Set up a real combined entity for event/context regression tests."""
    config_entry = MockConfigEntry(
        domain="combined_lights",
        data={
            "name": "Combined Test",
            "stage_1_lights": ["light.stage_1_1"],
            "stage_2_lights": ["light.stage_2_1"],
            CONF_ENABLE_BACK_PROPAGATION: False,
            "debounce_delay": 0.0,
            "watchdog_delay": watchdog_delay,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    component = hass.data.get("entity_components", {}).get("light")
    assert component is not None
    combined_light = component.get_entity("light.combined_test_combined_test")
    assert combined_light is not None
    return config_entry, combined_light


async def test_manual_member_change_cancels_pending_watchdog(
    hass: HomeAssistant, mock_light_entities
):
    """A wall-switch OFF must invalidate an older turn-on watchdog."""
    hass.states.async_set("light.stage_1_1", STATE_ON, {ATTR_BRIGHTNESS: 128})
    config_entry, combined_light = await _setup_combined_light(
        hass, watchdog_delay=0.05
    )

    try:
        combined_light._apply_changes_to_ha = AsyncMock(return_value=True)
        combined_light._schedule_watchdog({"light.stage_1_1": 128})

        manual_context = Context(id="wall-switch-off")
        hass.states.async_set("light.stage_1_1", STATE_OFF, context=manual_context)
        await asyncio.sleep(0.1)

        combined_light._apply_changes_to_ha.assert_not_awaited()
    finally:
        await hass.config_entries.async_unload(config_entry.entry_id)


async def test_manual_change_before_watchdog_creation_invalidates_command(
    hass: HomeAssistant, mock_light_entities
):
    """A wall change during command delivery must prevent a stale watchdog."""
    hass.states.async_set("light.stage_1_1", STATE_ON, {ATTR_BRIGHTNESS: 10})
    config_entry, combined_light = await _setup_combined_light(
        hass, watchdog_delay=0.01
    )
    apply_started = asyncio.Event()
    release_apply = asyncio.Event()

    async def blocked_apply(changes, context):
        assert changes
        apply_started.set()
        await release_apply.wait()
        return True

    combined_light._apply_changes_to_ha = AsyncMock(side_effect=blocked_apply)

    try:
        command = asyncio.create_task(combined_light.async_turn_on(brightness=200))
        await apply_started.wait()

        hass.states.async_set(
            "light.stage_1_1",
            STATE_OFF,
            context=Context(id="wall-switch-during-command"),
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        release_apply.set()
        await command
        await asyncio.sleep(0.05)

        assert combined_light._apply_changes_to_ha.await_count == 1
    finally:
        release_apply.set()
        await hass.config_entries.async_unload(config_entry.entry_id)


async def test_manual_member_context_is_propagated_to_combined_entity(
    hass: HomeAssistant, mock_light_entities
):
    """A combined state update must carry the member light's event context."""
    config_entry, combined_light = await _setup_combined_light(hass)

    combined_events = []

    def capture_combined_event(event):
        if event.data.get("entity_id") == combined_light.entity_id:
            combined_events.append(event)

    remove_listener = hass.bus.async_listen(EVENT_STATE_CHANGED, capture_combined_event)

    try:
        automation_context = Context(id="previous-automation-command")
        combined_light.async_set_context(automation_context)

        manual_context = Context(id="wall-switch-on")
        hass.states.async_set(
            "light.stage_1_1",
            STATE_ON,
            {ATTR_BRIGHTNESS: 128},
            context=manual_context,
        )
        await hass.async_block_till_done()

        turned_on_events = [
            event
            for event in combined_events
            if event.data["new_state"].state == STATE_ON
        ]
        assert turned_on_events
        assert turned_on_events[-1].context.id == manual_context.id
    finally:
        remove_listener()
        await hass.config_entries.async_unload(config_entry.entry_id)


async def test_expected_member_confirmation_keeps_automation_context(
    hass: HomeAssistant, mock_light_entities
):
    """Foreign KNX confirmation context must not replace the command context."""
    config_entry, combined_light = await _setup_combined_light(hass)
    combined_events = []

    def capture_combined_event(event):
        if event.data.get("entity_id") == combined_light.entity_id:
            combined_events.append(event)

    remove_listener = hass.bus.async_listen(EVENT_STATE_CHANGED, capture_combined_event)

    try:
        automation_context = Context(id="motion-automation-command")
        combined_light.async_set_context(automation_context)
        combined_light._manual_detector.track_expected_state("light.stage_1_1", 128)

        hass.states.async_set(
            "light.stage_1_1",
            STATE_ON,
            {ATTR_BRIGHTNESS: 128},
            context=Context(id="foreign-knx-confirmation"),
        )
        await hass.async_block_till_done()

        turned_on_events = [
            event
            for event in combined_events
            if event.data["new_state"].state == STATE_ON
        ]
        assert turned_on_events
        assert turned_on_events[-1].context.id == automation_context.id
    finally:
        remove_listener()
        await hass.config_entries.async_unload(config_entry.entry_id)


async def test_context_clobbering_race_condition(
    hass: HomeAssistant, mock_light_entities
):
    """Test that rapid updates clobber the integration context, causing valid events to be seen as manual."""

    # Setup config entry
    config_entry = MockConfigEntry(
        domain="combined_lights",
        data={
            "name": "Combined Test",
            "stage_1_lights": ["light.stage_1_1"],
            "stage_2_lights": ["light.stage_2_1"],
            CONF_ENABLE_BACK_PROPAGATION: True,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the entity instance
    # The entity_id is light.combined_test_combined_test based on the unique_id pattern
    entity_id = "light.combined_test_combined_test"

    # Retrieve the instance from the entity component
    component = hass.data.get("entity_components", {}).get("light")
    assert component is not None, "Light component not found"
    combined_light = component.get_entity(entity_id)
    assert combined_light is not None, f"Entity {entity_id} not found"

    # Mock LightController.turn_on_lights to capture calls and return expected states
    # We need to return a dict of expected states

    async def mock_turn_on_lights(entities, brightness_pct, context):
        # Return expected state (brightness value)
        brightness_val = int(brightness_pct / 100.0 * 255)
        return {entity: brightness_val for entity in entities}

    with patch(
        "custom_components.combined_lights.helpers.light_controller.LightController.turn_on_lights",
        side_effect=mock_turn_on_lights,
    ) as mock_turn_on:
        # 1. Operation A: Turn on to 50%
        # This will set the integration context to Context A
        await combined_light.async_turn_on(brightness=128)

        # Verify Op A happened
        assert mock_turn_on.call_count >= 1
        # Get the context from the last call of Op A
        args_a = mock_turn_on.call_args_list[-1]
        ctx_a = args_a[0][2]  # context is 3rd arg
        assert ctx_a is not None
        assert ctx_a.id in combined_light._manual_detector._recent_contexts

        # Capture call count so we can check Op B adds more calls
        call_count_after_a = mock_turn_on.call_count

        # 2. Operation B: Turn on to 100% immediately after
        # This will overwrite integration context to Context B
        await combined_light.async_turn_on(brightness=255)

        # Verify Op B happened
        assert mock_turn_on.call_count > call_count_after_a
        args_b = mock_turn_on.call_args_list[-1]
        ctx_b = args_b[0][2]
        assert ctx_b is not None
        assert ctx_a != ctx_b
        assert ctx_b.id in combined_light._manual_detector._recent_contexts
        assert ctx_a.id in combined_light._manual_detector._recent_contexts

        # 3. Now, the state change event from Operation A arrives!
        # It carries Context A.

        # We need to spy on the event bus firing to see if 'combined_light.external_change' is fired
        event_fired = False

        def external_change_listener(event):
            nonlocal event_fired
            event_fired = True

        hass.bus.async_listen(
            "combined_light.external_change", external_change_listener
        )

        # Fire the delayed event from Op A
        # Op A was 128 brightness (approx 50%).
        # For stage 1 light, 50% overall might mean 100% brightness if it's in stage 1?
        # Let's check the config: stage 1 lights are ["light.stage_1_1"].
        # Default breakpoints [25, 50, 75].
        # 50% is end of Stage 2.
        # So Stage 1 light should be ON at max brightness?
        # Let's just assume the brightness is whatever. The important thing is CONTEXT.
        # But wait, manual detector also checks brightness match.
        # If brightness matches expectation, it might ignore it even if context is different?
        # No, if context is external, it returns True immediately?
        # Let's check code:
        # if context_is_external: return True, "external_context"
        # So if context differs, it IS manual.

        # We use ctx_a. combined_light has ctx_b.
        # So context_is_external should be True.

        print(f"DEBUG: ctx_a.id={ctx_a.id}")
        print(
            f"DEBUG: recent_contexts={combined_light._manual_detector._recent_contexts}"
        )

        hass.states.async_set(
            "light.stage_1_1", STATE_ON, {ATTR_BRIGHTNESS: 128}, context=ctx_a
        )
        await hass.async_block_till_done()

        if event_fired:
            print(
                "\nBug reproduced: Delayed event from Op A was detected as manual change."
            )
        else:
            print("\nFIX VERIFIED: Delayed event from Op A was correctly ignored.")

        assert event_fired is False, "Event should be ignored with the fix"
