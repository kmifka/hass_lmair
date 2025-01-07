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
    UnitOfPrecipitationDepth,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    WEATHER_CHANNEL_NAME_TEMPLATE,
    HA_CONDITION_MAP,
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

    for channel in coordinator.weather_channels:
        # Only add weather entities for channels with weather_id
        if channel.weather_id:
            entities.append(LightManagerAirWeather(coordinator, channel))
    
    async_add_entities(entities)

class WeatherChannelMixin:
    """Mixin to handle weather channel access."""

    def _get_weather_channel(self):
        """Get the weather channel for this entity.

        Returns:
            The weather channel object or None if not found.
        """
        for channel in self._coordinator.weather_channels:
            if channel.id == self.weather_channel_id:
                return channel
        return None

class LightManagerAirWeather(LightManagerAirBaseEntity, WeatherChannelMixin, WeatherEntity):
    """Representation of a Light Manager Air weather entity."""

    def __init__(self, coordinator: LightManagerAirCoordinator, channel) -> None:
        """Initialize the weather entity."""
        self.weather_channel_id = channel.id

        super().__init__(
            coordinator=coordinator,
            command_container=channel,
            unique_id_suffix=f"weather_{channel.id}"
        )

        self._attr_name = WEATHER_CHANNEL_NAME_TEMPLATE.format(channel.id)
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
        self._attr_condition = HA_CONDITION_MAP.get(channel.weather_id)

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        channel = self._get_weather_channel()
        return channel.temperature if channel else None

    @property
    def humidity(self) -> int | None:
        """Return the current humidity."""
        channel = self._get_weather_channel()
        return channel.humidity if channel else None

    @property
    def native_wind_speed(self) -> float | None:
        """Return the current wind speed."""
        channel = self._get_weather_channel()
        return channel.wind_speed if channel else None

    @property
    def wind_bearing(self) -> float | None:
        """Return the current wind bearing in degrees."""
        channel = self._get_weather_channel()
        return channel.wind_direction if channel else None

    @property
    def native_precipitation(self) -> float | None:
        """Return the current precipitation amount in mm."""
        channel = self._get_weather_channel()
        return channel.rain if channel else None