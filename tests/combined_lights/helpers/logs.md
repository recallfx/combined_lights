# All off, knx switch stage 4 (study_ceiling) on, 100% brightness. result good, all lights on

2025-12-03 18:00:14.474 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: off@None -> on@0 | ctx=01KBJF2Q ours=False | expected=0 | updating=False
2025-12-03 18:00:14.474 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (expected_brightness_match, diff=0)
2025-12-03 18:00:15.775 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: on@0 -> on@255 | ctx=01KBJF2R ours=False | expected=None | updating=False
2025-12-03 18:00:15.776 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:00:15.776 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_ceiling: external_context
2025-12-03 18:00:15.776 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_ceiling state=on brightness=255
2025-12-03 18:00:15.776 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'False@0', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'True@255'}
2025-12-03 18:00:15.777 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=100.0%, back_prop_enabled=True, changes={'study_bg': 255, 'study_feature': 255, 'study_desk': 255}
2025-12-03 18:00:15.777 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:00:15.777 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context a872316c (total: 6)
2025-12-03 18:00:15.777 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 255, 'light.study_feature': 255, 'light.study_desk': 255} (excluding light.study_ceiling)
2025-12-03 18:00:15.777 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:00:15.778 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 255, 'study_feature': 255, 'study_desk': 255} (context=a872316c)
2025-12-03 18:00:15.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 255
2025-12-03 18:00:15.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 255
2025-12-03 18:00:15.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 255
2025-12-03 18:00:15.778 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg', 'study_feature', 'study_desk'] at 100.0%
2025-12-03 18:00:15.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=100.0%, brightness_value=255, entities=['light.study_bg', 'light.study_feature', 'light.study_desk']
2025-12-03 18:00:15.796 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg', 'light.study_feature', 'light.study_desk'] with brightness 255
2025-12-03 18:00:15.797 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:00:16.024 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: off@None -> on@255 | ctx=a872316c ours=True | expected=255 | updating=False
2025-12-03 18:00:16.024 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:00:16.043 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: off@None -> on@255 | ctx=a872316c ours=True | expected=255 | updating=False
2025-12-03 18:00:16.044 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)

# All on, knx switch all off at the same time, result not ok: all off, and then stage 1 switched on (should have stayed off)

2025-12-03 18:06:31.193 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@255 -> off@None | ctx=01KBJFE7 ours=False | expected=None | updating=False
2025-12-03 18:06:31.194 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:06:31.194 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_desk: external_context
2025-12-03 18:06:31.194 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_desk state=off brightness=0
2025-12-03 18:06:31.195 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@255', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'True@255'}
2025-12-03 18:06:31.195 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=60.0%, back_prop_enabled=True, changes={'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0}
2025-12-03 18:06:31.195 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:06:31.196 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context efa03a8b (total: 6)
2025-12-03 18:06:31.196 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 154, 'light.study_feature': 110, 'light.study_ceiling': 0} (excluding light.study_desk)
2025-12-03 18:06:31.196 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:06:31.196 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0} (context=efa03a8b)
2025-12-03 18:06:31.196 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 154
2025-12-03 18:06:31.197 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg'] at 60.4%
2025-12-03 18:06:31.197 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=60.4%, brightness_value=154, entities=['light.study_bg']
2025-12-03 18:06:31.198 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg'] with brightness 154
2025-12-03 18:06:31.198 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 110
2025-12-03 18:06:31.199 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature'] at 43.1%
2025-12-03 18:06:31.199 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=43.1%, brightness_value=110, entities=['light.study_feature']
2025-12-03 18:06:31.200 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature'] with brightness 110
2025-12-03 18:06:31.200 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:06:31.204 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_ceiling']
2025-12-03 18:06:31.206 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_ceiling']
2025-12-03 18:06:31.206 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:06:31.263 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@255 -> off@None | ctx=efa03a8b ours=True | expected=154 | updating=False
2025-12-03 18:06:31.264 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:06:31.405 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: on@255 -> off@None | ctx=efa03a8b ours=True | expected=0 | updating=False
2025-12-03 18:06:31.405 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:06:31.446 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: off@None -> on@0 | ctx=efa03a8b ours=True | expected=None | updating=False
2025-12-03 18:06:31.447 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:06:32.515 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@0 -> on@154 | ctx=efa03a8b ours=True | expected=None | updating=False
2025-12-03 18:06:32.515 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)

