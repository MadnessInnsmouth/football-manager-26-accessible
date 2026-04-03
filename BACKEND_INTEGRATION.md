# Football Manager 26 — Backend Integration Guide

## Overview

The backend is a TypeScript server hosted permanently at:

    https://game-server-hub.replit.app

It handles two things:

1. Multiplayer WebSocket relay — players connect and relay match messages to each other in real time.
2. Accounts and cloud saves — players register, log in, and save their game to the cloud.

The Python game client talks to the backend over HTTPS (for accounts and saves) and WSS (for multiplayer). No raw TCP is used.

---

## Files in the Game Repo

You need two files in the `services/` folder of your game:

    services/network_service.py   — multiplayer WebSocket client
    services/account_service.py   — account registration, login, and cloud saves

Both files are provided at the end of this document.

---

## GitHub Actions — Required pip packages

In `.github/workflows/release.yml`, the pip install step must include all of these:

    pip install pyinstaller wxPython accessible_output2 websocket-client requests

Without `websocket-client`, multiplayer will not bundle into the exe.
Without `requests`, cloud saves and accounts will not bundle into the exe.

---

## PyInstaller Spec — Required hidden imports

In `FootballManager26.spec`, the hidden imports line must be:

    hiddenimports = collect_submodules('accessible_output2') + collect_submodules('websocket')

The `requests` library does not need a hidden import because it is imported at the top of the file and PyInstaller detects it automatically. The `websocket` import happens inside a function, so it must be listed explicitly.

---

## Backend Endpoints

All endpoints are at `https://game-server-hub.replit.app`.

### Health check

    GET /api/healthz

Returns 200 if the server is running. No authentication needed.

---

### Register a new account

    POST /api/auth/register
    Content-Type: application/json

    {
      "username": "PlayerName",
      "email": "player@example.com",
      "password": "theirpassword"
    }

Success response (201):

    {
      "token": "<jwt token string>",
      "username": "PlayerName",
      "email": "player@example.com"
    }

Error responses:
- 400 if username, email, or password is missing
- 400 if username is shorter than 3 or longer than 50 characters
- 400 if password is shorter than 6 characters
- 409 if username or email is already taken

The token must be saved locally. `account_service.py` handles this automatically by saving to `%APPDATA%\FM26\auth_token.json` on Windows.

---

### Log in to an existing account

    POST /api/auth/login
    Content-Type: application/json

    {
      "username": "PlayerName",
      "password": "theirpassword"
    }

Success response (200):

    {
      "token": "<jwt token string>",
      "username": "PlayerName",
      "email": "player@example.com"
    }

Error responses:
- 400 if username or password is missing
- 401 if the username does not exist or password is wrong

After a successful login, save the token. It is valid for 30 days. `account_service.py` saves it automatically.

---

### Upload a cloud save

    POST /api/saves/upload
    Authorization: Bearer <token>
    Content-Type: application/json

    {
      "save_name": "career_1",
      "save_data": "<your entire game state as a JSON string>"
    }

`save_name` is optional. If omitted it defaults to `"default"`. Each player can have multiple named saves. Uploading to the same `save_name` overwrites the previous save.

Success response (200):

    { "ok": true, "save_name": "career_1" }

Error responses:
- 401 if the token is missing or expired
- 413 if the save data is larger than 2 MB
- 400 if save_data is missing

The 2 MB limit is generous. A full squad with all stats serialised to JSON is typically well under 500 KB.

---

### Download a cloud save

    GET /api/saves/download?save_name=career_1
    Authorization: Bearer <token>

`save_name` is optional, defaults to `"default"`.

Success response (200):

    {
      "save_name": "career_1",
      "save_data": "<the JSON string you uploaded>",
      "updated_at": "2026-04-03T09:00:00.000Z"
    }

Error responses:
- 401 if the token is missing or expired
- 404 if no save with that name exists for this player

---

### List all cloud saves for the logged-in player

    GET /api/saves/list
    Authorization: Bearer <token>

Success response (200):

    {
      "saves": [
        { "save_name": "career_1", "updated_at": "2026-04-03T09:00:00.000Z" },
        { "save_name": "default",  "updated_at": "2026-04-02T14:22:00.000Z" }
      ]
    }

Returns newest saves first. Returns an empty array if the player has no saves. Use this to show a list of slots when the player clicks Load Game.

---

### Delete a cloud save

    DELETE /api/saves/delete
    Authorization: Bearer <token>
    Content-Type: application/json

    { "save_name": "career_1" }

Success response (200):

    { "ok": true }

---

## Multiplayer WebSocket

The WebSocket endpoint is:

    wss://game-server-hub.replit.app/api/multiplayer

Connect using `websocket.WebSocket().connect(url)` from the `websocket-client` library. All messages are JSON objects with a `type` field and a `payload` field.

