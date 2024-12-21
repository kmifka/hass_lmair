"""Cover platform for Light Manager Air."""
import logging
from shutil import posix
from typing import Optional, Any
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from homeassistant.components.cover import CoverEntity, CoverEntityFeature, ATTR_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity, ToggleCommandMixin
from .const import DOMAIN, CONF_ENTITY_CONVERSIONS, CONF_TARGET_TYPE, CONF_ZONE_NAME, CONF_ACTUATOR_NAME, \
    CONF_COVER_TIMINGS, CONF_ENTITY_ID, CONF_TRAVEL_UP_TIME, CONF_TRAVEL_DOWN_TIME, CONF_CUSTOM_STOP_LOGIC, \
    STORAGE_VERSION, STORAGE_KEY_COVER_POSITIONS
from .coordinator import LightManagerAirCoordinator
from .helpers.travelcalculator import TravelCalculator, TravelStatus

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
        self._tc = None
        self._unsubscribe_auto_updater = None
        self._custom_stop_logic = False
        self._store = Store(
            coordinator.hass, 
            STORAGE_VERSION,
            STORAGE_KEY_COVER_POSITIONS
        )

        self._is_manual_position = False

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

    async def async_added_to_hass(self) -> None:
        """Set up the entity when added to hass."""
        await super().async_added_to_hass()

        # Initialize travel calculator after entity_id is available
        up_time = None
        down_time = None
        if self._coordinator.hass.data[DOMAIN].get(CONF_COVER_TIMINGS):
            for entry in self._coordinator.hass.data[DOMAIN][CONF_COVER_TIMINGS]:
                if entry[CONF_ENTITY_ID] == self.entity_id:
                    up_time = entry[CONF_TRAVEL_UP_TIME]
                    down_time = entry.get(CONF_TRAVEL_DOWN_TIME) or up_time
                    self._custom_stop_logic = entry.get(CONF_CUSTOM_STOP_LOGIC)
                    self._attr_supported_features |= CoverEntityFeature.SET_POSITION
                    break

        if up_time:
            # Initialize TravelCalculator if both times are defined
            self._tc = TravelCalculator(
                travel_time_down=int(down_time),
                travel_time_up=int(up_time),
            )
            await self._load_stored_position()

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
    def is_opening(self):
        """Return if the cover is opening or not."""
        if self._tc:
            return self._tc.is_traveling() and self._tc.travel_direction == TravelStatus.DIRECTION_UP

    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        if self._tc:
            return self._tc.is_traveling() and self._tc.travel_direction == TravelStatus.DIRECTION_DOWN

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._tc:
            return self._tc.is_closed()
        return not super().is_on

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover in percent."""
        if self._tc:
            return self._tc.current_position()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._send_open()

        if self._tc:
            self._is_manual_position = False
            self._tc.start_travel_up()
            self._start_auto_updater()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._send_close()

        if self._tc:
            self._is_manual_position = False
            self._tc.start_travel_down()
            self._start_auto_updater()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._send_stop()

        if self._tc and self._tc.is_traveling():
            self._is_manual_position = False
            self._tc.stop()
            self._stop_auto_updater()
            self.hass.async_create_task(self._save_position())

    async def async_set_cover_position(self, **kwargs: Any):
        position = kwargs[ATTR_POSITION]
        """Move cover to a designated position."""
        if not self._tc:
            return

        current_position = self._tc.current_position()
        if position < current_position and self._tc.travel_direction != TravelStatus.DIRECTION_DOWN:
            await self._send_close()
        elif position > current_position and self._tc.travel_direction != TravelStatus.DIRECTION_UP:
            await self._send_open()

        self._is_manual_position = position != 100 and position != 0
        self._tc.start_travel(position)
        self._start_auto_updater()

    async def _send_open(self):
        if self._is_converted:
            await self.async_turn_on()
            return

        await self._send_command("up")

    async def _send_close(self):
        if self._is_converted:
            await self.async_turn_off()
            return

        await self._send_command("down")

    async def _send_stop(self):
        if self._tc and self._custom_stop_logic:
            if self._tc.travel_direction == TravelStatus.DIRECTION_UP:
                await self._send_open()
            elif self._tc.travel_direction == TravelStatus.DIRECTION_DOWN:
                await self._send_close()
        else:
            if self._is_converted:
                return  # No stop function available

            await self._send_command("stop")

    async def _send_command(self, command):
        for cmd in self._actuator.commands:
            if cmd.name.lower() == command.lower():
                try:
                    await self.hass.async_add_executor_job(cmd.call)
                    break
                except ConnectionError as e:
                    raise HomeAssistantError(e)

    def _start_auto_updater(self):
        """Start interval that periodically updates the position."""
        if not self._unsubscribe_auto_updater:
            interval = timedelta(seconds=0.5)  # Update every 0.5s
            self._unsubscribe_auto_updater = async_track_time_interval(
                self.hass, self._auto_updater_hook, interval
            )

    def _stop_auto_updater(self):
        """Stop the auto updater."""
        if self._unsubscribe_auto_updater:
            self._unsubscribe_auto_updater()
            self._unsubscribe_auto_updater = None

    @callback
    async def _auto_updater_hook(self, now):
        """Called periodically while cover is moving."""
        if not self._tc:
            return

        # If target position is reached, stop movement and save position
        if self._tc.position_reached():
            if self._is_manual_position:
                self._is_manual_position = False
                await self._send_stop()
            self._tc.stop()
            self._stop_auto_updater()
            # Save position asynchronously
            self.hass.async_create_task(self._save_position())

        self.async_write_ha_state()

    async def _load_stored_position(self) -> None:
        """Load the stored position for this cover."""
        if not self._tc:
            return

        position = None

        try:
            stored_data = await self._store.async_load()
            if stored_data and isinstance(stored_data, dict):
                positions = stored_data.get("positions", {})
                if self.unique_id in positions:
                    position = positions[self.unique_id]
        except Exception as err:
            _LOGGER.error("Error loading stored position for %s: %s", self.entity_id, err)

        # If no position is stored use super state for position open or close
        position = position or self._tc.position_closed if not super().is_on else self._tc.position_closed

        self._tc.set_position(position)

    async def _save_position(self) -> None:
        """Save the current position for this cover."""
        if not self._tc:
            return

        try:
            stored_data = await self._store.async_load() or {}
            positions = stored_data.get("positions", {})
            positions[self.unique_id] = self._tc.current_position()
            await self._store.async_save({"positions": positions})
        except Exception as err:
            _LOGGER.error("Error saving position for %s: %s", self.entity_id, err)


