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
    CONF_ENABLE_RADIO_BUS,
    CONF_RADIO_POLLING_INTERVAL,
    CONF_ENABLE_MARKER_UPDATES,
    CONF_ENABLE_WEATHER_UPDATES,
    CONF_WEATHER_UPDATE_INTERVAL,
    DEFAULT_WEATHER_UPDATE_INTERVAL,
)
from .lmair import LMAir

_LOGGER = logging.getLogger(__name__)


RADIO_BUS_SIGNAL_EVENT = f"{DOMAIN}_radio_bus_signal"
DATA_UPDATE_EVENT = f"{DOMAIN}_data_update"


class UpdateHandler:
    """Handles periodic updates for a specific feature."""

    def __init__(self, hass, coordinator, update_type, default_interval):
        """Initialize the update handler."""
        self._hass = hass
        self._coordinator = coordinator
        self._update_type = update_type
        self._default_interval = default_interval
        self._unsubscribe = None

    async def _handle_update(self, _now=None):
        """Handle the update."""
        if self._coordinator.light_manager:
            try:
                _LOGGER.debug("UPDATE " + self._update_type)
                # Dynamically call the corresponding method
                update_method = getattr(self._coordinator.light_manager, f"load_{self._update_type}")
                result = await self._hass.async_add_executor_job(update_method)
                
                # Special handling for Radio Bus signals
                if self._update_type == "radio_signals":
                    for signal in result:
                        self._hass.bus.async_fire(RADIO_BUS_SIGNAL_EVENT, {
                            "device_id": self._coordinator.device_id,
                            "signal_type": signal.get("signal_type"),
                            "signal_code": signal.get("signal_code")
                        })
                else:
                    setattr(self._coordinator, self._update_type, result)
                    self._hass.bus.async_fire(DATA_UPDATE_EVENT, {
                        "device_id": self._coordinator.device_id
                    })

            except ConnectionError:
                _LOGGER.debug("ERROR " + self._update_type)
                pass

    def start(self, update_interval=None):
        """Start periodic updates."""
        if self._unsubscribe:
            return

        _LOGGER.debug("START " + self._update_type)

        update_interval = update_interval or self._default_interval

        self._unsubscribe = async_track_time_interval(
            self._hass,
            self._handle_update,
            timedelta(milliseconds=update_interval)
        )

        self._hass.async_create_task(self._handle_update())

    def stop(self):
        """Stop periodic updates."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None


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
        self.zones = []
        self.scenes = []
        self.markers = []
        self.weather_channels = []
        self._device_info = None

        self._update_handlers = {
            "radio": UpdateHandler(hass, self, "radio_signals", DEFAULT_RADIO_POLLING_INTERVAL),
            "markers": UpdateHandler(hass, self, "markers", DEFAULT_MARKER_UPDATE_INTERVAL),
            "weather": UpdateHandler(hass, self, "weather_channels", DEFAULT_WEATHER_UPDATE_INTERVAL)
        }

        self._start_enabled_update_handler()

    def _start_enabled_update_handler(self):
        """Start all enabled features."""
        if self.entry.options.get(CONF_ENABLE_RADIO_BUS, True):
            self._update_handlers["radio"].start(
                self.entry.options.get(CONF_RADIO_POLLING_INTERVAL)
            )

        if self.entry.options.get(CONF_ENABLE_MARKER_UPDATES, True):
            self._update_handlers["markers"].start(
                self.entry.options.get(CONF_MARKER_UPDATE_INTERVAL)
            )

        if self.entry.options.get(CONF_ENABLE_WEATHER_UPDATES, True):
            self._update_handlers["weather"].start(
                self.entry.options.get(CONF_WEATHER_UPDATE_INTERVAL)
            )

    async def _handle_options_update(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        for handler in self._update_handlers.values():
            handler.stop()

        self._start_enabled_update_handler()

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

        self.zones, self.scenes = await self.hass.async_add_executor_job(
            self.light_manager.load_fixtures
        )

        device_registry = dr.async_get(self.hass)
        self._device_info = {
            "identifiers": {(DOMAIN, self.light_manager.mac_address)},
            "name": f"Light Manager Air",
            "manufacturer": "jbmedia",
            "model": "Light Manager Air",
            "sw_version": self.light_manager.fw_version,
        }
        device = device_registry.async_get_or_create(config_entry_id=self.entry.entry_id, **self.device_info)

        self.device_id = device.id

        # Listen for options updates
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._handle_options_update)
        )

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    async def _async_update_data(self):
        """Fetch data from Light Manager Air."""
        try:
            # Update marker states
            self.markers = await self.hass.async_add_executor_job(
                self.light_manager.load_markers
            )
            # Update weather data
            self.weather_channels = await self.hass.async_add_executor_job(
                self.light_manager.load_weather_channels
            )

            self.hass.bus.async_fire(DATA_UPDATE_EVENT, {
                "device_id": self.device_id
            })
            
        except ConnectionError as e:
            raise UpdateFailed(e)
