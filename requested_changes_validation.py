from pathlib import Path
import re
import py_compile

ROOT = Path(__file__).resolve().parent
ui = (ROOT / 'ui.py').read_text(encoding='utf-8')
engine = (ROOT / 'game_engine.py').read_text(encoding='utf-8')

for name in ['ui.py', 'game_engine.py', 'models.py', 'save_system.py']:
    py_compile.compile(str(ROOT / name), doraise=True)
print('COMPILE_OK', True)

print('HAS_BACK_TO_DASHBOARD', 'Back to Dashboard' in ui)
print('HAS_BACK_TO_MAIN_MENU', 'Back to Main Menu' in ui)
print('HAS_MATCH_PANEL_NAME', 'Match Panel' in ui)
print('HAS_LIVE_COMMENTARY_PANEL_NAME', 'Live Commentary Panel' in ui)
print('HAS_LIVE_MATCH_CENTRE_NAME', 'SetName("Live Match Centre")' in ui)
print('HAS_REVIEW_SELECTED_SQUAD', 'Review Selected Squad' in ui)
print('HAS_PRE_KICKOFF_METHOD', 'def show_pre_kickoff_squad_review' in ui)
print('HAS_POST_MATCH_RESULTS_SCREEN', 'def show_post_match_results_screen' in ui)
print('HAS_MATCH_RESULTS_MENU_ITEM', 'Match &Results' in ui)
print('HAS_ESC_BIND', 'wx.EVT_CHAR_HOOK' in ui and 'WXK_ESCAPE' in ui)
print('HAS_INBOX_UI', 'def show_inbox' in ui and 'Open Message' in ui)

m = re.search(r'def process_transfer_offers\(state\):(.*?)(?:\n\ndef |\Z)', engine, re.S)
body = m.group(1) if m else ''
print('PROCESS_TRANSFER_OFFERS_FOUND', bool(m))
print('PROCESS_TRANSFER_OFFERS_HAS_PASS', 'pass' in body)
print('HAS_RESPOND_TO_TRANSFER_OFFER', 'def respond_to_transfer_offer' in engine)
print('HAS_LIST_PLAYER_FOR_SALE', 'def list_player_for_sale' in engine)
print('HAS_DOMESTIC_CUP_DEFS', 'DOMESTIC_CUP_DEFINITIONS' in engine)
print('HAS_FA_CUP', 'FA Cup' in engine)
print('HAS_COPA_DEL_REY', 'Copa del Rey' in engine)
print('HAS_COUPE_DE_FRANCE', 'Coupe de France' in engine)
print('HAS_INIT_COMPETITIONS_CUPS', '_cup_club_ids' in engine and '_create_knockout_fixtures' in engine)
print('HAS_POST_MATCH_OTHER_RESULTS_HELPER', 'def get_post_match_other_results' in engine)
