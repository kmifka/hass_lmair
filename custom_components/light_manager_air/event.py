"""Event platform for Light Manager Air."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import (
    EventEntity,
    EventDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LightManagerAirCoordinator, RADIO_BUS_SIGNAL_EVENT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air event entities."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([LightManagerAirRadioEvent(coordinator)])

class LightManagerAirRadioEvent(EventEntity):
    """Representation of a Light Manager Air radio event."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["radio_signal"]
    _attr_has_entity_name = True
    _attr_name = "Radio Signal"

    def __init__(self, coordinator: LightManagerAirCoordinator) -> None:
        """Initialize the event."""
        self._coordinator = coordinator
        self._attr_device_id = coordinator.device_id
        self._attr_unique_id = f"{coordinator.device_id}_radio_event"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.hass.bus.async_listen(
            RADIO_BUS_SIGNAL_EVENT,
            self._handle_event
        )

    @callback
    def _handle_event(self, event) -> None:
        """Handle the radio signal event."""
        if event.data.get("device_id") != self._attr_device_id:
            return

        self._trigger_event(
            "radio_signal",
            {
                "signal_type": event.data.get("signal_type"),
                "signal_code": event.data.get("signal_code")
            }
        )
        self.async_write_ha_state()