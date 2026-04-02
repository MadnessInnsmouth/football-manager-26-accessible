#include "models.hpp"
#include "nlohmann/json.hpp"

#include <algorithm>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace fm {

using json = nlohmann::json;

static SquadValidationOutput validate_selected_xi_impl(const std::vector<int>& player_ids, const std::vector<SquadPlayer>& roster) {
    SquadValidationOutput out;
    if (static_cast<int>(player_ids.size()) != 11) {
        out.ok = false;
        out.message = "You must select exactly 11 available players.";
        return out;
    }

    std::unordered_map<int, SquadPlayer> by_id;
    for (const auto& p : roster) by_id[p.id] = p;

    std::set<int> seen;
    bool has_gk = false;
    for (int id : player_ids) {
        if (seen.count(id)) {
            out.ok = false;
            out.message = "Duplicate players are not allowed in the starting eleven.";
            return out;
        }
        seen.insert(id);
        auto it = by_id.find(id);
        if (it == by_id.end()) {
            out.ok = false;
            out.message = "One or more selected players do not exist in the supplied roster.";
            return out;
        }
        if (!it->second.available) {
            out.ok = false;
            out.message = "You must select exactly 11 available players.";
            return out;
        }
        if (it->second.position == "Goalkeeper") has_gk = true;
        out.normalized_ids.push_back(id);
    }

    if (!has_gk) {
        out.ok = false;
        out.message = "Your starting eleven must include a goalkeeper.";
        return out;
    }

    out.ok = true;
    out.message = "Starting eleven updated.";
    return out;
}

static StadiumPreviewOutput preview_stadium_upgrade_impl(const StadiumPreviewInput& in) {
    StadiumPreviewOutput out;
    out.current_capacity = in.current_capacity;
    out.target_capacity = std::max(in.current_capacity, in.target_capacity);
    if (out.target_capacity <= in.current_capacity) {
        out.cost = 0;
        out.affordable = true;
        out.spoken_summary = "Choose a target capacity above the current stadium capacity.";
        return out;
    }

    const int increase = out.target_capacity - in.current_capacity;
    out.cost = static_cast<int>(increase * (55 + in.seating_level * 6) + 25000);
    out.affordable = in.budget >= out.cost;

    std::ostringstream ss;
    ss << "Target Capacity: " << out.target_capacity << ". Cost: " << out.cost << ". ";
    ss << (out.affordable ? "You can afford this upgrade." : "You cannot afford this upgrade.");
    out.spoken_summary = ss.str();
    return out;
}

static ContractEvaluationOutput evaluate_contract_offer_impl(const ContractEvaluationInput& in) {
    ContractEvaluationOutput out;
    out.counter_role = in.desired_role;
    out.counter_years = in.desired_years;
    out.counter_wage = std::max(in.minimum_wage, (in.minimum_wage + in.desired_wage) / 2);

    if (in.join_score < 30) {
        out.success = false;
        out.outcome = "rejected";
        out.message = in.player_name + " has no interest in joining your club.";
        return out;
    }
    if (in.insulting_offers >= 2) {
        out.success = false;
        out.outcome = "walked_away";
        out.message = in.player_name + " is offended by the repeated low offers and walks away from negotiations.";
        return out;
    }
    if (in.repeated_lowball >= 3) {
        out.success = false;
        out.outcome = "rejected";
        out.message = in.player_name + " loses patience after repeated low offers and rejects further talks.";
        return out;
    }
    if (in.offered_role_value + 10 < in.expected_role_value) {
        out.success = false;
        out.outcome = "counter";
        out.counter_wage = std::max(in.desired_wage, static_cast<int>(in.desired_wage * 1.05));
        out.message = in.player_name + " wants a bigger squad role: " + in.desired_role + ".";
        return out;
    }
    if (in.offered_wage < static_cast<int>(in.minimum_wage * 0.75)) {
        out.success = false;
        out.outcome = "counter";
        out.message = in.player_name + " rejects the low wage offer and wants a more serious proposal.";
        return out;
    }
    if (in.offered_wage < in.minimum_wage) {
        out.success = false;
        out.outcome = "counter";
        std::ostringstream ss;
        ss << in.player_name << " rejects the wage offer and wants around " << out.counter_wage
           << " per week for " << in.desired_years << " years as a " << in.desired_role << ".";
        out.message = ss.str();
        return out;
    }
    if (in.offered_years != in.desired_years && in.offered_years < 1) {
        out.success = false;
        out.outcome = "counter";
        out.message = in.player_name + " wants a more realistic contract length.";
        return out;
    }

    int role_bonus = (in.offered_role_value == in.expected_role_value) ? 8 : 0;
    int wage_bonus = std::min(20, static_cast<int>(((in.offered_wage - in.minimum_wage) / static_cast<double>(std::max(1, in.minimum_wage))) * 30.0));
    int years_bonus = (in.offered_years == in.desired_years) ? 5 : (in.offered_years >= 1 ? 2 : -5);
    int patience_penalty = std::min(12, in.repeated_lowball * 4);
    int acceptance_score = in.join_score + role_bonus + wage_bonus + years_bonus - patience_penalty;

    if (acceptance_score >= 45) {
        out.success = true;
        out.outcome = "accepted";
        std::ostringstream ss;
        ss << in.player_name << " accepts your offer of " << in.offered_wage
           << " per week for " << in.offered_years << " years as a " << in.offered_role << ".";
        out.message = ss.str();
        out.counter_wage = in.offered_wage;
        out.counter_years = in.offered_years;
        out.counter_role = in.offered_role;
        return out;
    }

    out.success = false;
    out.outcome = "rejected";
    out.message = in.player_name + " declines after considering the offer.";
    return out;
}

