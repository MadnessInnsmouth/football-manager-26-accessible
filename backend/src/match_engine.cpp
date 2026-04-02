#include "models.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <random>
#include <sstream>

namespace fm {
namespace {

static void add_event(MatchOutput& output, int minute, const std::string& event_type, const std::string& team_name,
                      const std::string& player_name, const std::string& assist_name, const std::string& commentary) {
    output.events.push_back(MatchEvent{minute, event_type, team_name, player_name, assist_name, commentary});
}

static double player_overall(const PlayerSummary& p) {
    if (p.position == "Goalkeeper") {
        return p.goalkeeping * 0.45 + p.physical * 0.2 + p.passing * 0.1 + p.pace * 0.1 + p.defending * 0.15;
    }
    if (p.position == "Defender") {
        return p.defending * 0.35 + p.physical * 0.2 + p.pace * 0.15 + p.passing * 0.2 + p.shooting * 0.1;
    }
    if (p.position == "Midfielder") {
        return p.passing * 0.3 + p.shooting * 0.15 + p.physical * 0.15 + p.pace * 0.15 + p.defending * 0.25;
    }
    return p.shooting * 0.35 + p.pace * 0.25 + p.physical * 0.15 + p.passing * 0.15 + p.defending * 0.1;
}

static double team_base_strength(const TeamSummary& team) {
    if (team.selected_xi.empty()) return 1.0;
    double total = 0.0;
    for (const auto& p : team.selected_xi) total += player_overall(p);
    return total / static_cast<double>(team.selected_xi.size());
}

static const PlayerSummary* pick_weighted(const std::vector<PlayerSummary>& players, std::mt19937& rng, const std::string& mode) {
    if (players.empty()) return nullptr;
    std::vector<int> weights;
    weights.reserve(players.size());
    for (const auto& p : players) {
        int w = 1;
        if (mode == "scorer") {
            if (p.position == "Forward") w = p.shooting * 3 + p.pace;
            else if (p.position == "Midfielder") w = p.shooting * 2 + p.passing;
            else if (p.position == "Defender") w = p.shooting + p.physical;
            else w = std::max(1, p.shooting / 2);
        } else if (mode == "assist") {
            w = p.passing * 2 + p.pace;
        } else if (mode == "discipline") {
            w = p.physical + p.defending;
        } else {
            w = std::max(1, static_cast<int>(std::round(player_overall(p))));
        }
        weights.push_back(std::max(1, w));
    }
    std::discrete_distribution<int> dist(weights.begin(), weights.end());
    return &players[dist(rng)];
}

static const PlayerSummary* pick_assister(const std::vector<PlayerSummary>& players, const std::string& scorer_id, std::mt19937& rng) {
    std::vector<PlayerSummary> candidates;
    for (const auto& p : players) {
        if (p.id != scorer_id && p.position != "Goalkeeper") candidates.push_back(p);
    }
    if (candidates.empty()) return nullptr;
    return pick_weighted(candidates, rng, "assist");
}

static double injury_chance(const TeamSummary& team, const PlayerSummary& player) {
    double intensity = static_cast<double>(team.training_intensity);
    double medical = static_cast<double>(team.medical_level);
    double pitch = static_cast<double>(team.pitch_quality);
    double age_mod = player.age >= 30 ? 0.01 : 0.0;
    double v = 0.015 + intensity * 0.01 - medical * 0.004 - pitch * 0.002 + age_mod;
    return std::max(0.005, v);
}

static void apply_table_result(WeekTableRow& home, WeekTableRow& away, const MatchOutput& result) {
    home.goals_for += result.home_goals;
    home.goals_against += result.away_goals;
    away.goals_for += result.away_goals;
    away.goals_against += result.home_goals;
    home.goal_difference = home.goals_for - home.goals_against;
    away.goal_difference = away.goals_for - away.goals_against;
    if (result.home_goals > result.away_goals) {
        home.wins += 1;
        home.points += 3;
        away.losses += 1;
    } else if (result.home_goals < result.away_goals) {
        away.wins += 1;
        away.points += 3;
        home.losses += 1;
    } else {
        home.draws += 1;
        away.draws += 1;
        home.points += 1;
        away.points += 1;
    }
}

} // namespace

MatchOutput simulate_match(const MatchInput& input) {
    MatchOutput output;
    output.home_team = input.home.name;
    output.away_team = input.away.name;

    std::mt19937 rng;
    if (input.has_seed) rng.seed(input.seed);
    else rng.seed(std::random_device{}());

    double home_base = team_base_strength(input.home) * (1.08 + input.home.pitch_quality * 0.005);
    double away_base = team_base_strength(input.away);

    add_event(output, 0, "Kick Off", "", "", "", "Kick off. " + input.home.name + " versus " + input.away.name + ".");

    std::uniform_real_distribution<double> prob(0.0, 1.0);
    std::uniform_int_distribution<int> stoppage_dist(2, 5);
    std::uniform_int_distribution<int> injury_weeks_dist(1, 5);

    int home_red_count = 0;
    int away_red_count = 0;

    for (int minute = 1; minute <= 90; ++minute) {
        if (minute == 46) {
            std::ostringstream ss;
            ss << "Half time. " << output.home_team << ' ' << output.home_goals << ", " << output.away_team << ' ' << output.away_goals << '.';
            add_event(output, 45, "Half Time", "", "", "", ss.str());
        }

        if (prob(rng) > 0.30) continue;

        double home_chance = home_base / std::max(1.0, away_base);
        double away_chance = away_base / std::max(1.0, home_base);
        double total = home_chance + away_chance;
        bool is_home = prob(rng) < (home_chance / total);

        const TeamSummary& atk_team = is_home ? input.home : input.away;
        const TeamSummary& def_team = is_home ? input.away : input.home;
        const auto& atk_xi = is_home ? input.home.selected_xi : input.away.selected_xi;
        const auto& def_xi = is_home ? input.away.selected_xi : input.home.selected_xi;

        double roll = prob(rng);
        if (roll < 0.15) {
            if (is_home) output.home_shots++; else output.away_shots++;
            double goal_chance = 0.33 + (is_home ? home_base : away_base) * 0.01;
            if (prob(rng) < goal_chance) {
                bool is_penalty = prob(rng) < 0.08;
                const PlayerSummary* scorer = pick_weighted(atk_xi, rng, "scorer");
                if (is_penalty) {
                    if (prob(rng) < 0.78) {
                        if (is_home) { output.home_goals++; output.home_on_target++; }
                        else { output.away_goals++; output.away_on_target++; }
                        std::ostringstream ss;
                        ss << minute << "' Goal for " << atk_team.name << ". Scorer: " << (scorer ? scorer->name : "Unknown")
                           << ". Score: " << output.home_team << ' ' << output.home_goals << ", " << output.away_team << ' ' << output.away_goals << '.';
                        add_event(output, minute, "Penalty Scored", atk_team.name, scorer ? scorer->name : "", "", ss.str());
                    } else {
                        std::ostringstream ss;
                        ss << minute << "' Penalty missed by " << (scorer ? scorer->name : "Unknown") << " of " << atk_team.name << '.';
                        add_event(output, minute, "Penalty Missed", atk_team.name, scorer ? scorer->name : "", "", ss.str());
                    }
                } else {
                    const PlayerSummary* assister = scorer ? pick_assister(atk_xi, scorer->id, rng) : nullptr;
                    if (is_home) { output.home_goals++; output.home_on_target++; }
                    else { output.away_goals++; output.away_on_target++; }
                    std::ostringstream ss;
                    ss << minute << "' Goal for " << atk_team.name << ". Scorer: " << (scorer ? scorer->name : "Unknown") << '.';
                    if (assister) ss << " Assist by " << assister->name << '.';
                    ss << " Score: " << output.home_team << ' ' << output.home_goals << ", " << output.away_team << ' ' << output.away_goals << '.';
                    add_event(output, minute, "Goal", atk_team.name, scorer ? scorer->name : "", assister ? assister->name : "", ss.str());
                }
            } else {
                const PlayerSummary* shooter = pick_weighted(atk_xi, rng, "scorer");
                if (prob(rng) < 0.5) {
                    if (is_home) output.home_on_target++; else output.away_on_target++;
                    std::ostringstream ss;
                    ss << minute << "' " << (shooter ? shooter->name : "A player") << " has a shot saved for " << atk_team.name << '.';
                    add_event(output, minute, "Shot Saved", atk_team.name, shooter ? shooter->name : "", "", ss.str());
                } else {
                    std::ostringstream ss;
                    ss << minute << "' " << (shooter ? shooter->name : "A player") << " shoots wide for " << atk_team.name << '.';
                    add_event(output, minute, "Shot Wide", atk_team.name, shooter ? shooter->name : "", "", ss.str());
                }
            }
        } else if (roll < 0.30) {
            if (is_home) output.home_corners++; else output.away_corners++;
            add_event(output, minute, "Corner", atk_team.name, "", "", std::to_string(minute) + "' Corner to " + atk_team.name + ".");
        } else if (roll < 0.55) {
            const PlayerSummary* fouler = pick_weighted(def_xi, rng, "discipline");
            if (is_home) output.away_fouls++; else output.home_fouls++;
            add_event(output, minute, "Foul", def_team.name, fouler ? fouler->name : "", "", std::to_string(minute) + "' Foul by " + (fouler ? fouler->name : std::string("a player")) + " of " + def_team.name + ".");
            double card_roll = prob(rng);
            if (card_roll < 0.15 && fouler) {
                if (is_home) output.away_yellows++; else output.home_yellows++;
                add_event(output, minute, "Yellow Card", def_team.name, fouler->name, "", std::to_string(minute) + "' Yellow card for " + fouler->name + " of " + def_team.name + ".");
            } else if (card_roll < 0.03 && fouler) {
                if (is_home) { output.away_reds++; away_red_count++; }
                else { output.home_reds++; home_red_count++; }
                int count = is_home ? 11 - away_red_count : 11 - home_red_count;
                add_event(output, minute, "Red Card", def_team.name, fouler->name, "", std::to_string(minute) + "' Red card for " + fouler->name + " of " + def_team.name + ". " + def_team.name + " are down to " + std::to_string(count) + " men.");
            }
        } else if (roll < 0.62) {
            const PlayerSummary* player = pick_weighted(atk_xi, rng, "default");
            if (player && prob(rng) < injury_chance(atk_team, *player)) {
                int weeks = injury_weeks_dist(rng);
                add_event(output, minute, "Injury", atk_team.name, player->name, "", std::to_string(minute) + "' Injury concern for " + atk_team.name + ". " + player->name + " may miss " + std::to_string(weeks) + " weeks.");
            }
        }
    }

    int stoppage = stoppage_dist(rng);
    for (int minute = 91; minute < 91 + stoppage; ++minute) {
        if (prob(rng) < 0.12) {
            bool is_home = prob(rng) < 0.5;
            const TeamSummary& atk_team = is_home ? input.home : input.away;
            const auto& atk_xi = is_home ? input.home.selected_xi : input.away.selected_xi;
            if (is_home) output.home_shots++; else output.away_shots++;
            if (prob(rng) < 0.25) {
                const PlayerSummary* scorer = pick_weighted(atk_xi, rng, "scorer");
                if (is_home) { output.home_goals++; output.home_on_target++; }
                else { output.away_goals++; output.away_on_target++; }
                std::ostringstream ss;
                ss << "90+" << (minute - 90) << "' Goal for " << atk_team.name << ". Scorer: " << (scorer ? scorer->name : "Unknown")
                   << ". Score: " << output.home_team << ' ' << output.home_goals << ", " << output.away_team << ' ' << output.away_goals << '.';
                add_event(output, minute, "Goal", atk_team.name, scorer ? scorer->name : "", "", ss.str());
            }
        }
    }

    add_event(output, 90, "Full Time", "", "", "", "Full time. " + output.home_team + " " + std::to_string(output.home_goals) + ", " + output.away_team + " " + std::to_string(output.away_goals) + ".");

    std::uniform_real_distribution<double> fill_pct(0.4, 0.9);
    output.attendance = static_cast<int>(input.home.stadium_capacity * fill_pct(rng));
    return output;
}

WeekSimulationOutput simulate_week(const WeekSimulationInput& input) {
    WeekSimulationOutput out;
    std::map<std::string, WeekTableRow> table_map;

    for (const auto& fixture : input.fixtures) {
        MatchInput match_input;
        match_input.home = fixture.home;
        match_input.away = fixture.away;
        match_input.seed = fixture.seed;
        match_input.has_seed = fixture.has_seed;

        MatchOutput match_result = simulate_match(match_input);
        WeekFixtureResult fixture_result;
        fixture_result.fixture_id = fixture.fixture_id;
        fixture_result.competition_id = fixture.competition_id;
        fixture_result.stage = fixture.stage;
        fixture_result.week = fixture.week;
        fixture_result.match = match_result;
        out.results.push_back(fixture_result);

        auto& home_row = table_map[fixture.home.id];
        if (home_row.club_id.empty()) {
            home_row.club_id = fixture.home.id;
            home_row.club_name = fixture.home.name;
        }
        auto& away_row = table_map[fixture.away.id];
        if (away_row.club_id.empty()) {
            away_row.club_id = fixture.away.id;
            away_row.club_name = fixture.away.name;
        }
        apply_table_result(home_row, away_row, match_result);
    }

    for (auto& kv : table_map) {
        out.table.push_back(kv.second);
    }
    std::sort(out.table.begin(), out.table.end(), [](const WeekTableRow& a, const WeekTableRow& b) {
        if (a.points != b.points) return a.points > b.points;
        if (a.goal_difference != b.goal_difference) return a.goal_difference > b.goal_difference;
        if (a.goals_for != b.goals_for) return a.goals_for > b.goals_for;
        return a.club_name < b.club_name;
    });
    return out;
}

} // namespace fm
