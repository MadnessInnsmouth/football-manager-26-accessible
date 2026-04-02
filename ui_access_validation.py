from services.game_service import service as game_engine
import save_system
import ui


def main():
    state = game_engine.create_new_game("Validation FC", "VFC", "England", "Validation Park")
    club = state.clubs[state.player_club_id]

    transfer_items = game_engine.get_transfer_market_players(state, position_filter="All", search_text="")
    listing, player, seller = transfer_items[0]
    profile = game_engine.get_player_market_profile(state, listing, player, seller)

    quick_home = ui.FootballManagerApp._build_quick_match_club

    print("TRANSFER_PROFILE_NAME", bool(profile.get("name")))
    print("TRANSFER_PROFILE_AGE", profile.get("age", -1) > 0)
    print("TRANSFER_PROFILE_POSITION", bool(profile.get("position")))
    print("TRANSFER_PROFILE_RATING", 1 <= profile.get("rating", 0) <= 99)
    print("TRANSFER_PROFILE_CURRENT_CLUB", bool(profile.get("current_club")))
    print("TRANSFER_PROFILE_FACTS", len(profile.get("facts", [])) > 0)
    print("CLUB_FINANCE_BUDGET", club.budget > 0)
    print("CLUB_TRANSFER_BUDGET", club.transfer_budget >= 0)

    original_limit = club.transfer_budget
    club.transfer_budget = min(club.budget, max(0, club.transfer_budget // 2))
    print("FINANCE_LIMIT_SET", club.transfer_budget <= original_limit)

    save_system.save_game(state)
    loaded = save_system.load_game()
    print("SAVE_LOAD_OK", loaded is not None)
    if loaded:
        loaded_club = loaded.clubs[loaded.player_club_id]
        print("SAVE_LOAD_TRANSFER_BUDGET", loaded_club.transfer_budget == club.transfer_budget)
        print("SAVE_LOAD_BUDGET", loaded_club.budget == club.budget)

    home = quick_home(None, "Home Test", "England", home=True)
    away = quick_home(None, "Away Test", "England", home=False)
    result = game_engine.simulate_match(home, away)
    print("QUICK_MP_RESULT", result is not None)
    print("QUICK_MP_EVENTS", len(result.events) > 0)
    print("FULL_TIME_ONE", sum(1 for e in result.events if e.event_type.value == 'Full Time') == 1)

    print("UI_HAS_SETTINGS_SCREEN", hasattr(ui.FootballManagerApp, 'show_settings_placeholder'))
    print("UI_HAS_FINANCE_SCREEN", hasattr(ui.FootballManagerApp, 'show_finance_screen'))
    print("UI_HAS_QUICK_MP", hasattr(ui.FootballManagerApp, 'show_quick_multiplayer'))


if __name__ == "__main__":
    main()
