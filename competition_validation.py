import game_engine
import save_system


def main():
    state = game_engine.create_new_game("Validation FC", "VFC", "England", "Validation Park")
    comp_ids = {c.id for c in state.competitions}
    print("HAS_FA_CUP", "fa_cup" in comp_ids)
    print("HAS_EFL_CUP", "efl_cup" in comp_ids)
    print("HAS_EFL_TROPHY", "efl_trophy" in comp_ids)
    print("HAS_UCL", "uefa_champions_league" in comp_ids)
    print("HAS_UEL", "uefa_europa_league" in comp_ids)
    print("HAS_UECL", "uefa_conference_league" in comp_ids)
    print("HAS_USC", "uefa_super_cup" in comp_ids)

    draws_ok = all(bool(c.draw_state.get("rounds", [])) for c in state.competitions if c.competition_type != c.competition_type.LEAGUE)
    print("DRAWS_OK", draws_ok)

    q = state.continental_qualification
    print("QUAL_COUNTRIES", sorted(q.keys()))
    overflow_ok = True
    for country, slots in q.items():
        seen = set()
        for slot_name, ids in slots.items():
            for cid in ids:
                if cid in seen:
                    overflow_ok = False
                seen.add(cid)
    print("QUAL_OVERFLOW_OK", overflow_ok)

    european_pool_ok = any(c.country in ("Germany", "Italy") for c in game_engine.build_european_competition_pool(state).values())
    print("EURO_POOL_OK", european_pool_ok)

    player_fixture_count = len(game_engine.get_player_fixtures(state, 1))
    print("PLAYER_FIXTURES_WEEK1", player_fixture_count)

    playable_comp_names = [c.name for c in game_engine.get_playable_competitions_for_club(state)]
    print("PLAYABLE_COMP_COUNT", len(playable_comp_names))

    path = save_system.get_save_path()
    save_system.save_game(state)
    loaded = save_system.load_game()
    print("SAVE_LOAD_OK", loaded is not None)
    if loaded:
        print("SAVE_LOAD_COMP_COUNT", len(loaded.competitions))
        print("SAVE_LOAD_DRAW_STATE", bool(next((c.draw_state for c in loaded.competitions if c.id == "fa_cup"), {})))


if __name__ == "__main__":
    main()
