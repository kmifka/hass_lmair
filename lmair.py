import socket
import threading
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from threading import Thread, Event
from time import sleep
from typing import List, Optional, Callable

import requests as requests


class LMFixture:
    """Base class for all light manager fixtures"""

    def __init__(self, url: str, name: str):
        self._url = url
        self._name = name

    def _send(self, path: str):
        """Sends a command to the light manager"""
        return requests.get(self._url + path)

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self._name})"


class LMCommand(LMFixture):
    """Describing a callable command"""

    def __init__(self, url, config: ET.Element):
        super().__init__(url, config.findtext("./name"))
        self._param = config.findtext("./param")

    @property
    def name(self) -> str:
        """Name of the command"""
        return self._name

    @property
    def param(self) -> str:
        """Param data of the command"""
        return self._param

    def call(self):
        """Starts the command on light manager"""
        self._send("?" + self.param)


class LMActuator(LMFixture):
    """Describing an actuator"""

    def __init__(self, url: str, config: ET.Element):
        super().__init__(url, config.findtext("./name"))
        self._type = config.findtext("./type") or "scene"
        self._commands = [LMCommand(url, command) for command in config.findall("./commandlist/command")]

    @property
    def name(self) -> str:
        """Name of the actuator"""
        return self._name

    @property
    def type(self) -> str:
        """Type of the actuator e.g. trust"""
        return self._type

    @property
    def commands(self) -> List[LMCommand]:
        """List of all supported commands"""
        return self._commands


class LMZone(LMFixture):
    """Describing a group of actuators"""

    def __init__(self, url: str, config: ET.Element):
        super().__init__(url, config.findtext("./zonename"))
        self._actuators = [LMActuator(url, actuator) for actuator in config.findall("./actuators/actuator")]

    @property
    def name(self) -> str:
        """Name of the zone"""
        return self._name

    @property
    def actuators(self) -> List[LMActuator]:
        """List of all included actuators"""
        return self._actuators


class LMConnector:
    """Handles the TCP connection to the light manager"""
    CONNECT_CMD = "/control?pcip="
    RECEIVE_IDENTIFIER = "rfit,"

    def __init__(self, url: str, refresh_interval: int = 20, receive_port: int = 30304):
        self._url = url
        self._ip: str = socket.gethostbyname(socket.getfqdn())
        self._refresh_interval: int = refresh_interval
        self._socket: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._ip, receive_port))
        self._socket.listen(5)
        self._stop: Event = Event()
        self._thread: Optional[Thread] = None
        self._refresh_thread: Optional[Thread] = None

    def connect(self, callback: Callable[[str], None]):
        """Connects to the TCP stream"""
        if self._thread and self._refresh_thread:
            return

        self._stop.clear()

        def _refresh_connection():
            while not self._stop.is_set():
                self._send_connect(self._ip)
                sleep(self._refresh_interval)

        def _receive():
            while not self._stop.is_set():
                new_sock, address = self._socket.accept()
                data = new_sock.recv(1024).replace(b"\x00", b"").decode()
                new_sock.close()

                if data.startswith(self.RECEIVE_IDENTIFIER):
                    callback(data.replace(self.RECEIVE_IDENTIFIER, "", 1))
                else:
                    self._send_connect(self._ip)

        self._thread = Thread(target=_receive)
        self._refresh_thread = Thread(target=_refresh_connection)
        self._thread.start()
        self._refresh_thread.start()

    def disconnect(self):
        """Connects from the TCP stream"""
        if not self._thread and not self._refresh_thread:
            return

        self._stop.set()
        self._send_connect("")

        if self._thread is not threading.current_thread():
            self._thread.join(0)
        self._refresh_thread.join(0)
        self._thread = None
        self._refresh_thread = None

    def _send_connect(self, ip):
        """Sends connect message to the light manager"""
        requests.post(self._url + "/control", {"pcip": ip})


class LMAir(LMFixture):
    """Handling communication with jb media light manager air"""

    def __init__(self, url: str):
        super().__init__(url, urlparse(url).hostname)
        self._connector = None

    def load_fixtures(self) -> [List[LMZone], List[LMCommand]]:
        """Load all fixtures (zones, actuators and scenes)"""
        config = self._load_config()
        zones = [LMZone(self._url, zone) for zone in config.findall("./zone")]
        scenes = [LMCommand(self._url, zone) for zone in config.findall("./lightscenes/scene")]
        return zones, scenes

    def start_radio_bus_listening(self, callback: Callable[[str], None]):
        """Start listening for radio bus actuators. The callback is called whenever a code is received."""
        if not self._connector:
            self._connector = LMConnector(self._url)
        self._connector.connect(callback)

    def stop_radio_bus_listening(self):
        """Stop listening for radio bus actuators"""
        if self._connector:
            self._connector.disconnect()

    def _load_config(self):
        """Loads the config xml from light manager"""
        config_response = self._send("/config.xml")
        return ET.fromstring(config_response.content.decode())
