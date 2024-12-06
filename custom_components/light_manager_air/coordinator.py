"""DataUpdateCoordinator for Light Manager Air."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_RADIO_POLLING_INTERVAL,
    CONF_MARKER_UPDATE_INTERVAL,
    DEFAULT_MARKER_UPDATE_INTERVAL,
    DEFAULT_RATE_LIMIT,
    DEFAULT_RATE_WINDOW,
    CONF_RATE_LIMIT,
    CONF_RATE_WINDOW,
    CONF_ENABLE_RADIO_BUS,
    CONF_RADIO_POLLING_INTERVAL,
    CONF_ENABLE_MARKER_UPDATES,
    Priority,
    MIN_POLLING_CALLS,
    POLLING_TIME_WINDOW,
)
from .lmair import LMAir

_LOGGER = logging.getLogger(__name__)


RADIO_BUS_SIGNAL_EVENT = f"{DOMAIN}_radio_bus_signal"
DATA_UPDATE_EVENT = f"{DOMAIN}_data_update"


class LightManagerAirCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Light Manager Air data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.device_id = None
        self.light_manager = None
        self.zones = None
        self.scenes = None
        self.markers = None
        self._radio_bus_unsubscribe = None
        self._marker_update_unsubscribe = None
        self._device_info = None

        # Start radio bus listening if enabled in options
        if self.entry.options.get(CONF_ENABLE_RADIO_BUS, True):
            self.start_radio_bus_listening(self.entry.options.get(CONF_RADIO_POLLING_INTERVAL, DEFAULT_RADIO_POLLING_INTERVAL))

        # Start marker updates if enabled in options
        if self.entry.options.get(CONF_ENABLE_MARKER_UPDATES, True):
            self.start_marker_updates(self.entry.options.get(CONF_MARKER_UPDATE_INTERVAL, DEFAULT_MARKER_UPDATE_INTERVAL))

    async def async_setup(self):
        """Set up the coordinator."""
        url = self.entry.data[CONF_HOST]
        username = self.entry.data[CONF_USERNAME]
        password = self.entry.data[CONF_PASSWORD]

        try:
            self.light_manager = await self.hass.async_add_executor_job(
                LMAir, url, username, password
            )
        except ConnectionError as e:
            raise ConfigEntryNotReady(e)

        device_registry = dr.async_get(self.hass)
        self._device_info = {
            "identifiers": {(DOMAIN, self.light_manager.mac_address)},
            "name": f"Light Manager Air",
            "manufacturer": "jb media",
            "model": "Light Manager Air",
            "sw_version": self.light_manager.fw_version,
        }
        device = device_registry.async_get_or_create(config_entry_id=self.entry.entry_id, **self.device_info)

        self.device_id = device.id

        # Listen for options updates
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._handle_options_update)
        )

    async def _handle_options_update(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        self.stop_radio_bus_listening()
        self.stop_marker_updates()

        if entry.options.get(CONF_ENABLE_RADIO_BUS, True):
            self.start_radio_bus_listening(entry.options.get(CONF_RADIO_POLLING_INTERVAL, DEFAULT_RADIO_POLLING_INTERVAL))

        if entry.options.get(CONF_ENABLE_MARKER_UPDATES, True):
            self.start_marker_updates(entry.options.get(CONF_MARKER_UPDATE_INTERVAL, DEFAULT_MARKER_UPDATE_INTERVAL))

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    async def _async_update_data(self):
        """Fetch data from Light Manager Air."""
        try:
            self.zones, self.scenes = await self.hass.async_add_executor_job(
                self.light_manager.load_fixtures
            )
            # Update marker states
            self.markers = await self.hass.async_add_executor_job(
                self.light_manager.load_markers
            )
            # Update weather data
            weather_channels = await self.hass.async_add_executor_job(
                self.light_manager.load_weather_channels
            )
            
            data = {
                "zones": self.zones,
                "scenes": self.scenes,
                "markers": self.markers,
                "weather_channels": weather_channels,
            }

            self.hass.bus.async_fire(DATA_UPDATE_EVENT, {
                "device_id": self.device_id
            })
            
            return data
            
        except ConnectionError as e:
            raise UpdateFailed(e)

    def start_radio_bus_listening(self, polling_interval=None):
        """Start listening for radio bus signals."""
        if self._radio_bus_unsubscribe:
            return

        polling_interval = polling_interval or DEFAULT_RADIO_POLLING_INTERVAL

        async def _handle_radio_codes(_now=None):
            """Fetch and process radio signals."""
            if self.light_manager:
                try:
                    signals = await self.hass.async_add_executor_job(
                        self.light_manager.receive_radio_signals, polling_interval
                    )
                except ConnectionError:
                    return

                for signal in signals:
                    self.hass.bus.async_fire(RADIO_BUS_SIGNAL_EVENT, {
                        "device_id": self.device_id,
                        "signal_type": signal.get("signal_type"),
                        "signal_code": signal.get("signal_code")
                    })

        self._radio_bus_unsubscribe = async_track_time_interval(
            self.hass,
            _handle_radio_codes,
            timedelta(milliseconds=polling_interval)
        )

        self.hass.async_create_task(_handle_radio_codes())

    def stop_radio_bus_listening(self):
        """Stop listening for radio bus signals."""
        if self._radio_bus_unsubscribe:
            self._radio_bus_unsubscribe()
            self._radio_bus_unsubscribe = None

    def start_marker_updates(self, update_interval=None):
        """Start marker update polling."""
        if self._marker_update_unsubscribe:
            return

        update_interval = update_interval or DEFAULT_MARKER_UPDATE_INTERVAL

        async def _handle_marker_update(_now=None):
            """Update marker states."""
            if self.light_manager:
                try:
                    self.markers = await self.hass.async_add_executor_job(
                        self.light_manager.load_markers
                    )
                    self.hass.bus.async_fire(DATA_UPDATE_EVENT, {
                        "device_id": self.device_id
                    })
                except ConnectionError:
                    pass

        self._marker_update_unsubscribe = async_track_time_interval(
            self.hass,
            _handle_marker_update,
            timedelta(milliseconds=update_interval)
        )

        self.hass.async_create_task(_handle_marker_update())

    def stop_marker_updates(self):
        """Stop marker update polling."""
        if self._marker_update_unsubscribe:
            self._marker_update_unsubscribe()
            self._marker_update_unsubscribe = None