## again knx switch off all, result good: now stage 1 gets switched off

2025-12-03 18:07:56.294 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@154 -> off@None | ctx=01KBJFGT ours=False | expected=None | updating=False
2025-12-03 18:07:56.294 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:07:56.294 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:07:56.295 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=off brightness=0
2025-12-03 18:07:56.295 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'False@0', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:07:56.295 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=0.0%, back_prop_enabled=True, changes={'study_feature': 110, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:07:56.296 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:07:56.296 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 310edaf2 (total: 6)
2025-12-03 18:07:56.296 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 110, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:07:56.296 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:07:56.296 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 110, 'study_desk': 0, 'study_ceiling': 0} (context=310edaf2)
2025-12-03 18:07:56.297 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 110
2025-12-03 18:07:56.297 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature'] at 43.1%
2025-12-03 18:07:56.297 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=43.1%, brightness_value=110, entities=['light.study_feature']
2025-12-03 18:07:56.298 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature'] with brightness 110
2025-12-03 18:07:56.298 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:07:56.298 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:07:56.299 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_desk', 'study_ceiling']
2025-12-03 18:07:56.328 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_desk', 'light.study_ceiling']
2025-12-03 18:07:56.329 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False

# all off, knx switch stage 3 (study_desk) on 100%. result good: all lights are on 100%

2025-12-03 18:08:46.640 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: off@None -> on@0 | ctx=01KBJFJB ours=False | expected=0 | updating=False
2025-12-03 18:08:46.640 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (expected_brightness_match, diff=0)
2025-12-03 18:08:47.843 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@0 -> on@255 | ctx=01KBJFJC ours=False | expected=None | updating=False
2025-12-03 18:08:47.843 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:08:47.843 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_desk: external_context
2025-12-03 18:08:47.844 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_desk state=on brightness=255
2025-12-03 18:08:47.844 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'False@0', 'study_feature': 'False@0', 'study_desk': 'True@255', 'study_ceiling': 'False@0'}
2025-12-03 18:08:47.844 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=100.0%, back_prop_enabled=True, changes={'study_bg': 255, 'study_feature': 255, 'study_ceiling': 255}
2025-12-03 18:08:47.845 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:08:47.845 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 7e1f11b5 (total: 6)
2025-12-03 18:08:47.845 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 255, 'light.study_feature': 255, 'light.study_ceiling': 255} (excluding light.study_desk)
2025-12-03 18:08:47.845 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:08:47.846 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 255, 'study_feature': 255, 'study_ceiling': 255} (context=7e1f11b5)
2025-12-03 18:08:47.846 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 255
2025-12-03 18:08:47.846 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 255
2025-12-03 18:08:47.846 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 255
2025-12-03 18:08:47.846 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg', 'study_feature', 'study_ceiling'] at 100.0%
2025-12-03 18:08:47.846 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=100.0%, brightness_value=255, entities=['light.study_bg', 'light.study_feature', 'light.study_ceiling']
2025-12-03 18:08:47.882 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg', 'light.study_feature', 'light.study_ceiling'] with brightness 255
2025-12-03 18:08:47.882 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:08:48.027 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: off@None -> on@255 | ctx=7e1f11b5 ours=True | expected=255 | updating=False
2025-12-03 18:08:48.028 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:08:48.374 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: off@None -> on@255 | ctx=7e1f11b5 ours=True | expected=255 | updating=False
2025-12-03 18:08:48.374 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)

## knx switch reduce brightness on stage 3 (study_desk) to ~50%, result good: stage 4 swithed off and others reduced brightness

