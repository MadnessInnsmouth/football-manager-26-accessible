"""Safe speech wrapper for Football Manager 26."""

from __future__ import annotations

try:
    import accessible_output2.outputs.auto as ao2
    _speaker = ao2.Auto()
except Exception:
    _speaker = None


def speak(text: str, interrupt: bool = False) -> bool:
    if not text or _speaker is None:
        return False
    try:
        _speaker.speak(str(text), interrupt=interrupt)
        return True
    except Exception:
        return False


def priority_announce(text: str) -> bool:
    return speak(text, interrupt=True)
