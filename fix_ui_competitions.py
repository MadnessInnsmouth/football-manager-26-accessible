from pathlib import Path

path = Path(r"C:\Users\abdul\Projects\football_manager\ui.py")
content = path.read_text(encoding="utf-8")
bad = '("&League Table", self.show_league_table),`r`n            ("&Competitions", self.show_competitions_overview),'
good = '("&League Table", self.show_league_table),\n            ("&Competitions", self.show_competitions_overview),'
content = content.replace(bad, good)
path.write_text(content, encoding="utf-8")
print("fixed")