2025-12-03 18:10:32.618 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@255 -> on@47 | ctx=01KBJFNJ ours=False | expected=None | updating=False
2025-12-03 18:10:32.618 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:10:32.619 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_desk: external_context
2025-12-03 18:10:32.619 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_desk state=on brightness=47
2025-12-03 18:10:32.619 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@255', 'study_feature': 'False@0', 'study_desk': 'True@47', 'study_ceiling': 'True@255'}
2025-12-03 18:10:32.620 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=67.0%, back_prop_enabled=True, changes={'study_bg': 170, 'study_feature': 134, 'study_ceiling': 0}
2025-12-03 18:10:32.620 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:10:32.620 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 2a7a70c9 (total: 6)
2025-12-03 18:10:32.621 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 170, 'light.study_feature': 134, 'light.study_ceiling': 0} (excluding light.study_desk)
2025-12-03 18:10:32.621 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:10:32.621 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 170, 'study_feature': 134, 'study_ceiling': 0} (context=2a7a70c9)
2025-12-03 18:10:32.621 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 170
2025-12-03 18:10:32.621 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg'] at 66.7%
2025-12-03 18:10:32.622 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=66.7%, brightness_value=169, entities=['light.study_bg']
2025-12-03 18:10:32.623 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg'] with brightness 169
2025-12-03 18:10:32.623 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 134
2025-12-03 18:10:32.623 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature'] at 52.5%
2025-12-03 18:10:32.624 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=52.5%, brightness_value=134, entities=['light.study_feature']
2025-12-03 18:10:32.640 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature'] with brightness 134
2025-12-03 18:10:32.641 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:10:32.641 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_ceiling']
2025-12-03 18:10:32.642 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_ceiling']
2025-12-03 18:10:32.642 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:10:32.712 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@255 -> on@169 | ctx=2a7a70c9 ours=True | expected=170 | updating=False
2025-12-03 18:10:32.712 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:10:32.826 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: on@255 -> off@None | ctx=2a7a70c9 ours=True | expected=0 | updating=False
2025-12-03 18:10:32.827 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)

## knx reduces stage 3 (study_desk) to min, result looks ok, but needs to verify that stage 1 and 2 got reduced too

2025-12-03 18:13:40.436 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@47 -> on@3 | ctx=01KBJFVA ours=False | expected=None | updating=False
2025-12-03 18:13:40.436 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:13:40.436 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_desk: external_context
2025-12-03 18:13:40.436 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_desk state=on brightness=3
2025-12-03 18:13:40.437 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@169', 'study_feature': 'False@0', 'study_desk': 'True@3', 'study_ceiling': 'False@0'}
2025-12-03 18:13:40.437 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=60.1%, back_prop_enabled=True, changes={'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0}
2025-12-03 18:13:40.437 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:13:40.438 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 8d32f611 (total: 6)
2025-12-03 18:13:40.438 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 154, 'light.study_feature': 110, 'light.study_ceiling': 0} (excluding light.study_desk)
2025-12-03 18:13:40.438 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:13:40.438 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0} (context=8d32f611)
2025-12-03 18:13:40.438 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 154
2025-12-03 18:13:40.438 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg'] at 60.4%
2025-12-03 18:13:40.439 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=60.4%, brightness_value=154, entities=['light.study_bg']
2025-12-03 18:13:40.440 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg'] with brightness 154
2025-12-03 18:13:40.440 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 110
2025-12-03 18:13:40.440 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature'] at 43.1%
2025-12-03 18:13:40.440 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=43.1%, brightness_value=110, entities=['light.study_feature']
2025-12-03 18:13:40.441 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature'] with brightness 110
2025-12-03 18:13:40.441 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:13:40.456 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_ceiling']
2025-12-03 18:13:40.457 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_ceiling']
2025-12-03 18:13:40.458 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:13:40.514 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@169 -> on@154 | ctx=8d32f611 ours=True | expected=154 | updating=False
2025-12-03 18:13:40.514 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)

## knx switch switches stage 3 (study_desk) off, result looks ok

