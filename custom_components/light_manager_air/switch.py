"""Switch platform for Light Manager Air."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity, ToggleCommandMixin
from .const import DOMAIN, CONF_ENTITY_CONVERSIONS, CONF_TARGET_TYPE, CONF_ZONE_NAME, CONF_ACTUATOR_NAME
from .coordinator import LightManagerAirCoordinator
from .lmair import LMMarker


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air switches."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    # Add marker switches
    if coordinator.markers:
        for marker in coordinator.markers:
            entities.append(LightManagerAirMarkerSwitch(coordinator, marker))

    # Add converted switches
    for zone in coordinator.zones:
        for actuator in zone.actuators:
            if LightManagerAirSwitch.check_actuator(actuator, zone.name, hass):
                entities.append(LightManagerAirSwitch(coordinator, zone, actuator))

    async_add_entities(entities)


class LightManagerAirMarkerSwitch(LightManagerAirBaseEntity, ToggleCommandMixin, SwitchEntity):
    """Representation of a Light Manager Air Marker Switch."""

    def __init__(self, coordinator: LightManagerAirCoordinator, marker: LMMarker):
        """Initialize the marker switch."""
        super().__init__(
            coordinator=coordinator,
            command_container=marker,
            unique_id_suffix=f"marker_{marker.marker_id}"
        )

    @property
    def is_on(self) -> bool:
        """Return true if the marker is on."""
        return self._command_container.state


class LightManagerAirSwitch(LightManagerAirBaseEntity, ToggleCommandMixin, SwitchEntity):
    """Representation of a Light Manager Air Switch."""

    def __init__(self, coordinator, zone, actuator):
        """Initialize the switch."""
        unique_id = f"{zone.name}_{actuator.name}"
        super().__init__(
            coordinator=coordinator,
            command_container=actuator,
            unique_id_suffix=unique_id,
            zone_name=zone.name
        )
        self._actuator = actuator

    @staticmethod
    def check_actuator(actuator, zone_name, hass):
        """Check if actuator should be handled as a switch."""
        # First check if there's a conversion configured
        if CONF_ENTITY_CONVERSIONS in hass.data[DOMAIN]:
            for conversion in hass.data[DOMAIN][CONF_ENTITY_CONVERSIONS]:
                if (conversion[CONF_ZONE_NAME] == zone_name and 
                    conversion[CONF_ACTUATOR_NAME] == actuator.name):
                    return conversion[CONF_TARGET_TYPE] == "switch"

        return False