"""Config flow for Light Manager Air."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector, SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .const import (
    DOMAIN,
    DEFAULT_RADIO_POLLING_INTERVAL,
    DEFAULT_RATE_LIMIT,
    DEFAULT_RATE_WINDOW,
    CONF_RATE_LIMIT,
    CONF_RATE_WINDOW,
    CONF_ENABLE_RADIO_BUS,
    CONF_RADIO_POLLING_INTERVAL,
    CONF_ENABLE_MARKER_UPDATES, CONF_MARKER_UPDATE_INTERVAL, DEFAULT_MARKER_UPDATE_INTERVAL,
)
from .lmair import LMAir

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class LightManagerAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Light Manager Air."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:

        flow_error = None
        options = []

        discovered_devices = await self.hass.async_add_executor_job(LMAir.discover)

        if discovered_devices:
            for device in discovered_devices:
                options.append(device.host)

        if user_input:
            try:
                # Test connection
                lm = await self.hass.async_add_executor_job(
                    LMAir, user_input[CONF_HOST], user_input.get(CONF_USERNAME), user_input.get(CONF_PASSWORD)
                )

                await self.async_set_unique_id(lm.mac_address)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=lm.mac_address,
                    data={
                        CONF_HOST: lm.host, 
                        CONF_USERNAME: lm.username, 
                        CONF_PASSWORD: lm.password
                    },
                    options={CONF_ENABLE_RADIO_BUS: True}
                )
            except ConnectionError:
                flow_error={"base": "cannot_connect"}


        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): SelectSelector(
                    SelectSelectorConfig(options=options, custom_value=True)
                ) if options else str,
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str
            }),
            errors=flow_error
        )

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
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENABLE_RADIO_BUS,
                        default=self.config_entry.options.get(CONF_ENABLE_RADIO_BUS, True),
                    ): bool,
                    vol.Required(
                        CONF_RADIO_POLLING_INTERVAL,
                        default=self.config_entry.options.get(CONF_RADIO_POLLING_INTERVAL, DEFAULT_RADIO_POLLING_INTERVAL),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_ENABLE_MARKER_UPDATES,
                        default=self.config_entry.options.get(CONF_ENABLE_MARKER_UPDATES, True),
                    ): bool,
                    vol.Required(
                        CONF_MARKER_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(CONF_MARKER_UPDATE_INTERVAL, DEFAULT_MARKER_UPDATE_INTERVAL),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_RATE_LIMIT,
                        default=self.config_entry.options.get(
                            CONF_RATE_LIMIT, DEFAULT_RATE_LIMIT
                        ),
                    ): int,
                    vol.Required(
                        CONF_RATE_WINDOW,
                        default=self.config_entry.options.get(
                            CONF_RATE_WINDOW, DEFAULT_RATE_WINDOW
                        ),
                    ): float
                }
            ),
        )