2025-12-03 18:15:04.835 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@3 -> off@None | ctx=01KBJFXW ours=False | expected=None | updating=False
2025-12-03 18:15:04.836 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:15:04.836 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_desk: external_context
2025-12-03 18:15:04.836 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_desk state=off brightness=0
2025-12-03 18:15:04.837 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@154', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:15:04.837 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=60.0%, back_prop_enabled=True, changes={'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0}
2025-12-03 18:15:04.837 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:15:04.838 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 60a09dba (total: 6)
2025-12-03 18:15:04.838 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_bg': 154, 'light.study_feature': 110, 'light.study_ceiling': 0} (excluding light.study_desk)
2025-12-03 18:15:04.838 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:15:04.838 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_bg': 154, 'study_feature': 110, 'study_ceiling': 0} (context=60a09dba)
2025-12-03 18:15:04.838 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_bg -> 154
2025-12-03 18:15:04.839 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_bg'] at 60.4%
2025-12-03 18:15:04.839 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=60.4%, brightness_value=154, entities=['light.study_bg']
2025-12-03 18:15:04.840 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_bg'] with brightness 154
2025-12-03 18:15:04.841 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 110
2025-12-03 18:15:04.841 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature'] at 43.1%
2025-12-03 18:15:04.841 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=43.1%, brightness_value=110, entities=['light.study_feature']
2025-12-03 18:15:04.860 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature'] with brightness 110
2025-12-03 18:15:04.860 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:15:04.860 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_ceiling']
2025-12-03 18:15:04.861 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_ceiling']
2025-12-03 18:15:04.861 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
 Live

## knx switch reduces brightness on stage 1 (study_bg), result looks ok:

2025-12-03 18:15:36.530 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@154 -> on@34 | ctx=01KBJFYV ours=False | expected=154 | updating=False
2025-12-03 18:15:36.531 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (brightness_mismatch, expected=154 got=34 diff=120)
2025-12-03 18:15:36.531 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: brightness_mismatch
2025-12-03 18:15:36.531 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=34
2025-12-03 18:15:36.531 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@34', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:15:36.532 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=12.5%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:15:36.532 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:15:36.532 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 269223b0 (total: 6)
2025-12-03 18:15:36.533 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:15:36.533 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:15:36.533 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=269223b0)
2025-12-03 18:15:36.533 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:15:36.533 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:15:36.534 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:15:36.534 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:15:36.560 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:15:36.560 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:15:37.251 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@34 -> on@19 | ctx=01KBJFYW ours=False | expected=None | updating=False
2025-12-03 18:15:37.251 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:15:37.252 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:15:37.252 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=19
2025-12-03 18:15:37.252 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@19', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:15:37.253 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=6.5%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:15:37.253 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:15:37.253 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context e36db7f9 (total: 6)
2025-12-03 18:15:37.253 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:15:37.254 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:15:37.254 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=e36db7f9)
2025-12-03 18:15:37.254 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:15:37.254 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:15:37.254 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:15:37.254 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:15:37.270 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:15:37.271 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
 Live

## knx switch off stage 1 (study_bg), result looks ok:

2025-12-03 18:24:52.776 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@19 -> off@None | ctx=01KBJGFT ours=False | expected=None | updating=False
2025-12-03 18:24:52.776 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:24:52.776 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:24:52.777 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=off brightness=0
2025-12-03 18:24:52.777 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'False@0', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:24:52.777 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=0.0%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:24:52.777 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:24:52.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context ff140ca4 (total: 6)
2025-12-03 18:24:52.778 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:24:52.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:24:52.778 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=ff140ca4)
2025-12-03 18:24:52.778 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:24:52.779 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:24:52.779 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:24:52.779 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:24:52.800 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:24:52.800 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False

# knx switch increase brightness stage 1 (study_bg), result not ok, some other stages switched on and then off, in the end stage 1 brightness looks ok.

