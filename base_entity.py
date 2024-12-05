"""Base entity for Light Manager Air."""
import logging
from abc import ABC
from typing import Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_ENTITY_ID, CONF_MARKER_ID, DOMAIN, CONF_MAPPINGS
from .coordinator import DATA_UPDATE_EVENT
from .lmair import _LMFixture

_LOGGER = logging.getLogger(__name__)


class LightManagerAirBaseEntity(ABC):
    """Base class for Light Manager Air entities."""

    def __init__(self, coordinator, unique_id_suffix: str, command_container: _LMFixture, zone_name: Optional[str] = None):
        """Initialize the base entity.
        
        :param coordinator: The coordinator instance
        :param command_container: The command container (actuator or marker)
        :param unique_id_suffix: Suffix for the unique ID (e.g., "marker_1" or "zone_actuator_1")
        :param zone_name: Optional zone name the entity belongs to
        """
        self._coordinator = coordinator
        self._command_container = command_container
        self._zone_name = zone_name
        self._attr_device_id = coordinator.device_id
        self._attr_name = command_container.name
        self._attr_unique_id = f"{self._attr_device_id}_{unique_id_suffix}"
        self._mapped_marker = None

        if zone_name:
            # Create device info for zoned entity
            self._attr_device_info = {
                "identifiers": {(DOMAIN, f"{self._attr_device_id}_{zone_name}")},
                "name": zone_name,
                "via_device": (DOMAIN, self._attr_device_id),
                "model": "Zone",
                "sw_version": coordinator.light_manager.fw_version,
                "suggested_area": self._zone_name
            }
        else:
            # Create device info for main device entity
            self._attr_device_info = coordinator.device_info

    def _setup_marker_mapping(self):
        """Setup marker mapping if configured."""
        if not self._coordinator.hass.data[DOMAIN].get(CONF_MAPPINGS):
            return

        for mapping in self._coordinator.hass.data[DOMAIN][CONF_MAPPINGS]:
            if mapping[CONF_ENTITY_ID] == self.entity_id:
                marker_id = mapping[CONF_MARKER_ID] - 1
                for marker in self._coordinator.markers:
                    if marker.marker_id == marker_id:
                        self._mapped_marker = marker
                        break
                break

    @property
    def is_on(self) -> bool | None:
        """Return if entity is on."""
        if self._mapped_marker:
            return self._mapped_marker.state
        return None

    async def async_added_to_hass(self) -> None:
        """Set up the entity when added to hass."""
        self._setup_marker_mapping()

        self._coordinator.hass.bus.async_listen(
            DATA_UPDATE_EVENT,
            self._handle_coordinator_update
        )

        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self, event):
        """Handle coordinator update event."""
        if event.data.get("device_id") == self._attr_device_id:
            self.async_write_ha_state()

    async def _async_call_command(self,
                                  hass: HomeAssistant,
                                  command_name: Optional[str] = None,
                                  command_index: Optional[int] = None
                                  ) -> None:
        """Call a command by its name or index."""
        if command_index is not None:
            try:
                await hass.async_add_executor_job(
                    self._command_container.commands[command_index].call
                )
            except (IndexError, ConnectionError) as e:
                raise HomeAssistantError(e)
            return

        if command_name:
            for cmd in self._command_container.commands:
                if command_name in cmd.name.lower():
                    try:
                        await hass.async_add_executor_job(cmd.call)
                        break
                    except ConnectionError as e:
                        raise HomeAssistantError(e)


class ToggleCommandMixin:
    """Mixin for toggle command functionality."""

    COMMAND_ON = 0
    COMMAND_TOGGLE = 1
    COMMAND_OFF = 2

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._async_call_command(self.hass, command_index=self.COMMAND_ON)
        if hasattr(self, '_coordinator'):
            await self._coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._async_call_command(self.hass, command_index=self.COMMAND_OFF)
        if hasattr(self, '_coordinator'):
            await self._coordinator.async_refresh()

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        await self._async_call_command(self.hass, command_index=self.COMMAND_TOGGLE)
        if hasattr(self, '_coordinator'):
            await self._coordinator.async_refresh()
