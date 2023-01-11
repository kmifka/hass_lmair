# Light Manager Air SDK (Python)

This is an SDK for communication with the light manager air from the vendor jb media (https://www.jbmedia.eu/light-manager/).

The loading of zones, actuators and scenes is supported as well as the execution of the respective commands.

It is also possible to listen for radio bus signals.

## Examples

Connect to Light Manager Air

    lmair = LMAir("http://lmair")


Call a specific command

    zones, scenes = lmair.load_fixtures()
    zones[0].actuators[0].commands[0].call()

Turn a light on when a radio bus signal is received

    def callback(data):
        if data == "12282E9A":
            zones[0].actuators[0].commands[0].call()
            lmair.stop_radio_bus_listening()

    lmair.start_radio_bus_listening(callback)

    
