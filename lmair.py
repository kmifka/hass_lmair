from __future__ import annotations

import re
import socket
import threading
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from threading import Thread, Event
from time import sleep
from typing import List, Optional, Callable

import requests
from requests import Response


class _LMConnector:
    """Handles the TCP connection to the light manager"""
    CONNECT_CMD = "/control?pcip="
    RECEIVE_IDENTIFIER = "rfit,"
    DISCOVER_MESSAGE = "D"

    def __init__(self, url: str, username: str, password: str, refresh_interval: int = None,
                 adapter_ip: str = None, receive_port: int = None):
        """
        :param url: url for connecting to light manager. E.g. http://lmair
        :param username: lan username
        :param password: lan password
        :param refresh_interval: interval of tcp connection refresh in seconds
        :param adapter_ip: Ip of the desired network adapter
        :param receive_port: port of the tcp connection
        """
        self._lm_url = url
        self._adapter_ip: str = adapter_ip or self._get_default_adapter_ip()
        self._username: str = username
        self._password: str = password
        self._refresh_interval: int = refresh_interval or 20
        self._receive_port: int = receive_port or 30304
        self._stop: Event = Event()
        self._socket: Optional[socket] = None
        self._thread: Optional[Thread] = None
        self._refresh_thread: Optional[Thread] = None

    @staticmethod
    def discover(discover_target_ip=None, wait_duration: int = None, discover_adapter_ip: str = None,
                 discover_port: int = None) -> dict:
        """
        Discovers all devices in local network

        :param discover_target_ip: Optional. Specific target adapter_ip for discovery.
        :param wait_duration: Optional. Duration in seconds of waiting for response
        :param discover_adapter_ip:  Optional. Ip of the desired network adapter
        :param discover_port: Optional. Broadcast port
        :return: Returns a dict with adapter_ip addresses as keys and device info as value
        """

        discover_target_ip = discover_target_ip or "255.255.255.255"
        wait_duration = wait_duration or 3
        discover_port = discover_port or 30303

        def receive():
            while not stop_event.is_set():
                try:
                    data, [host, _] = sock.recvfrom(1024)
                    devices[host] = data.decode()
                except OSError as error:
                    pass

        sock = None

        try:
            adapter_ip = discover_adapter_ip or _LMConnector._get_default_adapter_ip()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((adapter_ip, discover_port))
            sock.sendto(_LMConnector.DISCOVER_MESSAGE.encode(), (discover_target_ip, discover_port))

            stop_event = Event()

            devices = {}

            discover_thread = Thread(target=receive)

            discover_thread.start()
            sleep(wait_duration)
            stop_event.set()
            discover_thread.join(0)

            return devices
        finally:
            if sock:
                sock.close()

    def connect(self, callback: Callable[[str], None]) -> None:
        """Connects to the TCP stream

        :param callback: Callback that is called when data has been received
        """
        if self._thread and self._refresh_thread:
            return

        self._stop.clear()

        def _refresh_connection():
            while not self._stop.is_set():
                self._send_connect(self._adapter_ip)
                sleep(self._refresh_interval)

        def _receive():
            while not self._stop.is_set():
                new_sock = None
                try:
                    new_sock, address = self._socket.accept()
                    data = new_sock.recv(1024).replace(b"\x00", b"").decode()

                    if data.startswith(self.RECEIVE_IDENTIFIER):
                        callback(data.replace(self.RECEIVE_IDENTIFIER, "", 1))
                    else:
                        self._send_connect(self._adapter_ip)
                finally:
                    if new_sock:
                        new_sock.close()

        self._socket: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._adapter_ip, self._receive_port))
        self._socket.listen(5)

        self._thread = Thread(target=_receive)
        self._refresh_thread = Thread(target=_refresh_connection)
        self._thread.start()
        self._refresh_thread.start()

    def disconnect(self) -> None:
        """Connects from the TCP stream"""
        if not self._thread and not self._refresh_thread:
            return

        self._stop.set()
        self._send_connect("")

        if self._thread is not threading.current_thread():
            self._thread.join(0)
        self._refresh_thread.join(0)
        self._socket.close()
        self._socket = None
        self._thread = None
        self._refresh_thread = None

    def send(self, path: str, cmd: str = None, value: str = None, check_response: bool = True) -> Response:
        """Sends a command to the light manager

        :param check_response: If true, the response is checked
        :param path: Destination path
        :param cmd: Command key
        :param value: Command value
        :return: Returns the response
        """

        auth = None
        if self._username or self._password:
            auth = (self._username, self._password)
        if not cmd or not value:
            response = requests.get(self._lm_url + path, auth=auth)
        else:
            response = requests.post(self._lm_url + path, {cmd: value}, auth=auth)

        if response.status_code == 401:
            raise AssertionError("Wrong username or password!")

        if check_response and response.reason != "OK":
            raise AssertionError(f"Request was not successful! ({response.content.decode()})")

        return response

    def _send_connect(self, ip: str) -> None:
        """Sends connect message to the light manager

        :param ip: IP address of host system
        """
        self.send("/control", "pcip", ip)

    @staticmethod
    def _get_default_adapter_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip


class _LMFixture:
    """Base class for all light manager fixtures"""

    def __init__(self, name: str):
        """
        :param name: Name of the fixture
        """
        self._name = name

    @property
    def name(self):
        """
        :return: Name of the fixture
        """
        return self._name

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self._name})"


