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