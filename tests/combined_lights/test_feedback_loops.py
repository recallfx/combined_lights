"""Test feedback loops and potential interference in Combined Lights."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Context, HomeAssistant, State

from custom_components.combined_lights.const import CONF_ENABLE_BACK_PROPAGATION
from custom_components.combined_lights.light import CombinedLight

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def mock_light_entities(hass):
    """Create mock light entities."""
    hass.states.async_set("light.stage_1_1", STATE_OFF)
    hass.states.async_set("light.stage_2_1", STATE_OFF)
    return ["light.stage_1_1", "light.stage_2_1"]


async def test_context_clobbering_race_condition(hass: HomeAssistant, mock_light_entities):
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
    # The entity_id is likely light.combined_test based on the name "Combined Test"
    entity_id = "light.combined_test"
    
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

    with patch("custom_components.combined_lights.helpers.light_controller.LightController.turn_on_lights", side_effect=mock_turn_on_lights) as mock_turn_on:
        
        # 1. Operation A: Turn on to 50%
        # This will set the integration context to Context A
        await combined_light.async_turn_on(brightness=128)
        
        # Verify Op A happened
        assert mock_turn_on.call_count >= 1
        # Get the context from the last call of Op A
        args_a = mock_turn_on.call_args_list[-1]
        ctx_a = args_a[0][2] # context is 3rd arg
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
            
        hass.bus.async_listen("combined_light.external_change", external_change_listener)
        
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
        print(f"DEBUG: recent_contexts={combined_light._manual_detector._recent_contexts}")
        
        hass.states.async_set(
            "light.stage_1_1", 
            STATE_ON, 
            {ATTR_BRIGHTNESS: 128}, 
            context=ctx_a
        )
        await hass.async_block_till_done()
        
        if event_fired:
            print("\nBug reproduced: Delayed event from Op A was detected as manual change.")
        else:
            print("\nFIX VERIFIED: Delayed event from Op A was correctly ignored.")
            
        assert event_fired is False, "Event should be ignored with the fix"

