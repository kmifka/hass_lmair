"""Constants for the Light Manager Air integration."""
from enum import Enum

import voluptuous as vol
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_EXCEPTIONAL,
)

DOMAIN = "light_manager_air"
CONF_DISCOVERED_DEVICE = "discovered_device"
CONF_MARKER_UPDATE_INTERVAL = "marker_update_interval"
CONF_MAPPINGS = "marker_mappings"
CONF_MARKER_ID = "marker_id"
CONF_ENTITY_ID = "entity_id"
CONF_HIDE_MARKER = "hide_marker"
CONF_INVERT = "invert"
CONF_IGNORED_ZONES = "ignored_zones"

DEFAULT_NAME = "Light Manager Air"

DEFAULT_RADIO_POLLING_INTERVAL = 2000
DEFAULT_MARKER_UPDATE_INTERVAL = 5000
DEFAULT_WEATHER_UPDATE_INTERVAL = 300000

# Weather constants
WEATHER_CHANNEL_NAME_TEMPLATE = "Channel {}"

# Mapping of OpenWeatherMap IDs to Home Assistant weather conditions
HA_CONDITION_MAP = {
    # Thunderstorm
    200: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with light rain
    201: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with rain
    202: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with heavy rain
    210: ATTR_CONDITION_LIGHTNING,        # light thunderstorm
    211: ATTR_CONDITION_LIGHTNING,        # thunderstorm
    212: ATTR_CONDITION_LIGHTNING,        # heavy thunderstorm
    221: ATTR_CONDITION_LIGHTNING,        # ragged thunderstorm
    230: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with light drizzle
    231: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with drizzle
    232: ATTR_CONDITION_LIGHTNING_RAINY,  # thunderstorm with heavy drizzle
    
    # Drizzle & Rain
    300: ATTR_CONDITION_RAINY,  # light intensity drizzle
    301: ATTR_CONDITION_RAINY,  # drizzle
    302: ATTR_CONDITION_RAINY,  # heavy intensity drizzle
    310: ATTR_CONDITION_RAINY,  # light intensity drizzle rain
    311: ATTR_CONDITION_RAINY,  # drizzle rain
    312: ATTR_CONDITION_RAINY,  # heavy intensity drizzle rain
    313: ATTR_CONDITION_RAINY,  # shower rain and drizzle
    314: ATTR_CONDITION_RAINY,  # heavy shower rain and drizzle
    321: ATTR_CONDITION_RAINY,  # shower drizzle
    500: ATTR_CONDITION_RAINY,  # light rain
    501: ATTR_CONDITION_RAINY,  # moderate rain
    502: ATTR_CONDITION_POURING,  # heavy intensity rain
    503: ATTR_CONDITION_POURING,  # very heavy rain
    504: ATTR_CONDITION_POURING,  # extreme rain
    511: ATTR_CONDITION_SNOWY_RAINY,  # freezing rain
    520: ATTR_CONDITION_RAINY,  # light intensity shower rain
    521: ATTR_CONDITION_RAINY,  # shower rain
    522: ATTR_CONDITION_POURING,  # heavy intensity shower rain
    531: ATTR_CONDITION_RAINY,  # ragged shower rain
    
    # Snow
    600: ATTR_CONDITION_SNOWY,  # light snow
    601: ATTR_CONDITION_SNOWY,  # snow
    602: ATTR_CONDITION_SNOWY,  # heavy snow
    611: ATTR_CONDITION_SNOWY_RAINY,  # sleet
    612: ATTR_CONDITION_SNOWY_RAINY,  # light shower sleet
    613: ATTR_CONDITION_SNOWY_RAINY,  # shower sleet
    615: ATTR_CONDITION_SNOWY_RAINY,  # light rain and snow
    616: ATTR_CONDITION_SNOWY_RAINY,  # rain and snow
    620: ATTR_CONDITION_SNOWY,  # light shower snow
    621: ATTR_CONDITION_SNOWY,  # shower snow
    622: ATTR_CONDITION_SNOWY,  # heavy shower snow
    
    # Atmosphere
    701: ATTR_CONDITION_FOG,     # mist
    711: ATTR_CONDITION_FOG,     # smoke
    721: ATTR_CONDITION_FOG,     # haze
    731: ATTR_CONDITION_FOG,     # sand/dust
    741: ATTR_CONDITION_FOG,     # fog
    751: ATTR_CONDITION_FOG,     # sand
    761: ATTR_CONDITION_FOG,     # dust
    762: ATTR_CONDITION_FOG,     # volcanic ash
    771: ATTR_CONDITION_WINDY,   # squalls
    781: ATTR_CONDITION_EXCEPTIONAL,  # tornado
    
    # Clear & Clouds
    800: ATTR_CONDITION_CLEAR_NIGHT,  # clear sky
    801: ATTR_CONDITION_PARTLYCLOUDY,  # few clouds
    802: ATTR_CONDITION_PARTLYCLOUDY,  # scattered clouds
    803: ATTR_CONDITION_CLOUDY,  # broken clouds
    804: ATTR_CONDITION_CLOUDY,  # overcast clouds
}

# Rate Limiter defaults
DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_WINDOW = 3
CONF_RATE_LIMIT = "rate_limit"
CONF_RATE_WINDOW = "rate_window"

# Entity type conversion constants
CONF_ENTITY_CONVERSIONS = "entity_conversions"
CONF_ZONE_NAME = "zone_name"
CONF_ACTUATOR_NAME = "actuator_name"
CONF_TARGET_TYPE = "target_type"

VALID_TARGET_TYPES = ["light", "switch", "cover"]

# Schema for Entity Conversion
CONVERSION_SCHEMA = vol.Schema({
    vol.Required(CONF_ZONE_NAME): str,
    vol.Required(CONF_ACTUATOR_NAME): str,
    vol.Required(CONF_TARGET_TYPE): vol.In(VALID_TARGET_TYPES),
})

# Config flow constants
CONF_ENABLE_RADIO_BUS = "enable_radio_bus"
CONF_RADIO_POLLING_INTERVAL = "polling_interval"

# Schema for the Mapping
MAPPING_SCHEMA = vol.Schema({
    vol.Required(CONF_MARKER_ID): int,
    vol.Required(CONF_ENTITY_ID): str,
    vol.Optional(CONF_INVERT, default=False): bool,
})

CONF_ENABLE_MARKER_UPDATES = "enable_marker_updates"

MIN_POLLING_CALLS = 3
POLLING_TIME_WINDOW = 60  # in seconds

CONF_ENABLE_WEATHER_UPDATES = "enable_weather_updates"
CONF_WEATHER_UPDATE_INTERVAL = "weather_update_interval"

class Priority(Enum):
    EVENT = 1
    POLLING = 2

MINIMUM_FIRMWARE_VERSION = "11.1"