class LMCommand(_LMFixture):
    """Describing a callable command"""

    def __init__(self, connector: _LMConnector,
                 name: Optional[str] = None,
                 param: Optional[str] = None,
                 config: Optional[ET.Element] = None):
        """
        :param connector: light manager connector
        :param name: name of the command
        :param param: param of the command (e.g. 'cmd=typ,it,did,0996,aid,215,acmd,0,seq,6')
        :param config: command part of the config.xml (Optional. Only if name and param are None)
        """
        super().__init__(name or config.findtext("./name"))
        self._connector = connector
        self._param = param or config.findtext("./param")

    @property
    def name(self) -> str:
        """
        :return: Name of the command
        """
        return self._name

    @property
    def param(self) -> str:
        """
        :return: Param data of the command
        """
        return self._param

    def call(self) -> None:
        """
        :return: Starts the command on light manager
        """
        self._connector.send("?" + self.param)


class LMActuator(_LMFixture):
    """Describing an actuator"""

    def __init__(self, config: ET.Element, connector: _LMConnector):
        """
        :param config: actuator part of the config.xml
        :param connector: light manager connector
        """
        super().__init__(config.findtext("./name"))
        self._type = config.findtext("./type") or "scene"
        self._commands = [LMCommand(connector, config=command) for command in config.findall("./commandlist/command")]

    @property
    def name(self) -> str:
        """
        :return: Name of the actuator
        """
        return self._name

    @property
    def type(self) -> str:
        """
        :return: Type of the actuator e.g. trust
        """
        return self._type

    @property
    def commands(self) -> List[LMCommand]:
        """
        :return: List of all supported commands
        """
        return self._commands


class LMZone(_LMFixture):
    """Describing a group of actuators"""

    def __init__(self, config: ET.Element, connector: _LMConnector):
        """
        :param config: zone part of the config.xml
        :param connector: light manager connector
        """
        super().__init__(config.findtext("./zonename"))
        self._actuators = [LMActuator(actuator, connector) for actuator in config.findall("./actuators/actuator")]

    @property
    def name(self) -> str:
        """
        :return: Name of the zone
        """
        return self._name

    @property
    def actuators(self) -> List[LMActuator]:
        """
        :return: List of all included actuators
        """
        return self._actuators


class LMAir(_LMFixture):
    """Handling communication with jb media light manager air"""

    _config = None

    def __init__(self, url: str, username: str = None, password: str = None, adapter_ip: str = None, info: str = None):
        """
        Initiates a new LMAir instance with given data. Only url is mandatory.
        If username, password or info is not given, it will be loaded from the device.

        :param url: url for connecting to light manager. E.g. http://lmair
        :param username: Optional. lan username
        :param password: Optional. lan password
        :param adapter_ip: Optional. Ip of the network adapter which is connected to light manager
        :param info: Optional. device info
        """
        if not url or not info:
            url, info = next(iter(_LMConnector.discover(urlparse(url).hostname).items()))

        if not url.startswith("http"):
            url = "http://" + url

        parsed_url = urlparse(url)

        self._lm_hostname = str(parsed_url.hostname)

        self._lm_url = parsed_url.scheme + "://" + self._lm_hostname

        def get_info_value(key: str) -> Optional[str]:
            result = re.search(key + r"[ :](.+?)\r\n", info)
            if not result:
                return None
            return result.group(1).strip()

        self._username = username or get_info_value("Login")
        self._password = password or get_info_value("Pass")

        super().__init__(get_info_value("WhoAmI"))
        self._fw_version = get_info_value("FWVersion")
        self._ssid = get_info_value("SSID")
        self._connector = _LMConnector(self._lm_url, self._username, self._password, adapter_ip=adapter_ip)

    @property
    def host(self):
        """
        :return: host of light manager
        """
        return self._lm_hostname

    @property
    def fw_version(self):
        """
        :return: firmware version of light manager
        """
        return self._fw_version

    @property
    def ssid(self):
        """
        :return: currently connected wlan ssid
        """
        return self._ssid

    @staticmethod
    def discover(wait_duration: int = None, discover_adapter_ip: str = None, discover_port: int = None) -> List[LMAir]:
        """
        Discovers all devices in local network

        :param wait_duration: Optional. Duration in seconds of waiting for response
        :param discover_adapter_ip: Optional. Ip of the desired network adapter
        :param discover_port: Optional. Broadcast port
        :return: List of LMAir instances
        """
        return [
            LMAir(host, info=info) for host, info in _LMConnector.discover(
                wait_duration=wait_duration, discover_adapter_ip=discover_adapter_ip, discover_port=discover_port
            ).items()
        ]

    def load_fixtures(self) -> [List[LMZone], List[LMCommand]]:
        """Load all fixtures (zones, actuators and scenes)

        :return: Tupel with list of zones and list of scenes
        """
        config = self._load_config()
        zones = [LMZone(zone, self._connector) for zone in config.findall("./zone")]
        scenes = [LMCommand(self._connector, config=zone) for zone in config.findall("./lightscenes/scene")]
        return zones, scenes

    def send_command(self, command: Optional[str]):
        """Sends a custom command

        :param command: command to send (e.g. 'typ,it,did,0996,aid,215,acmd,0,seq,6')
        """
        LMCommand(self._connector, name="custom_command", param="cmd=" + command).call()

    def start_radio_bus_listening(self, callback: Callable[[str], None]) -> None:
        """Start listening for radio bus actuators.

        :param callback: Callback function which is called whenever a code is received.
        """
        self._connector.connect(callback)

    def stop_radio_bus_listening(self) -> None:
        """Stop listening for radio bus actuators"""
        self._connector.disconnect()

    def _load_config(self) -> ET.Element:
        """Loads the config xml from light manager"""

        if self._config:
            return self._config

        config_response = self._connector.send("/config.xml")

        self._config = ET.fromstring(config_response.content.decode())
        return self._config
