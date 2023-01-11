# Light Manager Air SDK (Python)

This is an SDK for communication with the light manager air from the vendor jb media (https://www.jbmedia.eu/light-manager/).

The loading of zones, actuators and scenes is supported as well as the execution of the respective commands.

It is also possible to listen for radio bus signals.

For getting the connection to the devices service discovery is also available.

## Installation

    pip install light-manager-air

## Examples

### Connect to Light Manager Air by url

    light_manager = LMAir("http://lmair")

### Or connect to Light Manager Air by service discovery (recommended)

    light_managers = LMAir.discover()
    assert len(light_managers) > 0
    light_manager = light_managers[0]

### Call a specific command

    zones, scenes = light_manager.load_fixtures()
    zones[0].actuators[0].commands[0].call()

### Turn a light on when a radio bus signal is received

    def callback(data):
        if data == "12282E9A":
            zones[0].actuators[0].commands[0].call()
            light_manager.stop_radio_bus_listening()

    light_manager.start_radio_bus_listening(callback)

    
