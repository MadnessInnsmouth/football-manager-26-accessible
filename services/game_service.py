from __future__ import annotations

import engine_bridge
import save_system


class GameService:
    def __init__(self):
        self.backend = engine_bridge.bridge

    def get_status(self):
        return self.backend.get_status()

    def create_new_game(self, club_name, short_name, country, stadium_name, manager_name="Manager"):
        return self.backend.create_new_game(club_name, short_name, country, stadium_name, manager_name)

    def load(self):
        return save_system.load_game()

    def save(self, state):
        return save_system.save_game(state)

    def autosave(self, state):
        return save_system.autosave_game(state)

    def get_save_path(self):
        return save_system.get_save_path()

    def __getattr__(self, item):
        return getattr(self.backend, item)


service = GameService()
