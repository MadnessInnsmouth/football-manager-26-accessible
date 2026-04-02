from services.game_service import service

for country in ["England", "Spain", "France"]:
    state = service.create_new_game(f"Test {country}", country[:3].upper(), country, f"{country} Ground")
    print("COUNTRY", country)
    print("CLUBS", len(state.clubs))
    print("LEAGUE", state.league.name, state.league.tier)
    print("FIXTURES", len(state.league.fixtures))
    print("TRANSFER_LIST", len(state.transfer_list))
    player_club = state.clubs[state.player_club_id]
    print("PLAYER_SQUAD", len(player_club.players), len(player_club.youth_team))
    player_fixtures = service.get_player_fixtures(state)
    print("PLAYER_FIXTURES_WEEK1", len(player_fixtures))
    results = service.play_week(state)
    print("PLAY_WEEK_RESULTS", len(results))
    print("DATE_AFTER", state.current_date)
    print("CURRENT_WEEK", state.league.current_week)
    print("TABLE_SIZE", len(service.get_league_table(state)))
    print("WINDOW", service.get_transfer_window_status(state)["open"])
