"""Weather platform for Light Manager Air."""
import logging
from typing import Any

from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    WEATHER_CONDITION_MAP, WEATHER_CHANNEL_NAME_TEMPLATE,
)
from .coordinator import LightManagerAirCoordinator
from .base_entity import LightManagerAirBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Light Manager Air weather entities."""
    coordinator: LightManagerAirCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    weather_channels = coordinator.data.get("weather_channels", [])
    _LOGGER.debug(weather_channels)
    
    for channel in weather_channels:
        # Only add weather entities for channels with weather_id
        if channel.weather_id:
            entities.append(LightManagerAirWeather(coordinator, channel))
    
    async_add_entities(entities)

class LightManagerAirWeather(LightManagerAirBaseEntity, WeatherEntity):
    """Representation of a Light Manager Air weather entity."""

    def __init__(self, coordinator: LightManagerAirCoordinator, channel) -> None:
        """Initialize the weather entity."""
        self.weather_channel = channel

        super().__init__(
            coordinator=coordinator,
            command_container=channel,
            unique_id_suffix=f"weather_{channel.channel_id}"
        )

        self._attr_name = WEATHER_CHANNEL_NAME_TEMPLATE.format(channel.channel_id)
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        return WEATHER_CONDITION_MAP.get(self.weather_channel.weather_id)

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.weather_channel.temperature

    @property
    def humidity(self) -> int | None:
        """Return the current humidity."""
        return self.weather_channel.humidity

    @property
    def native_wind_speed(self) -> float | None:
        """Return the current wind speed."""
        return self.weather_channel.wind_speed

    @property
    def wind_bearing(self) -> int | None:
        """Return the current wind direction."""
        return self.weather_channel.wind_direction