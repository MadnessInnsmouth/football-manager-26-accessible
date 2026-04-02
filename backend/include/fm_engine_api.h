#pragma once

#ifdef _WIN32
  #ifdef FM_ENGINE_BUILD
    #define FM_API __declspec(dllexport)
  #else
    #define FM_API __declspec(dllimport)
  #endif
#else
  #define FM_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct FM_ResultBuffer {
    const char* data;
    int length;
} FM_ResultBuffer;

FM_API FM_ResultBuffer fm_simulate_match_json(const char* match_json);
FM_API FM_ResultBuffer fm_simulate_week_json(const char* week_json);
FM_API FM_ResultBuffer fm_validate_squad_json(const char* squad_json);
FM_API FM_ResultBuffer fm_validate_selected_xi(const int* player_ids, int count, const char* roster_json);
FM_API FM_ResultBuffer fm_preview_stadium_upgrade_json(const char* stadium_json);
FM_API FM_ResultBuffer fm_summarize_club_records_json(const char* records_json);
FM_API FM_ResultBuffer fm_summarize_youth_players_json(const char* youth_json);
FM_API FM_ResultBuffer fm_get_transfer_window_status_json(const char* date_json);
FM_API FM_ResultBuffer fm_evaluate_contract_offer_json(const char* contract_json);
FM_API const char* fm_backend_version(void);
FM_API void fm_free_buffer(FM_ResultBuffer buffer);

#ifdef __cplusplus
}
#endif
