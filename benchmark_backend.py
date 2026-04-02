import time

import engine_bridge
import game_engine
import match_engine as py_match_engine

state = engine_bridge.bridge.create_new_game("Bench FC", "BFC", "England", "Bench Park", manager_name="Bench Manager")
club = state.clubs[state.player_club_id]
club.auto_select_squad()
opp = next(c for cid, c in state.clubs.items() if cid != state.player_club_id and c.league_tier == club.league_tier)
opp.auto_select_squad()

start = time.perf_counter()
for _ in range(200):
    py_match_engine.simulate_match(club, opp)
end = time.perf_counter()
py_match_time = end - start

fallbacks = 0
native_successes = 0
errors = 0
error_samples = []
start = time.perf_counter()
for _ in range(200):
    engine_bridge.bridge.simulate_match(club, opp)
    used_native = bool(engine_bridge.bridge.last_match_used_native)
    used_fallback = bool(engine_bridge.bridge.last_match_fallback_used)
    err = engine_bridge.bridge.last_native_match_error or ""
    if used_native:
        native_successes += 1
    if used_fallback:
        fallbacks += 1
    if err:
        errors += 1
        if len(error_samples) < 5:
            error_samples.append(err)
end = time.perf_counter()
bridge_match_time = end - start

week_state_native = engine_bridge.bridge.create_new_game("Week Native", "WN", "England", "Week Park", manager_name="Week Native")
week_fixtures_native = [f for f in game_engine.get_week_fixtures(week_state_native, week_state_native.league.current_week) if not f.played]
start = time.perf_counter()
week_native = engine_bridge.bridge.simulate_week_native(week_fixtures_native, week_state_native.clubs)
end = time.perf_counter()
week_native_time = end - start

week_state_python = engine_bridge.bridge.create_new_game("Week Python", "WP", "England", "Week Park", manager_name="Week Python")
week_fixtures_python = [f for f in game_engine.get_week_fixtures(week_state_python, week_state_python.league.current_week) if not f.played]
start = time.perf_counter()
week_python_count = 0
for fixture in week_fixtures_python:
    home = week_state_python.clubs[fixture.home_id]
    away = week_state_python.clubs[fixture.away_id]
    py_match_engine.simulate_match(home, away)
    week_python_count += 1
end = time.perf_counter()
week_python_time = end - start

status = engine_bridge.bridge.get_status()
print("ACTIVE_BACKEND_MODE", status.mode)
print("ACTIVE_BACKEND_NATIVE", status.native_available)
print("ACTIVE_NATIVE_MATCH_ENABLED", status.native_match_enabled)
print("ACTIVE_NATIVE_WEEK_ENABLED", status.native_week_enabled)
print("PYTHON_MATCH_SIM_200", round(py_match_time, 6))
print("BRIDGE_MATCH_SIM_200", round(bridge_match_time, 6))
print("NATIVE_MATCH_SUCCESSES", native_successes)
print("NATIVE_MATCH_FALLBACKS", fallbacks)
print("NATIVE_MATCH_ERRORS", errors)
print("NATIVE_MATCH_ERROR_SAMPLES", error_samples)
print("PYTHON_WEEK_FIXTURES", week_python_count)
print("PYTHON_WEEK_SIM", round(week_python_time, 6))
print("NATIVE_WEEK_RESULTS", len(week_native.get("results", [])) if week_native else 0)
print("NATIVE_WEEK_TABLE", len(week_native.get("table", [])) if week_native else 0)
print("NATIVE_WEEK_SIM", round(week_native_time, 6))
print("NATIVE_WEEK_FALLBACK", engine_bridge.bridge.last_week_fallback_used)
print("NATIVE_WEEK_ERROR", engine_bridge.bridge.last_native_week_error)
