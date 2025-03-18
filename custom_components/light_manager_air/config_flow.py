"""Config flow for Light Manager Air."""
from __future__ import annotations

import logging
import traceback
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
from packaging import version

from .const import (
    DOMAIN,
    DEFAULT_RADIO_POLLING_INTERVAL,
    CONF_ENABLE_RADIO_BUS,
    CONF_RADIO_POLLING_INTERVAL,
    CONF_ENABLE_MARKER_UPDATES,
    CONF_MARKER_UPDATE_INTERVAL,
    DEFAULT_MARKER_UPDATE_INTERVAL,
    CONF_ENABLE_WEATHER_UPDATES,
    CONF_WEATHER_UPDATE_INTERVAL,
    DEFAULT_WEATHER_UPDATE_INTERVAL,
    MINIMUM_FIRMWARE_VERSION,
)
from .lmair import LMAir

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class LightManagerAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Light Manager Air."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle a flow initiated by the user."""
        flow_error = None
        options = []

        # Safely discover devices
        try:
            _LOGGER.debug("Attempting to discover Light Manager Air devices...")
            discovered_devices = await self.hass.async_add_executor_job(LMAir.discover)
            
            if discovered_devices:
                _LOGGER.debug(f"Discovered {len(discovered_devices)} devices")
                for device in discovered_devices:
                    try:
                        options.append(device.host)
                        _LOGGER.debug(f"Added device with host: {device.host}")
                    except Exception as host_err:
                        _LOGGER.warning(f"Could not add discovered device to options: {host_err}")
            else:
                _LOGGER.debug("No devices discovered automatically")
                
        except Exception as disc_err:
            _LOGGER.error(f"Error during device discovery: {disc_err}")
            _LOGGER.debug(f"Discovery error details: {traceback.format_exc()}")
            # Continue with an empty options list

        if user_input:
            _LOGGER.debug(f"Processing user input: {user_input}")
            try:
                host = user_input.get(CONF_HOST, "").strip()
                username = user_input.get(CONF_USERNAME, "")
                password = user_input.get(CONF_PASSWORD, "")
                
                if not host:
                    _LOGGER.warning("No host provided")
                    flow_error = {"base": "invalid_host"}
                else:
                    # Test connection
                    _LOGGER.debug(f"Testing connection to {host}")
                    try:
                        lm = await self.hass.async_add_executor_job(
                            LMAir, host, username, password
                        )
                        
                        # Verify we have required attributes
                        if not hasattr(lm, 'fw_version') or not lm.fw_version:
                            _LOGGER.warning("Connected to device but could not get firmware version")
                            flow_error = {"base": "firmware_unavailable"}
                        elif not hasattr(lm, 'mac_address') or not lm.mac_address:
                            _LOGGER.warning("Connected to device but could not get MAC address")
                            flow_error = {"base": "mac_unavailable"}
                        # Check firmware version
                        elif version.parse(lm.fw_version) < version.parse(MINIMUM_FIRMWARE_VERSION):
                            _LOGGER.warning(f"Firmware too old: {lm.fw_version} < {MINIMUM_FIRMWARE_VERSION}")
                            flow_error = {"base": "firmware_too_old"}
                        else:
                            _LOGGER.debug(f"Setting unique ID: {lm.mac_address}")
                            try:
                                await self.async_set_unique_id(lm.mac_address)
                                self._abort_if_unique_id_configured()
                                
                                _LOGGER.debug("Creating configuration entry")
                                return self.async_create_entry(
                                    title=lm.mac_address,
                                    data={
                                        CONF_HOST: lm.host, 
                                        CONF_USERNAME: lm.username, 
                                        CONF_PASSWORD: lm.password
                                    },
                                    options={CONF_ENABLE_RADIO_BUS: True}
                                )
                            except Exception as entry_err:
                                _LOGGER.error(f"Error creating entry: {entry_err}")
                                _LOGGER.debug(f"Entry creation error details: {traceback.format_exc()}")
                                flow_error = {"base": "entry_error"}
                    except ConnectionError as conn_err:
                        _LOGGER.error(f"Connection error: {conn_err}")
                        flow_error = {"base": "cannot_connect"}
                    except Exception as setup_err:
                        _LOGGER.error(f"Setup error: {setup_err}")
                        _LOGGER.debug(f"Setup error details: {traceback.format_exc()}")
                        flow_error = {"base": "unknown"}
            except Exception as process_err:
                _LOGGER.error(f"Error processing user input: {process_err}")
                _LOGGER.debug(f"Processing error details: {traceback.format_exc()}")
                flow_error = {"base": "unknown"}

        _LOGGER.debug(f"Showing form with options: {options}, errors: {flow_error}")
        
        # Prepare error messages dictionary
        errors = {
            "cannot_connect": "Failed to connect to the Light Manager Air device",
            "firmware_too_old": f"Firmware version too old, please update to at least {MINIMUM_FIRMWARE_VERSION}",
            "firmware_unavailable": "Could not determine firmware version",
            "mac_unavailable": "Could not determine MAC address",
            "invalid_host": "Please provide a valid hostname or IP address",
            "entry_error": "Error creating configuration entry",
            "unknown": "An unexpected error occurred",
        }

        # Flow errors need to be a dict[str, str] for async_show_form
        errors_dict: dict[str, str] | None = None
        
        if flow_error and "base" in flow_error:
            error_key = flow_error["base"]
            # Log the error message for the user
            error_msg = errors.get(error_key, "Unknown error")
            _LOGGER.error(f"Configuration error: {error_msg}")
            # Create a proper dict[str, str] for errors param
            errors_dict = {"base": error_key}
        
        try:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): SelectSelector(
                        SelectSelectorConfig(options=options, custom_value=True)
                    ) if options else str,
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str
                }),
                errors=errors_dict
            )
        except Exception as form_err:
            _LOGGER.error(f"Error showing form: {form_err}")
            _LOGGER.debug(f"Form error details: {traceback.format_exc()}")
            # If we can't show the form, we need to abort
            return self.async_abort(reason="form_error")

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LightManagerAirOptionsFlow:
        """Get the options flow."""
        return LightManagerAirOptionsFlow(config_entry)


class LightManagerAirOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage the options."""
        try:
            if user_input is not None:
                _LOGGER.debug(f"Saving options: {user_input}")
                return self.async_create_entry(title="", data=user_input)

            # Get current options with defaults
            current_radio_bus = self.config_entry.options.get(CONF_ENABLE_RADIO_BUS, True)
            current_radio_interval = self.config_entry.options.get(
                CONF_RADIO_POLLING_INTERVAL, DEFAULT_RADIO_POLLING_INTERVAL
            )
            current_marker_updates = self.config_entry.options.get(CONF_ENABLE_MARKER_UPDATES, True)
            current_marker_interval = self.config_entry.options.get(
                CONF_MARKER_UPDATE_INTERVAL, DEFAULT_MARKER_UPDATE_INTERVAL
            )
            current_weather_updates = self.config_entry.options.get(CONF_ENABLE_WEATHER_UPDATES, True)
            current_weather_interval = self.config_entry.options.get(
                CONF_WEATHER_UPDATE_INTERVAL, DEFAULT_WEATHER_UPDATE_INTERVAL
            )
            
            _LOGGER.debug("Showing options form")
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_ENABLE_RADIO_BUS,
                            default=current_radio_bus,
                        ): bool,
                        vol.Required(
                            CONF_RADIO_POLLING_INTERVAL,
                            default=current_radio_interval,
                        ): vol.Coerce(int),
                        vol.Required(
                            CONF_ENABLE_MARKER_UPDATES,
                            default=current_marker_updates,
                        ): bool,
                        vol.Required(
                            CONF_MARKER_UPDATE_INTERVAL,
                            default=current_marker_interval,
                        ): vol.Coerce(int),
                        vol.Required(
                            CONF_ENABLE_WEATHER_UPDATES,
                            default=current_weather_updates,
                        ): bool,
                        vol.Required(
                            CONF_WEATHER_UPDATE_INTERVAL,
                            default=current_weather_interval,
                        ): vol.Coerce(int)
                    }
                ),
                # Pass a properly typed None for the errors parameter
            errors=None,
            )
        except Exception as e:
            _LOGGER.error(f"Error in options flow: {e}")
            _LOGGER.debug(f"Options flow error details: {traceback.format_exc()}")
            return self.async_abort(reason="options_error")