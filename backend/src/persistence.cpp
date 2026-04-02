#include "models.hpp"
#include "nlohmann/json.hpp"

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

namespace fm {

using json = nlohmann::json;

static std::string json_to_string_id(const json& value) {
    if (value.is_string()) return value.get<std::string>();
    if (value.is_number_integer()) return std::to_string(value.get<long long>());
    if (value.is_number_unsigned()) return std::to_string(value.get<unsigned long long>());
    if (value.is_number_float()) {
        const auto v = value.get<double>();
        return std::to_string(static_cast<long long>(std::llround(v)));
    }
    return "";
}

static void from_json(const json& j, PlayerSummary& p) {
    p.id = j.contains("id") ? json_to_string_id(j.at("id")) : "";
    p.name = j.value("name", "");
    p.position = j.value("position", "");
    p.overall = j.value("overall", 1);
    p.shooting = j.value("shooting", 1);
    p.passing = j.value("passing", 1);
    p.defending = j.value("defending", 1);
    p.pace = j.value("pace", 1);
    p.physical = j.value("physical", 1);
    p.goalkeeping = j.value("goalkeeping", 1);
    p.age = j.value("age", 18);
    p.available = j.value("available", true);
}

static void from_json(const json& j, TeamSummary& t) {
    t.id = j.contains("id") ? json_to_string_id(j.at("id")) : "";
    t.name = j.value("name", "");
    t.stadium_capacity = j.value("stadium_capacity", 3000);
    t.pitch_quality = j.value("pitch_quality", 3);
    t.training_intensity = j.value("training_intensity", 3);
    t.medical_level = j.value("medical_level", 3);
    t.selected_xi.clear();
    for (const auto& item : j.value("selected_xi", json::array())) {
        PlayerSummary p;
        from_json(item, p);
        t.selected_xi.push_back(p);
    }
}

static void from_json(const json& j, WeekFixtureInput& f) {
    f.fixture_id = j.value("fixture_id", "");
    f.competition_id = j.value("competition_id", "league_main");
    f.stage = j.value("stage", "League");
    f.week = j.value("week", 0);
    from_json(j.at("home"), f.home);
    from_json(j.at("away"), f.away);
    if (j.contains("seed")) {
        f.seed = j.at("seed").get<unsigned int>();
        f.has_seed = true;
    }
}

static void to_json(json& j, const MatchEvent& e) {
    j = json{{"minute", e.minute}, {"event_type", e.event_type}, {"team_name", e.team_name}, {"player_name", e.player_name}, {"assist_name", e.assist_name}, {"commentary", e.commentary}};
}

static void to_json(json& j, const MatchOutput& o) {
    j = json{{"home_team", o.home_team}, {"away_team", o.away_team}, {"home_goals", o.home_goals}, {"away_goals", o.away_goals}, {"home_shots", o.home_shots}, {"away_shots", o.away_shots}, {"home_on_target", o.home_on_target}, {"away_on_target", o.away_on_target}, {"home_corners", o.home_corners}, {"away_corners", o.away_corners}, {"home_fouls", o.home_fouls}, {"away_fouls", o.away_fouls}, {"home_yellows", o.home_yellows}, {"away_yellows", o.away_yellows}, {"home_reds", o.home_reds}, {"away_reds", o.away_reds}, {"attendance", o.attendance}, {"events", o.events}};
}

static void to_json(json& j, const WeekFixtureResult& r) {
    j = json{{"fixture_id", r.fixture_id}, {"competition_id", r.competition_id}, {"stage", r.stage}, {"week", r.week}, {"match", r.match}};
}

static void to_json(json& j, const WeekTableRow& r) {
    j = json{{"club_id", r.club_id}, {"club_name", r.club_name}, {"wins", r.wins}, {"draws", r.draws}, {"losses", r.losses}, {"goals_for", r.goals_for}, {"goals_against", r.goals_against}, {"points", r.points}, {"goal_difference", r.goal_difference}};
}

MatchInput parse_match_input_json(const std::string& text, bool& ok, std::string& error_message) {
    MatchInput input;
    ok = false;
    error_message.clear();
    try {
        const auto j = json::parse(text);
        from_json(j.at("home"), input.home);
        from_json(j.at("away"), input.away);
        if (j.contains("seed")) {
            input.seed = j.at("seed").get<unsigned int>();
            input.has_seed = true;
        }
        if (input.home.name.empty() || input.away.name.empty()) {
            error_message = "Both teams must have names.";
            return input;
        }
        if (input.home.selected_xi.size() != 11 || input.away.selected_xi.size() != 11) {
            error_message = "Both teams must provide exactly 11 selected players.";
            return input;
        }
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return input;
}

std::string serialize_match_output_json(const MatchOutput& output) {
    json j = output;
    return j.dump();
}

WeekSimulationInput parse_week_input_json(const std::string& text, bool& ok, std::string& error_message) {
    WeekSimulationInput input;
    ok = false;
    error_message.clear();
    try {
        const auto j = json::parse(text);
        const auto arr = j.contains("fixtures") ? j.at("fixtures") : json::array();
        for (const auto& item : arr) {
            WeekFixtureInput fixture;
            from_json(item, fixture);
            if (fixture.home.selected_xi.size() != 11 || fixture.away.selected_xi.size() != 11) {
                error_message = "Every fixture must contain exactly 11 selected players per team.";
                return input;
            }
            input.fixtures.push_back(fixture);
        }
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return input;
}

std::string serialize_week_output_json(const WeekSimulationOutput& output) {
    json j{{"results", output.results}, {"table", output.table}};
    return j.dump();
}

std::vector<SquadPlayer> parse_roster_json(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    std::vector<SquadPlayer> players;
    try {
        const auto j = json::parse(text);
        const auto arr = j.contains("players") ? j.at("players") : j;
        for (const auto& item : arr) {
            SquadPlayer p;
            p.id = item.value("id", 0);
            p.name = item.value("name", "");
            p.position = item.value("position", "");
            p.available = item.value("available", true);
            players.push_back(p);
        }
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return players;
}

std::string serialize_squad_validation_json(const SquadValidationOutput& output) {
    json j{{"ok", output.ok}, {"message", output.message}, {"normalized_ids", output.normalized_ids}};
    return j.dump();
}

StadiumPreviewInput parse_stadium_preview_json(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    StadiumPreviewInput input;
    try {
        const auto j = json::parse(text);
        input.current_capacity = j.value("current_capacity", 0);
        input.target_capacity = j.value("target_capacity", 0);
        input.seating_level = j.value("seating_level", 1);
        input.budget = j.value("budget", 0);
        input.league_tier = j.value("league_tier", 5);
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return input;
}

std::string serialize_stadium_preview_json(const StadiumPreviewOutput& output) {
    json j{{"current_capacity", output.current_capacity}, {"target_capacity", output.target_capacity}, {"cost", output.cost}, {"affordable", output.affordable}, {"spoken_summary", output.spoken_summary}};
    return j.dump();
}

ClubRecordsSummary summarize_records_json_text(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    ClubRecordsSummary out;
    try {
        const auto j = json::parse(text);
        int finish = j.value("highest_league_finish", 999);
        out.highest_league_finish = (finish == 999) ? std::string("Not set") : std::to_string(finish);
        out.most_points = j.value("most_points", 0);
        out.most_goals_scored = j.value("most_goals_scored", 0);
        int gd = j.value("best_goal_difference", -999);
        out.best_goal_difference = (gd == -999) ? 0 : gd;
        out.biggest_win = j.value("biggest_win", "None");
        out.biggest_defeat = j.value("biggest_defeat", "None");
        out.highest_scoring_match = j.value("highest_scoring_match", "None");
        out.all_time_top_scorer = j.value("all_time_top_scorer", "None");
        out.all_time_top_scorer_goals = j.value("all_time_top_scorer_goals", 0);
        out.most_appearances_player = j.value("most_appearances_player", "None");
        out.most_appearances = j.value("most_appearances", 0);
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return out;
}

std::string serialize_records_summary_json(const ClubRecordsSummary& out) {
    json j{{"highest_league_finish", out.highest_league_finish}, {"most_points", out.most_points}, {"most_goals_scored", out.most_goals_scored}, {"best_goal_difference", out.best_goal_difference}, {"biggest_win", out.biggest_win}, {"biggest_defeat", out.biggest_defeat}, {"highest_scoring_match", out.highest_scoring_match}, {"all_time_top_scorer", out.all_time_top_scorer}, {"all_time_top_scorer_goals", out.all_time_top_scorer_goals}, {"most_appearances_player", out.most_appearances_player}, {"most_appearances", out.most_appearances}};
    return j.dump();
}

YouthSummaryOutput summarize_youth_json_text(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    YouthSummaryOutput out;
    try {
        const auto j = json::parse(text);
        const auto arr = j.contains("players") ? j.at("players") : j;
        int total = 0;
        for (const auto& item : arr) {
            YouthSummaryPlayer p;
            p.name = item.value("name", "");
            p.position = item.value("position", "");
            p.age = item.value("age", 0);
            p.overall = item.value("overall", 0);
            p.potential = item.value("potential", 0);
            p.desired_wage = item.value("desired_wage", 0);
            out.players.push_back(p);
            total += p.overall;
            out.highest_potential = std::max(out.highest_potential, p.potential);
        }
        out.count = static_cast<int>(out.players.size());
        out.average_overall = out.count ? static_cast<double>(total) / static_cast<double>(out.count) : 0.0;
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return out;
}

std::string serialize_youth_summary_json(const YouthSummaryOutput& out) {
    json players = json::array();
    for (const auto& p : out.players) {
        players.push_back(json{{"name", p.name}, {"position", p.position}, {"age", p.age}, {"overall", p.overall}, {"potential", p.potential}, {"desired_wage", p.desired_wage}});
    }
    json j{{"count", out.count}, {"average_overall", out.average_overall}, {"highest_potential", out.highest_potential}, {"players", players}};
    return j.dump();
}

TransferWindowOutput transfer_window_status_from_json(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    TransferWindowOutput out;
    try {
        const auto j = json::parse(text);
        const std::string country = j.value("country", "England");
        const std::string current_date = j.value("current_date", "2026-07-01");
        if (current_date.size() < 10) {
            error_message = "Invalid current_date format.";
            return out;
        }
        const int year = std::stoi(current_date.substr(0, 4));
        const int month = std::stoi(current_date.substr(5, 2));
        const int day = std::stoi(current_date.substr(8, 2));
        auto in_range = [&](int sm, int sd, int em, int ed) {
            if (month < sm || month > em) return false;
            if (month == sm && day < sd) return false;
            if (month == em && day > ed) return false;
            return true;
        };
        if (country == "England") {
            if (in_range(6, 14, 8, 30)) {
                out.open = true;
                out.label = "Open - Summer Window until " + std::to_string(year) + "-08-30";
            } else if (in_range(1, 1, 1, 31)) {
                out.open = true;
                out.label = "Open - Winter Window until " + std::to_string(year) + "-01-31";
            } else if (month < 6 || (month == 6 && day < 14)) {
                out.label = "Closed - Next: Summer Window opens " + std::to_string(year) + "-06-14";
            } else {
                out.label = "Closed - Next: Winter Window opens " + std::to_string(year + 1) + "-01-01";
            }
        } else if (country == "Spain") {
            if (in_range(7, 1, 8, 31)) {
                out.open = true;
                out.label = "Open - Summer Window until " + std::to_string(year) + "-08-31";
            } else if (in_range(1, 2, 1, 31)) {
                out.open = true;
                out.label = "Open - Winter Window until " + std::to_string(year) + "-01-31";
            } else if (month < 7 || (month == 7 && day < 1)) {
                out.label = "Closed - Next: Summer Window opens " + std::to_string(year) + "-07-01";
            } else {
                out.label = "Closed - Next: Winter Window opens " + std::to_string(year + 1) + "-01-02";
            }
        } else {
            if (in_range(7, 1, 8, 31)) {
                out.open = true;
                out.label = "Open - Summer Window until " + std::to_string(year) + "-08-31";
            } else if (in_range(1, 1, 1, 31)) {
                out.open = true;
                out.label = "Open - Winter Window until " + std::to_string(year) + "-01-31";
            } else if (month < 7 || (month == 7 && day < 1)) {
                out.label = "Closed - Next: Summer Window opens " + std::to_string(year) + "-07-01";
            } else {
                out.label = "Closed - Next: Winter Window opens " + std::to_string(year + 1) + "-01-01";
            }
        }
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return out;
}

std::string serialize_transfer_window_json(const TransferWindowOutput& out) {
    json j{{"open", out.open}, {"label", out.label}};
    return j.dump();
}

ContractEvaluationInput parse_contract_evaluation_json(const std::string& text, bool& ok, std::string& error_message) {
    ok = false;
    error_message.clear();
    ContractEvaluationInput input;
    try {
        const auto j = json::parse(text);
        input.desired_wage = j.value("desired_wage", 0);
        input.minimum_wage = j.value("minimum_wage", 0);
        input.desired_years = j.value("desired_years", 0);
        input.offered_wage = j.value("offered_wage", 0);
        input.offered_years = j.value("offered_years", 0);
        input.expected_role_value = j.value("expected_role_value", 50);
        input.offered_role_value = j.value("offered_role_value", 50);
        input.join_score = j.value("join_score", 50);
        input.repeated_lowball = j.value("repeated_lowball", 0);
        input.insulting_offers = j.value("insulting_offers", 0);
        input.player_name = j.value("player_name", "Player");
        input.desired_role = j.value("desired_role", "Rotation");
        input.offered_role = j.value("offered_role", "Rotation");
        ok = true;
    } catch (const std::exception& ex) {
        error_message = ex.what();
    }
    return input;
}

std::string serialize_contract_evaluation_json(const ContractEvaluationOutput& out) {
    json j{{"success", out.success}, {"outcome", out.outcome}, {"message", out.message}, {"counter_wage", out.counter_wage}, {"counter_years", out.counter_years}, {"counter_role", out.counter_role}};
    return j.dump();
}

} // namespace fm
