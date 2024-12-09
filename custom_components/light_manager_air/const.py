"""Constants for the Light Manager Air integration."""
from enum import Enum

import voluptuous as vol

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

# Weather constants
WEATHER_INDOOR_CHANNEL_ID = 0
WEATHER_CHANNEL_NAME_TEMPLATE = "Weather Channel {}"
WEATHER_CONDITION_MAP = {
    # Thunderstorm
    200: "thunderstorm_with_light_rain",
    201: "thunderstorm_with_rain",
    202: "thunderstorm_with_heavy_rain",
    210: "light_thunderstorm",
    211: "thunderstorm",
    212: "heavy_thunderstorm",
    221: "ragged_thunderstorm",
    230: "thunderstorm_with_light_drizzle",
    231: "thunderstorm_with_drizzle",
    232: "thunderstorm_with_heavy_drizzle",
    
    # Drizzle
    300: "light_drizzle",
    301: "drizzle",
    302: "heavy_drizzle",
    310: "light_drizzle_rain",
    311: "drizzle_rain",
    312: "heavy_drizzle_rain",
    313: "shower_rain_and_drizzle",
    314: "heavy_shower_rain_and_drizzle",
    321: "shower_drizzle",
    
    # Rain
    500: "light_rain",
    501: "moderate_rain",
    502: "heavy_rain",
    503: "very_heavy_rain",
    504: "extreme_rain",
    511: "freezing_rain",
    520: "light_shower_rain",
    521: "shower_rain",
    522: "heavy_shower_rain",
    531: "ragged_shower_rain",
    
    # Snow
    600: "light_snow",
    601: "snow",
    602: "heavy_snow",
    611: "sleet",
    612: "light_shower_sleet",
    613: "shower_sleet",
    615: "light_rain_and_snow",
    616: "rain_and_snow",
    620: "light_shower_snow",
    621: "shower_snow",
    622: "heavy_shower_snow",
    
    # Atmosphere
    701: "mist",
    711: "smoke",
    721: "haze",
    731: "sand_dust",
    741: "fog",
    751: "sand",
    761: "dust",
    762: "volcanic_ash",
    771: "squalls",
    781: "tornado",
    
    # Clear
    800: "clear_sky",
    
    # Clouds
    801: "few_clouds",
    802: "scattered_clouds",
    803: "broken_clouds",
    804: "overcast_clouds"
}

# Entity naming
WEATHER_CHANNEL_NAME_TEMPLATE = "Weather Channel {}"

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

# Schema für Entity Konversion
CONVERSION_SCHEMA = vol.Schema({
    vol.Required(CONF_ZONE_NAME): str,
    vol.Required(CONF_ACTUATOR_NAME): str,
    vol.Required(CONF_TARGET_TYPE): vol.In(VALID_TARGET_TYPES),
})

# Config flow constants
CONF_ENABLE_RADIO_BUS = "enable_radio_bus"
CONF_RADIO_POLLING_INTERVAL = "polling_interval"

# Schema für das Mapping
MAPPING_SCHEMA = vol.Schema({
    vol.Required(CONF_MARKER_ID): int,
    vol.Required(CONF_ENTITY_ID): str,
    vol.Optional(CONF_INVERT, default=False): bool,
})

CONF_ENABLE_MARKER_UPDATES = "enable_marker_updates"

MIN_POLLING_CALLS = 3
POLLING_TIME_WINDOW = 60  # in seconds

class Priority(Enum):
    EVENT = 1
    POLLING = 2