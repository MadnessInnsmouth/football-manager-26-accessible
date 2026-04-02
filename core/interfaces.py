from dataclasses import dataclass
from typing import Protocol, Any, List


class AudioServiceProtocol(Protocol):
    def speak(self, text: str, interrupt: bool = False) -> None: ...
    def play_sound(self, sound_id: str) -> None: ...


class RenderServiceProtocol(Protocol):
    def notify_screen_change(self, screen_name: str) -> None: ...
    def notify_match_event(self, event_text: str) -> None: ...


class NetworkServiceProtocol(Protocol):
    def is_enabled(self) -> bool: ...
    def sync_state(self, payload: dict) -> None: ...
    def send_event(self, event_name: str, payload: dict) -> None: ...


@dataclass
class ServiceBundle:
    audio: Any = None
    render: Any = None
    network: Any = None
