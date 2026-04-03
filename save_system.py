"""Local save/load system for Football Manager 26."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from models import (
    Club, ClubRecordBook, Competition, CompetitionType, EventType, Fixture, FinanceRecord,
    Formation, GameState, InboxMessage, IncomingTransferOffer, Infrastructure, LeagueSeason,
    LeagueTier, MatchEvent, MatchResult, Mentality, MessageType, PlayStyle, Player,
    Position, Stadium, Tactic, TrainingFacility, TransferListing, Trophy, TrophyType,
    YouthAcademy,
)


def _get_save_dir() -> str:
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return os.path.join(local_appdata, "FootballManager26")
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return os.path.join(xdg, "football_manager_26")
    return str(Path.home() / ".football_manager_26")


SAVE_DIR = _get_save_dir()
SAVE_FILE = os.path.join(SAVE_DIR, "savegame.json")
BACKUP_FILE = os.path.join(SAVE_DIR, "savegame_backup.json")

_ENUM_TYPES = {
    "Position": Position,
    "Formation": Formation,
    "Mentality": Mentality,
    "PlayStyle": PlayStyle,
    "EventType": EventType,
    "TrophyType": TrophyType,
    "CompetitionType": CompetitionType,
    "MessageType": MessageType,
}

_DATACLASS_TYPES = {
    "Player": Player,
    "Tactic": Tactic,
    "Stadium": Stadium,
    "TrainingFacility": TrainingFacility,
    "YouthAcademy": YouthAcademy,
    "Infrastructure": Infrastructure,
    "Club": Club,
    "ClubRecordBook": ClubRecordBook,
    "MatchEvent": MatchEvent,
    "MatchResult": MatchResult,
    "Fixture": Fixture,
    "LeagueSeason": LeagueSeason,
    "FinanceRecord": FinanceRecord,
    "TransferListing": TransferListing,
    "IncomingTransferOffer": IncomingTransferOffer,
    "InboxMessage": InboxMessage,
    "Trophy": Trophy,
    "Competition": Competition,
    "LeagueTier": LeagueTier,
    "GameState": GameState,
}


def get_save_path() -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return SAVE_FILE


def _serialize(obj: Any):
    if is_dataclass(obj):
        payload = {field.name: _serialize(getattr(obj, field.name)) for field in fields(obj)}
        payload["__type__"] = obj.__class__.__name__
        return payload
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    enum_cls_name = obj.__class__.__name__ if hasattr(obj, "__class__") else ""
    if enum_cls_name in _ENUM_TYPES:
        return {"__enum__": enum_cls_name, "value": obj.name}
    return obj


def _deserialize(obj: Any):
    if isinstance(obj, list):
        return [_deserialize(v) for v in obj]
    if isinstance(obj, dict):
        if "__enum__" in obj:
            return _ENUM_TYPES[obj["__enum__"]][obj["value"]]
        if "__type__" in obj:
            cls = _DATACLASS_TYPES[obj["__type__"]]
            values = {k: _deserialize(v) for k, v in obj.items() if k != "__type__"}
            return _construct_dataclass(cls, values)
        return {k: _deserialize(v) for k, v in obj.items()}
    return obj


def _construct_dataclass(cls, values: dict):
    if cls is Player:
        return Player(**values)
    if cls is Club:
        club = Club(**values)
        if club.players is None:
            club.players = []
        if club.youth_team is None:
            club.youth_team = []
        if club.records is None:
            club.records = ClubRecordBook()
        return club
    if cls is GameState:
        return GameState(**values).ensure_defaults()
    return cls(**values)


def _apply_backward_compatibility(data):
    if isinstance(data, GameState):
        return data.ensure_defaults()
    if not isinstance(data, dict):
        return None
    clubs = {cid: _club_from_legacy(cdata) for cid, cdata in data.get("clubs", {}).items()}
    league_data = data.get("league")
    league = None
    if league_data:
        league = LeagueSeason(name=league_data.get("name", "League"), country=league_data.get("country", "England"), tier=league_data.get("tier", 5), club_ids=league_data.get("club_ids", []), fixtures=[_fixture_from_legacy(fx) for fx in league_data.get("fixtures", [])], current_week=league_data.get("current_week", 1), total_weeks=league_data.get("total_weeks", 38))
    state = GameState(
        player_club_id=data.get("player_club_id", ""),
        clubs=clubs,
        league=league,
        season_number=data.get("season_number", 1),
        transfer_list=[TransferListing(**t) for t in data.get("transfer_list", [])],
        finance_history=[FinanceRecord(**r) for r in data.get("finance_history", [])],
        season_over=data.get("season_over", False),
        trophies=[_trophy_from_legacy(t) for t in data.get("trophies", [])],
        youth_players=[_player_from_legacy(p) for p in data.get("youth_players", [])],
        competitions=[_competition_from_legacy(c) for c in data.get("competitions", [])],
        league_system=[_league_tier_from_legacy(t) for t in data.get("league_system", [])],
        continental_qualification=data.get("continental_qualification", {}),
        pending_messages=data.get("pending_messages", []),
        current_date=data.get("current_date", "2026-07-01"),
        country=data.get("country", league.country if league else "England"),
        inbox=[_inbox_message_from_legacy(m) for m in data.get("inbox", [])],
        incoming_transfer_offers=[_incoming_offer_from_legacy(o) for o in data.get("incoming_transfer_offers", [])],
    )
    return state.ensure_defaults()


def _player_from_legacy(data):
    return Player(
        id=data["id"], first_name=data["first_name"], last_name=data["last_name"], age=data["age"], nationality=data["nationality"],
        position=Position[data.get("position", "MID")], goalkeeping=data.get("goalkeeping", 1), defending=data.get("defending", 1),
        passing=data.get("passing", 1), shooting=data.get("shooting", 1), pace=data.get("pace", 1), physical=data.get("physical", 1),
        morale=data.get("morale", 14), fitness=data.get("fitness", 100), goals=data.get("goals", 0), assists=data.get("assists", 0),
        yellow_cards=data.get("yellow_cards", 0), red_cards=data.get("red_cards", 0), appearances=data.get("appearances", 0),
        career_goals=data.get("career_goals", data.get("goals", 0)), career_appearances=data.get("career_appearances", data.get("appearances", 0)),
        injured_weeks=data.get("injured_weeks", 0), suspended_matches=data.get("suspended_matches", 0), value=data.get("value", 0), wage=data.get("wage", 0),
        contract_years=data.get("contract_years", 2), season_joined=data.get("season_joined", 1), is_youth=data.get("is_youth", False),
        potential=data.get("potential", max(50, data.get("shooting", 1) * 4)), squad_role_expectation=data.get("squad_role_expectation", "Rotation"),
        minimum_acceptable_wage=data.get("minimum_acceptable_wage", 0), desired_wage=data.get("desired_wage", 0), desired_contract_length=data.get("desired_contract_length", 2),
        willingness_to_join=data.get("willingness_to_join", 50), shortlisted=data.get("shortlisted", False), scouted=data.get("scouted", False),
        scouting_notes=data.get("scouting_notes", ""), transfer_listed=data.get("transfer_listed", False), asking_price_override=data.get("asking_price_override", 0),
    )


def _tactic_from_legacy(data):
    return Tactic(formation=Formation[data.get("formation", "F442")], mentality=Mentality[data.get("mentality", "BALANCED")], style=PlayStyle[data.get("style", "DIRECT")])


def _records_from_legacy(data):
    if not data:
        return ClubRecordBook()
    return ClubRecordBook(
        highest_league_finish=data.get("highest_league_finish", 999), most_points=data.get("most_points", 0), most_goals_scored=data.get("most_goals_scored", 0), best_goal_difference=data.get("best_goal_difference", -999),
        biggest_win=data.get("biggest_win", "None"), biggest_defeat=data.get("biggest_defeat", "None"), highest_scoring_match=data.get("highest_scoring_match", "None"), longest_winning_streak=data.get("longest_winning_streak", 0),
        longest_unbeaten_streak=data.get("longest_unbeaten_streak", 0), all_time_top_scorer=data.get("all_time_top_scorer", "None"), all_time_top_scorer_goals=data.get("all_time_top_scorer_goals", 0),
        most_appearances_player=data.get("most_appearances_player", "None"), most_appearances=data.get("most_appearances", 0), current_winning_streak=data.get("current_winning_streak", 0), current_unbeaten_streak=data.get("current_unbeaten_streak", 0),
    )


def _infrastructure_from_legacy(data):
    if not data:
        return Infrastructure()
    if "stadium" in data:
        stadium_data = data.get("stadium", {})
        training_data = data.get("training", {})
        youth_data = data.get("youth", {})
        return Infrastructure(
            stadium=Stadium(seating_level=stadium_data.get("seating_level", 1), pitch_quality=stadium_data.get("pitch_quality", 3), facilities_level=stadium_data.get("facilities_level", 3), club_shop_level=stadium_data.get("club_shop_level", 0), cafe_level=stadium_data.get("cafe_level", 0), hospitality_level=stadium_data.get("hospitality_level", 0), parking_level=stadium_data.get("parking_level", 1), fan_zone_level=stadium_data.get("fan_zone_level", 0)),
            training=TrainingFacility(level=training_data.get("level", 3), intensity=training_data.get("intensity", 3), medical_level=training_data.get("medical_level", 3), training_ground_level=training_data.get("training_ground_level", 3), sports_science_level=training_data.get("sports_science_level", 2)),
            youth=YouthAcademy(level=youth_data.get("level", 3), recruitment_level=youth_data.get("recruitment_level", 3), scouting_level=youth_data.get("scouting_level", 3)),
        )
    return Infrastructure()


def _club_from_legacy(data):
    club = Club(
        id=data["id"], name=data["name"], short_name=data["short_name"], country=data["country"], league_tier=data["league_tier"], reputation=data.get("reputation", 20),
        budget=data.get("budget", 0), wage_budget_weekly=data.get("wage_budget_weekly", 0), stadium_name=data.get("stadium_name", "Stadium"), stadium_capacity=data.get("stadium_capacity", 3000),
        tactic=_tactic_from_legacy(data.get("tactic", {})), infrastructure=_infrastructure_from_legacy(data.get("infrastructure", {})), is_player_club=data.get("is_player_club", False), wins=data.get("wins", 0),
        draws=data.get("draws", 0), losses=data.get("losses", 0), goals_for=data.get("goals_for", 0), goals_against=data.get("goals_against", 0), sponsor_income_weekly=data.get("sponsor_income_weekly", 0),
        ticket_price=data.get("ticket_price", 10), debt=data.get("debt", 0), max_debt=data.get("max_debt", 100000), transfer_budget=data.get("transfer_budget", 0),
        balance=data.get("balance", data.get("budget", 0)), weekly_wage_commitment=data.get("weekly_wage_commitment", 0), manager_name=data.get("manager_name", "Manager"),
        records=_records_from_legacy(data.get("records", {})), selected_squad_ids=data.get("selected_squad_ids", []), shortlist_player_ids=data.get("shortlist_player_ids", []),
        transfer_spending_limit=data.get("transfer_spending_limit", data.get("transfer_budget", 0)), sold_players_income_season=data.get("sold_players_income_season", 0), bought_players_spend_season=data.get("bought_players_spend_season", 0),
    )
    club.players = [_player_from_legacy(p) for p in data.get("players", [])]
    club.youth_team = [_player_from_legacy(p) for p in data.get("youth_team", [])]
    return club


def _match_event_from_legacy(data):
    return MatchEvent(minute=data.get("minute", 0), event_type=EventType[data.get("event_type", "KICK_OFF")], team_name=data.get("team_name", ""), player_name=data.get("player_name", ""), assist_name=data.get("assist_name", ""), commentary=data.get("commentary", ""))


def _match_result_from_legacy(data):
    return MatchResult(home_team=data.get("home_team", ""), away_team=data.get("away_team", ""), home_goals=data.get("home_goals", 0), away_goals=data.get("away_goals", 0), events=[_match_event_from_legacy(e) for e in data.get("events", [])], home_shots=data.get("home_shots", 0), away_shots=data.get("away_shots", 0), home_on_target=data.get("home_on_target", 0), away_on_target=data.get("away_on_target", 0), home_corners=data.get("home_corners", 0), away_corners=data.get("away_corners", 0), home_fouls=data.get("home_fouls", 0), away_fouls=data.get("away_fouls", 0), home_yellows=data.get("home_yellows", 0), away_yellows=data.get("away_yellows", 0), home_reds=data.get("home_reds", 0), away_reds=data.get("away_reds", 0), attendance=data.get("attendance", 0))


def _fixture_from_legacy(data):
    return Fixture(home_id=data.get("home_id", ""), away_id=data.get("away_id", ""), week=data.get("week", 1), competition_id=data.get("competition_id", "league_main"), stage=data.get("stage", "League"), played=data.get("played", False), result=_match_result_from_legacy(data["result"]) if data.get("result") else None)


def _competition_from_legacy(data):
    ctype = data.get("competition_type", "LEAGUE")
    if ctype in CompetitionType.__members__:
        enum_type = CompetitionType[ctype]
    else:
        try:
            enum_type = CompetitionType(ctype)
        except Exception:
            enum_type = CompetitionType.LEAGUE
    return Competition(
        id=data.get("id", "comp"), name=data.get("name", "Competition"), competition_type=enum_type, country=data.get("country", "England"), level=data.get("level", "domestic"), tier=data.get("tier", 1),
        club_ids=data.get("club_ids", []), fixtures=[_fixture_from_legacy(f) for f in data.get("fixtures", [])], current_round=data.get("current_round", ""), active=data.get("active", True), winner_club_id=data.get("winner_club_id", ""),
        runner_up_club_id=data.get("runner_up_club_id", ""), qualification_places=data.get("qualification_places", 0), rounds=data.get("rounds", []), qualified_club_ids=data.get("qualified_club_ids", []),
        entry_rules=data.get("entry_rules", {}), slot_rules=data.get("slot_rules", {}), scheduled_weeks=data.get("scheduled_weeks", []), draw_state=data.get("draw_state", {}), draw_rules=data.get("draw_rules", {}),
    )


def _league_tier_from_legacy(data):
    return LeagueTier(country=data.get("country", "England"), name=data.get("name", "League"), tier=data.get("tier", 5), club_ids=data.get("club_ids", []), promotion_places=data.get("promotion_places", 0), playoff_places=data.get("playoff_places", []), relegation_places=data.get("relegation_places", 0))


def _inbox_message_from_legacy(data):
    msg_type = data.get("message_type", "SYSTEM")
    if isinstance(msg_type, str):
        msg_type = MessageType[msg_type] if msg_type in MessageType.__members__ else MessageType.SYSTEM
    return InboxMessage(id=data.get("id", "msg"), week=data.get("week", 1), season=data.get("season", 1), subject=data.get("subject", "Message"), body=data.get("body", ""), message_type=msg_type, read=data.get("read", False), related_player_id=data.get("related_player_id", ""), related_club_id=data.get("related_club_id", ""), action_required=data.get("action_required", False), metadata=data.get("metadata", {}))


def _incoming_offer_from_legacy(data):
    return IncomingTransferOffer(id=data.get("id", "offer"), player_id=data.get("player_id", ""), buyer_club_id=data.get("buyer_club_id", ""), seller_club_id=data.get("seller_club_id", ""), fee=data.get("fee", 0), week_created=data.get("week_created", 1), status=data.get("status", "pending"))


def _trophy_from_legacy(data):
    ttype = data.get("trophy_type", "LEAGUE_CHAMPION")
    if isinstance(ttype, str):
        if ttype in TrophyType.__members__:
            trophy_type = TrophyType[ttype]
        else:
            try:
                trophy_type = TrophyType(ttype)
            except Exception:
                trophy_type = TrophyType.LEAGUE_CHAMPION
    else:
        trophy_type = TrophyType.LEAGUE_CHAMPION
    return Trophy(trophy_type=trophy_type, season=data.get("season", 1), league_name=data.get("league_name", "League"), tier=data.get("tier", 1), competition_id=data.get("competition_id", ""), country=data.get("country", ""), metadata=data.get("metadata", {}))


def load_game():
    path = get_save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return None
    try:
        loaded = _deserialize(raw)
        if isinstance(loaded, GameState):
            return loaded.ensure_defaults()
        return _apply_backward_compatibility(raw)
    except Exception:
        return None


def save_game(game_state: GameState):
    path = get_save_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = _serialize(game_state)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as src, open(BACKUP_FILE, "w", encoding="utf-8") as bak:
                bak.write(src.read())
        except Exception:
            pass
    fd, temp_path = tempfile.mkstemp(prefix="fm26_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def autosave_game(game_state: GameState):
    save_game(game_state)


def serialize_to_json_string(game_state: GameState) -> str:
    """Serialize a GameState to a JSON string suitable for cloud save upload."""
    return json.dumps(_serialize(game_state))


def deserialize_from_json_string(json_string: str):
    """Deserialize a JSON string from a cloud save download into a GameState."""
    try:
        raw = json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return None
    try:
        loaded = _deserialize(raw)
        if isinstance(loaded, GameState):
            return loaded.ensure_defaults()
        return _apply_backward_compatibility(raw)
    except Exception:
        return None
