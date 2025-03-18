from __future__ import annotations

import json
import logging
import re
import socket
import xml.etree.ElementTree as ET
from time import time
from typing import List, Optional
from urllib.parse import urlparse, parse_qsl

import requests
from requests import Response

_LOGGER = logging.getLogger(__name__)


class _LMConnector:
    """Handles the connection to the Light Manager, including discovery and code polling."""
    DEFAULT_TIMEOUT = 1000
    COMMAND_KEY = "cmd"
    RECEIVE_IDENTIFIERS = ["rfhm,", "rfit,"]  # List of valid identifiers
    DISCOVER_MESSAGE = "D"
    POLL_ENDPOINT = "/poll.htm"

    def __init__(self, url: str, username: str, password: str, adapter_ip: str = None):
        """
        :param url: URL for connecting to Light Manager, e.g., http://lmair
        :param username: LAN username
        :param password: LAN password
        :param adapter_ip: IP of the desired network adapter
        """
        self._lm_url = url
        self._adapter_ip: str = adapter_ip or self._get_default_adapter_ip()
        self._username: str = username
        self._password: str = password

    def receive_radio_signals(self, timeout: int = None) -> list[dict[str, str]]:
        """Call the /poll.htm endpoint and returns any radio codes found.

        :return: List of received radio codes
        """
        signals = []

        response = self.send(self.POLL_ENDPOINT, check_response=False, timeout=timeout)

        if response.status_code == 200:
            data = response.text.strip()
            if data:
                for line in data.split('\r'):
                    line = line.strip()
                    if not line:
                        continue

                    for identifier in self.RECEIVE_IDENTIFIERS:
                        if line.startswith(identifier):
                            signal = line.split(",")
                            signals.append({"signal_type": signal[0], "signal_code": signal[1]})
                            break

        return signals

    @staticmethod
    def discover(wait_duration: int = None, discover_adapter_ip: str = None, discover_port: int = None) -> dict:
        """
        Discovers all devices in the local network.

        :param wait_duration: Optional. Duration in seconds of waiting for response.
        :param discover_adapter_ip: Optional. IP of the desired network adapter.
        :param discover_port: Optional. Broadcast port.
        :return: Returns a dict with IP addresses as keys and device info as value.
        """

        wait_duration = wait_duration or 3
        discover_port = discover_port or 30303

        adapter_ip = discover_adapter_ip or _LMConnector._get_default_adapter_ip()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((adapter_ip, discover_port))
            sock.sendto(_LMConnector.DISCOVER_MESSAGE.encode(), ("255.255.255.255", discover_port))
            sock.settimeout(1)

            devices = {}
            start_time = time()

            while (time() - start_time) < wait_duration:
                try:
                    data, info = sock.recvfrom(1024)
                    if data:
                        [host, _] = info
                        devices[host] = data.decode()
                except socket.timeout:
                    continue
                except OSError:
                    continue

            return devices
        except Exception as e:
            raise ConnectionError("Unable to auto discover light manager air") from e
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def send(self, path: str, cmd: [str, str] = None, retry: bool = False, check_response: bool = True,
             timeout: int = None) -> Response:
        """Sends a command to the Light Manager.

        :param retry: if true it tries to retry the command once
        :param timeout: timeout in ms
        :param check_response: If true, the response is checked.
        :param path: Destination path.
        :param cmd: Command list of tuple.
        :return: Returns the response.
        """

        auth = None
        if self._username or self._password:
            auth = (self._username, self._password)

        timeout = 3 or (timeout or _LMConnector.DEFAULT_TIMEOUT) / 1000

        try:
            if not cmd:
                response = requests.get(self._lm_url + path, auth=auth, timeout=timeout)
            else:
                response = requests.post(self._lm_url + path, data=cmd, auth=auth, timeout=timeout)
        except Exception as e:
            if retry:
                return self.send(path, cmd, False, check_response, timeout)
            raise ConnectionError("No answer from light manager air") from e

        if response.status_code == 401:
            raise ConnectionError("Wrong username or password!")

        if check_response and response.reason != "OK":
            raise ConnectionError(f"Request was not successful! ({response.content.decode()})")

        return response

    @staticmethod
    def _get_default_adapter_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Use Google's public DNS server to determine the default interface IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    def load_config(self) -> ET.Element:
        """Loads the config XML from the Light Manager."""
        config_response = self.send("/config.xml")
        try:
            return ET.fromstring(config_response.content.decode())
        except Exception as e:
            raise ConnectionError("Unable to load config") from e

    def load_params(self) -> dict[str, str]:
        """Loads the params from the Light Manager."""
        param_json = self.send("/params.json")
        try:
            return json.loads(param_json.content.decode())
        except Exception as e:
            raise ConnectionError("Unable to load params") from e

    def load_weather(self) -> dict:
        """Loads the weather data from the Light Manager.

        :return: Weather data from weather.json
        """
        weather_response = self.send("/weather.json")
        try:
            return json.loads(weather_response.content.decode())
        except Exception as e:
            raise ConnectionError("Unable to load weather") from e

    def load_marker_states(self) -> str:
        """Updates the marker states from params.json."""
        params = self.load_params()
        return params.get("marker state", "")

    @property
    def marker_states(self) -> str:
        """
        :return: Current marker states string
        """
        return self._marker_states


