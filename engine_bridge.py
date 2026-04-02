"""Bridge between the accessible Python UI and backend engine.

Current live architecture:
- Python owns mutable game state.
- Native DLL provides stateless acceleration kernels.
- Live match simulation prefers the native DLL and falls back to Python only
  on explicit native failure.
- Batch week simulation can use the native DLL for repeated fixture simulation
  and table recomputation, while Python still owns state mutation.
"""

from __future__ import annotations

import ctypes
import json
from dataclasses import dataclass
from pathlib import Path

import game_engine as py_engine
import match_engine as py_match_engine
import save_system
from models import EventType, MatchEvent, MatchResult, Position

ROOT = Path(__file__).resolve().parent
DLL_CANDIDATES = [
    ROOT / "backend" / "build" / "fm_backend.dll",
    ROOT / "backend" / "build" / "Release" / "fm_backend.dll",
    ROOT / "backend" / "build" / "Debug" / "fm_backend.dll",
]

_NATIVE_DLL = None
_NATIVE_MODE = "python-fallback"
for candidate in DLL_CANDIDATES:
    if candidate.exists():
        try:
            _NATIVE_DLL = ctypes.CDLL(str(candidate))
            _NATIVE_MODE = "native-stateless-dll"
            break
        except Exception:
            _NATIVE_DLL = None


@dataclass
class BackendStatus:
    mode: str
    native_available: bool
    message: str
    native_match_enabled: bool = False
    native_match_probe_ok: bool = False
    native_week_enabled: bool = False
    native_week_probe_ok: bool = False
    last_native_match_error: str = ""
    last_native_week_error: str = ""


class NativeStatelessBridge:
    class ResultBuffer(ctypes.Structure):
        _fields_ = [("data", ctypes.c_void_p), ("length", ctypes.c_int)]

    def __init__(self, dll):
        self.dll = dll
        self.contract_eval_available = False
        self.match_available = hasattr(self.dll, "fm_simulate_match_json")
        self.week_available = hasattr(self.dll, "fm_simulate_week_json")
        self.dll.fm_validate_squad_json.restype = self.ResultBuffer
        self.dll.fm_validate_squad_json.argtypes = [ctypes.c_char_p]
        self.dll.fm_validate_selected_xi.restype = self.ResultBuffer
        self.dll.fm_validate_selected_xi.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_char_p]
        self.dll.fm_preview_stadium_upgrade_json.restype = self.ResultBuffer
        self.dll.fm_preview_stadium_upgrade_json.argtypes = [ctypes.c_char_p]
        self.dll.fm_summarize_club_records_json.restype = self.ResultBuffer
        self.dll.fm_summarize_club_records_json.argtypes = [ctypes.c_char_p]
        self.dll.fm_summarize_youth_players_json.restype = self.ResultBuffer
        self.dll.fm_summarize_youth_players_json.argtypes = [ctypes.c_char_p]
        self.dll.fm_get_transfer_window_status_json.restype = self.ResultBuffer
        self.dll.fm_get_transfer_window_status_json.argtypes = [ctypes.c_char_p]
        if self.match_available:
            self.dll.fm_simulate_match_json.restype = self.ResultBuffer
            self.dll.fm_simulate_match_json.argtypes = [ctypes.c_char_p]
        if self.week_available:
            self.dll.fm_simulate_week_json.restype = self.ResultBuffer
            self.dll.fm_simulate_week_json.argtypes = [ctypes.c_char_p]
        if hasattr(self.dll, "fm_evaluate_contract_offer_json"):
            self.dll.fm_evaluate_contract_offer_json.restype = self.ResultBuffer
            self.dll.fm_evaluate_contract_offer_json.argtypes = [ctypes.c_char_p]
            self.contract_eval_available = True
        self.dll.fm_free_buffer.restype = None
        self.dll.fm_free_buffer.argtypes = [self.ResultBuffer]
        self.dll.fm_backend_version.restype = ctypes.c_char_p
        self.dll.fm_backend_version.argtypes = []

    def backend_version(self):
        value = self.dll.fm_backend_version()
        return value.decode("utf-8") if value else "unknown"

    def _decode(self, buf):
        try:
            if not buf.data or buf.length <= 0:
                return None
            raw = ctypes.string_at(buf.data, buf.length).decode("utf-8")
            return json.loads(raw) if raw else None
        finally:
            self.dll.fm_free_buffer(buf)

    def validate_selected_xi(self, selected_ids, roster_players):
        roster_json = json.dumps({"players": roster_players})
        arr = (ctypes.c_int * len(selected_ids))(*selected_ids)
        return self._decode(self.dll.fm_validate_selected_xi(arr, len(selected_ids), roster_json.encode("utf-8")))

    def preview_stadium_upgrade(self, payload):
        return self._decode(self.dll.fm_preview_stadium_upgrade_json(json.dumps(payload).encode("utf-8")))

    def summarize_club_records(self, payload):
        return self._decode(self.dll.fm_summarize_club_records_json(json.dumps(payload).encode("utf-8")))

    def summarize_youth_players(self, payload):
        return self._decode(self.dll.fm_summarize_youth_players_json(json.dumps(payload).encode("utf-8")))

    def get_transfer_window_status(self, payload):
        return self._decode(self.dll.fm_get_transfer_window_status_json(json.dumps(payload).encode("utf-8")))

    def evaluate_contract_offer(self, payload):
        if not self.contract_eval_available:
            return None
        return self._decode(self.dll.fm_evaluate_contract_offer_json(json.dumps(payload).encode("utf-8")))

    def simulate_match_json(self, payload):
        if not self.match_available:
            return None
        return self._decode(self.dll.fm_simulate_match_json(json.dumps(payload).encode("utf-8")))

    def simulate_week_json(self, payload):
        if not self.week_available:
            return None
        return self._decode(self.dll.fm_simulate_week_json(json.dumps(payload).encode("utf-8")))


