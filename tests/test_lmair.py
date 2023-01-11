import unittest
from threading import Event
from time import sleep

from lmair import LMAir


class MyTestCase(unittest.TestCase):
    device = None

    def _device(self):
        if self.device:
            return self.device

        devices = LMAir.discover()
        self.assertGreater(len(devices), 0, "Could not find any devices!")
        self.device = devices[0]
        return self.device

    def test_service_discovery(self):
        self._device()

    def test_fixture_loading(self):
        zones, scenes = self._device().load_fixtures()
        print(f"Found {len(zones)} zones and {len(scenes)} scenes.")
        self.assertTrue(zones, "Could not find any zones!")
        self.assertTrue(scenes, "Could not find any scenes!")

    def test_radio_bus_receiving(self):
        stop_event = Event()

        def callback(data):
            print("Received radio bus data: " + data)
            stop_event.set()
            self._device().stop_radio_bus_listening()

        self._device().start_radio_bus_listening(callback)

        print("Please send now any radio bus signal.")

        for _ in range(30):
            if stop_event.is_set():
                return
            sleep(1)

        raise self.failureException("Did not receive radio bus signal!")


if __name__ == '__main__':
    unittest.main()
