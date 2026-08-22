"""A device that is slow to answer at startup must not stay broken forever.

On 22.08.2026 Home Assistant was restarted while the Light Manager was busy.
Reading the fixture list timed out, the error escaped `async_setup`, and the
config entry went to `setup_error` and stayed there. Both covers on this
integration - the balcony awning and the projection screen - were unavailable
until the entry was reloaded by hand, and nothing said so.

The awning matters: it is the one an automation retracts when it gets windy,
and an awning that cannot be retracted is a safety problem rather than an
inconvenience. A timeout during startup is ordinary, so recovering from one has
to be automatic.
"""
import asyncio
import unittest

import requests

from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.light_manager_air.coordinator import LightManagerAirCoordinator


# Every way this call is known to fail. They look interchangeable and are not:
# only the first is the builtin ConnectionError, and the other three are its
# siblings under OSError, so "except ConnectionError" silently misses them.
TRANSPORT_FAILURES = [
    ConnectionError("No answer from light manager air"),
    requests.exceptions.ConnectionError("connection aborted"),
    requests.exceptions.ReadTimeout("read timed out"),
    TimeoutError("timed out"),
]


class _Hass:
    """Runs the executor jobs inline; the coordinator only needs this much."""

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class _Entry:
    data = {"host": "http://192.0.2.1", "username": "", "password": ""}
    options = {}


def _coordinator(construct=None, load_fixtures=None):
    """Build a coordinator without running its constructor.

    `__init__` starts three polling handlers that have nothing to do with the
    behaviour under test, so it is skipped deliberately and only the attributes
    `async_setup` actually reads are set.
    """
    coordinator = object.__new__(LightManagerAirCoordinator)
    coordinator.hass = _Hass()
    coordinator.entry = _Entry()
    coordinator.zones = []
    coordinator.scenes = []

    import custom_components.light_manager_air.coordinator as module

    def _fake_lmair(url, username, password):
        if construct is not None:
            raise construct
        return type(
            "_LM",
            (),
            {
                "load_fixtures": staticmethod(
                    lambda *a, **k: (_ for _ in ()).throw(load_fixtures)
                    if load_fixtures is not None
                    else ([], [])
                )
            },
        )()

    module.LMAir = _fake_lmair
    return coordinator


class CoordinatorSetupTest(unittest.TestCase):
    def test_a_failure_while_connecting_is_retryable(self):
        for error in TRANSPORT_FAILURES:
            with self.subTest(error=type(error).__name__):
                coordinator = _coordinator(construct=error)
                with self.assertRaises(ConfigEntryNotReady):
                    asyncio.run(coordinator.async_setup())

    def test_a_failure_while_loading_fixtures_is_retryable(self):
        """The regression. This step used to sit outside the guard."""
        for error in TRANSPORT_FAILURES:
            with self.subTest(error=type(error).__name__):
                coordinator = _coordinator(load_fixtures=error)
                with self.assertRaises(ConfigEntryNotReady) as caught:
                    asyncio.run(coordinator.async_setup())
                self.assertIsNotNone(
                    caught.exception.__cause__,
                    "the original error must stay attached, or the log says "
                    "only 'not ready' and never why",
                )

    def test_a_programming_error_is_not_disguised_as_a_retry(self):
        """Retrying forever would hide a bug that no amount of waiting fixes."""
        coordinator = _coordinator(load_fixtures=ValueError("bad response shape"))
        with self.assertRaises(ValueError):
            asyncio.run(coordinator.async_setup())


if __name__ == "__main__":
    unittest.main()