class _LMFixture:
    """Base class for all Light Manager fixtures."""

    def __init__(self, name: str):
        """
        :param name: Name of the fixture.
        """
        self._name = name

    @property
    def name(self):
        """
        :return: Name of the fixture.
        """
        return self._name

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self._name})"


class _LMCommandContainer(_LMFixture):
    """Base class for objects that contain commands."""

    def __init__(self, name: str, connector: _LMConnector):
        """Initialize the command container.
        
        :param name: Name of the container
        :param connector: Light Manager connector
        """
        super().__init__(name)
        self._connector = connector
        self._commands: List[LMCommand] = []

    @property
    def commands(self) -> List[LMCommand]:
        """
        :return: List of all commands.
        """
        return self._commands


class LMCommand(_LMFixture):
    """Describes a callable command."""

    def __init__(self, connector: _LMConnector,
                 name: Optional[str] = None,
                 cmd: Optional[str] = None,
                 config: Optional[ET.Element] = None):
        """
        :param connector: Light Manager connector.
        :param name: Name of the command.
        :param cmd: Command of the command as tuple or string (e.g., [("cmd", "typ,it,did,0996,aid,215,acmd,0,seq,6")]).
        :param config: Command part of the config.xml (Optional. Only if name and param are None).
        """
        super().__init__(name or config.findtext("./name"))
        self._connector = connector
        if cmd is not None:
            self._cmd = (_LMConnector.COMMAND_KEY, cmd)
        else:
            self._cmd = config.findtext("./param")
            # replace old command with new scene command
            self._cmd = self._cmd.replace("scene=0&scene=", "cmd=idx,")
            self._cmd = parse_qsl(self._cmd)

    @property
    def name(self) -> str:
        """
        :return: Name of the command.
        """
        return self._name

    @property
    def cmd(self) -> [str, str]:
        """
        :return: Param data of the command.
        """
        return self._cmd

    def call(self) -> None:
        """
        Starts the command on the Light Manager.
        """
        # Convert the cmd parameter to a dict if it's a tuple
        if isinstance(self._cmd, tuple):
            cmd_dict = {self._cmd[0]: self._cmd[1]}
        else:
            cmd_dict = dict(self._cmd)
        
        self._connector.send("/control", cmd=cmd_dict, retry=True)


class LMActuator(_LMCommandContainer):
    """Describes an actuator."""

    def __init__(self, config: ET.Element, connector: _LMConnector):
        """
        :param config: Actuator part of the config.xml.
        :param connector: Light Manager connector.
        """
        super().__init__(config.findtext("./name"), connector)
        self._type = config.findtext("./type")
        self._commands = [LMCommand(connector, config=command) for command in config.findall("./commandlist/command")]

    @property
    def type(self) -> str:
        """
        :return: Type of the actuator.
        """
        return self._type


