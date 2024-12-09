"""Cover platform for Light Manager Air."""
import logging

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity, ToggleCommandMixin
from .const import DOMAIN, CONF_ENTITY_CONVERSIONS, CONF_TARGET_TYPE, CONF_ZONE_NAME, CONF_ACTUATOR_NAME
from .coordinator import LightManagerAirCoordinator

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
        # Skip ignored zones
        if LightManagerAirBaseEntity.is_zone_ignored(zone.name, hass):
            continue
            
        for actuator in zone.actuators:
            if LightManagerAirCover.check_actuator(actuator, zone.name, hass):
                entities.append(LightManagerAirCover(coordinator, zone, actuator))

    async_add_entities(entities)

class LightManagerAirCover(LightManagerAirBaseEntity, ToggleCommandMixin, CoverEntity):
    """Representation of a Light Manager Air cover."""

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

        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        
        # Check if this is a converted entity
        self._is_converted = False
        if CONF_ENTITY_CONVERSIONS in self._coordinator.hass.data[DOMAIN]:
            for conversion in self._coordinator.hass.data[DOMAIN][CONF_ENTITY_CONVERSIONS]:
                if (conversion[CONF_ZONE_NAME] == zone.name and 
                    conversion[CONF_ACTUATOR_NAME] == actuator.name):
                    self._is_converted = True
                    break
        
        if not self._is_converted:
            features |= CoverEntityFeature.STOP
        
        self._attr_supported_features = features

    @staticmethod
    def check_actuator(actuator, zone_name, hass):
        """Check if actuator should be handled as a cover."""
        # First check if there's a conversion configured
        if CONF_ENTITY_CONVERSIONS in hass.data[DOMAIN]:
            for conversion in hass.data[DOMAIN][CONF_ENTITY_CONVERSIONS]:
                if (conversion[CONF_ZONE_NAME] == zone_name and 
                    conversion[CONF_ACTUATOR_NAME] == actuator.name):
                    return conversion[CONF_TARGET_TYPE] == "cover"

        # Default logic for native covers
        command_names = {cmd.name.lower() for cmd in actuator.commands}
        return {"up", "down", "stop"}.issubset(command_names)

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
        if self._is_converted:
            await self.async_turn_on()
            return

        for cmd in self._actuator.commands:
            if cmd.name.lower() == "up":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if self._is_converted:
            await self.async_turn_off()
            return

        for cmd in self._actuator.commands:
            if cmd.name.lower() == "down":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if self._is_converted:
            return  # No stop function available

        for cmd in self._actuator.commands:
            if cmd.name.lower() == "stop":
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

