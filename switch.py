"""Switch platform for Light Manager Air."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity, ToggleCommandMixin
from .const import DOMAIN
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