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


def _load_username():
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        return data.get("username", "")
    except Exception:
        return ""


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


def get_username():
    return _load_username()


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
        if r.status_code == 401:
            return SaveResult(ok=False, message="Session expired. Please log in again.")
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
        if r.status_code == 401:
            return SaveResult(ok=False, message="Session expired. Please log in again.")
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
