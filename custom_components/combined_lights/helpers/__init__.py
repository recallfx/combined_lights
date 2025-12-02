"""Helper classes for Combined Lights to improve separation of concerns."""

from .base_coordinator import (
    BaseBrightnessCalculator,
    BaseCombinedLightsCoordinator,
    LightState,
)
from .brightness_calculator import BrightnessCalculator
from .light_controller import LightController
from .manual_change_detector import ManualChangeDetector
from .zone_manager import ZoneManager

__all__ = [
    "BaseBrightnessCalculator",
    "BaseCombinedLightsCoordinator",
    "BrightnessCalculator",
    "LightController",
    "LightState",
    "ManualChangeDetector",
    "ZoneManager",
]
