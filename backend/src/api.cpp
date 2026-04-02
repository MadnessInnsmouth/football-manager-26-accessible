#include "fm_engine_api.h"
#include "models.hpp"
#include "nlohmann/json.hpp"

#include <cstdlib>
#include <cstring>
#include <exception>
#include <string>
#include <vector>

namespace {
FM_ResultBuffer make_buffer(const std::string& text) {
    char* mem = static_cast<char*>(std::malloc(text.size() + 1));
    if (!mem) return {nullptr, 0};
    std::memcpy(mem, text.c_str(), text.size() + 1);
    return {mem, static_cast<int>(text.size())};
}

std::string error_json(const std::string& message) {
    return nlohmann::json{{"success", false}, {"error", message}}.dump();
}
}

extern "C" {

FM_ResultBuffer fm_simulate_match_json(const char* match_json) {
    try {
        if (!match_json) return make_buffer(error_json("Null input."));
        bool ok = false;
        std::string error;
        fm::MatchInput input = fm::parse_match_input_json(std::string(match_json), ok, error);
        if (!ok) return make_buffer(error_json(error.empty() ? "Invalid match input." : error));
        fm::MatchOutput output = fm::simulate_match(input);
        return make_buffer(fm::serialize_match_output_json(output));
    } catch (const std::exception& ex) {
        return make_buffer(error_json(std::string("Native exception: ") + ex.what()));
    } catch (...) {
        return make_buffer(error_json("Unknown native exception during match simulation."));
    }
}

FM_ResultBuffer fm_simulate_week_json(const char* week_json) {
    try {
        if (!week_json) return make_buffer(error_json("Null input."));
        bool ok = false;
        std::string error;
        fm::WeekSimulationInput input = fm::parse_week_input_json(std::string(week_json), ok, error);
        if (!ok) return make_buffer(error_json(error.empty() ? "Invalid week input." : error));
        fm::WeekSimulationOutput output = fm::simulate_week(input);
        return make_buffer(fm::serialize_week_output_json(output));
    } catch (const std::exception& ex) {
        return make_buffer(error_json(std::string("Native exception: ") + ex.what()));
    } catch (...) {
        return make_buffer(error_json("Unknown native exception during week simulation."));
    }
}

FM_ResultBuffer fm_validate_squad_json(const char* squad_json) {
    try {
        if (!squad_json) {
            return make_buffer(nlohmann::json{{"ok", false}, {"message", "Null input."}, {"normalized_ids", nlohmann::json::array()}}.dump());
        }
        return make_buffer(fm::validate_squad_json(std::string(squad_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"ok", false}, {"message", std::string("Native exception: ") + ex.what()}, {"normalized_ids", nlohmann::json::array()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"ok", false}, {"message", "Unknown native exception."}, {"normalized_ids", nlohmann::json::array()}}.dump());
    }
}

FM_ResultBuffer fm_validate_selected_xi(const int* player_ids, int count, const char* roster_json) {
    try {
        if (!player_ids || !roster_json || count < 0) {
            return make_buffer(nlohmann::json{{"ok", false}, {"message", "Null input."}, {"normalized_ids", nlohmann::json::array()}}.dump());
        }
        std::vector<int> ids;
        ids.reserve(static_cast<size_t>(count));
        for (int i = 0; i < count; ++i) ids.push_back(player_ids[i]);
        return make_buffer(fm::validate_selected_xi_json(ids, std::string(roster_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"ok", false}, {"message", std::string("Native exception: ") + ex.what()}, {"normalized_ids", nlohmann::json::array()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"ok", false}, {"message", "Unknown native exception."}, {"normalized_ids", nlohmann::json::array()}}.dump());
    }
}

FM_ResultBuffer fm_preview_stadium_upgrade_json(const char* stadium_json) {
    try {
        if (!stadium_json) {
            return make_buffer(nlohmann::json{{"current_capacity", 0}, {"target_capacity", 0}, {"cost", 0}, {"affordable", false}, {"spoken_summary", "Null input."}}.dump());
        }
        return make_buffer(fm::preview_stadium_upgrade_json(std::string(stadium_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"current_capacity", 0}, {"target_capacity", 0}, {"cost", 0}, {"affordable", false}, {"spoken_summary", std::string("Native exception: ") + ex.what()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"current_capacity", 0}, {"target_capacity", 0}, {"cost", 0}, {"affordable", false}, {"spoken_summary", "Unknown native exception."}}.dump());
    }
}

FM_ResultBuffer fm_summarize_club_records_json(const char* records_json) {
    try {
        if (!records_json) return make_buffer(nlohmann::json{{"error", "Null input."}}.dump());
        return make_buffer(fm::summarize_club_records_json(std::string(records_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"error", std::string("Native exception: ") + ex.what()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"error", "Unknown native exception."}}.dump());
    }
}

FM_ResultBuffer fm_summarize_youth_players_json(const char* youth_json) {
    try {
        if (!youth_json) {
            return make_buffer(nlohmann::json{{"error", "Null input."}, {"count", 0}, {"average_overall", 0.0}, {"highest_potential", 0}, {"players", nlohmann::json::array()}}.dump());
        }
        return make_buffer(fm::summarize_youth_players_json(std::string(youth_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"error", std::string("Native exception: ") + ex.what()}, {"count", 0}, {"average_overall", 0.0}, {"highest_potential", 0}, {"players", nlohmann::json::array()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"error", "Unknown native exception."}, {"count", 0}, {"average_overall", 0.0}, {"highest_potential", 0}, {"players", nlohmann::json::array()}}.dump());
    }
}

FM_ResultBuffer fm_get_transfer_window_status_json(const char* date_json) {
    try {
        if (!date_json) {
            return make_buffer(nlohmann::json{{"open", false}, {"label", "Null input."}}.dump());
        }
        return make_buffer(fm::get_transfer_window_status_json(std::string(date_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"open", false}, {"label", std::string("Native exception: ") + ex.what()}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"open", false}, {"label", "Unknown native exception."}}.dump());
    }
}

FM_ResultBuffer fm_evaluate_contract_offer_json(const char* contract_json) {
    try {
        if (!contract_json) {
            return make_buffer(nlohmann::json{{"success", false}, {"outcome", "error"}, {"message", "Null input."}, {"counter_wage", 0}, {"counter_years", 0}, {"counter_role", ""}}.dump());
        }
        return make_buffer(fm::evaluate_contract_offer_json(std::string(contract_json)));
    } catch (const std::exception& ex) {
        return make_buffer(nlohmann::json{{"success", false}, {"outcome", "error"}, {"message", std::string("Native exception: ") + ex.what()}, {"counter_wage", 0}, {"counter_years", 0}, {"counter_role", ""}}.dump());
    } catch (...) {
        return make_buffer(nlohmann::json{{"success", false}, {"outcome", "error"}, {"message", "Unknown native exception."}, {"counter_wage", 0}, {"counter_years", 0}, {"counter_role", ""}}.dump());
    }
}

const char* fm_backend_version(void) {
    return "fm_backend_stateless_kernels_v5";
}

void fm_free_buffer(FM_ResultBuffer buffer) {
    if (buffer.data) {
        std::free((void*)buffer.data);
    }
}

}
