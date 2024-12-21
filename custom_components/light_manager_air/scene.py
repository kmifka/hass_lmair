"""Scene platform for Light Manager Air."""
from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity
from .const import DOMAIN, CONF_IGNORED_SCENE_ZONE
from .coordinator import LightManagerAirCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air scenes."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    if not LightManagerAirBaseEntity.is_zone_ignored(CONF_IGNORED_SCENE_ZONE, hass):
        scenes = []
        for scene in coordinator.scenes:
            scenes.append(LightManagerAirScene(coordinator, scene))

        async_add_entities(scenes)

class LightManagerAirScene(Scene):
    """Representation of a Light Manager Air scene."""

    def __init__(self, coordinator, scene):
        """Initialize the scene."""
        self._coordinator = coordinator
        self._scene = scene
        self._attr_device_id = coordinator.device_id
        self._attr_unique_id = f"{self._attr_device_id}_scene_{scene.name}"
        self._attr_name = scene.name

    async def async_activate(self, **kwargs) -> None:
        """Activate the scene."""
        try:
            await self.hass.async_add_executor_job(self._scene.call)
        except ConnectionError as e:
            raise HomeAssistantError(e)