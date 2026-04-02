import game_engine


class CompetitionService:
    def get_player_fixtures(self, state, week=None):
        return game_engine.get_player_fixtures(state, week)

    def get_competition_name(self, state, fixture):
        return game_engine.get_competition_name(state, fixture)

    def get_week_fixtures(self, state, week=None):
        return game_engine.get_week_fixtures(state, week)
