"""Minimal Home Assistant stand-ins so the coordinator can be imported.

The integration itself runs inside Home Assistant, but the parts of it that are
worth unit testing - the decision of which errors are retryable - do not need
Home Assistant at all. Installing it just to import three names would make the
test suite slow to set up and easy to skip, and a test nobody runs protects
nothing.

Only the names coordinator.py imports at module level are provided, and each is
the smallest thing that satisfies its use. If an import fails after a refactor,
add the name here rather than reaching for the real package.
"""
import sys
import types


def _module(name: str, **attributes) -> None:
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module


class _ConfigEntryNotReady(Exception):
    """Stand-in for homeassistant.exceptions.ConfigEntryNotReady.

    Home Assistant treats this one exception as "try again later" and retries
    the setup with a growing delay. Everything else leaves the config entry in
    `setup_error` until somebody reloads it by hand, which is why the tests
    care about the exception TYPE and not only about the failure.
    """


class _DataUpdateCoordinator:
    def __init__(self, hass=None, logger=None, name=None, update_interval=None):
        self.hass = hass


class _UpdateFailed(Exception):
    pass


class _Marker:
    """Stand-in for voluptuous markers - only their presence matters here."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self

    def __hash__(self):
        return id(self)


def _stub_voluptuous() -> None:
    """The schemas are declared at import time and never exercised here."""
    _module(
        "voluptuous",
        Schema=_Marker,
        Optional=_Marker,
        Required=_Marker,
        All=_Marker,
        Any=_Marker,
        Coerce=_Marker,
        In=_Marker,
        Range=_Marker,
        ALLOW_EXTRA=object(),
        Invalid=type("Invalid", (Exception,), {}),
    )


if "voluptuous" not in sys.modules:
    try:
        import voluptuous  # noqa: F401
    except ModuleNotFoundError:
        _stub_voluptuous()

if "homeassistant" not in sys.modules:
    _module("homeassistant")
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module(
        "homeassistant.const",
        CONF_HOST="host",
        CONF_USERNAME="username",
        CONF_PASSWORD="password",
        Platform=types.SimpleNamespace(
            **{
                name: name.lower()
                for name in ("LIGHT", "SCENE", "COVER", "SWITCH", "WEATHER",
                             "SENSOR", "EVENT", "BINARY_SENSOR", "BUTTON")
            }
        ),
    )
    _module("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
    _module("homeassistant.exceptions", ConfigEntryNotReady=_ConfigEntryNotReady)
    _module("homeassistant.helpers")
    _module("homeassistant.helpers.device_registry", async_get=lambda hass: None)
    _module(
        "homeassistant.helpers.event",
        async_track_time_interval=lambda *args, **kwargs: (lambda: None),
    )
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=_DataUpdateCoordinator,
        UpdateFailed=_UpdateFailed,
    )
    _module(
        "homeassistant.helpers.config_validation",
        string=str,
        ensure_list=lambda value: value if isinstance(value, list) else [value],
        boolean=bool,
        positive_int=int,
    )
    # const.py imports the weather condition names; their values are irrelevant
    # to anything tested here, so each stands for itself.
    _module("homeassistant.components")
    _module(
        "homeassistant.components.weather",
        **{
            name: name
            for name in (
                "ATTR_CONDITION_CLEAR_NIGHT", "ATTR_CONDITION_CLOUDY",
                "ATTR_CONDITION_FOG", "ATTR_CONDITION_LIGHTNING",
                "ATTR_CONDITION_LIGHTNING_RAINY", "ATTR_CONDITION_PARTLYCLOUDY",
                "ATTR_CONDITION_POURING", "ATTR_CONDITION_RAINY",
                "ATTR_CONDITION_SNOWY", "ATTR_CONDITION_SNOWY_RAINY",
                "ATTR_CONDITION_WINDY", "ATTR_CONDITION_EXCEPTIONAL",
                "ATTR_CONDITION_SUNNY", "ATTR_CONDITION_HAIL",
                "ATTR_CONDITION_WINDY_VARIANT",
            )
        },
    )
