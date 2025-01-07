"""Sensor platform for Light Manager Air."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import LightManagerAirBaseEntity
from .const import DOMAIN, WEATHER_CHANNEL_NAME_TEMPLATE
from .coordinator import LightManagerAirCoordinator
from .weather import WeatherChannelMixin

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air sensor entities."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for channel in coordinator.weather_channels:
        # Skip channels that provide full weather data
        if channel.weather_id:
            continue
            
        # Add temperature sensor
        if channel.temperature != "":
            entities.append(LightManagerAirTemperatureSensor(coordinator, channel))
            
        # Add humidity sensor if value > 0
        if channel.humidity != "" and channel.humidity > 0:
            entities.append(LightManagerAirHumiditySensor(coordinator, channel))

    async_add_entities(entities)

class LightManagerAirTemperatureSensor(LightManagerAirBaseEntity, WeatherChannelMixin, SensorEntity):
    """Temperature sensor for Light Manager Air."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: LightManagerAirCoordinator, channel) -> None:
        """Initialize the sensor."""
        self.weather_channel_id = channel.id
        
        name_suffix = WEATHER_CHANNEL_NAME_TEMPLATE.format(channel.id)
        
        super().__init__(
            coordinator=coordinator,
            command_container=channel,
            unique_id_suffix=f"temperature_{channel.id}"
        )
        
        self._attr_name = name_suffix

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        channel = self._get_weather_channel()
        return channel.temperature if channel else None

class LightManagerAirHumiditySensor(LightManagerAirBaseEntity, WeatherChannelMixin, SensorEntity):
    """Humidity sensor for Light Manager Air."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: LightManagerAirCoordinator, channel) -> None:
        """Initialize the sensor."""
        self.weather_channel_id = channel.id
        
        name_suffix = WEATHER_CHANNEL_NAME_TEMPLATE.format(channel.id)
        
        super().__init__(
            coordinator=coordinator,
            command_container=channel,
            unique_id_suffix=f"humidity_{channel.id}"
        )
        
        self._attr_name = name_suffix

    @property
    def native_value(self) -> int | None:
        """Return the humidity."""
        channel = self._get_weather_channel()
        return channel.humidity if channel else None 