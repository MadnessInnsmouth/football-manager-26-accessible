"""Core backend game engine for Football Manager 26.
This module owns game rules, season flow, finances, transfers, infrastructure,
and league/cup progression. The UI should only call into this via a service.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import List, Dict, Tuple
from uuid import uuid4

from models import (
    Club,
    Competition,
    CompetitionType,
    EventType,
    FinanceRecord,
    Fixture,
    GameState,
    InboxMessage,
    IncomingTransferOffer,
    LeagueSeason,
    LeagueTier,
    MatchEvent,
    MatchResult,
    MessageType,
    Player,
    Position,
    TransferListing,
    Trophy,
    TrophyType,
)
from database import LEAGUE_DATA, create_player_club, generate_player, setup_league_system
from match_engine import simulate_match

ROLE_VALUES = {"Prospect": 35, "Rotation": 50, "Starter": 68, "Key Player": 82}
TRANSFER_WINDOWS = {
    "England": [{"name": "Summer Window", "start": (6, 14), "end": (8, 30)}, {"name": "Winter Window", "start": (1, 1), "end": (1, 31)}],
    "Spain": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 2), "end": (1, 31)}],
    "France": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 1), "end": (1, 31)}],
    "Germany": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 1), "end": (1, 31)}],
    "Italy": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 2), "end": (1, 31)}],
}

COUNTRY_EUROPEAN_SLOTS = {
    "England": {"champions_league": 4, "europa_league": 2, "conference_league": 1},
    "Spain": {"champions_league": 4, "europa_league": 2, "conference_league": 1},
    "France": {"champions_league": 3, "europa_league": 2, "conference_league": 1},
    "Germany": {"champions_league": 4, "europa_league": 2, "conference_league": 1},
    "Italy": {"champions_league": 4, "europa_league": 2, "conference_league": 1},
}

DOMESTIC_CUP_DEFINITIONS = {
    "England": [
        {"id": "fa_cup", "name": "FA Cup", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.DOMESTIC_CUP, "weeks": [6, 10, 14, 18, 22], "max_entrants": 32, "entry_rules": {"all_playable": True}},
        {"id": "efl_cup", "name": "EFL Cup", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.LEAGUE_CUP, "weeks": [4, 8, 12, 16], "max_entrants": 16, "entry_rules": {"max_tier": 4}},
        {"id": "efl_trophy", "name": "EFL Trophy", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.LEAGUE_CUP, "weeks": [5, 9, 13, 17], "max_entrants": 16, "entry_rules": {"min_tier": 3, "max_tier": 4}},
    ],
    "Spain": [
        {"id": "copa_del_rey", "name": "Copa del Rey", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.DOMESTIC_CUP, "weeks": [6, 10, 14, 18, 22], "max_entrants": 32, "entry_rules": {"all_playable": True}},
        {"id": "supercopa_espana", "name": "Supercopa de España", "competition_type": CompetitionType.SUPER_CUP, "trophy": TrophyType.SUPER_CUP, "weeks": [24, 25], "max_entrants": 4, "entry_rules": {"top_n": 4}},
    ],
    "France": [
        {"id": "coupe_de_france", "name": "Coupe de France", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.DOMESTIC_CUP, "weeks": [6, 10, 14, 18, 22], "max_entrants": 32, "entry_rules": {"all_playable": True}},
        {"id": "trophee_des_champions", "name": "Trophée des Champions", "competition_type": CompetitionType.SUPER_CUP, "trophy": TrophyType.SUPER_CUP, "weeks": [3], "max_entrants": 2, "entry_rules": {"top_n": 2}},
    ],
    "Germany": [
        {"id": "dfb_pokal", "name": "DFB-Pokal", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.DOMESTIC_CUP, "weeks": [6, 10, 14, 18, 22], "max_entrants": 32, "entry_rules": {"all_playable": True}},
        {"id": "dfl_supercup", "name": "DFL-Supercup", "competition_type": CompetitionType.SUPER_CUP, "trophy": TrophyType.SUPER_CUP, "weeks": [3], "max_entrants": 2, "entry_rules": {"top_n": 2}},
    ],
    "Italy": [
        {"id": "coppa_italia", "name": "Coppa Italia", "competition_type": CompetitionType.DOMESTIC_CUP, "trophy": TrophyType.DOMESTIC_CUP, "weeks": [6, 10, 14, 18, 22], "max_entrants": 32, "entry_rules": {"all_playable": True}},
        {"id": "supercoppa_italiana", "name": "Supercoppa Italiana", "competition_type": CompetitionType.SUPER_CUP, "trophy": TrophyType.SUPER_CUP, "weeks": [3], "max_entrants": 2, "entry_rules": {"top_n": 2}},
    ],
}

UEFA_COMPETITION_DEFINITIONS = [
    {"id": "uefa_champions_league", "name": "UEFA Champions League", "competition_type": CompetitionType.CONTINENTAL_CUP, "trophy": TrophyType.CHAMPIONS_LEAGUE, "weeks": [7, 11, 15, 19], "slot_key": "champions_league", "max_entrants": 16, "rounds": ["Round of 16", "Quarter Final", "Semi Final", "Final"]},
    {"id": "uefa_europa_league", "name": "UEFA Europa League", "competition_type": CompetitionType.CONTINENTAL_CUP, "trophy": TrophyType.EUROPA_LEAGUE, "weeks": [8, 12, 16, 20], "slot_key": "europa_league", "max_entrants": 16, "rounds": ["Round of 16", "Quarter Final", "Semi Final", "Final"]},
    {"id": "uefa_conference_league", "name": "UEFA Conference League", "competition_type": CompetitionType.CONTINENTAL_CUP, "trophy": TrophyType.CONFERENCE_LEAGUE, "weeks": [9, 13, 17, 21], "slot_key": "conference_league", "max_entrants": 16, "rounds": ["Round of 16", "Quarter Final", "Semi Final", "Final"]},
    {"id": "uefa_super_cup", "name": "UEFA Super Cup", "competition_type": CompetitionType.SUPER_CUP, "trophy": TrophyType.SUPER_CUP, "weeks": [23], "slot_key": "super_cup", "max_entrants": 2, "rounds": ["Final"]},
]


# Core lifecycle

def create_new_game(club_name, short_name, country, stadium_name, manager_name="Manager"):
    player_club = create_player_club(club_name, short_name, country, stadium_name)
    player_club.manager_name = manager_name or "Manager"
    clubs, league, league_system = setup_league_system(country, player_club)
    state = GameState(player_club_id=player_club.id, clubs=clubs, league=league, league_system=league_system, country=country, current_date="2026-07-01").ensure_defaults()
    apply_league_financial_profiles(state)
    generate_initial_youth_teams(state)
    generate_fixtures(state)
    initialize_competitions(state)
    refresh_transfer_market(state)
    add_inbox_message(state, "Welcome to your new career", f"You are now in charge of {player_club.name}. Build your squad, manage your finances, and chase silverware.", MessageType.SYSTEM)
    return state


def get_season_label(state):
    start_year = 2025 + max(0, state.season_number - 1)
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def get_current_date(state):
    try:
        return date.fromisoformat(state.current_date)
    except Exception:
        d = date(2026, 7, 1)
        state.current_date = d.isoformat()
        return d


def advance_game_date(state, days=7):
    d = get_current_date(state) + timedelta(days=days)
    state.current_date = d.isoformat()
    return d


def add_inbox_message(state, subject, body, message_type=MessageType.SYSTEM, related_player_id="", related_club_id="", action_required=False, metadata=None):
    state.inbox.insert(0, InboxMessage(id=str(uuid4()), week=state.league.current_week if state.league else 1, season=state.season_number, subject=subject, body=body, message_type=message_type, related_player_id=related_player_id, related_club_id=related_club_id, action_required=action_required, metadata=metadata or {}))


def get_unread_inbox_count(state):
    return sum(1 for m in state.inbox if not m.read)


def get_transfer_window_status(state):
    country = state.country or (state.league.country if state.league else "England")
    d = get_current_date(state)
    windows = TRANSFER_WINDOWS.get(country, TRANSFER_WINDOWS["England"])
    for window in windows:
        start = date(d.year, window["start"][0], window["start"][1])
        end = date(d.year, window["end"][0], window["end"][1])
        if start <= d <= end:
            return {"open": True, "label": f"Open - {window['name']} until {end.isoformat()}"}
    upcoming = []
    for window in windows:
        for year in (d.year, d.year + 1):
            start = date(year, window["start"][0], window["start"][1])
            if start > d:
                upcoming.append((start, window["name"]))
    upcoming.sort(key=lambda x: x[0])
    if upcoming:
        nxt = upcoming[0]
        return {"open": False, "label": f"Closed - Next: {nxt[1]} opens {nxt[0].isoformat()}"}
    return {"open": False, "label": "Closed"}


def can_complete_transfer(state):
    return get_transfer_window_status(state)["open"]


def get_league_financial_profile(country, tier=None):
    data = LEAGUE_DATA.get(country, {})
    pyramid = data.get("pyramid")
    if tier and pyramid:
        found = next((p for p in pyramid if p["tier"] == tier), None)
        if found:
            return {"country": country, "league_name": found.get("name", "League"), "currency": data.get("currency", "GBP"), "avg_budget": found.get("avg_budget", 200000), "avg_wage": found.get("avg_wage", 1000), "ticket_price": found.get("ticket_price", 10), "sponsor_range": found.get("sponsor_range", (1000, 2000)), "max_debt": found.get("max_debt", 100000), "tier": found.get("tier", tier), "avg_reputation": found.get("avg_reputation", 25)}
    return {"country": country, "league_name": data.get("league_name", "League"), "currency": data.get("currency", "GBP"), "avg_budget": data.get("avg_budget", 200000), "avg_wage": data.get("avg_wage", 1000), "ticket_price": data.get("ticket_price", 10), "sponsor_range": data.get("sponsor_range", (1000, 2000)), "max_debt": data.get("max_debt", 100000), "tier": data.get("tier", 5), "avg_reputation": data.get("avg_reputation", 25)}


def apply_league_financial_profiles(state):
    for club in state.clubs.values():
        profile = get_league_financial_profile(club.country, club.league_tier)
        avg_budget = profile["avg_budget"]
        avg_wage = profile["avg_wage"]
        sponsor_low, sponsor_high = profile["sponsor_range"]
        club.ticket_price = profile["ticket_price"]
        club.max_debt = profile["max_debt"]
        club.sponsor_income_weekly = max(club.sponsor_income_weekly, random.randint(sponsor_low, sponsor_high))
        if club.is_player_club:
            club.transfer_budget = max(int(avg_budget * 0.18), int(club.budget * 0.30))
            club.wage_budget_weekly = max(club.wage_budget_weekly, int(avg_wage * 18))
        else:
            club.transfer_budget = max(int(avg_budget * 0.22), int(club.budget * 0.35))
            club.wage_budget_weekly = max(club.wage_budget_weekly, int(avg_wage * 22))
        if club.transfer_spending_limit <= 0:
            club.transfer_spending_limit = club.transfer_budget
        club.balance = club.budget
        club.weekly_wage_commitment = club.total_wages
        club.reputation = max(5, min(90, club.reputation + club.infrastructure.stadium.facilities_level - 3))
        for player in club.players + club.youth_team:
            player.ensure_contract_expectations(club.league_tier)


# Fixtures and calendars

def generate_fixtures(state):
    league = state.league
    club_ids = list(league.club_ids)
    player_id = state.player_club_id
    if player_id in club_ids:
        club_ids.remove(player_id)
        random.shuffle(club_ids)
        club_ids.insert(0, player_id)
    else:
        random.shuffle(club_ids)
    n = len(club_ids)
    if n % 2 == 1:
        club_ids.append(None)
        n += 1
    fixtures = []
    rotation = club_ids[:]
    week = 1
    for round_num in range(n - 1):
        round_fixtures = []
        for i in range(n // 2):
            team_a = rotation[i]
            team_b = rotation[n - 1 - i]
            if team_a is None or team_b is None:
                continue
            if i == 0 and round_num % 2 == 1:
                home, away = team_b, team_a
            else:
                home, away = team_a, team_b
            round_fixtures.append(Fixture(home_id=home, away_id=away, week=week, competition_id="league_main", stage="League"))
        if player_id:
            player_round = [f for f in round_fixtures if f.home_id == player_id or f.away_id == player_id]
            if not player_round and any(x is None for x in rotation):
                for _ in range(n - 1):
                    rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
                    round_fixtures = []
                    for j in range(n // 2):
                        team_a = rotation[j]
                        team_b = rotation[n - 1 - j]
                        if team_a is None or team_b is None:
                            continue
                        if j == 0 and round_num % 2 == 1:
                            home, away = team_b, team_a
                        else:
                            home, away = team_a, team_b
                        round_fixtures.append(Fixture(home_id=home, away_id=away, week=week, competition_id="league_main", stage="League"))
                    if any(f.home_id == player_id or f.away_id == player_id for f in round_fixtures):
                        break
        fixtures.extend(round_fixtures)
        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
        week += 1
    first_half = list(fixtures)
    max_week = max((f.week for f in first_half), default=0)
    for fixture in first_half:
        fixtures.append(Fixture(home_id=fixture.away_id, away_id=fixture.home_id, week=fixture.week + max_week, competition_id="league_main", stage="League"))
    league.fixtures = sorted(fixtures, key=lambda f: (f.week, f.home_id, f.away_id))
    league.total_weeks = max((f.week for f in league.fixtures), default=0)
    league.current_week = 1


def build_competition_calendar(state):
    uefa_windows = set()
    for definition in UEFA_COMPETITION_DEFINITIONS:
        uefa_windows.update(definition["weeks"])
    return {"uefa_reserved_weeks": sorted(uefa_windows)}


def reserve_uefa_windows(state):
    return build_competition_calendar(state)["uefa_reserved_weeks"]


def schedule_domestic_around_reserved_dates(base_weeks, reserved_weeks):
    scheduled = []
    current_week = 3
    for _ in base_weeks:
        while current_week in reserved_weeks:
            current_week += 1
        scheduled.append(current_week)
        current_week += 3
    return scheduled


def assign_domestic_cup_rounds(country, cup_definition, reserved_weeks):
    preferred = list(cup_definition.get("weeks", []))
    if all(w not in reserved_weeks for w in preferred):
        return preferred
    return schedule_domestic_around_reserved_dates(preferred, reserved_weeks)


# Competition system

def _clubs_for_country_tier(state, country, tier):
    return [c for c in state.clubs.values() if c.country == country and c.league_tier == tier]


def _build_external_european_clubs():
    pool = {}
    from database import LEAGUE_DATA
    for country in ["England", "Spain", "France", "Germany", "Italy"]:
        pyramid = LEAGUE_DATA[country]["pyramid"]
        for tier in pyramid[:2]:
            for name, short, stadium, cap in tier["clubs"][: min(8, len(tier["clubs"]))]:
                cid = f"ext_{country[:2]}_{short}_{tier['tier']}"
                club = Club(id=cid, name=name, short_name=short, country=country, league_tier=tier["tier"], reputation=tier["avg_reputation"], budget=tier["avg_budget"], wage_budget_weekly=tier["avg_wage"] * 22, stadium_name=stadium, stadium_capacity=cap)
                club.players = [generate_player(country, pos, tier["tier"], age=random.randint(18, 33)) for pos, count in [(Position.GK, 3), (Position.DEF, 8), (Position.MID, 8), (Position.FWD, 6)] for _ in range(count)]
                club.auto_select_squad()
                pool[cid] = club
    return pool


def build_european_competition_pool(state):
    pool = dict(state.clubs)
    external = _build_external_european_clubs()
    for cid, club in external.items():
        if cid not in pool:
            pool[cid] = club
    return pool


def apply_draw_rules(club_ids, draw_rules=None):
    draw_rules = draw_rules or {}
    ids = list(club_ids)
    random.shuffle(ids)
    if draw_rules.get("seeded"):
        half = len(ids) // 2
        seeds = sorted(ids[:half])
        unseeded = sorted(ids[half:])
        random.shuffle(seeds)
        random.shuffle(unseeded)
        ids = []
        for a, b in zip(seeds, unseeded):
            ids.extend([a, b])
    return ids


def create_knockout_draw(club_ids, weeks, competition_id, round_names=None, draw_rules=None):
    working = apply_draw_rules(club_ids, draw_rules)
    fixtures = []
    draw_summaries = []
    round_names = round_names or ["Round of 16", "Quarter Final", "Semi Final", "Final"]
    round_idx = 0
    current = list(working)
    while len(current) >= 2 and round_idx < len(weeks):
        if len(current) % 2 == 1:
            current = current[:-1]
        week = weeks[round_idx]
        stage = round_names[min(round_idx, len(round_names) - 1)]
        next_placeholders = []
        round_pairs = []
        for pair in range(0, len(current), 2):
            home = current[pair]
            away = current[pair + 1]
            fixtures.append(Fixture(home_id=home, away_id=away, week=week, competition_id=competition_id, stage=stage))
            round_pairs.append((home, away))
            next_placeholders.append(f"winner:{competition_id}:{week}:{pair//2}")
        draw_summaries.append({"week": week, "round": stage, "pairs": round_pairs})
        current = next_placeholders
        round_idx += 1
    return fixtures, draw_summaries


def draw_next_round(competition, week, results_by_pair):
    for fixture in [f for f in competition.fixtures if not f.played and f.week > week]:
        fixture.home_id = _resolve_placeholder_team(results_by_pair, fixture.home_id)
        fixture.away_id = _resolve_placeholder_team(results_by_pair, fixture.away_id)
    if competition.fixtures:
        pending = [f for f in competition.fixtures if not f.played and not str(f.home_id).startswith("winner:") and not str(f.away_id).startswith("winner:")]
        if pending:
            competition.current_round = pending[0].stage


def _competition_slot_metadata(country, slot_key):
    if slot_key == "champions_league":
        return TrophyType.CHAMPIONS_LEAGUE
    if slot_key == "europa_league":
        return TrophyType.EUROPA_LEAGUE
    if slot_key == "conference_league":
        return TrophyType.CONFERENCE_LEAGUE
    return TrophyType.SUPER_CUP


def _country_top_flight_name(country):
    return LEAGUE_DATA[country]["pyramid"][0]["name"]


def apply_country_qualification_rules(country, table, cup_winners):
    rules = COUNTRY_EUROPEAN_SLOTS.get(country, {"champions_league": 2, "europa_league": 1, "conference_league": 1})
    qualification = {"champions_league": [], "europa_league": [], "conference_league": []}
    ranked_ids = [club.id for club in table]
    current_idx = 0

    def take_next(slot, count):
        nonlocal current_idx
        while len(qualification[slot]) < count and current_idx < len(ranked_ids):
            cid = ranked_ids[current_idx]
            current_idx += 1
            if cid not in qualification["champions_league"] and cid not in qualification["europa_league"] and cid not in qualification["conference_league"]:
                qualification[slot].append(cid)

    take_next("champions_league", rules.get("champions_league", 0))
    take_next("europa_league", max(0, rules.get("europa_league", 0) - 1))
    # Cup winner gets priority Europa slot, else next league place
    domestic_cup_winner = cup_winners.get("domestic_cup")
    if domestic_cup_winner and domestic_cup_winner not in qualification["champions_league"] and domestic_cup_winner not in qualification["europa_league"]:
        qualification["europa_league"].append(domestic_cup_winner)
    else:
        take_next("europa_league", rules.get("europa_league", 0))
    take_next("conference_league", rules.get("conference_league", 0))
    return rebalance_qualification_slots(qualification, ranked_ids)


def rebalance_qualification_slots(qualification, ranked_ids):
    assigned = set()
    ordered = {"champions_league": [], "europa_league": [], "conference_league": []}
    for slot in ["champions_league", "europa_league", "conference_league"]:
        for cid in qualification.get(slot, []):
            if cid not in assigned:
                ordered[slot].append(cid)
                assigned.add(cid)
    # top-up in league order where needed
    targets = {"champions_league": len(qualification.get("champions_league", [])), "europa_league": len(qualification.get("europa_league", [])), "conference_league": len(qualification.get("conference_league", []))}
    for slot in ["champions_league", "europa_league", "conference_league"]:
        for cid in ranked_ids:
            if len(ordered[slot]) >= targets[slot]:
                break
            if cid not in assigned:
                ordered[slot].append(cid)
                assigned.add(cid)
    return ordered


def resolve_european_qualification(state):
    qualification = {}
    for country in ["England", "Spain", "France", "Germany", "Italy"]:
        clubs = [c for c in build_european_competition_pool(state).values() if c.country == country and c.league_tier == 1]
        clubs = sorted(clubs, key=lambda c: (c.reputation, c.budget), reverse=True)
        cup_winners = {}
        for comp in state.competitions:
            if comp.country == country and comp.competition_type == CompetitionType.DOMESTIC_CUP and comp.winner_club_id:
                cup_winners["domestic_cup"] = comp.winner_club_id
                break
        qualification[country] = apply_country_qualification_rules(country, clubs, cup_winners)
    state.continental_qualification = qualification
    return qualification


def _domestic_cup_entry_club_ids(state, country, definition):
    clubs = [c for c in build_european_competition_pool(state).values() if c.country == country]
    rules = definition.get("entry_rules", {})
    if rules.get("max_tier"):
        clubs = [c for c in clubs if c.league_tier <= rules["max_tier"]]
    if rules.get("min_tier"):
        clubs = [c for c in clubs if c.league_tier >= rules["min_tier"]]
    clubs = sorted(clubs, key=lambda c: (c.league_tier, -c.reputation, -c.budget))
    top_n = rules.get("top_n")
    if top_n:
        clubs = clubs[:top_n]
    max_entrants = definition.get("max_entrants", len(clubs))
    club_ids = [c.id for c in clubs[:max_entrants]]
    if len(club_ids) % 2 == 1:
        club_ids = club_ids[:-1]
    return club_ids


def _competition_round_names(max_entrants):
    if max_entrants >= 32:
        return ["Round of 32", "Round of 16", "Quarter Final", "Semi Final", "Final"]
    if max_entrants >= 16:
        return ["Round of 16", "Quarter Final", "Semi Final", "Final"]
    if max_entrants >= 8:
        return ["Quarter Final", "Semi Final", "Final"]
    if max_entrants >= 4:
        return ["Semi Final", "Final"]
    return ["Final"]


def initialize_competitions(state):
    state.competitions = []
    state.competitions.append(Competition(id="league_main", name=state.league.name, competition_type=CompetitionType.LEAGUE, country=state.league.country, level="domestic", tier=state.league.tier, club_ids=list(state.league.club_ids), fixtures=list(state.league.fixtures), current_round="League Season", rounds=["League Season"], scheduled_weeks=list(range(1, state.league.total_weeks + 1))))

    calendar = build_competition_calendar(state)
    reserved_weeks = set(calendar["uefa_reserved_weeks"])

    for country in ["England", "Spain", "France", "Germany", "Italy"]:
        for definition in DOMESTIC_CUP_DEFINITIONS.get(country, []):
            club_ids = _domestic_cup_entry_club_ids(state, country, definition)
            if len(club_ids) < 2:
                continue
            weeks = assign_domestic_cup_rounds(country, definition, reserved_weeks)
            round_names = _competition_round_names(len(club_ids))
            fixtures, draw_state_list = create_knockout_draw(club_ids, weeks, definition["id"], round_names=round_names, draw_rules={"seeded": definition["competition_type"] == CompetitionType.SUPER_CUP})
            comp = Competition(
                id=definition["id"],
                name=definition["name"],
                competition_type=definition["competition_type"],
                country=country,
                level="domestic",
                tier=1,
                club_ids=club_ids,
                fixtures=fixtures,
                current_round=fixtures[0].stage if fixtures else "",
                rounds=round_names,
                scheduled_weeks=weeks,
                entry_rules=definition.get("entry_rules", {}),
                draw_state={"rounds": draw_state_list},
                draw_rules={"seeded": definition["competition_type"] == CompetitionType.SUPER_CUP},
            )
            state.competitions.append(comp)
            if country == state.country:
                for draw_round in draw_state_list:
                    add_inbox_message(state, f"Draw completed: {comp.name} - {draw_round['round']}", f"The {comp.name} draw for {draw_round['round']} has been made.", MessageType.COMPETITION, metadata={"competition_id": comp.id, "round": draw_round['round']})

    resolve_european_qualification(state)
    european_pool = build_european_competition_pool(state)
    for definition in UEFA_COMPETITION_DEFINITIONS:
        if definition["id"] == "uefa_super_cup":
            continue
        entrants = []
        for country, slots in state.continental_qualification.items():
            entrants.extend(slots.get(definition["slot_key"], []))
        entrants = [cid for cid in entrants if cid in european_pool]
        max_entrants = definition.get("max_entrants", 16)
        entrants = entrants[:max_entrants]
        if len(entrants) % 2 == 1:
            entrants = entrants[:-1]
        if len(entrants) < 2:
            continue
        fixtures, draw_state_list = create_knockout_draw(entrants, definition["weeks"], definition["id"], round_names=definition["rounds"], draw_rules={"seeded": True})
        state.competitions.append(Competition(
            id=definition["id"], name=definition["name"], competition_type=definition["competition_type"], country="Europe", level="continental", tier=1,
            club_ids=entrants, qualified_club_ids=list(entrants), fixtures=fixtures, current_round=fixtures[0].stage if fixtures else "", rounds=list(definition["rounds"]), scheduled_weeks=list(definition["weeks"]),
            slot_rules={"slot_key": definition["slot_key"]}, draw_state={"rounds": draw_state_list}, draw_rules={"seeded": True},
        ))

    # UEFA Super Cup if winners known from prior season or fallback top entrants
    cl = next((c for c in state.competitions if c.id == "uefa_champions_league"), None)
    el = next((c for c in state.competitions if c.id == "uefa_europa_league"), None)
    if cl and el and len(cl.club_ids) > 0 and len(el.club_ids) > 0:
        entrants = [cl.club_ids[0], el.club_ids[0]]
        fixtures, draw_state_list = create_knockout_draw(entrants, [23], "uefa_super_cup", round_names=["Final"], draw_rules={"seeded": False})
        state.competitions.append(Competition(id="uefa_super_cup", name="UEFA Super Cup", competition_type=CompetitionType.SUPER_CUP, country="Europe", level="continental", tier=1, club_ids=entrants, qualified_club_ids=list(entrants), fixtures=fixtures, current_round="Final", rounds=["Final"], scheduled_weeks=[23], draw_state={"rounds": draw_state_list}))


def get_competitions_for_ui(state):
    return [c for c in state.competitions if c.id != "league_main"]


def get_week_fixtures(state, week=None):
    if week is None:
        week = state.league.current_week
    fixtures = []
    for comp in state.competitions:
        fixtures.extend([f for f in comp.fixtures if f.week == week])
    return fixtures


def get_player_fixtures(state, week=None):
    pid = state.player_club_id
    return [f for f in get_week_fixtures(state, week) if f.home_id == pid or f.away_id == pid]


def get_player_fixture(state, week=None):
    fixtures = get_player_fixtures(state, week)
    return fixtures[0] if fixtures else None


def get_competition_name(state, fixture):
    if fixture.competition_id == "league_main":
        return state.league.name
    comp = next((c for c in state.competitions if c.id == fixture.competition_id), None)
    return comp.name if comp else fixture.stage


def get_player_selected_squad(club):
    selected = [p for p in club.players if p.id in club.selected_squad_ids and p.is_available]
    if len(selected) < 11:
        club.auto_select_squad()
        selected = [p for p in club.players if p.id in club.selected_squad_ids and p.is_available]
    return selected[:11]


def set_selected_squad(club, player_ids):
    valid = [p.id for p in club.players if p.is_available and p.id in player_ids]
    if len(valid) != 11:
        return False, "You must select exactly 11 available players."
    has_gk = any(p.id in valid and p.position == Position.GK for p in club.players)
    if not has_gk:
        return False, "Your starting eleven must include a goalkeeper."
    club.selected_squad_ids = valid
    return True, "Starting eleven updated."


def _play_fixture_native(state, fixture):
    from engine_bridge import bridge as backend_bridge
    club_pool = state.clubs
    home = club_pool.get(fixture.home_id)
    away = club_pool.get(fixture.away_id)
    if home is None or away is None:
        # Build European pool to resolve external clubs
        pool = build_european_competition_pool(state)
        if home is None:
            home = pool.get(fixture.home_id)
        if away is None:
            away = pool.get(fixture.away_id)
    if home is None or away is None:
        raise KeyError(f"Club IDs not found in available pools: home={fixture.home_id}, away={fixture.away_id}")
    return backend_bridge.simulate_match(home, away)


def _resolve_placeholder_team(results_by_pair, placeholder):
    if not isinstance(placeholder, str) or not placeholder.startswith("winner:"):
        return placeholder
    _, comp_id, week_str, pair_idx = placeholder.split(":")
    return results_by_pair.get((comp_id, int(week_str), int(pair_idx)), placeholder)


def _cup_definition_by_id(country, competition_id):
    for definition in DOMESTIC_CUP_DEFINITIONS.get(country, []):
        if definition["id"] == competition_id:
            return definition
    for definition in UEFA_COMPETITION_DEFINITIONS:
        if definition["id"] == competition_id:
            return definition
    return None


def _advance_knockout_competition(state, competition, week, results_by_pair):
    draw_next_round(competition, week, results_by_pair)
    all_real_fixtures = [f for f in competition.fixtures if not str(f.home_id).startswith("winner:") and not str(f.away_id).startswith("winner:")]
    if all_real_fixtures and all(f.played for f in all_real_fixtures if f.stage == "Final"):
        final = next((f for f in all_real_fixtures if f.stage == "Final" and f.played and f.result), None)
        if final:
            winner_id = final.home_id if final.result.home_goals >= final.result.away_goals else final.away_id
            runner_id = final.away_id if winner_id == final.home_id else final.home_id
            competition.winner_club_id = winner_id
            competition.runner_up_club_id = runner_id
            competition.active = False
            definition = _cup_definition_by_id(competition.country if competition.country != "Europe" else state.country, competition.id)
            trophy_type = definition["trophy"] if definition and "trophy" in definition else TrophyType.DOMESTIC_CUP
            state.trophies.append(Trophy(trophy_type=trophy_type, season=state.season_number, league_name=competition.name, tier=competition.tier, competition_id=competition.id, country=competition.country))
            if winner_id == state.player_club_id:
                add_inbox_message(state, f"Competition Won: {competition.name}", f"You have won the {competition.name}.", MessageType.COMPETITION, metadata={"competition_id": competition.id})
            elif state.player_club_id in competition.club_ids:
                winner_club = state.clubs.get(winner_id)
                winner_name = winner_club.name if winner_club else "Unknown Club"
                add_inbox_message(state, f"Competition Finished: {competition.name}", f"{winner_name} won the {competition.name}.", MessageType.COMPETITION, metadata={"competition_id": competition.id})


def play_week(state):
    week = state.league.current_week
    fixtures = get_week_fixtures(state, week)
    results = []
    cup_pair_winners = {}
    for fixture in fixtures:
        if fixture.played or fixture.home_id is None or fixture.away_id is None or str(fixture.home_id).startswith("winner:") or str(fixture.away_id).startswith("winner:"):
            continue
        result = _play_fixture_native(state, fixture)
        fixture.result = result
        fixture.played = True
        _update_match_records(state, fixture, result)
        if fixture.competition_id == "league_main":
            home = state.clubs[fixture.home_id]
            away = state.clubs[fixture.away_id]
            _apply_league_result(home, away, result)
        else:
            winner_id = fixture.home_id if result.home_goals >= result.away_goals else fixture.away_id
            pair_idx = 0
            try:
                stage_fixtures = [f for f in next(c for c in state.competitions if c.id == fixture.competition_id).fixtures if f.week == fixture.week]
                pair_idx = stage_fixtures.index(fixture)
            except Exception:
                pair_idx = 0
            cup_pair_winners[(fixture.competition_id, fixture.week, pair_idx)] = winner_id
        results.append((fixture, result))

    for competition in [c for c in state.competitions if c.competition_type in (CompetitionType.DOMESTIC_CUP, CompetitionType.CONTINENTAL_CUP, CompetitionType.SUPER_CUP) and c.active]:
        _advance_knockout_competition(state, competition, week, cup_pair_winners)

    process_transfer_offers(state)
    process_weekly_finances(state, week)
    process_player_development(state)
    progress_contracts_and_recovery(state)
    advance_game_date(state, 7)
    state.league.current_week += 1
    if state.league.current_week > state.league.total_weeks:
        state.season_over = True
        generate_youth_intake(state)
        process_end_of_season(state)
    if week % 4 == 0:
        refresh_transfer_market(state)
    add_inbox_message(state, f"Weekly Finance Report - Week {week}", _finance_report_text(state), MessageType.FINANCE)
    return results


def _finance_report_text(state):
    club = state.clubs[state.player_club_id]
    return (
        f"Budget: {club.budget:,}\n"
        f"Transfer Budget: {club.transfer_budget:,}\n"
        f"Transfer Spending Limit: {club.transfer_spending_limit:,}\n"
        f"Weekly Wages: {club.total_wages:,}\n"
        f"Balance: {club.balance:,}\n"
        f"Debt: {club.debt:,}\n"
        f"Sold Players Income This Season: {club.sold_players_income_season:,}\n"
        f"Bought Players Spend This Season: {club.bought_players_spend_season:,}"
    )


def _apply_league_result(home, away, result):
    if result.home_goals > result.away_goals:
        home.wins += 1
        away.losses += 1
    elif result.home_goals < result.away_goals:
        away.wins += 1
        home.losses += 1
    else:
        home.draws += 1
        away.draws += 1
    home.goals_for += result.home_goals
    home.goals_against += result.away_goals
    away.goals_for += result.away_goals
    away.goals_against += result.home_goals


def _update_match_records(state, fixture, result):
    home = state.clubs.get(fixture.home_id)
    away = state.clubs.get(fixture.away_id)
    if home is None or away is None:
        pool = build_european_competition_pool(state)
        if home is None:
            home = pool.get(fixture.home_id)
        if away is None:
            away = pool.get(fixture.away_id)
    if home is None or away is None:
        return
    for p in get_player_selected_squad(home):
        p.appearances += 1
        p.career_appearances += 1
    for p in get_player_selected_squad(away):
        p.appearances += 1
        p.career_appearances += 1

    for event in result.events:
        if event.event_type in (EventType.GOAL, EventType.PENALTY_SCORED):
            club = home if event.team_name == home.name else away if event.team_name == away.name else None
            if club:
                scorer = next((p for p in club.players if p.full_name == event.player_name), None)
                if scorer:
                    scorer.goals += 1
                    scorer.career_goals += 1
                assister = next((p for p in club.players if p.full_name == event.assist_name), None)
                if assister:
                    assister.assists += 1

    _update_club_records_after_result(home, result.home_goals, result.away_goals, result.score_line)
    _update_club_records_after_result(away, result.away_goals, result.home_goals, result.score_line)


def _update_club_records_after_result(club, goals_for, goals_against, score_line):
    records = club.records
    margin = goals_for - goals_against
    if margin > 0:
        records.current_winning_streak += 1
        records.current_unbeaten_streak += 1
        records.longest_winning_streak = max(records.longest_winning_streak, records.current_winning_streak)
        records.longest_unbeaten_streak = max(records.longest_unbeaten_streak, records.current_unbeaten_streak)
    elif margin == 0:
        records.current_winning_streak = 0
        records.current_unbeaten_streak += 1
        records.longest_unbeaten_streak = max(records.longest_unbeaten_streak, records.current_unbeaten_streak)
    else:
        records.current_winning_streak = 0
        records.current_unbeaten_streak = 0
    if margin > 0 and (records.biggest_win == "None" or margin > _extract_margin(records.biggest_win)):
        records.biggest_win = score_line
    if margin < 0:
        defeat_margin = abs(margin)
        if records.biggest_defeat == "None" or defeat_margin > _extract_margin(records.biggest_defeat):
            records.biggest_defeat = score_line
    if (goals_for + goals_against) > _extract_total_goals(records.highest_scoring_match):
        records.highest_scoring_match = score_line
    for p in club.players:
        if p.career_goals > records.all_time_top_scorer_goals:
            records.all_time_top_scorer_goals = p.career_goals
            records.all_time_top_scorer = p.full_name
        if p.career_appearances > records.most_appearances:
            records.most_appearances = p.career_appearances
            records.most_appearances_player = p.full_name


def _extract_margin(score_line):
    try:
        left = score_line.split()[-3]
        right = score_line.split()[-1]
        return abs(int(left) - int(right))
    except Exception:
        return 0


def _extract_total_goals(score_line):
    try:
        left = score_line.split()[-3]
        right = score_line.split()[-1]
        return int(left) + int(right)
    except Exception:
        return 0


def progress_contracts_and_recovery(state):
    for club in state.clubs.values():
        for player in club.players + club.youth_team:
            if player.injured_weeks > 0:
                player.injured_weeks -= 1
            if player.suspended_matches > 0:
                player.suspended_matches -= 1
            player.fitness = min(100, player.fitness + max(2, club.infrastructure.training.medical_level))
            if player.contract_years > 0 and state.league.current_week % 12 == 0:
                player.contract_years = max(0, player.contract_years - 1)
        club.weekly_wage_commitment = club.total_wages
        club.balance = club.budget


def process_weekly_finances(state, week):
    club = state.clubs[state.player_club_id]
    infra = club.infrastructure
    wages = club.total_wages
    club.budget -= wages
    state.finance_history.append(FinanceRecord(week, "Player Wages", -wages))
    club.budget += club.sponsor_income_weekly
    state.finance_history.append(FinanceRecord(week, "Sponsorship", club.sponsor_income_weekly))
    facility_income = (infra.stadium.club_shop_level * 2200 + infra.stadium.cafe_level * 1800 + infra.stadium.hospitality_level * 3000 + infra.stadium.fan_zone_level * 1500)
    if facility_income:
        club.budget += facility_income
        state.finance_history.append(FinanceRecord(week, "Facility Revenue", facility_income))
    upkeep = (infra.stadium.facilities_level * 1200 + infra.training.level * 1500 + infra.training.medical_level * 800 + infra.youth.level * 900 + infra.youth.recruitment_level * 700 + infra.youth.scouting_level * 650 + infra.stadium.pitch_quality * 600 + infra.training.training_ground_level * 700 + infra.training.sports_science_level * 900 + infra.stadium.parking_level * 500)
    club.budget -= upkeep
    state.finance_history.append(FinanceRecord(week, "Infrastructure Upkeep", -upkeep))
    for fixture in get_player_fixtures(state, week):
        if fixture.home_id == state.player_club_id and fixture.result:
            attendance_bonus = min(0.98, 0.45 + infra.stadium.seating_level * 0.03 + club.reputation * 0.005 + infra.stadium.parking_level * 0.02)
            revenue = int(min(club.stadium_capacity, fixture.result.attendance * attendance_bonus) * club.ticket_price)
            club.budget += revenue
            state.finance_history.append(FinanceRecord(week, f"Match Day Revenue ({get_competition_name(state, fixture)})", revenue))
    club.balance = club.budget
    club.debt = abs(club.budget) if club.budget < 0 else 0


def process_player_development(state):
    for club in state.clubs.values():
        training = club.infrastructure.training
        youth_boost = club.infrastructure.youth.level
        scouting_boost = club.infrastructure.youth.scouting_level
        injury_risk = 0.01 * max(0, training.intensity - 3)
        for player in club.players + club.youth_team:
            age_factor = 1.5 if player.age <= 21 else (1.0 if player.age <= 27 else 0.5)
            growth_chance = min(0.62, 0.08 + training.level * 0.03 + training.training_ground_level * 0.015 + youth_boost * 0.01 + scouting_boost * 0.005)
            decline_chance = 0.02 if player.age < 30 else 0.10 + (player.age - 30) * 0.02
            if player.age <= 24 and random.random() < growth_chance * age_factor:
                improve_player(player, max_overall=player.potential)
            elif player.age >= 31 and random.random() < decline_chance:
                decline_player(player)
            if player.injured_weeks == 0 and random.random() < injury_risk:
                player.injured_weeks = random.randint(1, 3)


def improve_player(player, max_overall=99):
    attrs = ["goalkeeping", "defending", "passing", "shooting", "pace", "physical"]
    random.shuffle(attrs)
    for attr in attrs[:2]:
        if getattr(player, attr) < 99 and player.overall < max_overall:
            setattr(player, attr, getattr(player, attr) + 1)
    player.value = max(player.value, int(player.overall * player.overall * random.randint(900, 1600)))


def decline_player(player):
    attr = random.choice(["defending", "passing", "shooting", "pace", "physical"])
    setattr(player, attr, max(1, getattr(player, attr) - 1))
    player.value = max(1000, int(player.value * 0.92))


def get_league_table(state):
    clubs = [state.clubs[cid] for cid in state.league.club_ids]
    return sorted(clubs, key=lambda c: (c.points, c.gd, c.goals_for), reverse=True)


def get_competition_results(state, competition_id):
    comp = next((c for c in state.competitions if c.id == competition_id), None)
    if not comp:
        return []
    out = []
    for fixture in comp.fixtures:
        if fixture.played and fixture.result:
            out.append(f"Week {fixture.week} - {fixture.stage}: {fixture.result.score_line}")
    return out


def get_competition_draw_text(state, competition_id):
    comp = next((c for c in state.competitions if c.id == competition_id), None)
    if not comp:
        return []
    lines = []
    for round_info in comp.draw_state.get("rounds", []):
        lines.append(f"{round_info['round']} (Week {round_info['week']}):")
        for home, away in round_info.get("pairs", []):
            home_name = state.clubs[home].name if home in state.clubs else home
            away_name = state.clubs[away].name if away in state.clubs else away
            lines.append(f"- {home_name} vs {away_name}")
        lines.append("")
    return lines or ["No draw information available."]


def get_playable_competitions_for_club(state, club_id=None):
    club_id = club_id or state.player_club_id
    comps = []
    for comp in state.competitions:
        if club_id in comp.club_ids:
            comps.append(comp)
    return comps


def get_league_benchmarks(state, club):
    same_tier = [c for c in state.clubs.values() if c.country == club.country and c.league_tier == club.league_tier]
    if not same_tier:
        same_tier = list(state.clubs.values())
    count = max(1, len(same_tier))
    return {"seating_capacity": sum(c.stadium_capacity for c in same_tier) / count, "seating_level": sum(c.infrastructure.stadium.seating_level for c in same_tier) / count, "pitch_quality": sum(c.infrastructure.stadium.pitch_quality for c in same_tier) / count, "parking_level": sum(c.infrastructure.stadium.parking_level for c in same_tier) / count, "training_level": sum(c.infrastructure.training.level for c in same_tier) / count, "medical_level": sum(c.infrastructure.training.medical_level for c in same_tier) / count, "youth_level": sum(c.infrastructure.youth.level for c in same_tier) / count, "recruitment_level": sum(c.infrastructure.youth.recruitment_level for c in same_tier) / count, "scouting_level": sum(c.infrastructure.youth.scouting_level for c in same_tier) / count}


def describe_relative(value, benchmark):
    if value >= benchmark + 1.2:
        return "Excellent"
    if value >= benchmark + 0.3:
        return "Above League Standard"
    if value <= benchmark - 1.2:
        return "Poor"
    if value <= benchmark - 0.3:
        return "Below League Standard"
    return "Around League Standard"


def get_stadium_upgrade_cost(current_capacity, target_capacity, seating_level):
    if target_capacity <= current_capacity:
        return 0
    increase = target_capacity - current_capacity
    return int(increase * (45 + seating_level * 6) + seating_level * 25000)


def upgrade_stadium_to_capacity(club, target_capacity):
    target_capacity = int(target_capacity)
    if target_capacity <= club.stadium_capacity:
        return False, "Target capacity must be higher than current capacity."
    cost = get_stadium_upgrade_cost(club.stadium_capacity, target_capacity, club.infrastructure.stadium.seating_level)
    if club.budget < cost:
        return False, f"Not enough budget. Upgrade cost is {cost:,}."
    club.budget -= cost
    club.stadium_capacity = target_capacity
    return True, f"Stadium expanded to {target_capacity:,} capacity for {cost:,}."


def _simple_infra_upgrade(club, cost, current_value, max_value, setter, label):
    if current_value >= max_value:
        return False, f"{label} is already at maximum level."
    if club.budget < cost:
        return False, f"Not enough budget. {label} upgrade costs {cost:,}."
    club.budget -= cost
    setter(current_value + 1)
    club.balance = club.budget
    return True, f"{label} upgraded to level {current_value + 1}."


def upgrade_pitch(club):
    return _simple_infra_upgrade(club, club.infrastructure.pitch_upgrade_cost(), club.infrastructure.stadium.pitch_quality, 10, lambda v: setattr(club.infrastructure.stadium, "pitch_quality", v), "Pitch")


def upgrade_training(club):
    return _simple_infra_upgrade(club, club.infrastructure.training_upgrade_cost(), club.infrastructure.training.level, 10, lambda v: setattr(club.infrastructure.training, "level", v), "Training")


def upgrade_medical(club):
    return _simple_infra_upgrade(club, club.infrastructure.medical_upgrade_cost(), club.infrastructure.training.medical_level, 10, lambda v: setattr(club.infrastructure.training, "medical_level", v), "Medical")


def upgrade_parking(club):
    return _simple_infra_upgrade(club, club.infrastructure.parking_upgrade_cost(), club.infrastructure.stadium.parking_level, 5, lambda v: setattr(club.infrastructure.stadium, "parking_level", v), "Parking")


def upgrade_youth_academy(club):
    return _simple_infra_upgrade(club, club.infrastructure.youth_upgrade_cost(), club.infrastructure.youth.level, 10, lambda v: setattr(club.infrastructure.youth, "level", v), "Youth academy")


def upgrade_youth_recruitment(club):
    return _simple_infra_upgrade(club, club.infrastructure.youth_recruitment_upgrade_cost(), club.infrastructure.youth.recruitment_level, 10, lambda v: setattr(club.infrastructure.youth, "recruitment_level", v), "Youth recruitment")


def upgrade_scouting(club):
    return _simple_infra_upgrade(club, club.infrastructure.scouting_upgrade_cost(), club.infrastructure.youth.scouting_level, 10, lambda v: setattr(club.infrastructure.youth, "scouting_level", v), "Scouting")


def set_training_intensity(club, intensity):
    club.infrastructure.training.intensity = max(1, min(5, int(intensity)))
    return True, f"Training intensity set to {club.infrastructure.training.intensity}."


def generate_initial_youth_teams(state):
    for club in state.clubs.values():
        if not club.youth_team:
            quality = club.infrastructure.youth.level
            count = 5 if club.is_player_club else 4
            for _ in range(count):
                club.youth_team.append(generate_youth_player(club, quality))
    state.youth_players = list(state.clubs[state.player_club_id].youth_team)


def generate_youth_player(club, quality):
    age = random.randint(15, 18)
    position = random.choice(list(Position))
    player = generate_player(club.country, position, club.league_tier, age=age)
    player.is_youth = True
    player.potential = min(99, player.overall + 8 + quality + club.infrastructure.youth.scouting_level + random.randint(0, 8))
    player.value = int(player.value * 0.45)
    player.wage = 0
    player.contract_years = 0
    player.squad_role_expectation = "Prospect"
    player.willingness_to_join = 85
    player.ensure_contract_expectations(club.league_tier)
    return player


def generate_youth_intake(state):
    for club in state.clubs.values():
        intake_size = 2 + club.infrastructure.youth.recruitment_level // 3
        for _ in range(intake_size):
            club.youth_team.append(generate_youth_player(club, club.infrastructure.youth.level))
            if club.id == state.player_club_id:
                add_inbox_message(state, "Youth Intake Arrival", f"A new youth intake has arrived at {club.name}.", MessageType.YOUTH)
    state.youth_players = list(state.clubs[state.player_club_id].youth_team)


def promote_youth_player(state, player_id, wage, years):
    club = state.clubs[state.player_club_id]
    player = next((p for p in club.youth_team if p.id == player_id), None)
    if not player:
        return False, "Youth player not found."
    if wage > club.wage_budget_weekly * 3:
        return False, "That wage offer is too high for your current wage structure."
    player.is_youth = False
    player.wage = int(wage)
    player.contract_years = int(years)
    player.season_joined = state.season_number
    club.youth_team = [p for p in club.youth_team if p.id != player_id]
    club.players.append(player)
    club.auto_select_squad()
    add_inbox_message(state, "Youth Promotion", f"{player.full_name} has been promoted to the first team on a {years}-year deal.", MessageType.YOUTH, related_player_id=player.id)
    return True, f"{player.full_name} promoted to the first team on a {years}-year deal."


def get_player_contract_demands(player, buyer_club):
    player.ensure_contract_expectations(buyer_club.league_tier)
    return {"desired_wage": player.desired_wage, "minimum_wage": player.minimum_acceptable_wage, "desired_years": max(player.min_contract_years(), min(player.max_contract_years(), player.desired_contract_length)), "role": player.squad_role_expectation}


def evaluate_join_decision(player, buyer_club):
    score = player.willingness_to_join
    score += max(-10, min(20, buyer_club.reputation - 40))
    score += max(-8, min(12, (6 - buyer_club.league_tier) * 3))
    score += buyer_club.infrastructure.training.level
    return max(1, min(100, score))


def negotiate_contract(player, buyer_club, wage_offer, years_offer, role_offer, negotiation_history=None):
    negotiation_history = negotiation_history or []
    demands = get_player_contract_demands(player, buyer_club)
    join_score = evaluate_join_decision(player, buyer_club)
    repeated_lowball = sum(1 for prev in negotiation_history if prev.get("wage", 0) < demands["minimum_wage"])
    insulting_offers = sum(1 for prev in negotiation_history if prev.get("wage", 0) < demands["minimum_wage"] * 0.75)
    if wage_offer < demands["minimum_wage"] * 0.75:
        insulting_offers += 1
    if wage_offer < demands["minimum_wage"]:
        repeated_lowball += 1
    if join_score < 25:
        return {"success": False, "outcome": "rejected", "message": f"{player.full_name} does not want to join your club."}
    if insulting_offers >= 2:
        return {"success": False, "outcome": "walked_away", "message": f"{player.full_name} is offended by your offers and walks away from talks."}
    if repeated_lowball >= 3:
        return {"success": False, "outcome": "rejected", "message": f"{player.full_name} rejects further talks after repeated low offers."}
    desired_role_value = ROLE_VALUES.get(demands["role"], 50)
    offered_role_value = ROLE_VALUES.get(role_offer, 50)
    wage_score = wage_offer / max(1, demands["desired_wage"])
    years_penalty = abs(years_offer - demands["desired_years"])
    role_penalty = max(0, desired_role_value - offered_role_value) / 25.0
    offer_score = wage_score * 100 + join_score - years_penalty * 8 - role_penalty * 10
    if wage_offer >= demands["desired_wage"] and years_offer >= player.min_contract_years() and offered_role_value >= desired_role_value - 10 and buyer_club.wage_budget_weekly >= wage_offer:
        return {"success": True, "outcome": "accepted", "message": f"{player.full_name} accepts your contract offer."}
    if offer_score >= 120 and wage_offer >= demands["minimum_wage"] and buyer_club.wage_budget_weekly >= wage_offer:
        return {"success": True, "outcome": "accepted", "message": f"{player.full_name} accepts after negotiation."}
    counter_wage = max(demands["minimum_wage"], int((wage_offer + demands["desired_wage"]) / 2))
    counter_years = max(player.min_contract_years(), min(player.max_contract_years(), max(years_offer, demands["desired_years"])))
    counter_role = demands["role"] if offered_role_value < desired_role_value else role_offer
    return {"success": False, "outcome": "counter", "message": f"{player.full_name} wants {counter_wage:,} per week for {counter_years} years as {counter_role}.", "counter_wage": counter_wage, "counter_years": counter_years, "counter_role": counter_role}


def finalize_transfer_from_negotiation(state, listing, wage, years, role):
    if not can_complete_transfer(state):
        return False, "The transfer window is closed."
    buyer = state.clubs[state.player_club_id]
    seller = state.clubs.get(listing.club_id)
    if not seller:
        return False, "Selling club not found."
    player = next((p for p in seller.players if p.id == listing.player_id), None)
    if not player:
        return False, "Player not found."
    effective_limit = buyer.transfer_spending_limit or buyer.transfer_budget
    if buyer.transfer_budget < listing.asking_price or buyer.budget < listing.asking_price or listing.asking_price > effective_limit:
        return False, "You do not have enough budget or available transfer limit to complete the transfer."
    if wage > buyer.wage_budget_weekly * 3:
        return False, "That wage is beyond your wage structure."
    buyer.transfer_budget -= listing.asking_price
    buyer.budget -= listing.asking_price
    buyer.bought_players_spend_season += listing.asking_price
    seller.budget += listing.asking_price
    seller.sold_players_income_season += listing.asking_price
    seller.players = [p for p in seller.players if p.id != player.id]
    player.wage = int(wage)
    player.contract_years = int(years)
    player.squad_role_expectation = role
    player.season_joined = state.season_number
    buyer.players.append(player)
    buyer.auto_select_squad()
    state.transfer_list = [t for t in state.transfer_list if not (t.player_id == listing.player_id and t.club_id == listing.club_id)]
    add_inbox_message(state, "Transfer Completed", f"{player.full_name} has joined {buyer.name} from {seller.name} for {listing.asking_price:,}.", MessageType.TRANSFER, related_player_id=player.id, related_club_id=seller.id)
    return True, f"Transfer completed: {player.full_name} joins {buyer.name}."


def list_player_for_sale(state, player_id, asking_price=None):
    club = state.clubs[state.player_club_id]
    player = next((p for p in club.players if p.id == player_id), None)
    if not player:
        return False, "Player not found."
    player.transfer_listed = True
    if asking_price:
        player.asking_price_override = int(asking_price)
    price = player.asking_price_override or max(player.value, int(player.overall * player.overall * 1000))
    if not any(t.player_id == player.id and t.club_id == club.id for t in state.transfer_list):
        state.transfer_list.insert(0, TransferListing(player_id=player.id, club_id=club.id, asking_price=price))
    return True, f"{player.full_name} has been listed for transfer at {price:,}."


def process_transfer_offers(state):
    player_club = state.clubs[state.player_club_id]
    existing_pending = {(o.player_id, o.buyer_club_id) for o in state.incoming_transfer_offers if o.status == "pending"}
    listed_items = [t for t in state.transfer_list if t.club_id == state.player_club_id]
    for listing in listed_items:
        player = next((p for p in player_club.players if p.id == listing.player_id), None)
        if not player:
            continue
        for club in [c for c in state.clubs.values() if c.id != player_club.id and c.country == player_club.country]:
            if (player.id, club.id) in existing_pending:
                continue
            age_factor = 1.1 if player.age <= 27 else 0.8
            tier_factor = max(0.55, 1.25 - (club.league_tier - player_club.league_tier) * 0.12)
            affordability = 1.0 if club.transfer_budget >= listing.asking_price * 0.75 else 0.45
            rating_factor = min(1.35, max(0.65, player.overall / 60.0))
            chance = 0.08 * age_factor * tier_factor * affordability * rating_factor
            if player.transfer_listed:
                chance += 0.18
            if random.random() < min(0.75, chance):
                fee = int(listing.asking_price * random.uniform(0.88, 1.08))
                offer = IncomingTransferOffer(id=str(uuid4()), player_id=player.id, buyer_club_id=club.id, seller_club_id=player_club.id, fee=fee, week_created=state.league.current_week)
                state.incoming_transfer_offers.append(offer)
                add_inbox_message(state, f"Transfer Offer for {player.full_name}", f"{club.name} have offered {fee:,} for {player.full_name}.", MessageType.TRANSFER, related_player_id=player.id, related_club_id=club.id, action_required=True, metadata={"offer_id": offer.id})
                existing_pending.add((player.id, club.id))
                break


def respond_to_transfer_offer(state, offer_id, accept):
    offer = next((o for o in state.incoming_transfer_offers if o.id == offer_id and o.status == "pending"), None)
    if not offer:
        return False, "Transfer offer not found."
    buyer = state.clubs.get(offer.buyer_club_id)
    seller = state.clubs.get(offer.seller_club_id)
    if not buyer or not seller:
        return False, "Clubs not found for this offer."
    player = next((p for p in seller.players if p.id == offer.player_id), None)
    if not player:
        offer.status = "withdrawn"
        return False, "Player not found."
    if not accept:
        offer.status = "rejected"
        add_inbox_message(state, "Transfer Offer Rejected", f"You rejected {buyer.name}'s offer for {player.full_name}.", MessageType.TRANSFER, related_player_id=player.id, related_club_id=buyer.id)
        return True, f"You rejected the offer from {buyer.name}."
    if buyer.transfer_budget < offer.fee or buyer.budget < offer.fee:
        offer.status = "withdrawn"
        return False, f"{buyer.name} can no longer afford the deal."
    buyer.transfer_budget -= offer.fee
    buyer.budget -= offer.fee
    buyer.bought_players_spend_season += offer.fee
    seller.budget += offer.fee
    seller.sold_players_income_season += offer.fee
    seller.players = [p for p in seller.players if p.id != player.id]
    player.transfer_listed = False
    player.asking_price_override = 0
    buyer.players.append(player)
    offer.status = "accepted"
    state.transfer_list = [t for t in state.transfer_list if not (t.player_id == player.id and t.club_id == seller.id)]
    add_inbox_message(state, "Player Sold", f"{player.full_name} has been sold to {buyer.name} for {offer.fee:,}.", MessageType.TRANSFER, related_player_id=player.id, related_club_id=buyer.id)
    return True, f"Offer accepted. {player.full_name} joins {buyer.name}."


def refresh_transfer_market(state):
    listings = []
    for club in state.clubs.values():
        if club.id == state.player_club_id:
            continue
        sellable = sorted([p for p in club.players if not p.is_youth], key=lambda p: (p.overall, p.age), reverse=True)
        for player in sellable[: max(4, min(10, len(sellable) // 3))]:
            price = player.asking_price_override or max(player.value, int(player.overall * player.overall * 1200))
            listings.append(TransferListing(player_id=player.id, club_id=club.id, asking_price=price))
    player_club = state.clubs[state.player_club_id]
    for player in player_club.players:
        if player.transfer_listed:
            price = player.asking_price_override or max(player.value, int(player.overall * player.overall * 1200))
            listings.append(TransferListing(player_id=player.id, club_id=player_club.id, asking_price=price))
    random.shuffle(listings)
    state.transfer_list = listings[:180]


def get_transfer_market_players(state, position_filter="All", search_text=""):
    items = []
    search = (search_text or "").strip().lower()
    for listing in state.transfer_list:
        club = state.clubs.get(listing.club_id)
        player = next((p for p in club.players if p.id == listing.player_id), None) if club else None
        if not player:
            continue
        if position_filter and position_filter != "All" and player.position.name != position_filter:
            continue
        if search and search not in player.full_name.lower():
            continue
        items.append((listing, player, club))
    items.sort(key=lambda x: (-x[1].overall, x[1].age, x[1].full_name))
    return items


def get_player_market_profile(state, listing, player, club):
    return {"name": player.full_name, "age": player.age, "position": player.position.value, "rating": player.overall, "potential": player.potential, "nationality": player.nationality, "current_club": club.name if club else "Unknown", "current_club_short": club.short_name if club else "UNK", "goals": player.goals, "assists": player.assists, "appearances": player.appearances, "career_goals": player.career_goals, "career_appearances": player.career_appearances, "value": player.value, "asking_price": listing.asking_price, "wage": player.wage, "contract_years": player.contract_years, "scouted": player.scouted, "shortlisted": player.shortlisted, "facts": [f"Morale: {player.morale}", f"Fitness: {player.fitness}", f"Passing: {player.passing}", f"Shooting: {player.shooting}", f"Pace: {player.pace}", f"Physical: {player.physical}", f"Defending: {player.defending}", f"Goalkeeping: {player.goalkeeping}"], "scouting_notes": player.scouting_notes or "No scouting report yet."}


def add_player_to_shortlist(state, player_id):
    player_club = state.clubs[state.player_club_id]
    if player_id in player_club.shortlist_player_ids:
        return False, "Player is already on your shortlist."
    player_club.shortlist_player_ids.append(player_id)
    for club in state.clubs.values():
        for player in club.players:
            if player.id == player_id:
                player.shortlisted = True
                return True, f"{player.full_name} added to shortlist."
    return False, "Player not found."


def scout_player(state, player_id):
    for club in state.clubs.values():
        for player in club.players:
            if player.id == player_id:
                player.scouted = True
                player.scouting_notes = f"Scouting report: {player.full_name} is a {player.position.value.lower()} aged {player.age}. Current rating {player.overall}/99, potential {player.potential}/99. Strengths: passing {player.passing}, shooting {player.shooting}, pace {player.pace}, physical {player.physical}."
                add_inbox_message(state, f"Scout Report: {player.full_name}", player.scouting_notes, MessageType.SCOUT, related_player_id=player.id)
                return True, f"Scouting report completed for {player.full_name}."
    return False, "Player not found."


def process_end_of_season(state):
    table = get_league_table(state)
    player_club = state.clubs[state.player_club_id]
    pos = next((i + 1 for i, c in enumerate(table) if c.id == state.player_club_id), len(table))
    player_club.records.highest_league_finish = min(player_club.records.highest_league_finish, pos)
    player_club.records.most_points = max(player_club.records.most_points, player_club.points)
    player_club.records.most_goals_scored = max(player_club.records.most_goals_scored, player_club.goals_for)
    player_club.records.best_goal_difference = max(player_club.records.best_goal_difference, player_club.gd)
    if pos == 1:
        state.trophies.append(Trophy(TrophyType.LEAGUE_CHAMPION, state.season_number, state.league.name, state.league.tier, competition_id="league_main", country=state.country))
        add_inbox_message(state, "League Champions", f"Congratulations. {player_club.name} are champions of {state.league.name}.", MessageType.COMPETITION)
    elif pos <= max(1, _current_tier(state).promotion_places):
        state.trophies.append(Trophy(TrophyType.PROMOTION, state.season_number, state.league.name, state.league.tier, competition_id="league_main", country=state.country))
        add_inbox_message(state, "Promotion Secured", f"{player_club.name} secure promotion from {state.league.name}.", MessageType.COMPETITION)
    resolve_european_qualification(state)


def _current_tier(state):
    for tier in state.league_system:
        if tier.tier == state.league.tier and tier.country == state.country:
            return tier
    return LeagueTier(country=state.country, name=state.league.name, tier=state.league.tier, club_ids=list(state.league.club_ids), promotion_places=1)


def reset_for_new_season(state):
    state.season_over = False
    state.season_number += 1
    state.league.current_week = 1
    for club in state.clubs.values():
        club.reset_season_stats()
        club.auto_select_squad()
    generate_fixtures(state)
    initialize_competitions(state)
    refresh_transfer_market(state)


def get_post_match_other_results(state, week):
    lines = []
    for fixture in get_week_fixtures(state, week):
        if fixture.played and fixture.result and not (fixture.home_id == state.player_club_id or fixture.away_id == state.player_club_id):
            lines.append(f"{get_competition_name(state, fixture)}: {fixture.result.score_line}")
    return lines


def get_season_summary(state):
    table = get_league_table(state)
    player_club = state.clubs[state.player_club_id]
    position = next((i + 1 for i, c in enumerate(table) if c.id == player_club.id), len(table))
    profile = get_league_financial_profile(player_club.country, player_club.league_tier)
    tier_size = len(table)
    if position == 1:
        prize_money = int(profile["avg_budget"] * 0.45)
    elif position <= max(2, tier_size // 4):
        prize_money = int(profile["avg_budget"] * 0.28)
    elif position <= max(4, tier_size // 2):
        prize_money = int(profile["avg_budget"] * 0.18)
    else:
        prize_money = int(profile["avg_budget"] * 0.10)
    return {"position": position, "total_clubs": tier_size, "player_club": player_club, "prize_money": prize_money, "currency": profile["currency"], "messages": [m.subject for m in state.inbox[:5]]}
