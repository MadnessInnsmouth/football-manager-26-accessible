from __future__ import annotations

import json
import queue
import socket
import threading
from dataclasses import dataclass

DEFAULT_PORT = 34888
BUFFER_SIZE = 65536


@dataclass
class SessionInfo:
    mode: str
    host: str
    port: int
    connected: bool
    code: str


class NetworkService:
    def __init__(self):
        self.enabled = True
        self.server_socket = None
        self.client_socket = None
        self.conn = None
        self.mode = None
        self.host = ""
        self.port = DEFAULT_PORT
        self.inbox = queue.Queue()
        self.reader_thread = None
        self.running = False
        self.server_mode = "direct"

    def is_enabled(self) -> bool:
        return self.enabled

    def reset(self):
        self.running = False
        for sock in [self.conn, self.client_socket, self.server_socket]:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
        self.server_socket = None
        self.client_socket = None
        self.conn = None
        self.mode = None
        self.host = ""
        self.port = DEFAULT_PORT
        self.inbox = queue.Queue()
        self.reader_thread = None
        self.server_mode = "direct"

    def _start_reader(self, sock):
        self.running = True

        def loop():
            buffer = b""
            while self.running:
                try:
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        self.inbox.put({"type": "disconnect"})
                        break
                    buffer += data
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        if raw.strip():
                            self.inbox.put(json.loads(raw.decode("utf-8")))
                except Exception as exc:
                    self.inbox.put({"type": "error", "payload": {"message": str(exc)}})
                    break
            self.running = False

        self.reader_thread = threading.Thread(target=loop, daemon=True)
        self.reader_thread.start()

    def host_session(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> SessionInfo:
        self.reset()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(1)
        self.server_socket = srv
        self.mode = "host"
        self.host = host
        self.port = port
        self.server_mode = "direct"
        code = f"{self._get_local_ip()}:{port}"
        return SessionInfo(mode="host", host=host, port=port, connected=False, code=code)

    def wait_for_guest(self, timeout: float = 0.2):
        if not self.server_socket:
            return None
        self.server_socket.settimeout(timeout)
        try:
            conn, addr = self.server_socket.accept()
            self.conn = conn
            self._start_reader(conn)
            return {"connected": True, "address": addr[0], "port": addr[1]}
        except socket.timeout:
            return None

    def join_session(self, host: str, port: int = DEFAULT_PORT) -> SessionInfo:
        self.reset()
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect((host, port))
        self.client_socket = cli
        self.mode = "client"
        self.host = host
        self.port = port
        self.server_mode = "direct"
        self._start_reader(cli)
        return SessionInfo(mode="client", host=host, port=port, connected=True, code=f"{host}:{port}")

    def connect_server(self, host: str, port: int = DEFAULT_PORT) -> SessionInfo:
        self.reset()
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect((host, port))
        self.client_socket = cli
        self.mode = "client"
        self.host = host
        self.port = port
        self.server_mode = "relay"
        self._start_reader(cli)
        return SessionInfo(mode="client", host=host, port=port, connected=True, code=f"{host}:{port}")

    def create_room(self, club_name: str, country: str):
        if not self.client_socket:
            return False
        self.send_event("create_room", {"club_name": club_name, "country": country})
        return True

    def join_room(self, room_code: str, club_name: str, country: str):
        if not self.client_socket:
            return False
        self.send_event("join_room", {"room_code": room_code, "club_name": club_name, "country": country})
        return True

    def _active_socket(self):
        return self.conn or self.client_socket

    def send_event(self, event_name: str, payload: dict):
        sock = self._active_socket()
        if not sock:
            return False
        message = json.dumps({"type": event_name, "payload": payload}).encode("utf-8") + b"\n"
        sock.sendall(message)
        return True

    def poll_event(self):
        try:
            return self.inbox.get_nowait()
        except queue.Empty:
            return None

    def sync_state(self, payload: dict):
        return self.send_event("state", payload)

    def get_session_info(self):
        code = ""
        if self.server_mode == "direct" and self.mode == "host":
            code = f"{self._get_local_ip()}:{self.port}"
        elif self.host:
            code = f"{self.host}:{self.port}"
        return SessionInfo(
            mode=self.mode or "none",
            host=self.host,
            port=self.port,
            connected=self._active_socket() is not None,
            code=code,
        )

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


service = NetworkService()