class LMMarker(_LMCommandContainer):
    """Describes a marker."""

    def __init__(self, marker_id: int, state: bool, connector: _LMConnector):
        """
        :param marker_id: ID of the marker
        :param connector: Light Manager connector
        """
        super().__init__(f"Marker {marker_id + 1}", connector)
        self._marker_id = marker_id
        self._state = state
        self._commands = [
            LMCommand(connector, "on", f"typ,smk,{marker_id},1"),
            LMCommand(connector, "toggle", f"typ,smk,{marker_id},2"),
            LMCommand(connector, "off", f"typ,smk,{marker_id},0"),
        ]

    @property
    def marker_id(self) -> int:
        """
        :return: ID of the marker.
        """
        return self._marker_id

    @property
    def state(self) -> bool:
        """
        :return: Current state of the marker.
        """
        return self._state


class LMWeatherChannel(_LMFixture):
    """Describes a weather channel."""

    def __init__(self, channel_id: int, data: dict):
        """
        :param channel_id: ID of the channel
        :param data: Weather data for this channel
        """
        super().__init__(f"Weather Channel {channel_id}")
        self._channel_id = channel_id
        self._temperature = data.get("temperature")
        self._humidity = data.get("humidity")
        self._wind_speed = data.get("wind")
        self._wind_direction = data.get("direction")
        self._rain = data.get("rain")
        self._weather_id = data.get("weather id")
        self._weather_id = int(self._weather_id) if self._weather_id else None

    @property
    def channel_id(self) -> int:
        """Return the channel ID."""
        return self._channel_id

    @property
    def temperature(self) -> Optional[float]:
        """Return the temperature in °C."""
        return float(self._temperature) if self._temperature else None

    @property
    def humidity(self) -> Optional[int]:
        """Return the humidity in %."""
        return int(self._humidity) if self._humidity else None

    @property
    def wind_speed(self) -> Optional[float]:
        """Return the wind speed in km/h."""
        return float(self._wind_speed) if self._wind_speed else None

    @property
    def wind_direction(self) -> Optional[int]:
        """Return the wind direction in degrees."""
        return int(self._wind_direction) if self._wind_direction else None

    @property
    def rain(self) -> Optional[float]:
        """Return the rain amount in mm."""
        return float(self._rain) if self._rain else None

    @property
    def weather_id(self) -> Optional[int]:
        """Return the weather ID."""
        return self._weather_id


class LMZone(_LMFixture):
    """Describes a group of actuators."""

    def __init__(self, config: ET.Element, connector: _LMConnector):
        """
        :param config: Zone part of the config.xml.
        :param connector: Light Manager connector.
        """
        super().__init__(config.findtext("./zonename"))
        self._actuators = []
        for actuator in config.findall("./actuators/actuator"):
            new_actuator = LMActuator(actuator, connector)
            if len(new_actuator.commands) > 0:
                self._actuators.append(new_actuator)

    @property
    def name(self) -> str:
        """
        :return: Name of the zone.
        """
        return self._name

    @property
    def actuators(self) -> List[LMActuator]:
        """
        :return: List of all included actuators.
        """
        return self._actuators


