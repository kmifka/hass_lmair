"""The Light Manager Air integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, MAPPING_SCHEMA, CONF_MAPPINGS, CONF_ENTITY_CONVERSIONS, CONVERSION_SCHEMA, CONF_IGNORED_ZONES
from .coordinator import LightManagerAirCoordinator

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

PLATFORMS = [Platform.LIGHT, Platform.SCENE, Platform.COVER, Platform.SWITCH, Platform.WEATHER]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
            vol.Optional(CONF_MAPPINGS): vol.All(
                cv.ensure_list, [MAPPING_SCHEMA]
            ),
            vol.Optional(CONF_ENTITY_CONVERSIONS): vol.All(
                cv.ensure_list, [CONVERSION_SCHEMA]
            ),
            vol.Optional(CONF_IGNORED_ZONES, default=[]): vol.All(cv.ensure_list, [cv.string]),
        })
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Light Manager Air component."""
    if DOMAIN not in config:
        return True

    hass.data.setdefault(DOMAIN, {})

    if CONF_MAPPINGS in config[DOMAIN]:
        hass.data[DOMAIN][CONF_MAPPINGS] = config[DOMAIN][CONF_MAPPINGS]
    if CONF_ENTITY_CONVERSIONS in config[DOMAIN]:
        hass.data[DOMAIN][CONF_ENTITY_CONVERSIONS] = config[DOMAIN][CONF_ENTITY_CONVERSIONS]
    if CONF_IGNORED_ZONES in config[DOMAIN]:
        hass.data[DOMAIN][CONF_IGNORED_ZONES] = config[DOMAIN][CONF_IGNORED_ZONES]

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Light Manager Air from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    lm_coordinator = LightManagerAirCoordinator(hass, entry)
    await lm_coordinator.async_setup()
    await lm_coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = lm_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok 