import game_engine
state = game_engine.create_new_game("Audio FC", "AFC", "England", "Sound Park")
results = game_engine.play_week(state)
club = state.clubs[state.player_club_id]
player_result = next((r for r in results if r.home_team == club.name or r.away_team == club.name), None)
print("RESULT_FOUND", player_result is not None)
if player_result:
    print("EVENTS", len(player_result.events))
    print("FULL_TIME_EVENTS", sum(1 for e in player_result.events if e.event_type.name == 'FULL_TIME'))
    print("GOAL_EVENTS", sum(1 for e in player_result.events if e.event_type.name in ('GOAL','PENALTY_SCORED')))