### Message types sent from client to server

**create_room** — creates a new room and returns a 6-character room code.

    { "type": "create_room", "payload": { "club_name": "Arsenal", "country": "England" } }

Response from server:

    { "type": "room_created", "payload": { "room_code": "A1B2C3" } }

**join_room** — join an existing room using the code the host shared.

    { "type": "join_room", "payload": { "room_code": "A1B2C3", "club_name": "Chelsea", "country": "England" } }

Response to the guest:

    { "type": "room_joined", "payload": { "room_code": "A1B2C3" } }

Response broadcast to both host and guest:

    {
      "type": "room_ready",
      "payload": {
        "room_code": "A1B2C3",
        "host_club": "Arsenal",
        "guest_club": "Chelsea",
        "country": "England"
      }
    }

**start_match** — host sends this to begin the match. The payload is forwarded to both players.

    { "type": "start_match", "payload": { ... any match setup data ... } }

**match_result** — either player sends this after the match engine produces a result. Forwarded to both players.

    { "type": "match_result", "payload": { "home_score": 2, "away_score": 1, ... } }

**ping** — keepalive. Server replies with pong.

    { "type": "ping", "payload": {} }

### Message types sent from server to client

- `room_created` — sent to host after create_room
- `room_joined` — sent to guest after join_room
- `room_ready` — broadcast to both when the room is full
- `start_match` — relayed to both when host sends start_match
- `match_result` — relayed to both when either player sends match_result
- `pong` — reply to ping
- `peer_left` — sent to the remaining player when the other disconnects
- `error` — sent when something goes wrong, payload contains a `message` field

---

## How authentication works internally

Passwords are hashed with bcrypt (cost factor 12) before being stored. They are never stored in plain text. The server never returns the password hash.

When a player logs in, the server creates a JWT (JSON Web Token) signed with a secret key. The token contains the player's internal user ID and username. It expires after 30 days.

The game stores this token in `%APPDATA%\FM26\auth_token.json`. On every request that requires authentication, the token is sent in the `Authorization` header as `Bearer <token>`. The server verifies the signature and expiry before processing the request.

If the token is expired or tampered with, the server returns 401 and the game should prompt the player to log in again.

---

## How to use account_service.py in the game

Import the functions you need:

    from services.account_service import register, login, logout, is_logged_in
    from services.account_service import upload_save, download_save, list_saves

Check if a player is already logged in when the game starts:

    if is_logged_in():
        # show main menu with cloud save options
    else:
        # show login / register screen

Register a new player:

    result = register("PlayerName", "email@example.com", "mypassword")
    if result.ok:
        speak(f"Account created. Welcome, {result.username}.")
    else:
        speak(f"Registration failed: {result.message}")

Log in:

    result = login("PlayerName", "mypassword")
    if result.ok:
        speak("Logged in.")
    else:
        speak(f"Login failed: {result.message}")

Save the game to the cloud:

    import json
    save_data = json.dumps({
        "squad": squad_list,
        "season": current_season,
        "money": club_budget,
        "league_table": table,
    })
    result = upload_save(save_data, save_name="career_1")
    if result.ok:
        speak("Game saved to cloud.")
    else:
        speak(f"Cloud save failed: {result.message}")

Load from the cloud:

    result = download_save("career_1")
    if result.ok:
        game_state = json.loads(result.save_data)
        squad_list = game_state["squad"]
        speak("Game loaded.")
    else:
        speak(f"Could not load save: {result.message}")

Show a list of saves (for a load game menu):

    saves = list_saves()
    for s in saves:
        speak(f"{s['save_name']}, last saved {s['updated_at']}")

---

## Cloud save capacity

Each save is limited to 2 MB. A typical Football Manager save with a full squad, league table, fixtures, and financial data serialised to JSON is around 50 to 200 KB. This means you could store 10 or more named save slots per player without any issues. 50 players with 5 saves each would use roughly 50 MB total, which is well within limits for this deployment.

---

## Future additions

If you want to add more features later, all additions go in the backend TypeScript server and are called from Python on the client side.

Examples of things that are straightforward to add:

- League tables or leaderboards stored per user
- Match history log stored in the database
- Friends list (store user IDs in a junction table)
- Private rooms with passwords for multiplayer
- Email verification on register (would need a mail provider)
- Password reset flow

The pattern is always the same: add a route in `artifacts/api-server/src/routes/`, add a Python function in `account_service.py`, and call it from wherever in the game it is needed.

---

## Complete services/network_service.py

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

        def connect_server(self, host="", port=0, url=None):
            import websocket
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

        def host_session(self, host="0.0.0.0", port=0):
            return self.connect_server()

        def wait_for_guest(self, timeout=0.2):
            return None

        def join_session(self, host, port=0):
            return self.connect_server()

        def create_room(self, club_name, country):
            return self.send_event("create_room", {"club_name": club_name, "country": country})

        def join_room(self, room_code, club_name, country):
            return self.send_event("join_room", {"room_code": room_code, "club_name": club_name, "country": country})

        def send_event(self, event_name, payload):
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

        def sync_state(self, payload):
            return self.send_event("state", payload)

        def get_session_info(self):
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