class LMAir(_LMFixture):
    """Handles communication with the JB Media Light Manager Air."""

    def __init__(self, url: str, username: str = None, password: str = None, adapter_ip: str = None):
        """
        Initiates a new LMAir instance with given data. Only url is mandatory.
        If username, password, or info is not given, it will be loaded from the device.

        :param url: URL for connecting to Light Manager, e.g., http://lmair.
        :param username: Optional. LAN username.
        :param password: Optional. LAN password.
        :param adapter_ip: Optional. IP of the network adapter connected to Light Manager.
        """
        super().__init__("Light Manager Air")

        if not url:
            raise ValueError("URL must be given.")

        if not url.startswith("http"):
            url = "http://" + url

        parsed_url = urlparse(url)

        self._lm_hostname = str(parsed_url.hostname)
        self._lm_url = parsed_url.scheme + "://" + self._lm_hostname
        self._username = username
        self._password = password
        self._connector = _LMConnector(self._lm_url, self._username, self._password, adapter_ip=adapter_ip)
        self._config = None

        # Load initial params
        params = self._connector.load_params()
        self._mac_address = params["mac addr"]
        self._fw_version = params["firmware ver"]
        self._ssid = params["ssid"]

    @property
    def username(self):
        """
        :return: Username of the Light Manager.
        """
        return self._username

    @property
    def password(self):
        """
        :return: Password of the Light Manager.
        """
        return self._password

    @property
    def mac_address(self):
        """
        :return: Host of the Light Manager.
        """
        return self._mac_address

    @property
    def host(self):
        """
        :return: Host of the Light Manager.
        """
        return self._lm_hostname

    @property
    def fw_version(self):
        """
        :return: Firmware version of the Light Manager.
        """
        return self._fw_version

    @property
    def ssid(self):
        """
        :return: Currently connected WLAN SSID.
        """
        return self._ssid

    @staticmethod
    def discover(wait_duration: int = None, discover_adapter_ip: str = None, discover_port: int = None) -> List[LMAir]:
        """
        Discovers all devices in the local network.

        :param wait_duration: Optional. Duration in seconds of waiting for response.
        :param discover_adapter_ip: Optional. IP of the desired network adapter.
        :param discover_port: Optional. Broadcast port.
        :return: List of LMAir instances.
        """

        devices = _LMConnector.discover(
            wait_duration=wait_duration,
            discover_adapter_ip=discover_adapter_ip,
            discover_port=discover_port
        )

        def get_info_value(info: str, key: str) -> Optional[str]:
            pattern = re.compile(rf"{key}[ :](.+?)\r\n")
            result = pattern.search(info)
            if not result:
                return None
            return result.group(1).strip()

        return [LMAir(
            host,
            username=get_info_value(info, "Login"),
            password=get_info_value(info, "Pass"),
            adapter_ip=discover_adapter_ip
        ) for host, info in devices.items()]

    def load_radio_signals(self, timeout: int = None) -> list[dict[str, str]]:
        """Polls the /poll.htm endpoint once and returns any radio codes found.

        :return: List of received radio codes
        """
        return self._connector.receive_radio_signals(timeout)

    def load_fixtures(self) -> (List[LMZone], List[LMCommand]):
        """Loads all fixtures (zones, actuators, and scenes).

        :return: Tuple with list of zones and list of scenes.
        """
        if not self._config:
            self._config = self._connector.load_config()

        zones = [LMZone(zone, self._connector) for zone in self._config.findall("./zone")]
        scenes = [LMCommand(self._connector, config=scene) for scene in self._config.findall("./lightscenes/scene")]
        return zones, scenes

    def load_markers(self) -> List[LMMarker]:
        """Loads all markers.

        :return: List of all markers
        """
        marker_states = self._connector.load_marker_states()

        markers = []
        if marker_states:
            for i, state in enumerate(marker_states):
                if state in ["0", "1"]:  # Ignore invalid states
                    markers.append(LMMarker(
                        marker_id=i,
                        state=state == "1",
                        connector=self._connector
                    ))

        return markers

    def load_weather_channels(self) -> List[LMWeatherChannel]:
        """Loads all weather channels.

        :return: List of weather channels with data
        """
        weather_data = self._connector.load_weather()

        channels = []
        # Get all channel keys from the data
        channel_keys = [key for key in weather_data.keys() if key.startswith("channel")]

        for channel_key in channel_keys:
            channel_data = weather_data[channel_key]
            # Only add channels that have a non-empty temperature value
            if channel_data.get("temperature") and channel_data["temperature"].strip():
                channel_id = int(channel_key.replace("channel", ""))
                channels.append(LMWeatherChannel(channel_id, channel_data))

        return channels

    def send_command(self, command: Optional[str]):
        """Sends a custom command.

        :param command: Command to send (e.g., 'typ,it,did,0996,aid,215,acmd,0,seq,6').
        """
        LMCommand(self._connector, name="custom_command", cmd=command).call()
