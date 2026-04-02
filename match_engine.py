"""Match simulation engine for Football Manager 26."""

import random
from models import (
    Club, MatchEvent, MatchResult, EventType, Position,
    Mentality, FORMATION_SLOTS,
)

GOAL_TEMPLATES = [
    "{player} scores for {team}! A well-taken goal.",
    "GOAL! {player} finds the back of the net for {team}!",
    "{player} with a brilliant finish! The ball is in the net!",
    "It's a goal! {player} puts {team} ahead!",
    "{player} scores! What a moment for {team}!",
    "Clinical finish from {player}! {team} celebrate!",
    "The ball hits the net! {player} has scored for {team}!",
]
ASSIST_TEMPLATES = [
    " Assisted by {assist}.",
    " Great pass from {assist} to set up the goal.",
    " {assist} with the assist.",
    " Brilliant play from {assist} to create the chance.",
]
SHOT_SAVED_TEMPLATES = [
    "{player} shoots but it's saved by the goalkeeper.",
    "Good save! {player}'s shot is kept out.",
    "{player} forces a save from the keeper.",
    "The goalkeeper gets down well to stop {player}'s effort.",
]
SHOT_WIDE_TEMPLATES = [
    "{player} shoots but it goes wide of the post.",
    "{player}'s effort sails over the bar.",
    "Off target! {player} can't find the goal.",
    "{player} blazes it over from a good position.",
]
FOUL_TEMPLATES = [
    "Foul by {player} of {team}.",
    "{player} commits a foul. Free kick awarded.",
    "The referee blows for a foul on {player}.",
]
YELLOW_TEMPLATES = [
    "Yellow card! {player} of {team} is booked.",
    "{player} receives a yellow card for that challenge.",
    "The referee shows yellow to {player}.",
]
RED_TEMPLATES = [
    "RED CARD! {player} of {team} is sent off!",
    "{player} receives a straight red card! {team} down to {count} men!",
    "The referee shows red! {player} must leave the field!",
]
CORNER_TEMPLATES = [
    "Corner kick to {team}.",
    "{team} win a corner.",
]
INJURY_TEMPLATES = [
    "{player} goes down injured. The physio is called on.",
    "Concern for {team} as {player} appears to be hurt.",
]
PENALTY_SCORED_TEMPLATES = [
    "PENALTY SCORED! {player} sends the keeper the wrong way!",
    "{player} converts from the spot! Cool as you like!",
]
PENALTY_MISSED_TEMPLATES = [
    "PENALTY MISSED! {player} puts it wide!",
    "The goalkeeper saves the penalty from {player}!",
    "{player} hits the post from the spot!",
]


def get_starting_eleven(club):
    formation = club.tactic.formation
    slots = FORMATION_SLOTS[formation]
    available = [p for p in club.players if p.is_available]
    starting = []
    for pos, count in slots.items():
        candidates = sorted([p for p in available if p.position == pos and p not in starting], key=lambda p: p.overall, reverse=True)
        for i in range(count):
            if i < len(candidates):
                starting.append(candidates[i])
            else:
                remaining = [p for p in available if p not in starting]
                if remaining:
                    remaining.sort(key=lambda p: p.overall, reverse=True)
                    starting.append(remaining[0])
    return starting[:11]


def calculate_team_strength(club, starting_eleven=None):
    if starting_eleven is None:
        starting_eleven = get_starting_eleven(club)
    if not starting_eleven:
        return 1.0, 1.0, 1.0

    base = sum(p.overall for p in starting_eleven) / len(starting_eleven)
    attack_mod = 1.0
    defence_mod = 1.0
    mentality = club.tactic.mentality
    if mentality == Mentality.DEFENSIVE:
        attack_mod = 0.85
        defence_mod = 1.15
    elif mentality == Mentality.CAUTIOUS:
        attack_mod = 0.92
        defence_mod = 1.08
    elif mentality == Mentality.ATTACKING:
        attack_mod = 1.12
        defence_mod = 0.88
    elif mentality == Mentality.ALL_OUT:
        attack_mod = 1.25
        defence_mod = 0.75
    return base, attack_mod, defence_mod


def _pick_scorer(players):
    if not players:
        return None
    weights = []
    for p in players:
        if p.position == Position.FWD:
            w = p.shooting * 3 + p.pace
        elif p.position == Position.MID:
            w = p.shooting * 2 + p.passing
        elif p.position == Position.DEF:
            w = p.shooting + p.physical
        else:
            w = 1
        weights.append(max(1, w))
    return random.choices(players, weights=weights, k=1)[0]


