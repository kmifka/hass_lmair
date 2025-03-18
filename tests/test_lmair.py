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
        c = a.commands[2]
        c.call()

    def test_marker_10_toggle(self):
        """Test toggling marker 10 (on and off)."""
        light_manager = self._device()
        
        # Get all markers
        markers = light_manager.load_markers()
        
        # Check if marker 10 exists (index 9 since markers are 1-based in UI, 0-based in code)
        self.assertGreaterEqual(len(markers), 10, "Not enough markers available, need at least 10!")
        
        marker_10 = markers[9]  # 0-based index
        initial_state = marker_10.state
        print(f"Marker 10 initial state: {initial_state}")
        
        # Turn marker 10 ON
        print("Turning marker 10 ON...")
        marker_10.commands[0].call()  # "on" command is at index 0
        sleep(1)  # Wait for command to process
        
        # Reload markers to get updated state
        markers = light_manager.load_markers()
        marker_10 = markers[9]
        on_state = marker_10.state
        print(f"Marker 10 state after turning ON: {on_state}")
        
        # Turn marker 10 OFF
        print("Turning marker 10 OFF...")
        marker_10.commands[2].call()  # "off" command is at index 2
        sleep(1)  # Wait for command to process
        
        # Reload markers to get updated state
        markers = light_manager.load_markers()
        marker_10 = markers[9]
        off_state = marker_10.state
        print(f"Marker 10 state after turning OFF: {off_state}")
        
        # Verify the states changed as expected
        self.assertTrue(on_state, "Marker 10 should be ON after sending the ON command")
        self.assertFalse(off_state, "Marker 10 should be OFF after sending the OFF command")

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