class EngineBridge:
    def __init__(self):
        self.native = NativeStatelessBridge(_NATIVE_DLL) if _NATIVE_DLL is not None else None
        self.native_mode = _NATIVE_MODE
        self.native_match_enabled = self.native is not None and self.native.match_available
        self.native_week_enabled = self.native is not None and self.native.week_available
        self.last_native_match_error = ""
        self.last_native_week_error = ""
        self.last_match_used_native = False
        self.last_match_fallback_used = False
        self.last_week_used_native = False
        self.last_week_fallback_used = False

    def _player_to_native(self, player):
        return {
            "id": str(player.id),
            "name": player.full_name,
            "position": player.position.value if hasattr(player.position, "value") else str(player.position),
            "overall": int(player.overall),
            "shooting": int(player.shooting),
            "passing": int(player.passing),
            "defending": int(player.defending),
            "pace": int(player.pace),
            "physical": int(player.physical),
            "goalkeeping": int(player.goalkeeping),
            "age": int(player.age),
            "available": bool(player.is_available),
        }

    def _club_selected_xi(self, club):
        available = [p for p in club.players if p.is_available]
        selected = [p for p in available if p.id in club.selected_squad_ids]
        if len(selected) < 11:
            try:
                club.auto_select_squad()
            except Exception:
                pass
            available = [p for p in club.players if p.is_available]
            selected = [p for p in available if p.id in club.selected_squad_ids]

        selected_ids = {p.id for p in selected}
        gks = [p for p in available if p.position == Position.GK and p.id not in selected_ids]
        outfield = [p for p in available if p.position != Position.GK and p.id not in selected_ids]
        gks.sort(key=lambda p: (p.goalkeeping, p.overall), reverse=True)
        outfield.sort(key=lambda p: p.overall, reverse=True)

        if not any(p.position == Position.GK for p in selected):
            if gks:
                selected.append(gks.pop(0))
            elif available:
                fallback_gk = max(available, key=lambda p: (p.goalkeeping, p.overall))
                if fallback_gk not in selected:
                    selected.append(fallback_gk)
                    selected_ids.add(fallback_gk.id)

        selected_ids = {p.id for p in selected}
        gks = [p for p in available if p.position == Position.GK and p.id not in selected_ids]
        outfield = [p for p in available if p.position != Position.GK and p.id not in selected_ids]
        gks.sort(key=lambda p: (p.goalkeeping, p.overall), reverse=True)
        outfield.sort(key=lambda p: p.overall, reverse=True)

        while len(selected) < 11 and outfield:
            p = outfield.pop(0)
            selected.append(p)
            selected_ids.add(p.id)
        while len(selected) < 11 and gks:
            p = gks.pop(0)
            selected.append(p)
            selected_ids.add(p.id)

        if len(selected) < 11:
            remaining = [p for p in club.players if p.id not in selected_ids]
            remaining.sort(key=lambda p: p.overall, reverse=True)
            while len(selected) < 11 and remaining:
                p = remaining.pop(0)
                selected.append(p)
                selected_ids.add(p.id)

        prioritized = []
        seen = set()
        best_gk = None
        for p in selected:
            if p.position == Position.GK:
                if best_gk is None or (p.goalkeeping, p.overall) > (best_gk.goalkeeping, best_gk.overall):
                    best_gk = p
        if best_gk is not None:
            prioritized.append(best_gk)
            seen.add(best_gk.id)
        rest = [p for p in selected if p.id not in seen]
        rest.sort(key=lambda p: p.overall, reverse=True)
        for p in rest:
            if len(prioritized) >= 11:
                break
            prioritized.append(p)
            seen.add(p.id)

        final_xi = prioritized[:11]
        if len(final_xi) < 11:
            raise ValueError(f"Could not build a full XI for {club.name}; only {len(final_xi)} players available.")
        if len({p.id for p in final_xi}) != 11:
            deduped = []
            seen = set()
            for p in final_xi:
                if p.id not in seen:
                    deduped.append(p)
                    seen.add(p.id)
            final_xi = deduped
        if len(final_xi) != 11:
            raise ValueError(f"Could not build a unique XI for {club.name}; only {len(final_xi)} unique players.")
        return final_xi

    def _club_to_native_team(self, club):
        xi = self._club_selected_xi(club)
        return {
            "id": str(club.id),
            "name": club.name,
            "stadium_capacity": int(club.stadium_capacity),
            "pitch_quality": int(club.infrastructure.stadium.pitch_quality),
            "training_intensity": int(club.infrastructure.training.intensity),
            "medical_level": int(club.infrastructure.training.medical_level),
            "selected_xi": [self._player_to_native(p) for p in xi],
        }

    def _build_match_payload(self, home_club, away_club):
        seed = (hash(str(home_club.id)) ^ hash(str(away_club.id)) ^ hash(home_club.name) ^ hash(away_club.name)) & 0xFFFFFFFF
        return {
            "home": self._club_to_native_team(home_club),
            "away": self._club_to_native_team(away_club),
            "seed": int(seed),
        }

    def _build_week_payload(self, fixtures, clubs_by_id):
        payload_fixtures = []
        for idx, fixture in enumerate(fixtures):
            home = clubs_by_id[fixture.home_id]
            away = clubs_by_id[fixture.away_id]
            payload_fixtures.append({
                "fixture_id": f"{fixture.week}:{fixture.competition_id}:{idx}:{fixture.home_id}:{fixture.away_id}",
                "competition_id": fixture.competition_id,
                "stage": fixture.stage,
                "week": int(fixture.week),
                "home": self._club_to_native_team(home),
                "away": self._club_to_native_team(away),
                "seed": int((hash(str(fixture.home_id)) ^ hash(str(fixture.away_id)) ^ hash(fixture.stage) ^ fixture.week) & 0xFFFFFFFF),
            })
        return {"fixtures": payload_fixtures}

    def _native_result_to_match_result(self, data):
        events = []
        event_map = {
            "Kick Off": EventType.KICK_OFF,
            "Goal": EventType.GOAL,
            "Own Goal": EventType.OWN_GOAL,
            "Shot Saved": EventType.SHOT_SAVED,
            "Shot Wide": EventType.SHOT_WIDE,
            "Foul": EventType.FOUL,
            "Yellow Card": EventType.YELLOW_CARD,
            "Red Card": EventType.RED_CARD,
            "Corner": EventType.CORNER,
            "Injury": EventType.INJURY,
            "Substitution": EventType.SUBSTITUTION,
            "Half Time": EventType.HALF_TIME,
            "Full Time": EventType.FULL_TIME,
            "Penalty Scored": EventType.PENALTY_SCORED,
            "Penalty Missed": EventType.PENALTY_MISSED,
        }
        for item in data.get("events", []):
            et = event_map.get(item.get("event_type", ""), EventType.FOUL)
            events.append(MatchEvent(
                minute=int(item.get("minute", 0)),
                event_type=et,
                team_name=item.get("team_name", ""),
                player_name=item.get("player_name", ""),
                assist_name=item.get("assist_name", ""),
                commentary=item.get("commentary", ""),
            ))
        return MatchResult(
            home_team=data.get("home_team", "Home"),
            away_team=data.get("away_team", "Away"),
            home_goals=int(data.get("home_goals", 0)),
            away_goals=int(data.get("away_goals", 0)),
            events=events,
            home_shots=int(data.get("home_shots", 0)),
            away_shots=int(data.get("away_shots", 0)),
            home_on_target=int(data.get("home_on_target", 0)),
            away_on_target=int(data.get("away_on_target", 0)),
            home_corners=int(data.get("home_corners", 0)),
            away_corners=int(data.get("away_corners", 0)),
            home_fouls=int(data.get("home_fouls", 0)),
            away_fouls=int(data.get("away_fouls", 0)),
            home_yellows=int(data.get("home_yellows", 0)),
            away_yellows=int(data.get("away_yellows", 0)),
            home_reds=int(data.get("home_reds", 0)),
            away_reds=int(data.get("away_reds", 0)),
            attendance=int(data.get("attendance", 0)),
        )

    def _probe_native_match(self) -> bool:
        if self.native is None or not self.native.match_available:
            return False
        probe = {
            "home": {
                "id": "h",
                "name": "Home",
                "stadium_capacity": 5000,
                "pitch_quality": 3,
                "training_intensity": 3,
                "medical_level": 3,
                "selected_xi": [
                    {"id": f"h{i}", "name": f"Home {i}", "position": "Goalkeeper" if i == 0 else ("Defender" if i < 5 else ("Midfielder" if i < 8 else "Forward")), "overall": 60, "shooting": 55, "passing": 58, "defending": 57, "pace": 56, "physical": 59, "goalkeeping": 60 if i == 0 else 1, "age": 24, "available": True}
                    for i in range(11)
                ],
            },
            "away": {
                "id": "a",
                "name": "Away",
                "stadium_capacity": 5000,
                "pitch_quality": 3,
                "training_intensity": 3,
                "medical_level": 3,
                "selected_xi": [
                    {"id": f"a{i}", "name": f"Away {i}", "position": "Goalkeeper" if i == 0 else ("Defender" if i < 5 else ("Midfielder" if i < 8 else "Forward")), "overall": 60, "shooting": 55, "passing": 58, "defending": 57, "pace": 56, "physical": 59, "goalkeeping": 60 if i == 0 else 1, "age": 24, "available": True}
                    for i in range(11)
                ],
            },
            "seed": 7,
        }
        try:
            result = self.native.simulate_match_json(probe)
            return bool(result and "home_goals" in result and "away_goals" in result and "events" in result and not result.get("error"))
        except Exception as ex:
            self.last_native_match_error = str(ex)
            return False

    def _probe_native_week(self) -> bool:
        if self.native is None or not self.native.week_available:
            return False
        probe = {
            "fixtures": [
                {
                    "fixture_id": "f1",
                    "competition_id": "league_main",
                    "stage": "League",
                    "week": 1,
                    "home": {
                        "id": "h",
                        "name": "Home",
                        "stadium_capacity": 5000,
                        "pitch_quality": 3,
                        "training_intensity": 3,
                        "medical_level": 3,
                        "selected_xi": [
                            {"id": f"h{i}", "name": f"Home {i}", "position": "Goalkeeper" if i == 0 else ("Defender" if i < 5 else ("Midfielder" if i < 8 else "Forward")), "overall": 60, "shooting": 55, "passing": 58, "defending": 57, "pace": 56, "physical": 59, "goalkeeping": 60 if i == 0 else 1, "age": 24, "available": True}
                            for i in range(11)
                        ],
                    },
                    "away": {
                        "id": "a",
                        "name": "Away",
                        "stadium_capacity": 5000,
                        "pitch_quality": 3,
                        "training_intensity": 3,
                        "medical_level": 3,
                        "selected_xi": [
                            {"id": f"a{i}", "name": f"Away {i}", "position": "Goalkeeper" if i == 0 else ("Defender" if i < 5 else ("Midfielder" if i < 8 else "Forward")), "overall": 60, "shooting": 55, "passing": 58, "defending": 57, "pace": 56, "physical": 59, "goalkeeping": 60 if i == 0 else 1, "age": 24, "available": True}
                            for i in range(11)
                        ],
                    },
                    "seed": 7,
                }
            ]
        }
        try:
            result = self.native.simulate_week_json(probe)
            return bool(result and "results" in result and isinstance(result.get("results"), list) and not result.get("error"))
        except Exception as ex:
            self.last_native_week_error = str(ex)
            return False

    def get_status(self) -> BackendStatus:
        if self.native is not None:
            probe_ok = self._probe_native_match()
            week_probe_ok = self._probe_native_week()
            return BackendStatus(
                self.native_mode,
                True,
                f"Native stateless DLL active: {self.native.backend_version()}",
                native_match_enabled=self.native_match_enabled,
                native_match_probe_ok=probe_ok,
                native_week_enabled=self.native_week_enabled,
                native_week_probe_ok=week_probe_ok,
                last_native_match_error=self.last_native_match_error,
                last_native_week_error=self.last_native_week_error,
            )
        return BackendStatus(
            "python-fallback",
            False,
            "Native DLL unavailable; using Python engine.",
            native_match_enabled=False,
            native_match_probe_ok=False,
            native_week_enabled=False,
            native_week_probe_ok=False,
            last_native_match_error=self.last_native_match_error,
            last_native_week_error=self.last_native_week_error,
        )

    def simulate_match(self, home_club, away_club):
        self.last_match_used_native = False
        self.last_match_fallback_used = False
        self.last_native_match_error = ""
        if self.native is not None and self.native_match_enabled and self.native.match_available:
            try:
                payload = self._build_match_payload(home_club, away_club)
                data = self.native.simulate_match_json(payload)
                if data and not data.get("error") and "home_goals" in data and "away_goals" in data:
                    self.last_match_used_native = True
                    return self._native_result_to_match_result(data)
                self.last_native_match_error = data.get("error", "Native match returned invalid payload.") if isinstance(data, dict) else "Native match returned no data."
            except Exception as ex:
                self.last_native_match_error = str(ex)
        self.last_match_fallback_used = True
        return py_match_engine.simulate_match(home_club, away_club)

    def simulate_week_native(self, fixtures, clubs_by_id):
        self.last_week_used_native = False
        self.last_week_fallback_used = False
        self.last_native_week_error = ""
        if self.native is None or not self.native_week_enabled or not self.native.week_available:
            self.last_week_fallback_used = True
            return None
        try:
            payload = self._build_week_payload(fixtures, clubs_by_id)
            data = self.native.simulate_week_json(payload)
            if data and not data.get("error") and isinstance(data.get("results"), list):
                self.last_week_used_native = True
                return data
            self.last_native_week_error = data.get("error", "Native week returned invalid payload.") if isinstance(data, dict) else "Native week returned no data."
        except Exception as ex:
            self.last_native_week_error = str(ex)
        self.last_week_fallback_used = True
        return None

    def validate_selected_xi_native(self, selected_ids, roster_players):
        if self.native is not None:
            return self.native.validate_selected_xi(selected_ids, roster_players)
        return None

    def preview_stadium_upgrade_native(self, payload):
        if self.native is not None:
            return self.native.preview_stadium_upgrade(payload)
        return None

    def summarize_club_records_native(self, payload):
        if self.native is not None:
            return self.native.summarize_club_records(payload)
        return None

    def summarize_youth_players_native(self, payload):
        if self.native is not None:
            return self.native.summarize_youth_players(payload)
        return None

    def get_transfer_window_status_native(self, payload):
        if self.native is not None:
            return self.native.get_transfer_window_status(payload)
        return None

    def evaluate_contract_offer_native(self, payload):
        if self.native is not None:
            return self.native.evaluate_contract_offer(payload)
        return None

    def create_new_game(self, club_name, short_name, country, stadium_name, manager_name="Manager"):
        return py_engine.create_new_game(club_name, short_name, country, stadium_name, manager_name)

    def load_game(self):
        return save_system.load_game()

    def save_game(self, game_state):
        return save_system.save_game(game_state)

    def autosave_game(self, game_state):
        return save_system.autosave_game(game_state)

    def __getattr__(self, item):
        if hasattr(py_engine, item):
            return getattr(py_engine, item)
        raise AttributeError(f"EngineBridge has no attribute {item}")


bridge = EngineBridge()
