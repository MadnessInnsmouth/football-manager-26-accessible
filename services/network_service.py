"""Network service for Football Manager 26 - WebSocket relay client.

Requires: pip install websocket-client
"""
from __future__ import annotations
import json
import queue
import threading
from dataclasses import dataclass
from typing import Optional

DEFAULT_SERVER_URL = "wss://game-server-hub.replit.app/api/multiplayer"
DEFAULT_PORT = 34888


@dataclass
class SessionInfo:
    mode: str
    host: str
    port: int
    connected: bool
    code: str


class NetworkService:
    def __init__(self):
        self._ws = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.inbox: queue.Queue = queue.Queue()
        self.mode: Optional[str] = None
        self.host: str = ""
        self.port: int = 0
        self.server_mode: str = "relay"
        self.enabled: bool = True

    def is_enabled(self) -> bool:
        return self.enabled

    def reset(self):
        self._running = False
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._thread = None
        self.inbox = queue.Queue()
        self.mode = None
        self.host = ""
        self.port = 0
        self.server_mode = "relay"

    def connect_server(
        self,
        host: str = "",
        port: int = 0,
        url: Optional[str] = None,
    ) -> SessionInfo:
        import websocket  # pip install websocket-client

        self.reset()

        if url is None:
            if host and (host.startswith("ws://") or host.startswith("wss://")):
                url = host
            elif host:
                url = f"wss://{host}/api/multiplayer"
            else:
                url = DEFAULT_SERVER_URL

        ws = websocket.WebSocket()
        ws.connect(url)
        self._ws = ws
        self.mode = "client"
        self.server_mode = "relay"
        self.host = url
        self._start_reader(ws)
        return SessionInfo(mode="client", host=url, port=0, connected=True, code=url)

    def host_session(self, host: str = "0.0.0.0", port: int = 0) -> SessionInfo:
        return self.connect_server()

    def wait_for_guest(self, timeout: float = 0.2):
        return None

    def join_session(self, host: str, port: int = 0) -> SessionInfo:
        return self.connect_server()

    def create_room(self, club_name: str, country: str) -> bool:
        return self.send_event("create_room", {"club_name": club_name, "country": country})

    def join_room(self, room_code: str, club_name: str, country: str) -> bool:
        return self.send_event(
            "join_room",
            {"room_code": room_code, "club_name": club_name, "country": country},
        )

    def send_event(self, event_name: str, payload: dict) -> bool:
        if self._ws is None:
            return False
        try:
            self._ws.send(json.dumps({"type": event_name, "payload": payload}))
            return True
        except Exception as exc:
            self.inbox.put({"type": "error", "payload": {"message": str(exc)}})
            return False

    def poll_event(self):
        try:
            return self.inbox.get_nowait()
        except queue.Empty:
            return None

    def sync_state(self, payload: dict) -> bool:
        return self.send_event("state", payload)

    def get_session_info(self) -> SessionInfo:
        return SessionInfo(
            mode=self.mode or "none",
            host=self.host,
            port=self.port,
            connected=self._ws is not None,
            code=self.host,
        )

    def _start_reader(self, ws):
        self._running = True

        def loop():
            while self._running:
                try:
                    data = ws.recv()
                    if not data:
                        self.inbox.put({"type": "disconnect"})
                        break
                    self.inbox.put(json.loads(data))
                except Exception as exc:
                    if self._running:
                        self.inbox.put({"type": "error", "payload": {"message": str(exc)}})
                    break
            self._running = False

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()


service = NetworkService()