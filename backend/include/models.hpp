#pragma once

#include <string>
#include <vector>

namespace fm {

struct PlayerSummary {
    std::string id;
    std::string name;
    std::string position;
    int overall = 1;
    int shooting = 1;
    int passing = 1;
    int defending = 1;
    int pace = 1;
    int physical = 1;
    int goalkeeping = 1;
    int age = 24;
    bool available = true;
};

struct TeamSummary {
    std::string id;
    std::string name;
    int stadium_capacity = 3000;
    int pitch_quality = 3;
    int training_intensity = 3;
    int medical_level = 3;
    std::vector<PlayerSummary> selected_xi;
};

struct MatchInput {
    TeamSummary home;
    TeamSummary away;
    unsigned int seed = 0;
    bool has_seed = false;
};

struct MatchEvent {
    int minute = 0;
    std::string event_type;
    std::string team_name;
    std::string player_name;
    std::string assist_name;
    std::string commentary;
};

struct MatchOutput {
    std::string home_team;
    std::string away_team;
    int home_goals = 0;
    int away_goals = 0;
    int home_shots = 0;
    int away_shots = 0;
    int home_on_target = 0;
    int away_on_target = 0;
    int home_corners = 0;
    int away_corners = 0;
    int home_fouls = 0;
    int away_fouls = 0;
    int home_yellows = 0;
    int away_yellows = 0;
    int home_reds = 0;
    int away_reds = 0;
    int attendance = 0;
    std::vector<MatchEvent> events;
};

struct WeekFixtureInput {
    std::string fixture_id;
    std::string competition_id;
    std::string stage;
    int week = 0;
    TeamSummary home;
    TeamSummary away;
    unsigned int seed = 0;
    bool has_seed = false;
};

struct WeekSimulationInput {
    std::vector<WeekFixtureInput> fixtures;
};

struct WeekFixtureResult {
    std::string fixture_id;
    std::string competition_id;
    std::string stage;
    int week = 0;
    MatchOutput match;
};

struct WeekTableRow {
    std::string club_id;
    std::string club_name;
    int wins = 0;
    int draws = 0;
    int losses = 0;
    int goals_for = 0;
    int goals_against = 0;
    int points = 0;
    int goal_difference = 0;
};

struct WeekSimulationOutput {
    std::vector<WeekFixtureResult> results;
    std::vector<WeekTableRow> table;
};

struct SquadPlayer {
    int id = 0;
    std::string name;
    std::string position;
    bool available = true;
};

struct SquadValidationOutput {
    bool ok = false;
    std::string message;
    std::vector<int> normalized_ids;
};

struct StadiumPreviewInput {
    int current_capacity = 0;
    int target_capacity = 0;
    int seating_level = 1;
    int budget = 0;
    int league_tier = 5;
};

struct StadiumPreviewOutput {
    int current_capacity = 0;
    int target_capacity = 0;
    int cost = 0;
    bool affordable = false;
    std::string spoken_summary;
};

struct ClubRecordsSummary {
    std::string highest_league_finish;
    int most_points = 0;
    int most_goals_scored = 0;
    int best_goal_difference = 0;
    std::string biggest_win;
    std::string biggest_defeat;
    std::string highest_scoring_match;
    std::string all_time_top_scorer;
    int all_time_top_scorer_goals = 0;
    std::string most_appearances_player;
    int most_appearances = 0;
};

struct YouthSummaryPlayer {
    std::string name;
    std::string position;
    int age = 0;
    int overall = 0;
    int potential = 0;
    int desired_wage = 0;
};

struct YouthSummaryOutput {
    int count = 0;
    double average_overall = 0.0;
    int highest_potential = 0;
    std::vector<YouthSummaryPlayer> players;
};

struct TransferWindowOutput {
    bool open = false;
    std::string label;
};

struct ContractEvaluationInput {
    int desired_wage = 0;
    int minimum_wage = 0;
    int desired_years = 0;
    int offered_wage = 0;
    int offered_years = 0;
    int expected_role_value = 50;
    int offered_role_value = 50;
    int join_score = 50;
    int repeated_lowball = 0;
    int insulting_offers = 0;
    std::string player_name;
    std::string desired_role;
    std::string offered_role;
};

struct ContractEvaluationOutput {
    bool success = false;
    std::string outcome;
    std::string message;
    int counter_wage = 0;
    int counter_years = 0;
    std::string counter_role;
};

MatchInput parse_match_input_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_match_output_json(const MatchOutput& output);
MatchOutput simulate_match(const MatchInput& input);

WeekSimulationInput parse_week_input_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_week_output_json(const WeekSimulationOutput& output);
WeekSimulationOutput simulate_week(const WeekSimulationInput& input);

std::vector<SquadPlayer> parse_roster_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_squad_validation_json(const SquadValidationOutput& output);
StadiumPreviewInput parse_stadium_preview_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_stadium_preview_json(const StadiumPreviewOutput& output);
ClubRecordsSummary summarize_records_json_text(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_records_summary_json(const ClubRecordsSummary& out);
YouthSummaryOutput summarize_youth_json_text(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_youth_summary_json(const YouthSummaryOutput& out);
TransferWindowOutput transfer_window_status_from_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_transfer_window_json(const TransferWindowOutput& out);
ContractEvaluationInput parse_contract_evaluation_json(const std::string& text, bool& ok, std::string& error_message);
std::string serialize_contract_evaluation_json(const ContractEvaluationOutput& out);

std::string validate_selected_xi_json(const std::vector<int>& player_ids, const std::string& roster_json);
std::string validate_squad_json(const std::string& squad_json);
std::string preview_stadium_upgrade_json(const std::string& stadium_json);
std::string summarize_club_records_json(const std::string& records_json);
std::string summarize_youth_players_json(const std::string& youth_json);
std::string get_transfer_window_status_json(const std::string& date_json);
std::string evaluate_contract_offer_json(const std::string& contract_json);

} // namespace fm