std::string validate_selected_xi_json(const std::vector<int>& player_ids, const std::string& roster_json) {
    bool ok = false;
    std::string error;
    auto roster = parse_roster_json(roster_json, ok, error);
    if (!ok) {
        return json{{"ok", false}, {"message", error}, {"normalized_ids", json::array()}}.dump();
    }
    return serialize_squad_validation_json(validate_selected_xi_impl(player_ids, roster));
}

std::string validate_squad_json(const std::string& squad_json) {
    try {
        auto j = json::parse(squad_json);
        std::vector<int> ids = j.value("selected_ids", std::vector<int>{});
        auto roster_json = j.at("roster").dump();
        return validate_selected_xi_json(ids, roster_json);
    } catch (const std::exception& ex) {
        return json{{"ok", false}, {"message", ex.what()}, {"normalized_ids", json::array()}}.dump();
    }
}

std::string preview_stadium_upgrade_json(const std::string& stadium_json) {
    bool ok = false;
    std::string error;
    auto input = parse_stadium_preview_json(stadium_json, ok, error);
    if (!ok) {
        return json{{"current_capacity", 0}, {"target_capacity", 0}, {"cost", 0}, {"affordable", false}, {"spoken_summary", error}}.dump();
    }
    return serialize_stadium_preview_json(preview_stadium_upgrade_impl(input));
}

std::string summarize_club_records_json(const std::string& records_json) {
    bool ok = false;
    std::string error;
    auto out = summarize_records_json_text(records_json, ok, error);
    if (!ok) {
        return json{{"error", error}}.dump();
    }
    return serialize_records_summary_json(out);
}

std::string summarize_youth_players_json(const std::string& youth_json) {
    bool ok = false;
    std::string error;
    auto out = summarize_youth_json_text(youth_json, ok, error);
    if (!ok) {
        return json{{"error", error}, {"count", 0}, {"average_overall", 0.0}, {"highest_potential", 0}, {"players", json::array()}}.dump();
    }
    return serialize_youth_summary_json(out);
}

std::string get_transfer_window_status_json(const std::string& date_json) {
    bool ok = false;
    std::string error;
    auto out = transfer_window_status_from_json(date_json, ok, error);
    if (!ok) {
        return json{{"open", false}, {"label", error}}.dump();
    }
    return serialize_transfer_window_json(out);
}

std::string evaluate_contract_offer_json(const std::string& contract_json) {
    bool ok = false;
    std::string error;
    auto input = parse_contract_evaluation_json(contract_json, ok, error);
    if (!ok) {
        return json{{"success", false}, {"outcome", "error"}, {"message", error}, {"counter_wage", 0}, {"counter_years", 0}, {"counter_role", ""}}.dump();
    }
    return serialize_contract_evaluation_json(evaluate_contract_offer_impl(input));
}

} // namespace fm
