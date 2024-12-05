"""Constants for the Light Manager Air integration."""
import voluptuous as vol

DOMAIN = "light_manager_air"
CONF_DISCOVERED_DEVICE = "discovered_device"
CONF_MARKER_UPDATE_INTERVAL = "marker_update_interval"
CONF_MAPPINGS = "marker_mappings"
CONF_MARKER_ID = "marker_id"
CONF_ENTITY_ID = "entity_id"
CONF_HIDE_MARKER = "hide_marker"

DEFAULT_NAME = "Light Manager Air"

DEFAULT_RADIO_POLLING_INTERVAL = 2000
DEFAULT_MARKER_UPDATE_INTERVAL = 5000

# Schema für das Mapping
MAPPING_SCHEMA = vol.Schema({
    vol.Required(CONF_MARKER_ID): int,
    vol.Required(CONF_ENTITY_ID): str,
})