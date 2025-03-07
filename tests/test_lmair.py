import unittest
from threading import Event
from time import sleep

from custom_components.light_manager_air.lmair import LMAir


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

    def test_all_off(self):
        light_manager = self._device()
        light_manager.send_command(f"typ,it,did,1833F4A0,aid,215,acmd,0,seq,6")

    def test_fixture_loading(self):
        zones, scenes = self._device().load_fixtures()
        print(f"Found {len(zones)} zones and {len(scenes)} scenes.")
        self.assertTrue(zones, "Could not find any zones!")
        self.assertTrue(scenes, "Could not find any scenes!")
        z = zones[0]
        a = z.actuators[8]
        c = a.commands[0]
        c.call()


    def test_radio_bus_receiving(self):
        stop_event = Event()

        def callback(data):
            print("Received radio bus data: " + data)
            stop_event.set()
            #self._device().stop_radio_bus_listening()

        self._device().start_radio_bus_listening(callback)

        print("Please send now any radio bus signal.")

        for _ in range(30):
            if stop_event.is_set():
                return
            sleep(1000)

        raise self.failureException("Did not receive radio bus signal!")


if __name__ == '__main__':
    unittest.main()