def _pick_assister(players, scorer):
    candidates = [p for p in players if p != scorer and p.position != Position.GK]
    if not candidates:
        return None
    weights = [max(1, p.passing * 2 + p.pace) for p in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def _pick_any(players):
    if not players:
        return None
    outfield = [p for p in players if p.position != Position.GK]
    pool = outfield if outfield else players
    return random.choice(pool) if pool else None


def _injury_chance(club, player):
    infra = club.infrastructure
    intensity = infra.training.intensity
    medical = infra.training.medical_level
    pitch = infra.stadium.pitch_quality
    age_mod = 0.01 if player.age >= 30 else 0
    return max(0.005, 0.015 + intensity * 0.01 - medical * 0.004 - pitch * 0.002 + age_mod)


def simulate_match(home_club, away_club):
    home_xi = get_starting_eleven(home_club)
    away_xi = get_starting_eleven(away_club)
    home_base, home_atk, home_def = calculate_team_strength(home_club, home_xi)
    away_base, away_atk, away_def = calculate_team_strength(away_club, away_xi)

    home_base *= 1.08 + (home_club.infrastructure.stadium.pitch_quality * 0.005)

    events = []
    home_goals = 0
    away_goals = 0
    stats = {
        "home_shots": 0, "away_shots": 0,
        "home_on_target": 0, "away_on_target": 0,
        "home_corners": 0, "away_corners": 0,
        "home_fouls": 0, "away_fouls": 0,
        "home_yellows": 0, "away_yellows": 0,
        "home_reds": 0, "away_reds": 0,
    }
    home_red_count = 0
    away_red_count = 0

    events.append(MatchEvent(0, EventType.KICK_OFF, commentary=f"Kick off. {home_club.name} versus {away_club.name}."))

    for minute in range(1, 91):
        if minute == 46:
            events.append(MatchEvent(45, EventType.HALF_TIME, commentary=f"Half time. {home_club.name} {home_goals}, {away_club.name} {away_goals}."))

        if random.random() > 0.30:
            continue

        home_chance = home_base * home_atk / max(1, away_base * away_def)
        away_chance = away_base * away_atk / max(1, home_base * home_def)
        total = home_chance + away_chance
        is_home = random.random() < (home_chance / total)

        atk_team = home_club if is_home else away_club
        def_team = away_club if is_home else home_club
        atk_xi = home_xi if is_home else away_xi
        def_xi = away_xi if is_home else home_xi
        prefix = "home" if is_home else "away"

        if is_home and home_red_count > 0:
            home_base *= 0.95
        elif not is_home and away_red_count > 0:
            away_base *= 0.95

        roll = random.random()

        if roll < 0.15:
            stats[f"{prefix}_shots"] += 1
            goal_chance = 0.33 + (home_base if is_home else away_base) * 0.01
            if random.random() < goal_chance:
                is_penalty = random.random() < 0.08
                scorer = _pick_scorer(atk_xi)
                if scorer:
                    scorer.appearances = max(scorer.appearances, 1)
                if is_penalty:
                    if random.random() < 0.78:
                        if is_home:
                            home_goals += 1
                        else:
                            away_goals += 1
                        stats[f"{prefix}_on_target"] += 1
                        if scorer:
                            scorer.goals += 1
                        commentary = f"{minute}' Goal for {atk_team.name}. Scorer: {(scorer.full_name if scorer else 'Unknown')}. Score: {home_club.name} {home_goals}, {away_club.name} {away_goals}."
                        events.append(MatchEvent(minute, EventType.PENALTY_SCORED, atk_team.name, scorer.full_name if scorer else "", commentary=commentary))
                    else:
                        commentary = f"{minute}' Penalty missed by {(scorer.full_name if scorer else 'Unknown')} of {atk_team.name}."
                        events.append(MatchEvent(minute, EventType.PENALTY_MISSED, atk_team.name, scorer.full_name if scorer else "", commentary=commentary))
                else:
                    assister = _pick_assister(atk_xi, scorer) if scorer else None
                    if is_home:
                        home_goals += 1
                    else:
                        away_goals += 1
                    stats[f"{prefix}_on_target"] += 1
                    if scorer:
                        scorer.goals += 1
                    assist_text = f" Assist by {assister.full_name}." if assister else ""
                    if assister:
                        assister.assists += 1
                        assister.appearances = max(assister.appearances, 1)
                    commentary = f"{minute}' Goal for {atk_team.name}. Scorer: {(scorer.full_name if scorer else 'Unknown')}.{assist_text} Score: {home_club.name} {home_goals}, {away_club.name} {away_goals}."
                    events.append(MatchEvent(minute, EventType.GOAL, atk_team.name, scorer.full_name if scorer else "", assister.full_name if assister else "", commentary))
            else:
                shooter = _pick_scorer(atk_xi)
                if random.random() < 0.5:
                    stats[f"{prefix}_on_target"] += 1
                    commentary = f"{minute}' {(shooter.full_name if shooter else 'A player')} has a shot saved for {atk_team.name}."
                    events.append(MatchEvent(minute, EventType.SHOT_SAVED, atk_team.name, shooter.full_name if shooter else "", commentary=commentary))
                else:
                    commentary = f"{minute}' {(shooter.full_name if shooter else 'A player')} shoots wide for {atk_team.name}."
                    events.append(MatchEvent(minute, EventType.SHOT_WIDE, atk_team.name, shooter.full_name if shooter else "", commentary=commentary))

        elif roll < 0.30:
            stats[f"{prefix}_corners"] += 1
            commentary = f"{minute}' Corner to {atk_team.name}."
            events.append(MatchEvent(minute, EventType.CORNER, atk_team.name, commentary=commentary))

        elif roll < 0.55:
            fouler = _pick_any(def_xi)
            stats[f"{'away' if is_home else 'home'}_fouls"] += 1
            commentary = f"{minute}' Foul by {(fouler.full_name if fouler else 'a player')} of {def_team.name}."
            events.append(MatchEvent(minute, EventType.FOUL, def_team.name, fouler.full_name if fouler else "", commentary=commentary))
            card_roll = random.random()
            if card_roll < 0.15 and fouler:
                opp = "away" if is_home else "home"
                stats[f"{opp}_yellows"] += 1
                fouler.yellow_cards += 1
                commentary = f"{minute}' Yellow card for {fouler.full_name} of {def_team.name}."
                events.append(MatchEvent(minute, EventType.YELLOW_CARD, def_team.name, fouler.full_name, commentary=commentary))
                if fouler.yellow_cards >= 5:
                    fouler.suspended_matches = 1
            elif card_roll < 0.03 and fouler:
                opp = "away" if is_home else "home"
                stats[f"{opp}_reds"] += 1
                fouler.red_cards += 1
                if is_home:
                    away_red_count += 1
                    count = 11 - away_red_count
                else:
                    home_red_count += 1
                    count = 11 - home_red_count
                fouler.suspended_matches = 3
                commentary = f"{minute}' Red card for {fouler.full_name} of {def_team.name}. {def_team.name} are down to {count} men."
                events.append(MatchEvent(minute, EventType.RED_CARD, def_team.name, fouler.full_name, commentary=commentary))

        elif roll < 0.62:
            player = _pick_any(atk_xi)
            if player and random.random() < _injury_chance(atk_team, player):
                player.injured_weeks = random.randint(1, 5)
                commentary = f"{minute}' Injury concern for {atk_team.name}. {player.full_name} is hurt and may miss {player.injured_weeks} weeks."
                events.append(MatchEvent(minute, EventType.INJURY, atk_team.name, player.full_name, commentary=commentary))

    stoppage = random.randint(2, 5)
    for minute in range(91, 91 + stoppage):
        if random.random() < 0.12:
            is_home = random.random() < 0.5
            atk_team = home_club if is_home else away_club
            atk_xi = home_xi if is_home else away_xi
            prefix = "home" if is_home else "away"
            stats[f"{prefix}_shots"] += 1
            if random.random() < 0.25:
                scorer = _pick_scorer(atk_xi)
                if is_home:
                    home_goals += 1
                else:
                    away_goals += 1
                stats[f"{prefix}_on_target"] += 1
                if scorer:
                    scorer.goals += 1
                commentary = f"90+{minute-90}' Goal for {atk_team.name}. Scorer: {(scorer.full_name if scorer else 'Unknown')}. Score: {home_club.name} {home_goals}, {away_club.name} {away_goals}."
                events.append(MatchEvent(minute, EventType.GOAL, atk_team.name, scorer.full_name if scorer else "", commentary=commentary))

    events.append(MatchEvent(90, EventType.FULL_TIME, commentary=f"Full time. {home_club.name} {home_goals}, {away_club.name} {away_goals}."))

    for p in home_xi + away_xi:
        p.appearances += 1

    base_cap = home_club.stadium_capacity
    fill_pct = random.uniform(0.4, 0.9)
    attendance = int(base_cap * fill_pct)

    return MatchResult(
        home_team=home_club.name,
        away_team=away_club.name,
        home_goals=home_goals,
        away_goals=away_goals,
        events=events,
        attendance=attendance,
        **stats,
    )