---

## Complete services/account_service.py

    """Account and cloud save service for Football Manager 26.

    Requires: pip install requests
    """
    from __future__ import annotations

    import json
    import os
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Optional

    try:
        import requests
    except ImportError:
        requests = None

    BASE_URL = "https://game-server-hub.replit.app/api"
    TOKEN_FILE = Path(os.getenv("APPDATA", ".")) / "FM26" / "auth_token.json"


    @dataclass
    class AccountResult:
        ok: bool
        message: str
        username: str = ""
        token: str = ""


    @dataclass
    class SaveResult:
        ok: bool
        message: str
        save_data: str = ""


    def _headers(token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


    def _load_token():
        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            return data.get("token")
        except Exception:
            return None


    def _save_token(token, username):
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(
            json.dumps({"token": token, "username": username}), encoding="utf-8"
        )


    def _clear_token():
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except Exception:
            pass


    def register(username, email, password):
        if requests is None:
            return AccountResult(ok=False, message="requests library not installed.")
        try:
            r = requests.post(
                f"{BASE_URL}/auth/register",
                json={"username": username, "email": email, "password": password},
                timeout=10,
            )
            data = r.json()
            if r.status_code == 201:
                _save_token(data["token"], data["username"])
                return AccountResult(ok=True, message="Account created.", username=data["username"], token=data["token"])
            return AccountResult(ok=False, message=data.get("error", "Registration failed."))
        except Exception as exc:
            return AccountResult(ok=False, message=f"Connection error: {exc}")


    def login(username, password):
        if requests is None:
            return AccountResult(ok=False, message="requests library not installed.")
        try:
            r = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            data = r.json()
            if r.status_code == 200:
                _save_token(data["token"], data["username"])
                return AccountResult(ok=True, message="Logged in.", username=data["username"], token=data["token"])
            return AccountResult(ok=False, message=data.get("error", "Login failed."))
        except Exception as exc:
            return AccountResult(ok=False, message=f"Connection error: {exc}")


    def logout():
        _clear_token()


    def is_logged_in():
        return _load_token() is not None


    def upload_save(save_data, save_name="default"):
        if requests is None:
            return SaveResult(ok=False, message="requests library not installed.")
        token = _load_token()
        if not token:
            return SaveResult(ok=False, message="Not logged in.")
        try:
            r = requests.post(
                f"{BASE_URL}/saves/upload",
                json={"save_name": save_name, "save_data": save_data},
                headers=_headers(token),
                timeout=15,
            )
            data = r.json()
            if r.status_code == 200:
                return SaveResult(ok=True, message=f"Save '{save_name}' uploaded.")
            return SaveResult(ok=False, message=data.get("error", "Upload failed."))
        except Exception as exc:
            return SaveResult(ok=False, message=f"Connection error: {exc}")


    def download_save(save_name="default"):
        if requests is None:
            return SaveResult(ok=False, message="requests library not installed.")
        token = _load_token()
        if not token:
            return SaveResult(ok=False, message="Not logged in.")
        try:
            r = requests.get(
                f"{BASE_URL}/saves/download",
                params={"save_name": save_name},
                headers=_headers(token),
                timeout=15,
            )
            data = r.json()
            if r.status_code == 200:
                return SaveResult(ok=True, message="Save loaded.", save_data=data["save_data"])
            return SaveResult(ok=False, message=data.get("error", "Download failed."))
        except Exception as exc:
            return SaveResult(ok=False, message=f"Connection error: {exc}")


    def list_saves():
        if requests is None:
            return []
        token = _load_token()
        if not token:
            return []
        try:
            r = requests.get(
                f"{BASE_URL}/saves/list",
                headers=_headers(token),
                timeout=10,
            )
            if r.status_code == 200:
                return r.json().get("saves", [])
            return []
        except Exception:
            return []


    def delete_save(save_name="default"):
        if requests is None:
            return SaveResult(ok=False, message="requests library not installed.")
        token = _load_token()
        if not token:
            return SaveResult(ok=False, message="Not logged in.")
        try:
            r = requests.delete(
                f"{BASE_URL}/saves/delete",
                json={"save_name": save_name},
                headers=_headers(token),
                timeout=10,
            )
            if r.status_code == 200:
                return SaveResult(ok=True, message=f"Save '{save_name}' deleted.")
            data = r.json()
            return SaveResult(ok=False, message=data.get("error", "Delete failed."))
        except Exception as exc:
            return SaveResult(ok=False, message=f"Connection error: {exc}")
