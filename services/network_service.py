"""Network service for Football Manager 26 - WebSocket relay client."""
from __future__ import annotations
import json, queue, threading
from dataclasses import dataclass
from typing import Optional

DEFAULT_SERVER_URL = "wss://f5f700d0-d25f-4641-a5ee-93e4095aad4d-00-2n0esc1ef1hd0.worf.replit.dev/api/multiplayer"

@dataclass
class SessionInfo:
    mode: str; host: str; port: int; connected: bool; code: str

class NetworkService:
    def __init__(self):
        self._ws = None; self._thread = None; self._running = False
        self.inbox: queue.Queue = queue.Queue()
        self.mode = None; self.host = ""; self.port = 0
        self.server_mode = "relay"; self.enabled = True

    def is_enabled(self): return self.enabled

    def reset(self):
        self._running = False
        if self._ws:
            try: self._ws.close()
            except: pass
            self._ws = None
        self._thread = None; self.inbox = queue.Queue()
        self.mode = None; self.host = ""; self.port = 0; self.server_mode = "relay"

    def connect_server(self, host="", port=0, url=None):
        import websocket
        self.reset()
        if url is None:
            if host and (host.startswith("ws://") or host.startswith("wss://")): url = host
            elif host: url = f"wss://{host}/api/multiplayer"
            else: url = DEFAULT_SERVER_URL
        ws = websocket.WebSocket(); ws.connect(url)
        self._ws = ws; self.mode = "client"; self.server_mode = "relay"; self.host = url
        self._start_reader(ws)
        return SessionInfo(mode="client", host=url, port=0, connected=True, code=url)

    def host_session(self, host="0.0.0.0", port=0): return self.connect_server()
    def wait_for_guest(self, timeout=0.2): return None
    def join_session(self, host, port=0): return self.connect_server()

    def create_room(self, club_name, country):
        return self.send_event("create_room", {"club_name": club_name, "country": country})

    def join_room(self, room_code, club_name, country):
        return self.send_event("join_room", {"room_code": room_code, "club_name": club_name, "country": country})

    def send_event(self, event_name, payload):
        if not self._ws: return False
        try: self._ws.send(json.dumps({"type": event_name, "payload": payload})); return True
        except Exception as e: self.inbox.put({"type": "error", "payload": {"message": str(e)}}); return False

    def poll_event(self):
        try: return self.inbox.get_nowait()
        except queue.Empty: return None

    def sync_state(self, payload): return self.send_event("state", payload)

    def get_session_info(self):
        return SessionInfo(mode=self.mode or "none", host=self.host, port=self.port,
                           connected=self._ws is not None, code=self.host)

    def _start_reader(self, ws):
        self._running = True
        def loop():
            while self._running:
                try:
                    data = ws.recv()
                    if not data: self.inbox.put({"type": "disconnect"}); break
                    self.inbox.put(json.loads(data))
                except Exception as e:
                    if self._running: self.inbox.put({"type": "error", "payload": {"message": str(e)}})
                    break
            self._running = False
        self._thread = threading.Thread(target=loop, daemon=True); self._thread.start()

service = NetworkService()