2025-12-03 18:26:25.267 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: off@None -> on@0 | ctx=01KBJGJN ours=False | expected=None | updating=False
2025-12-03 18:26:25.268 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:26:25.268 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:26:25.268 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=255
2025-12-03 18:26:25.268 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@255', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:26:25.269 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=100.0%, back_prop_enabled=True, changes={'study_feature': 255, 'study_desk': 255, 'study_ceiling': 255}
2025-12-03 18:26:25.269 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:26:25.269 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 96d902c7 (total: 6)
2025-12-03 18:26:25.269 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 255, 'light.study_desk': 255, 'light.study_ceiling': 255} (excluding light.study_bg)
2025-12-03 18:26:25.270 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:26:25.270 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 255, 'study_desk': 255, 'study_ceiling': 255} (context=96d902c7)
2025-12-03 18:26:25.270 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 255
2025-12-03 18:26:25.270 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 255
2025-12-03 18:26:25.270 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 255
2025-12-03 18:26:25.270 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature', 'study_desk', 'study_ceiling'] at 100.0%
2025-12-03 18:26:25.271 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=100.0%, brightness_value=255, entities=['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:26:25.302 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature', 'light.study_desk', 'light.study_ceiling'] with brightness 255
2025-12-03 18:26:25.302 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:26:25.434 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: off@None -> on@255 | ctx=96d902c7 ours=True | expected=255 | updating=False
2025-12-03 18:26:25.435 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:26:25.783 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: off@None -> on@255 | ctx=96d902c7 ours=True | expected=255 | updating=False
2025-12-03 18:26:25.784 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:26:25.837 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@0 -> on@10 | ctx=01KBJGJN ours=False | expected=None | updating=False
2025-12-03 18:26:25.838 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:26:25.838 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:26:25.838 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=10
2025-12-03 18:26:25.838 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@10', 'study_feature': 'False@0', 'study_desk': 'True@255', 'study_ceiling': 'True@255'}
2025-12-03 18:26:25.839 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=3.0%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:26:25.839 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:26:25.839 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context eb908d50 (total: 6)
2025-12-03 18:26:25.839 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:26:25.840 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:26:25.840 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=eb908d50)
2025-12-03 18:26:25.840 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:26:25.840 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:26:25.840 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:26:25.840 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:26:25.876 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:26:25.876 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:26:25.927 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: on@255 -> off@None | ctx=eb908d50 ours=True | expected=0 | updating=False
2025-12-03 18:26:25.927 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:26:26.048 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: on@255 -> off@None | ctx=eb908d50 ours=True | expected=0 | updating=False
2025-12-03 18:26:26.049 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:26:26.548 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@10 -> on@15 | ctx=01KBJGJP ours=False | expected=None | updating=False
2025-12-03 18:26:26.548 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:26:26.548 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:26:26.549 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=15
2025-12-03 18:26:26.549 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@15', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:26:26.549 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=4.9%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:26:26.549 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:26:26.550 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context e0518209 (total: 6)
2025-12-03 18:26:26.550 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:26:26.550 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:26:26.550 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=e0518209)
2025-12-03 18:26:26.550 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:26:26.550 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:26:26.551 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:26:26.551 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:26:26.580 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:26:26.580 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False

## knx switch increase more brightness stage 1 (study_bg), result ok (but log is littered with unrelated actions)

025-12-03 18:29:07.994 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@15 -> on@46 | ctx=01KBJGQM ours=False | expected=None | updating=False
2025-12-03 18:29:07.994 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:29:07.995 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=46
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@46', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=17.2%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:29:07.996 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:29:07.996 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context b67719ac (total: 6)
2025-12-03 18:29:07.996 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:29:07.996 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:29:07.997 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=b67719ac)
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:29:07.997 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:29:08.024 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:29:08.024 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:29:08.711 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@46 -> on@71 | ctx=01KBJGQM ours=False | expected=None | updating=False
2025-12-03 18:29:08.711 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:29:08.711 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=71
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@71', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=27.1%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:29:08.713 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context bbfeb134 (total: 6)
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:29:08.713 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=bbfeb134)
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:29:08.714 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:29:08.734 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:29:08.734 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False

## knx switch increase even more brightness stage 1 (study_bg), result looks ok (not sure about the log) other stages switched on

