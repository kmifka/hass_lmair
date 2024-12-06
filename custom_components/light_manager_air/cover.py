"""Cover platform for Light Manager Air."""
import logging

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LightManagerAirCoordinator
from .base_entity import LightManagerAirBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air covers."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for zone in coordinator.zones:
        for actuator in zone.actuators:
            if LightManagerAirCover.check_actuator(actuator):
                entities.append(LightManagerAirCover(coordinator, zone, actuator))

    async_add_entities(entities)

class LightManagerAirCover(LightManagerAirBaseEntity, CoverEntity):
    """Representation of a Light Manager Air cover."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    @staticmethod
    def check_actuator(actuator):
        """Check if actuator should be handled as a cover."""
        command_names = {cmd.name.lower() for cmd in actuator.commands}
        return {"up", "down", "stop"}.issubset(command_names)

    def __init__(self, coordinator, zone, actuator):
        """Initialize the cover."""
        unique_id = f"{zone.name}_{actuator.name}"
        super().__init__(
            coordinator=coordinator,
            command_container=actuator,
            unique_id_suffix=unique_id,
            zone_name=zone.name
        )
        self._actuator = actuator

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self._mapped_marker:
            state = self._mapped_marker.state
            return state if self._invert_marker else not state
        return None

    def is_open(self) -> bool | None:
        """Return if the cover is open."""
        if self._mapped_marker:
            state = self._mapped_marker.state
            return not state if self._invert_marker else state
        return None

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        for cmd in self._actuator.commands:
            if cmd.name.lower() == "up":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        for cmd in self._actuator.commands:
            if cmd.name.lower() == "down":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        for cmd in self._actuator.commands:
            if cmd.name.lower() == "stop":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

