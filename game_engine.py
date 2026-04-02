"""Core backend game engine for Football Manager 26.
This module owns game rules, season flow, finances, transfers, infrastructure,
and league/cup progression. The UI should only call into this via a service.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import List

from models import (
    Club,
    Competition,
    CompetitionType,
    EventType,
    FinanceRecord,
    Fixture,
    GameState,
    LeagueSeason,
    LeagueTier,
    MatchEvent,
    MatchResult,
    Player,
    Position,
    TransferListing,
    Trophy,
    TrophyType,
)
from database import LEAGUE_DATA, create_player_club, generate_player, setup_league, setup_league_system
from match_engine import simulate_match

ROLE_VALUES = {"Prospect": 35, "Rotation": 50, "Starter": 68, "Key Player": 82}
TRANSFER_WINDOWS = {
    "England": [{"name": "Summer Window", "start": (6, 14), "end": (8, 30)}, {"name": "Winter Window", "start": (1, 1), "end": (1, 31)}],
    "Spain": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 2), "end": (1, 31)}],
    "France": [{"name": "Summer Window", "start": (7, 1), "end": (8, 31)}, {"name": "Winter Window", "start": (1, 1), "end": (1, 31)}],
}


def create_new_game(club_name, short_name, country, stadium_name, manager_name="Manager"):
    player_club = create_player_club(club_name, short_name, country, stadium_name)
    player_club.manager_name = manager_name or "Manager"
    clubs, league, league_system = setup_league_system(country, player_club)
    state = GameState(
        player_club_id=player_club.id,
        clubs=clubs,
        league=league,
        league_system=league_system,
        country=country,
        current_date="2026-07-01",
    ).ensure_defaults()
    apply_league_financial_profiles(state)
    generate_initial_youth_teams(state)
    generate_fixtures(state)
    initialize_competitions(state)
    refresh_transfer_market(state)
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
            return {
                "country": country,
                "league_name": found.get("name", "League"),
                "currency": data.get("currency", "GBP"),
                "avg_budget": found.get("avg_budget", 200000),
                "avg_wage": found.get("avg_wage", 1000),
                "ticket_price": found.get("ticket_price", 10),
                "sponsor_range": found.get("sponsor_range", (1000, 2000)),
                "max_debt": found.get("max_debt", 100000),
                "tier": found.get("tier", tier),
                "avg_reputation": found.get("avg_reputation", 25),
            }
    return {
        "country": country,
        "league_name": data.get("league_name", "League"),
        "currency": data.get("currency", "GBP"),
        "avg_budget": data.get("avg_budget", 200000),
        "avg_wage": data.get("avg_wage", 1000),
        "ticket_price": data.get("ticket_price", 10),
        "sponsor_range": data.get("sponsor_range", (1000, 2000)),
        "max_debt": data.get("max_debt", 100000),
        "tier": data.get("tier", 5),
        "avg_reputation": data.get("avg_reputation", 25),
    }


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
        club.balance = club.budget
        club.weekly_wage_commitment = club.total_wages
        club.reputation = max(5, min(90, club.reputation + club.infrastructure.stadium.facilities_level - 3))
        for player in club.players + club.youth_team:
            player.ensure_contract_expectations(club.league_tier)


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


def initialize_competitions(state):
    state.competitions = [
        Competition(
            id="league_main",
            name=state.league.name,
            competition_type=CompetitionType.LEAGUE,
            country=state.league.country,
            level="domestic",
            tier=state.league.tier,
            club_ids=list(state.league.club_ids),
            fixtures=list(state.league.fixtures),
            current_round="League Season",
        )
    ]


def get_week_fixtures(state, week=None):
    if week is None:
        week = state.league.current_week
    return [f for f in state.league.fixtures if f.week == week]


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


def play_week(state):
    from engine_bridge import bridge as backend_bridge

    week = state.league.current_week
    fixtures = get_week_fixtures(state, week)
    results = []
    for fixture in fixtures:
        if fixture.played:
            continue
        home = state.clubs[fixture.home_id]
        away = state.clubs[fixture.away_id]
        result = backend_bridge.simulate_match(home, away)
        fixture.result = result
        fixture.played = True
        _update_match_records(state, fixture, result)
        if fixture.competition_id == "league_main":
            _apply_league_result(home, away, result)
        results.append((fixture, result))

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
    return results


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
    home = state.clubs[fixture.home_id]
    away = state.clubs[fixture.away_id]
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
    facility_income = (
        infra.stadium.club_shop_level * 2200
        + infra.stadium.cafe_level * 1800
        + infra.stadium.hospitality_level * 3000
        + infra.stadium.fan_zone_level * 1500
    )
    if facility_income:
        club.budget += facility_income
        state.finance_history.append(FinanceRecord(week, "Facility Revenue", facility_income))
    upkeep = (
        infra.stadium.facilities_level * 1200
        + infra.training.level * 1500
        + infra.training.medical_level * 800
        + infra.youth.level * 900
        + infra.youth.recruitment_level * 700
        + infra.youth.scouting_level * 650
        + infra.stadium.pitch_quality * 600
        + infra.training.training_ground_level * 700
        + infra.training.sports_science_level * 900
        + infra.stadium.parking_level * 500
    )
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


def get_league_benchmarks(state, club):
    same_tier = [c for c in state.clubs.values() if c.country == club.country and c.league_tier == club.league_tier]
    if not same_tier:
        same_tier = list(state.clubs.values())
    count = max(1, len(same_tier))
    return {
        "seating_capacity": sum(c.stadium_capacity for c in same_tier) / count,
        "seating_level": sum(c.infrastructure.stadium.seating_level for c in same_tier) / count,
        "pitch_quality": sum(c.infrastructure.stadium.pitch_quality for c in same_tier) / count,
        "parking_level": sum(c.infrastructure.stadium.parking_level for c in same_tier) / count,
        "training_level": sum(c.infrastructure.training.level for c in same_tier) / count,
        "medical_level": sum(c.infrastructure.training.medical_level for c in same_tier) / count,
        "youth_level": sum(c.infrastructure.youth.level for c in same_tier) / count,
        "recruitment_level": sum(c.infrastructure.youth.recruitment_level for c in same_tier) / count,
        "scouting_level": sum(c.infrastructure.youth.scouting_level for c in same_tier) / count,
    }


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
    return True, f"{player.full_name} promoted to the first team on a {years}-year deal."


def get_player_contract_demands(player, buyer_club):
    player.ensure_contract_expectations(buyer_club.league_tier)
    return {
        "desired_wage": player.desired_wage,
        "minimum_wage": player.minimum_acceptable_wage,
        "desired_years": max(player.min_contract_years(), min(player.max_contract_years(), player.desired_contract_length)),
        "role": player.squad_role_expectation,
    }


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
    return {
        "success": False,
        "outcome": "counter",
        "message": f"{player.full_name} wants {counter_wage:,} per week for {counter_years} years as {counter_role}.",
        "counter_wage": counter_wage,
        "counter_years": counter_years,
        "counter_role": counter_role,
    }


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
    if buyer.transfer_budget < listing.asking_price or buyer.budget < listing.asking_price:
        return False, "You do not have enough budget to complete the transfer."
    if wage > buyer.wage_budget_weekly * 3:
        return False, "That wage is beyond your wage structure."
    buyer.transfer_budget -= listing.asking_price
    buyer.budget -= listing.asking_price
    seller.budget += listing.asking_price
    seller.players = [p for p in seller.players if p.id != player.id]
    player.wage = int(wage)
    player.contract_years = int(years)
    player.squad_role_expectation = role
    player.season_joined = state.season_number
    buyer.players.append(player)
    buyer.auto_select_squad()
    state.transfer_list = [t for t in state.transfer_list if not (t.player_id == listing.player_id and t.club_id == listing.club_id)]
    return True, f"Transfer completed: {player.full_name} joins {buyer.name}."


def refresh_transfer_market(state):
    listings = []
    for club in state.clubs.values():
        if club.id == state.player_club_id:
            continue
        sellable = sorted([p for p in club.players if not p.is_youth], key=lambda p: (p.overall, p.age), reverse=True)
        for player in sellable[: max(4, min(10, len(sellable) // 3))]:
            price = max(player.value, int(player.overall * player.overall * 1200))
            listings.append(TransferListing(player_id=player.id, club_id=club.id, asking_price=price))
    random.shuffle(listings)
    state.transfer_list = listings[:140]


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
    return {
        "name": player.full_name,
        "age": player.age,
        "position": player.position.value,
        "rating": player.overall,
        "potential": player.potential,
        "nationality": player.nationality,
        "current_club": club.name if club else "Unknown",
        "current_club_short": club.short_name if club else "UNK",
        "goals": player.goals,
        "assists": player.assists,
        "appearances": player.appearances,
        "career_goals": player.career_goals,
        "career_appearances": player.career_appearances,
        "value": player.value,
        "asking_price": listing.asking_price,
        "wage": player.wage,
        "contract_years": player.contract_years,
        "scouted": player.scouted,
        "shortlisted": player.shortlisted,
        "facts": [
            f"Morale: {player.morale}",
            f"Fitness: {player.fitness}",
            f"Passing: {player.passing}",
            f"Shooting: {player.shooting}",
            f"Pace: {player.pace}",
            f"Physical: {player.physical}",
            f"Defending: {player.defending}",
            f"Goalkeeping: {player.goalkeeping}",
        ],
        "scouting_notes": player.scouting_notes or "No scouting report yet.",
    }


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
                player.scouting_notes = (
                    f"Scouting report: {player.full_name} is a {player.position.value.lower()} aged {player.age}. "
                    f"Current rating {player.overall}/99, potential {player.potential}/99. "
                    f"Strengths: passing {player.passing}, shooting {player.shooting}, pace {player.pace}, physical {player.physical}."
                )
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
        state.trophies.append(Trophy(TrophyType.LEAGUE_CHAMPION, state.season_number, state.league.name, state.league.tier))
        state.pending_messages.append(f"Congratulations. {player_club.name} are league champions.")
    elif pos <= max(1, _current_tier(state).promotion_places):
        state.pending_messages.append(f"{player_club.name} secure promotion from {state.league.name}.")
    reset_for_new_season(state)


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
    refresh_transfer_market(state)


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
    return {
        "position": position,
        "total_clubs": tier_size,
        "player_club": player_club,
        "prize_money": prize_money,
        "currency": profile["currency"],
        "messages": list(state.pending_messages),
    }