2025-12-03 18:29:07.994 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@15 -> on@46 | ctx=01KBJGQM ours=False | expected=None | updating=False
2025-12-03 18:29:07.994 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:29:07.995 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=46
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@46', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:29:07.995 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=17.2%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:29:07.996 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:29:07.996 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context b67719ac (total: 6)
2025-12-03 18:29:07.996 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:29:07.996 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:29:07.997 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=b67719ac)
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:29:07.997 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:29:07.997 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:29:08.024 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:29:08.024 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:29:08.711 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@46 -> on@71 | ctx=01KBJGQM ours=False | expected=None | updating=False
2025-12-03 18:29:08.711 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:29:08.711 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=71
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@71', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:29:08.712 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=27.1%, back_prop_enabled=True, changes={'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0}
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:29:08.713 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context bbfeb134 (total: 6)
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 0, 'light.study_desk': 0, 'light.study_ceiling': 0} (excluding light.study_bg)
2025-12-03 18:29:08.713 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:29:08.713 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 0, 'study_desk': 0, 'study_ceiling': 0} (context=bbfeb134)
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 0
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 0
2025-12-03 18:29:08.714 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 0
2025-12-03 18:29:08.714 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_off for ['study_feature', 'study_desk', 'study_ceiling']
2025-12-03 18:29:08.734 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_off for ['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:29:08.734 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:30:46.964 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_bg: on@71 -> on@255 | ctx=01KBJGTM ours=False | expected=None | updating=False
2025-12-03 18:30:46.964 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> MANUAL (external_context, no expectation)
2025-12-03 18:30:46.965 DEBUG (MainThread) [custom_components.combined_lights.light] Manual intervention detected for light.study_bg: external_context
2025-12-03 18:30:46.965 INFO (MainThread) [custom_components.combined_lights.light] HANDLE manual change: study_bg state=on brightness=255
2025-12-03 18:30:46.965 INFO (MainThread) [custom_components.combined_lights.light]   Lights state after sync: {'study_bg': 'True@255', 'study_feature': 'False@0', 'study_desk': 'False@0', 'study_ceiling': 'False@0'}
2025-12-03 18:30:46.966 INFO (MainThread) [custom_components.combined_lights.light]   Result: overall=100.0%, back_prop_enabled=True, changes={'study_feature': 255, 'study_desk': 255, 'study_ceiling': 255}
2025-12-03 18:30:46.966 INFO (MainThread) [custom_components.combined_lights.light]   Scheduling back-propagation for 3 lights
2025-12-03 18:30:46.966 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Added context 96ee1ad3 (total: 6)
2025-12-03 18:30:46.966 INFO (MainThread) [custom_components.combined_lights.light] Back-propagation: applying changes {'light.study_feature': 255, 'light.study_desk': 255, 'light.study_ceiling': 255} (excluding light.study_bg)
2025-12-03 18:30:46.967 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to True
2025-12-03 18:30:46.967 INFO (MainThread) [custom_components.combined_lights.light] APPLY changes to HA: {'study_feature': 255, 'study_desk': 255, 'study_ceiling': 255} (context=96ee1ad3)
2025-12-03 18:30:46.967 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_feature -> 255
2025-12-03 18:30:46.967 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_desk -> 255
2025-12-03 18:30:46.968 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Tracking expected state: light.study_ceiling -> 255
2025-12-03 18:30:46.968 INFO (MainThread) [custom_components.combined_lights.light]   Calling turn_on for ['study_feature', 'study_desk', 'study_ceiling'] at 100.0%
2025-12-03 18:30:46.968 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] LightController.turn_on_lights: brightness_pct=100.0%, brightness_value=255, entities=['light.study_feature', 'light.study_desk', 'light.study_ceiling']
2025-12-03 18:30:47.008 DEBUG (MainThread) [custom_components.combined_lights.helpers.light_controller] Called light.turn_on for ['light.study_feature', 'light.study_desk', 'light.study_ceiling'] with brightness 255
2025-12-03 18:30:47.009 DEBUG (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] Updating flag set to False
2025-12-03 18:30:47.135 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_desk: off@None -> on@255 | ctx=96ee1ad3 ours=True | expected=255 | updating=False
2025-12-03 18:30:47.135 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
2025-12-03 18:30:47.467 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector] StateChange study_ceiling: off@None -> on@255 | ctx=96ee1ad3 ours=True | expected=255 | updating=False
2025-12-03 18:30:47.468 INFO (MainThread) [custom_components.combined_lights.helpers.manual_change_detector]   -> NOT manual (recent_context_match)
 Live
