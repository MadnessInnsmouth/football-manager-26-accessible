from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
DLLS = [
    BACKEND / "build" / "fm_backend.dll",
    BACKEND / "build" / "Release" / "fm_backend.dll",
    BACKEND / "build" / "Debug" / "fm_backend.dll",
]
BUILD_MARKERS = [
    BACKEND / "build" / "CMakeCache.txt",
    BACKEND / "build" / "build.ninja",
    BACKEND / "build" / "Release" / "fm_backend.dll",
    BACKEND / "build" / "fm_backend.dll",
]

print("DLL_EXISTS", any(p.exists() for p in DLLS))
print("BUILD_ARTIFACTS_PRESENT", any(p.exists() for p in BUILD_MARKERS))
print("ABSOLUTE_CMAKE_EXISTS", Path(r"C:\Program Files\CMake\bin\cmake.exe").exists())

import engine_bridge

status = engine_bridge.bridge.get_status()
print("BRIDGE_MODE", status.mode)
print("NATIVE_ACTIVE", status.native_available)
print("NATIVE_MATCH_ENABLED", status.native_match_enabled)
print("NATIVE_MATCH_PROBE_OK", status.native_match_probe_ok)
print("NATIVE_WEEK_ENABLED", status.native_week_enabled)
print("NATIVE_WEEK_PROBE_OK", status.native_week_probe_ok)
print("LAST_NATIVE_MATCH_ERROR", bool(status.last_native_match_error), status.last_native_match_error)
print("LAST_NATIVE_WEEK_ERROR", bool(status.last_native_week_error), status.last_native_week_error)

state = engine_bridge.bridge.create_new_game("Parity FC", "PFC", "England", "Parity Park", manager_name="Parity Manager")
club = state.clubs[state.player_club_id]
club.auto_select_squad()
opp = next(c for cid, c in state.clubs.items() if cid != state.player_club_id and c.league_tier == club.league_tier)
opp.auto_select_squad()

result = engine_bridge.bridge.simulate_match(club, opp)
print("MATCH_RESULT_VALID", bool(result and hasattr(result, "home_goals") and hasattr(result, "away_goals") and isinstance(result.events, list)))
print("MATCH_EVENTS_COUNT", len(result.events) if result else 0)
print("FULL_TIME_EVENTS", sum(1 for e in (result.events if result else []) if getattr(e.event_type, "name", "") == "FULL_TIME"))
print("NATIVE_MATCH_FALLBACK_OCCURRED", engine_bridge.bridge.last_match_fallback_used)
print("NATIVE_MATCH_PATH_SUCCESS", engine_bridge.bridge.last_match_used_native)

fixtures = [f for f in engine_bridge.bridge.get_week_fixtures(state, state.league.current_week) if not f.played]
week_data = engine_bridge.bridge.simulate_week_native(fixtures, state.clubs)
print("NATIVE_WEEK_RESULT_PRESENT", week_data is not None)
print("NATIVE_WEEK_FALLBACK_OCCURRED", engine_bridge.bridge.last_week_fallback_used)
print("NATIVE_WEEK_PATH_SUCCESS", engine_bridge.bridge.last_week_used_native)
print("NATIVE_WEEK_RESULTS_COUNT", len(week_data.get("results", [])) if week_data else 0)
print("NATIVE_WEEK_TABLE_COUNT", len(week_data.get("table", [])) if week_data else 0)

roster = []
id_map = {}
for idx, p in enumerate(club.players, 1):
    roster.append({"id": idx, "source_id": p.id, "name": p.full_name, "position": p.position.value, "available": bool(p.is_available)})
    id_map[p.id] = idx
selected_ids = [id_map[p.id] for p in club.players if p.id in club.selected_squad_ids][:11]

native_squad = engine_bridge.bridge.validate_selected_xi_native(selected_ids, roster)
print("NATIVE_SQUAD_RESULT_PRESENT", native_squad is not None)

preview = engine_bridge.bridge.preview_stadium_upgrade_native({
    "current_capacity": club.stadium_capacity,
    "target_capacity": max(club.stadium_capacity + 1000, 4000),
    "seating_level": club.infrastructure.stadium.seating_level,
    "budget": club.budget,
    "league_tier": club.league_tier,
})
print("NATIVE_STADIUM_RESULT_PRESENT", preview is not None)

window = engine_bridge.bridge.get_transfer_window_status_native({"country": state.country, "current_date": state.current_date})
print("NATIVE_TRANSFER_RESULT_PRESENT", window is not None)

records_payload = {
    "highest_league_finish": club.records.highest_league_finish,
    "most_points": club.records.most_points,
    "most_goals_scored": club.records.most_goals_scored,
    "best_goal_difference": club.records.best_goal_difference,
    "biggest_win": club.records.biggest_win,
    "biggest_defeat": club.records.biggest_defeat,
    "highest_scoring_match": club.records.highest_scoring_match,
    "all_time_top_scorer": club.records.all_time_top_scorer,
    "all_time_top_scorer_goals": club.records.all_time_top_scorer_goals,
    "most_appearances_player": club.records.most_appearances_player,
    "most_appearances": club.records.most_appearances,
}
records = engine_bridge.bridge.summarize_club_records_native(records_payload)
print("NATIVE_RECORDS_RESULT_PRESENT", records is not None)

youth = engine_bridge.bridge.summarize_youth_players_native({
    "players": [
        {
            "name": p.full_name,
            "position": p.position.value,
            "age": p.age,
            "overall": p.overall,
            "potential": p.potential,
            "desired_wage": p.desired_wage,
        }
        for p in club.youth_team
    ]
})
print("NATIVE_YOUTH_RESULT_PRESENT", youth is not None)

ui_text = (ROOT / "ui.py").read_text(encoding="utf-8")
print("UI_HAS_NATIVE_SUMMARY_HOOKS", "_native_records_summary" in ui_text and "_native_youth_summary" in ui_text and "_native_stadium_preview" in ui_text)
