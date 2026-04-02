#pragma once

#include <string>
#include <vector>

namespace fm {

struct SubmitLineupRequest {
    std::string game_id;
    std::string club_id;
    std::vector<std::string> player_ids;
};

struct AdvanceWeekRequest {
    std::string game_id;
    std::string manager_id;
};

struct TransferNegotiationRequest {
    std::string game_id;
    std::string manager_id;
    std::string player_id;
    int wage_offer = 0;
    int contract_years = 0;
    std::string role_offer;
};

struct ActionResponse {
    bool success = false;
    std::string message;
    std::string payload_json;
};

} // namespace fm
