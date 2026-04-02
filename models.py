"""Data models for Football Manager 26 - Accessible Edition."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class Position(Enum):
    GK = "Goalkeeper"
    DEF = "Defender"
    MID = "Midfielder"
    FWD = "Forward"


class Formation(Enum):
    F442 = "4-4-2"
    F433 = "4-3-3"
    F352 = "3-5-2"
    F4231 = "4-2-3-1"
    F532 = "5-3-2"
    F451 = "4-5-1"


FORMATION_SLOTS = {
    Formation.F442: {Position.GK: 1, Position.DEF: 4, Position.MID: 4, Position.FWD: 2},
    Formation.F433: {Position.GK: 1, Position.DEF: 4, Position.MID: 3, Position.FWD: 3},
    Formation.F352: {Position.GK: 1, Position.DEF: 3, Position.MID: 5, Position.FWD: 2},
    Formation.F4231: {Position.GK: 1, Position.DEF: 4, Position.MID: 5, Position.FWD: 1},
    Formation.F532: {Position.GK: 1, Position.DEF: 5, Position.MID: 3, Position.FWD: 2},
    Formation.F451: {Position.GK: 1, Position.DEF: 4, Position.MID: 5, Position.FWD: 1},
}


class Mentality(Enum):
    DEFENSIVE = "Defensive"
    CAUTIOUS = "Cautious"
    BALANCED = "Balanced"
    ATTACKING = "Attacking"
    ALL_OUT = "All-Out Attack"


class PlayStyle(Enum):
    DIRECT = "Direct"
    POSSESSION = "Possession"
    COUNTER = "Counter-Attack"


class TrophyType(Enum):
    LEAGUE_CHAMPION = "League Champion"
    PLAYOFF_WINNER = "Play-Off Winner"
    DOMESTIC_CUP = "Domestic Cup"
    LEAGUE_CUP = "League Cup"
    CHAMPIONS_LEAGUE = "Champions League"
    EUROPA_LEAGUE = "Europa League"
    CONFERENCE_LEAGUE = "Conference League"
    SUPER_CUP = "Super Cup"
    PROMOTION = "Promotion"


class CompetitionType(Enum):
    LEAGUE = "league"
    DOMESTIC_CUP = "domestic_cup"
    CONTINENTAL_CUP = "continental_cup"
    SUPER_CUP = "super_cup"
    PLAYOFF = "playoff"


class MessageType(Enum):
    SCOUT = "Scout Report"
    FINANCE = "Finance Report"
    TRANSFER = "Transfer"
    BOARD = "Board"
    COMPETITION = "Competition"
    YOUTH = "Youth Academy"
    SYSTEM = "System"


@dataclass
class Trophy:
    trophy_type: TrophyType
    season: int
    league_name: str
    tier: int
    competition_id: str = ""
    country: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ClubRecordBook:
    highest_league_finish: int = 999
    most_points: int = 0
    most_goals_scored: int = 0
    best_goal_difference: int = -999
    biggest_win: str = "None"
    biggest_defeat: str = "None"
    highest_scoring_match: str = "None"
    longest_winning_streak: int = 0
    longest_unbeaten_streak: int = 0
    all_time_top_scorer: str = "None"
    all_time_top_scorer_goals: int = 0
    most_appearances_player: str = "None"
    most_appearances: int = 0
    current_winning_streak: int = 0
    current_unbeaten_streak: int = 0


@dataclass
class Stadium:
    seating_level: int = 1
    pitch_quality: int = 3
    facilities_level: int = 3
    club_shop_level: int = 0
    cafe_level: int = 0
    hospitality_level: int = 0
    parking_level: int = 1
    fan_zone_level: int = 0


@dataclass
class TrainingFacility:
    level: int = 3
    intensity: int = 3
    medical_level: int = 3
    training_ground_level: int = 3
    sports_science_level: int = 2


@dataclass
class YouthAcademy:
    level: int = 3
    recruitment_level: int = 3
    scouting_level: int = 3


@dataclass
class Infrastructure:
    stadium: Stadium = field(default_factory=Stadium)
    training: TrainingFacility = field(default_factory=TrainingFacility)
    youth: YouthAcademy = field(default_factory=YouthAcademy)

    @property
    def pitch_quality(self):
        return self.stadium.pitch_quality

    @property
    def training_level(self):
        return self.training.level

    @property
    def youth_academy_level(self):
        return self.youth.level

    def stadium_seating_upgrade_cost(self, current_capacity):
        if self.stadium.seating_level >= 10:
            return 0
        return 75000 + current_capacity * 6 + self.stadium.seating_level * 25000

    def pitch_upgrade_cost(self):
        if self.stadium.pitch_quality >= 10:
            return 0
        return 20000 + (self.stadium.pitch_quality + 1) * 25000

    def facilities_upgrade_cost(self):
        if self.stadium.facilities_level >= 10:
            return 0
        return 30000 + (self.stadium.facilities_level + 1) * 30000

    def club_shop_upgrade_cost(self):
        if self.stadium.club_shop_level >= 5:
            return 0
        return 25000 + (self.stadium.club_shop_level + 1) * 20000

    def cafe_upgrade_cost(self):
        if self.stadium.cafe_level >= 5:
            return 0
        return 22000 + (self.stadium.cafe_level + 1) * 18000

    def hospitality_upgrade_cost(self):
        if self.stadium.hospitality_level >= 5:
            return 0
        return 35000 + (self.stadium.hospitality_level + 1) * 30000

    def parking_upgrade_cost(self):
        if self.stadium.parking_level >= 5:
            return 0
        return 18000 + (self.stadium.parking_level + 1) * 15000

    def fan_zone_upgrade_cost(self):
        if self.stadium.fan_zone_level >= 5:
            return 0
        return 20000 + (self.stadium.fan_zone_level + 1) * 17000

    def training_upgrade_cost(self):
        if self.training.level >= 10:
            return 0
        return 30000 + (self.training.level + 1) * 35000

    def medical_upgrade_cost(self):
        if self.training.medical_level >= 10:
            return 0
        return 25000 + (self.training.medical_level + 1) * 25000

    def training_ground_upgrade_cost(self):
        if self.training.training_ground_level >= 10:
            return 0
        return 28000 + (self.training.training_ground_level + 1) * 28000

    def sports_science_upgrade_cost(self):
        if self.training.sports_science_level >= 10:
            return 0
        return 26000 + (self.training.sports_science_level + 1) * 24000

    def youth_upgrade_cost(self):
        if self.youth.level >= 10:
            return 0
        return 25000 + (self.youth.level + 1) * 30000

    def youth_recruitment_upgrade_cost(self):
        if self.youth.recruitment_level >= 10:
            return 0
        return 20000 + (self.youth.recruitment_level + 1) * 25000

    def scouting_upgrade_cost(self):
        if self.youth.scouting_level >= 10:
            return 0
        return 22000 + (self.youth.scouting_level + 1) * 23000


@dataclass
class Player:
    id: str
    first_name: str
    last_name: str
    age: int
    nationality: str
    position: Position
    goalkeeping: int = 1
    defending: int = 1
    passing: int = 1
    shooting: int = 1
    pace: int = 1
    physical: int = 1
    morale: int = 14
    fitness: int = 100
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    appearances: int = 0
    career_goals: int = 0
    career_appearances: int = 0
    injured_weeks: int = 0
    suspended_matches: int = 0
    value: int = 0
    wage: int = 0
    contract_years: int = 2
    season_joined: int = 1
    is_youth: bool = False
    potential: int = 50
    squad_role_expectation: str = "Rotation"
    minimum_acceptable_wage: int = 0
    desired_wage: int = 0
    desired_contract_length: int = 2
    willingness_to_join: int = 50
    shortlisted: bool = False
    scouted: bool = False
    scouting_notes: str = ""
    transfer_listed: bool = False
    asking_price_override: int = 0

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def overall(self):
        if self.position == Position.GK:
            return round(self.goalkeeping * 0.45 + self.physical * 0.2 + self.passing * 0.1 + self.pace * 0.1 + self.defending * 0.15)
        elif self.position == Position.DEF:
            return round(self.defending * 0.35 + self.physical * 0.2 + self.pace * 0.15 + self.passing * 0.2 + self.shooting * 0.1)
        elif self.position == Position.MID:
            return round(self.passing * 0.3 + self.shooting * 0.15 + self.physical * 0.15 + self.pace * 0.15 + self.defending * 0.25)
        else:
            return round(self.shooting * 0.35 + self.pace * 0.25 + self.physical * 0.15 + self.passing * 0.15 + self.defending * 0.1)

    @property
    def is_available(self):
        return self.injured_weeks == 0 and self.suspended_matches == 0

    def wage_demand(self, tier):
        base = self.overall * self.overall * max(1, 6 - tier) * 3
        return max(100, int(base))

    def min_contract_years(self):
        if self.age >= 32:
            return 1
        elif self.age >= 28:
            return 1
        return 2

    def max_contract_years(self):
        if self.age >= 34:
            return 1
        elif self.age >= 31:
            return 2
        return 4

    def ensure_contract_expectations(self, tier):
        if self.minimum_acceptable_wage <= 0:
            self.minimum_acceptable_wage = max(100, int(self.wage_demand(tier) * 0.85))
        if self.desired_wage <= 0:
            self.desired_wage = max(self.minimum_acceptable_wage, int(self.wage_demand(tier) * 1.05))
        self.desired_contract_length = max(self.min_contract_years(), min(self.max_contract_years(), self.desired_contract_length or 2))
        self.willingness_to_join = max(1, min(100, self.willingness_to_join or 50))
        if not self.squad_role_expectation:
            self.squad_role_expectation = "Rotation"
        if self.potential < self.overall:
            self.potential = min(99, self.overall + 2)


@dataclass
class Tactic:
    formation: Formation = Formation.F442
    mentality: Mentality = Mentality.BALANCED
    style: PlayStyle = PlayStyle.DIRECT


@dataclass
class Club:
    id: str
    name: str
    short_name: str
    country: str
    league_tier: int
    reputation: int
    budget: int
    wage_budget_weekly: int
    stadium_name: str
    stadium_capacity: int
    players: List[Player] = field(default_factory=list)
    tactic: Tactic = field(default_factory=Tactic)
    infrastructure: Infrastructure = field(default_factory=Infrastructure)
    is_player_club: bool = False
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    sponsor_income_weekly: int = 0
    ticket_price: int = 10
    debt: int = 0
    max_debt: int = 100000
    transfer_budget: int = 0
    balance: int = 0
    weekly_wage_commitment: int = 0
    youth_team: List[Player] = field(default_factory=list)
    records: ClubRecordBook = field(default_factory=ClubRecordBook)
    selected_squad_ids: List[str] = field(default_factory=list)
    manager_name: str = "Manager"
    shortlist_player_ids: List[str] = field(default_factory=list)
    transfer_spending_limit: int = 0
    sold_players_income_season: int = 0
    bought_players_spend_season: int = 0

    @property
    def points(self):
        return self.wins * 3 + self.draws

    @property
    def played(self):
        return self.wins + self.draws + self.losses

    @property
    def gd(self):
        return self.goals_for - self.goals_against

    @property
    def total_wages(self):
        return sum(p.wage for p in self.players if not p.is_youth)

    def reset_season_stats(self):
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.goals_for = 0
        self.goals_against = 0
        self.records.current_winning_streak = 0
        self.records.current_unbeaten_streak = 0
        self.sold_players_income_season = 0
        self.bought_players_spend_season = 0
        for p in self.players + self.youth_team:
            p.goals = 0
            p.assists = 0
            p.yellow_cards = 0
            p.red_cards = 0
            p.appearances = 0
            p.injured_weeks = 0
            p.suspended_matches = 0

    def ensure_financial_fields(self):
        if self.transfer_budget <= 0:
            self.transfer_budget = max(0, int(self.budget * 0.35))
        if self.transfer_spending_limit <= 0:
            self.transfer_spending_limit = self.transfer_budget
        self.balance = self.budget
        self.weekly_wage_commitment = self.total_wages
        if not self.selected_squad_ids:
            self.auto_select_squad()
        if not self.manager_name:
            self.manager_name = "Manager"
        if self.shortlist_player_ids is None:
            self.shortlist_player_ids = []

    def auto_select_squad(self):
        available = [p for p in self.players if p.is_available]
        available.sort(key=lambda p: (p.position.value, -p.overall))
        by_pos = {
            Position.GK: sorted([p for p in available if p.position == Position.GK], key=lambda p: -p.overall),
            Position.DEF: sorted([p for p in available if p.position == Position.DEF], key=lambda p: -p.overall),
            Position.MID: sorted([p for p in available if p.position == Position.MID], key=lambda p: -p.overall),
            Position.FWD: sorted([p for p in available if p.position == Position.FWD], key=lambda p: -p.overall),
        }
        selected = []
        selected.extend([p.id for p in by_pos[Position.GK][:1]])
        selected.extend([p.id for p in by_pos[Position.DEF][:4]])
        selected.extend([p.id for p in by_pos[Position.MID][:4]])
        selected.extend([p.id for p in by_pos[Position.FWD][:2]])
        if len(selected) < 11:
            extras = [p.id for p in sorted(available, key=lambda p: -p.overall) if p.id not in selected]
            selected.extend(extras[: 11 - len(selected)])
        self.selected_squad_ids = selected[:11]


class EventType(Enum):
    KICK_OFF = "Kick Off"
    GOAL = "Goal"
    OWN_GOAL = "Own Goal"
    SHOT_SAVED = "Shot Saved"
    SHOT_WIDE = "Shot Wide"
    FOUL = "Foul"
    YELLOW_CARD = "Yellow Card"
    RED_CARD = "Red Card"
    CORNER = "Corner"
    INJURY = "Injury"
    SUBSTITUTION = "Substitution"
    HALF_TIME = "Half Time"
    FULL_TIME = "Full Time"
    PENALTY_SCORED = "Penalty Scored"
    PENALTY_MISSED = "Penalty Missed"


@dataclass
class MatchEvent:
    minute: int
    event_type: EventType
    team_name: str = ""
    player_name: str = ""
    assist_name: str = ""
    commentary: str = ""


@dataclass
class MatchResult:
    home_team: str
    away_team: str
    home_goals: int = 0
    away_goals: int = 0
    events: List[MatchEvent] = field(default_factory=list)
    home_shots: int = 0
    away_shots: int = 0
    home_on_target: int = 0
    away_on_target: int = 0
    home_corners: int = 0
    away_corners: int = 0
    home_fouls: int = 0
    away_fouls: int = 0
    home_yellows: int = 0
    away_yellows: int = 0
    home_reds: int = 0
    away_reds: int = 0
    attendance: int = 0

    @property
    def score_line(self):
        return f"{self.home_team} {self.home_goals} - {self.away_goals} {self.away_team}"


@dataclass
class Fixture:
    home_id: str
    away_id: str
    week: int
    competition_id: str = "league_main"
    stage: str = "League"
    played: bool = False
    result: Optional[MatchResult] = None


@dataclass
class TransferListing:
    player_id: str
    club_id: str
    asking_price: int


@dataclass
class IncomingTransferOffer:
    id: str
    player_id: str
    buyer_club_id: str
    seller_club_id: str
    fee: int
    week_created: int
    status: str = "pending"


@dataclass
class InboxMessage:
    id: str
    week: int
    season: int
    subject: str
    body: str
    message_type: MessageType = MessageType.SYSTEM
    read: bool = False
    related_player_id: str = ""
    related_club_id: str = ""
    action_required: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class LeagueSeason:
    name: str
    country: str
    tier: int
    club_ids: List[str] = field(default_factory=list)
    fixtures: List[Fixture] = field(default_factory=list)
    current_week: int = 1
    total_weeks: int = 38


@dataclass
class FinanceRecord:
    week: int
    description: str
    amount: int


@dataclass
class Competition:
    id: str
    name: str
    competition_type: CompetitionType
    country: str
    level: str = "domestic"
    tier: int = 1
    club_ids: List[str] = field(default_factory=list)
    fixtures: List[Fixture] = field(default_factory=list)
    current_round: str = ""
    active: bool = True
    winner_club_id: str = ""
    runner_up_club_id: str = ""
    qualification_places: int = 0
    rounds: List[str] = field(default_factory=list)
    qualified_club_ids: List[str] = field(default_factory=list)
    entry_rules: Dict[str, Any] = field(default_factory=dict)
    slot_rules: Dict[str, Any] = field(default_factory=dict)
    scheduled_weeks: List[int] = field(default_factory=list)
    draw_state: Dict[str, Any] = field(default_factory=dict)
    draw_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeagueTier:
    country: str
    name: str
    tier: int
    club_ids: List[str] = field(default_factory=list)
    promotion_places: int = 0
    playoff_places: List[int] = field(default_factory=list)
    relegation_places: int = 0


@dataclass
class GameState:
    player_club_id: str = ""
    clubs: Dict[str, Club] = field(default_factory=dict)
    league: Optional[LeagueSeason] = None
    season_number: int = 1
    transfer_list: List[TransferListing] = field(default_factory=list)
    finance_history: List[FinanceRecord] = field(default_factory=list)
    season_over: bool = False
    trophies: List[Trophy] = field(default_factory=list)
    youth_players: List[Player] = field(default_factory=list)
    competitions: List[Competition] = field(default_factory=list)
    league_system: List[LeagueTier] = field(default_factory=list)
    continental_qualification: Dict[str, List[str]] = field(default_factory=dict)
    pending_messages: List[str] = field(default_factory=list)
    current_date: str = "2026-07-01"
    country: str = "England"
    inbox: List[InboxMessage] = field(default_factory=list)
    incoming_transfer_offers: List[IncomingTransferOffer] = field(default_factory=list)

    def ensure_defaults(self):
        for club in self.clubs.values():
            if club.infrastructure is None:
                club.infrastructure = Infrastructure()
            if club.records is None:
                club.records = ClubRecordBook()
            club.ensure_financial_fields()
            for player in club.players + club.youth_team:
                player.ensure_contract_expectations(club.league_tier)
                if player.is_youth:
                    player.is_youth = True
                if player.shortlisted is None:
                    player.shortlisted = False
                if player.scouted is None:
                    player.scouted = False
                if player.scouting_notes is None:
                    player.scouting_notes = ""
                if player.transfer_listed is None:
                    player.transfer_listed = False
                if player.asking_price_override is None:
                    player.asking_price_override = 0
        if self.competitions is None:
            self.competitions = []
        if self.league_system is None:
            self.league_system = []
        if self.continental_qualification is None:
            self.continental_qualification = {}
        if self.pending_messages is None:
            self.pending_messages = []
        if not self.current_date:
            self.current_date = "2026-07-01"
        if not self.country and self.league:
            self.country = self.league.country
        if self.inbox is None:
            self.inbox = []
        if self.incoming_transfer_offers is None:
            self.incoming_transfer_offers = []
        return self
