"""Accessible GUI for Football Manager 26 - wxPython + NVDA screen reader support."""

import threading

import wx

from speech import speak, priority_announce
from models import EventType, Club, Position, MessageType
from database import LEAGUE_DATA, generate_player
from services.game_service import service as game_engine
from services.network_service import service as network_service, DEFAULT_PORT
from services import account_service
import save_system


class FootballManagerApp(wx.Frame):
    BG = wx.Colour(18, 18, 18)
    PANEL_BG = wx.Colour(28, 28, 28)
    SURFACE_BG = wx.Colour(38, 38, 38)
    CTRL_BG = wx.Colour(45, 45, 45)
    ACCENT = wx.Colour(88, 166, 255)
    SUCCESS = wx.Colour(87, 171, 90)
    WARNING = wx.Colour(230, 180, 60)
    FG = wx.Colour(235, 235, 235)
    MUTED_FG = wx.Colour(190, 190, 190)
    ROLE_OPTIONS = ["Prospect", "Rotation", "Starter", "Key Player"]
    POSITION_FILTERS = ["All", "GK", "DEF", "MID", "FWD"]

    def __init__(self):
        super().__init__(None, title="Football Manager 26 - Accessible Edition", size=(1280, 900))
        self.SetMinSize((980, 720))
        self.game_state = None
        self._season_prize_awarded = False
        self._full_time_spoken = False
        self._speech_queue = []
        self._speech_timer = None
        self._commentary_timer = None
        self._active_negotiation = None
        self._current_match_fixture = None
        self._week_player_fixtures = []
        self._transfer_market_items = []
        self._last_content_focus = None
        self._match_lines = []
        self._nav_stack = []
        self.panel = wx.Panel(self)
        self.scroll = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.scroll.SetScrollRate(0, 20)
        self.outer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.outer)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.sizer)
        self.outer.Add(self.scroll, 1, wx.EXPAND)
        self._apply_dark_theme()
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetBackgroundColour(self.SURFACE_BG)
        self.status_bar.SetForegroundColour(self.FG)
        self.set_status("Welcome to Football Manager 26 - Accessible Edition")
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Centre()
        self.Show()
        self.show_welcome_screen()
        speak("Football Manager 26 Accessible Edition. Press Tab to navigate, Enter to activate buttons.", interrupt=False)

    def _on_char_hook(self, event):
        key = event.GetKeyCode()
        focused = wx.Window.FindFocus()
        if key == wx.WXK_ESCAPE:
            if isinstance(focused, wx.TextCtrl) and focused.IsEditable():
                event.Skip()
                return
            self.go_back()
            return
        event.Skip()

    def _push_nav(self, screen_callable):
        if not self._nav_stack or self._nav_stack[-1] != screen_callable:
            self._nav_stack.append(screen_callable)

    def go_back(self):
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()
            previous = self._nav_stack[-1]
            previous(track=False)
        else:
            self.show_main_menu(track=False)

    def _roster_payload(self, club):
        payload = []
        for idx, p in enumerate(club.players, 1):
            payload.append({"id": idx, "source_id": p.id, "name": p.full_name, "position": p.position.value, "available": bool(p.is_available)})
        return payload

    def _selected_indices_from_ids(self, club, selected_ids):
        roster = self._roster_payload(club)
        id_map = {row["source_id"]: row["id"] for row in roster}
        return [id_map[pid] for pid in selected_ids if pid in id_map]

    def _native_transfer_window(self):
        if not self.game_state:
            return None
        payload = {"country": self.game_state.country, "current_date": self.game_state.current_date}
        return game_engine.get_transfer_window_status_native(payload)

    def _native_records_summary(self, club):
        payload = {
            "highest_league_finish": club.records.highest_league_finish,
            "most_points": club.records.most_points,
            "most_goals_scored": club.records.most_goals_scored,
            "best_goal_difference": club.records.best_goal_difference,
            "biggest_win": club.records.biggest_win,
            "biggest_defeat": club.records.biggest_defeat,
            "highest_scoring_match": club.records.highest_scoring_match,
            "all_time_top_scorer": club.records.all_time_top_scorer,
            "all_time_top_scorer_goals": club.records.all_time_top_scorer_goals,
            "most_appearances_player": club.records.most_appearances_player,
            "most_appearances": club.records.most_appearances,
        }
        return game_engine.summarize_club_records_native(payload)

    def _native_youth_summary(self, club):
        payload = {"players": [{"name": p.full_name, "position": p.position.value, "age": p.age, "overall": p.overall, "potential": p.potential, "desired_wage": p.desired_wage} for p in club.youth_team]}
        return game_engine.summarize_youth_players_native(payload)

    def _native_stadium_preview(self, club, target):
        payload = {"current_capacity": int(club.stadium_capacity), "target_capacity": int(target), "seating_level": int(club.infrastructure.stadium.seating_level), "budget": int(club.budget), "league_tier": int(club.league_tier)}
        return game_engine.preview_stadium_upgrade_native(payload)

    def _native_contract_eval(self, payload):
        return game_engine.evaluate_contract_offer_native(payload)

    def has_save_game(self):
        return save_system.load_game() is not None

    def autosave(self):
        if self.game_state:
            save_system.autosave_game(self.game_state)
            self._cloud_save_background()

    def _cloud_save_background(self):
        """Upload save to cloud in background if logged in. Non-blocking."""
        if not account_service.is_logged_in() or not self.game_state:
            return

        def _upload():
            try:
                json_str = save_system.serialize_to_json_string(self.game_state)
                account_service.upload_save(json_str, save_name="default")
            except (OSError, ValueError, TypeError):
                pass

        threading.Thread(target=_upload, daemon=True).start()

    def _apply_dark_theme(self):
        self.SetBackgroundColour(self.BG)
        self.SetForegroundColour(self.FG)
        self.panel.SetBackgroundColour(self.BG)
        self.panel.SetForegroundColour(self.FG)
        self.scroll.SetBackgroundColour(self.BG)
        self.scroll.SetForegroundColour(self.FG)

    def _style_control(self, ctrl, surface=False):
        bg = self.SURFACE_BG if surface else self.CTRL_BG
        try:
            ctrl.SetBackgroundColour(bg)
            ctrl.SetForegroundColour(self.FG)
        except Exception:
            pass

    def _add_group(self, title, subtitle=None):
        box = wx.StaticBox(self.scroll, label=title)
        box.SetForegroundColour(self.ACCENT)
        box.SetBackgroundColour(self.PANEL_BG)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        if subtitle:
            sub = wx.StaticText(self.scroll, label=subtitle)
            sub.Wrap(980)
            sub.SetForegroundColour(self.MUTED_FG)
            sizer.Add(sub, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.sizer.Add(sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        return sizer

    def set_status(self, text):
        self.status_bar.SetStatusText(text)

    def clear(self):
        speak("", interrupt=True)
        self._cancel_timers()
        self.sizer.Clear(True)
        self.scroll.DestroyChildren()
        self.scroll.SetBackgroundColour(self.BG)
        self.scroll.SetForegroundColour(self.FG)

    def _cancel_timers(self):
        if self._commentary_timer:
            try:
                self._commentary_timer.Stop()
            except Exception:
                pass
            self._commentary_timer = None
        if self._speech_timer:
            try:
                self._speech_timer.Stop()
            except Exception:
                pass
            self._speech_timer = None
        self._speech_queue = []

    def _queue_speech(self, text, priority=False):
        if priority:
            priority_announce(text)
            return
        self._speech_queue.append(text)
        if not self._speech_timer:
            self._dequeue_speech()

    def _dequeue_speech(self):
        if not self._speech_queue:
            self._speech_timer = None
            return
        text = self._speech_queue.pop(0)
        speak(text, interrupt=False)
        duration = max(1400, min(4200, 55 * len(text)))
        self._speech_timer = wx.CallLater(duration, self._dequeue_speech)

    def _add_section_heading(self, text, subtext=None):
        title = wx.StaticText(self.scroll, label=text)
        title.SetForegroundColour(self.ACCENT)
        title.SetFont(wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.sizer.Add(title, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        if subtext:
            st = wx.StaticText(self.scroll, label=subtext)
            st.Wrap(1040)
            st.SetForegroundColour(self.MUTED_FG)
            self.sizer.Add(st, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        return title

    def _top_header(self):
        if not self.game_state:
            return
        gs = self.game_state
        club = gs.clubs[gs.player_club_id]
        dt = game_engine.get_current_date(gs)
        window = self._native_transfer_window() or game_engine.get_transfer_window_status(gs)
        open_text = "OPEN" if window["open"] else "CLOSED"
        unread = game_engine.get_unread_inbox_count(gs)
        box = self._add_group(
            "Season Header",
            f"Country: {club.country}    Season: {game_engine.get_season_label(gs)}    Date: {dt.strftime('%d %B %Y')}    Week: {gs.league.current_week}/{gs.league.total_weeks}    Unread Inbox: {unread}",
        )
        badge = wx.StaticText(self.scroll, label=f"Transfer Window: {open_text}")
        badge.SetForegroundColour(self.SUCCESS if window["open"] else self.WARNING)
        box.Add(badge, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _make_readable_text(self, text, min_height=260):
        ctrl = wx.TextCtrl(self.scroll, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_NONE)
        self._style_control(ctrl, surface=True)
        ctrl.SetMinSize((-1, min_height))
        ctrl.SetName("Information")
        self._last_content_focus = ctrl
        return ctrl

    def _make_live_commentary_surface(self):
        outer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.scroll, label="Live Match Commentary")
        label.SetForegroundColour(self.ACCENT)
        label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        outer.Add(label, 0, wx.ALL, 8)
        self.match_commentary_list = wx.ListBox(self.scroll, style=wx.LB_SINGLE)
        self._style_control(self.match_commentary_list, surface=True)
        self.match_commentary_list.SetMinSize((-1, 320))
        self.match_commentary_list.SetName("Live Match Commentary")
        outer.Add(self.match_commentary_list, 1, wx.EXPAND | wx.ALL, 8)
        return outer

    def show_welcome_screen(self):
        """Initial screen shown on launch. Checks login state and routes accordingly."""
        self._nav_stack = []
        self.clear()
        self.set_status("Welcome")
        self.sizer.AddStretchSpacer()
        box = self._add_group(
            "Welcome to Football Manager 26",
            "Accessible Edition - A fully text-based, screen reader friendly football management game.",
        )
        welcome_text = (
            "Welcome to Football Manager 26 Accessible Edition!\n\n"
            "Build your dream club from the ground up. Manage your squad, navigate the transfer market, "
            "develop youth players, and lead your team to glory across multiple seasons and competitions.\n\n"
            "Your progress can be saved locally and to the cloud so you never lose your career.\n\n"
            "Sign in or create an account to enable cloud saves and online multiplayer, "
            "or continue as a guest to play offline with local saves only."
        )
        info = self._make_readable_text(welcome_text, min_height=180)
        box.Add(info, 0, wx.EXPAND | wx.ALL, 10)
        if account_service.is_logged_in():
            username = account_service.get_username()
            status_lbl = wx.StaticText(self.scroll, label=f"Signed in as: {username}")
            status_lbl.SetForegroundColour(self.SUCCESS)
            box.Add(status_lbl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            continue_btn = wx.Button(self.scroll, label=f"&Continue as {username}", size=(300, 42))
            self._style_control(continue_btn)
            continue_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_main_menu(track=True))
            box.Add(continue_btn, 0, wx.ALL, 6)
            logout_btn = wx.Button(self.scroll, label="&Log Out and Switch Account", size=(300, 42))
            self._style_control(logout_btn)
            logout_btn.Bind(wx.EVT_BUTTON, lambda e: (account_service.logout(), self.show_welcome_screen()))
            box.Add(logout_btn, 0, wx.ALL, 6)
            first = continue_btn
        else:
            login_btn = wx.Button(self.scroll, label="&Log In", size=(300, 42))
            self._style_control(login_btn)
            login_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_login_screen())
            box.Add(login_btn, 0, wx.ALL, 6)
            register_btn = wx.Button(self.scroll, label="&Create Account", size=(300, 42))
            self._style_control(register_btn)
            register_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_register_screen())
            box.Add(register_btn, 0, wx.ALL, 6)
            guest_btn = wx.Button(self.scroll, label="Continue as &Guest (Offline Only)", size=(300, 42))
            self._style_control(guest_btn)
            guest_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_main_menu(track=True))
            box.Add(guest_btn, 0, wx.ALL, 6)
            first = login_btn
        quit_btn = wx.Button(self.scroll, label="&Quit Game", size=(300, 42))
        self._style_control(quit_btn)
        quit_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        box.Add(quit_btn, 0, wx.ALL, 6)
        self.sizer.AddStretchSpacer()
        self.scroll.Layout()
        self.scroll.FitInside()
        if first:
            wx.CallAfter(first.SetFocus)

    def show_login_screen(self):
        self._push_nav(self.show_login_screen)
        self.clear()
        self.set_status("Log In")
        self.sizer.AddStretchSpacer()
        self._add_section_heading("Log In to Football Manager 26", "Enter your username and password to sign in.")
        box = self._add_group(
            "Account Login",
            "Sign in with your account to access cloud saves, online multiplayer, and keep your career progress safe.",
        )
        form = wx.FlexGridSizer(cols=2, vgap=14, hgap=18)
        form.AddGrowableCol(1)
        lbl_user = wx.StaticText(self.scroll, label="Username:")
        lbl_user.SetForegroundColour(self.FG)
        form.Add(lbl_user, 0, wx.ALIGN_CENTER_VERTICAL)
        self._login_username = wx.TextCtrl(self.scroll, size=(340, -1))
        self._login_username.SetName("Username")
        self._style_control(self._login_username)
        form.Add(self._login_username, 0, wx.EXPAND)
        lbl_pass = wx.StaticText(self.scroll, label="Password:")
        lbl_pass.SetForegroundColour(self.FG)
        form.Add(lbl_pass, 0, wx.ALIGN_CENTER_VERTICAL)
        self._login_password = wx.TextCtrl(self.scroll, size=(340, -1), style=wx.TE_PASSWORD)
        self._login_password.SetName("Password")
        self._style_control(self._login_password)
        form.Add(self._login_password, 0, wx.EXPAND)
        box.Add(form, 0, wx.ALL | wx.EXPAND, 18)
        self._login_status = wx.StaticText(self.scroll, label="")
        self._login_status.SetForegroundColour(self.WARNING)
        box.Add(self._login_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        login_btn = wx.Button(self.scroll, label="&Log In", size=(220, 44))
        self._style_control(login_btn)
        login_btn.Bind(wx.EVT_BUTTON, self._do_login)
        btn_row.Add(login_btn, 0, wx.ALL, 6)
        register_link = wx.Button(self.scroll, label="&Create Account Instead", size=(220, 44))
        self._style_control(register_link)
        register_link.Bind(wx.EVT_BUTTON, lambda e: self.show_register_screen())
        btn_row.Add(register_link, 0, wx.ALL, 6)
        back_btn = wx.Button(self.scroll, label="&Back", size=(220, 44))
        self._style_control(back_btn)
        back_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_welcome_screen())
        btn_row.Add(back_btn, 0, wx.ALL, 6)
        box.Add(btn_row, 0, wx.ALL, 12)
        self.sizer.AddStretchSpacer()
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self._login_username.SetFocus)
        speak("Log in screen. Enter your username and password, then press Log In.", interrupt=False)

    def _do_login(self, event):
        username = self._login_username.GetValue().strip()
        password = self._login_password.GetValue()
        if not username or not password:
            self._login_status.SetLabel("Please enter both username and password.")
            speak("Please enter both username and password.")
            return
        self._login_status.SetLabel("Logging in...")
        self._login_status.SetForegroundColour(self.MUTED_FG)
        speak("Logging in, please wait.")
        wx.Yield()
        result = account_service.login(username, password)
        if result.ok:
            self._login_status.SetLabel(f"Welcome back, {result.username}!")
            self._login_status.SetForegroundColour(self.SUCCESS)
            speak(f"Logged in. Welcome back, {result.username}.")
            wx.CallLater(1200, self.show_main_menu, True)
        else:
            self._login_status.SetLabel(result.message)
            self._login_status.SetForegroundColour(self.WARNING)
            speak(f"Login failed. {result.message}")

    def show_register_screen(self):
        self._push_nav(self.show_register_screen)
        self.clear()
        self.set_status("Create Account")
        self.sizer.AddStretchSpacer()
        self._add_section_heading("Create Your Account", "Register a new account for cloud saves and multiplayer.")
        box = self._add_group(
            "New Account Registration",
            "Create a free account to unlock cloud saves and online multiplayer.\n"
            "Username: 3 to 50 characters. Password: at least 6 characters.",
        )
        form = wx.FlexGridSizer(cols=2, vgap=14, hgap=18)
        form.AddGrowableCol(1)
        for label_text, attr, style, name in [
            ("Username:", "_reg_username", 0, "Username"),
            ("Email:", "_reg_email", 0, "Email"),
            ("Password:", "_reg_password", wx.TE_PASSWORD, "Password"),
            ("Confirm Password:", "_reg_confirm", wx.TE_PASSWORD, "Confirm Password"),
        ]:
            lbl = wx.StaticText(self.scroll, label=label_text)
            lbl.SetForegroundColour(self.FG)
            form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            txt = wx.TextCtrl(self.scroll, size=(340, -1), style=style)
            txt.SetName(name)
            self._style_control(txt)
            setattr(self, attr, txt)
            form.Add(txt, 0, wx.EXPAND)
        box.Add(form, 0, wx.ALL | wx.EXPAND, 18)
        self._reg_status = wx.StaticText(self.scroll, label="")
        self._reg_status.SetForegroundColour(self.WARNING)
        box.Add(self._reg_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        reg_btn = wx.Button(self.scroll, label="&Create Account", size=(220, 44))
        self._style_control(reg_btn)
        reg_btn.Bind(wx.EVT_BUTTON, self._do_register)
        btn_row.Add(reg_btn, 0, wx.ALL, 6)
        login_link = wx.Button(self.scroll, label="&Log In Instead", size=(220, 44))
        self._style_control(login_link)
        login_link.Bind(wx.EVT_BUTTON, lambda e: self.show_login_screen())
        btn_row.Add(login_link, 0, wx.ALL, 6)
        back_btn = wx.Button(self.scroll, label="&Back", size=(220, 44))
        self._style_control(back_btn)
        back_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_welcome_screen())
        btn_row.Add(back_btn, 0, wx.ALL, 6)
        box.Add(btn_row, 0, wx.ALL, 12)
        self.sizer.AddStretchSpacer()
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self._reg_username.SetFocus)
        speak("Create account screen. Fill in your details and press Create Account.", interrupt=False)

    def _do_register(self, event):
        username = self._reg_username.GetValue().strip()
        email = self._reg_email.GetValue().strip()
        password = self._reg_password.GetValue()
        confirm = self._reg_confirm.GetValue()
        if not username or not email or not password:
            self._reg_status.SetLabel("Please fill in all fields.")
            speak("Please fill in all fields.")
            return
        if len(username) < 3 or len(username) > 50:
            self._reg_status.SetLabel("Username must be between 3 and 50 characters.")
            speak("Username must be between 3 and 50 characters.")
            return
        if len(password) < 6:
            self._reg_status.SetLabel("Password must be at least 6 characters.")
            speak("Password must be at least 6 characters.")
            return
        if password != confirm:
            self._reg_status.SetLabel("Passwords do not match.")
            speak("Passwords do not match.")
            return
        self._reg_status.SetLabel("Creating account...")
        self._reg_status.SetForegroundColour(self.MUTED_FG)
        speak("Creating account, please wait.")
        wx.Yield()
        result = account_service.register(username, email, password)
        if result.ok:
            self._reg_status.SetLabel(f"Account created. Welcome, {result.username}!")
            self._reg_status.SetForegroundColour(self.SUCCESS)
            speak(f"Account created. Welcome, {result.username}.")
            wx.CallLater(1200, self.show_main_menu, True)
        else:
            self._reg_status.SetLabel(result.message)
            self._reg_status.SetForegroundColour(self.WARNING)
            speak(f"Registration failed. {result.message}")

    def show_main_menu(self, track=True):
        if track:
            self._nav_stack = []
            self._push_nav(self.show_main_menu)
        self.clear()
        self.set_status("Main Menu")
        self.sizer.AddStretchSpacer()
        box = self._add_group("Football Manager 26", "Accessible Edition. Start a new career, continue your save, or play online.")
        if account_service.is_logged_in():
            acct_lbl = wx.StaticText(self.scroll, label=f"Signed in as: {account_service.get_username()}")
            acct_lbl.SetForegroundColour(self.SUCCESS)
            box.Add(acct_lbl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        buttons = [("&New Game", self.show_club_creation)]
        if self.game_state or self.has_save_game():
            buttons.append(("&Continue", self._continue_game))
        if account_service.is_logged_in():
            buttons.append(("&Load Game", self.show_cloud_load))
        if self.game_state and account_service.is_logged_in():
            buttons.append(("&Save Game", self._cloud_save_explicit))
        buttons.append(("&Multiplayer", self.show_remote_multiplayer))
        buttons.append(("S&ettings", self.show_settings_placeholder))
        buttons.append(("&Quit Game", self.Close))
        first = None
        for label, handler in buttons:
            btn = wx.Button(self.scroll, label=label, size=(300, 42))
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, lambda e, h=handler: h())
            if first is None:
                first = btn
            box.Add(btn, 0, wx.ALL, 6)
        self.sizer.AddStretchSpacer()
        self.scroll.Layout()
        self.scroll.FitInside()
        if first:
            wx.CallAfter(first.SetFocus)
        speak("Main Menu. Use Tab to browse options, Enter to activate.", interrupt=False)

    def _continue_game(self):
        """Continue from in-memory game state or load from local save."""
        if self.game_state:
            self.show_dashboard()
            speak("Continuing your game.", interrupt=False)
        else:
            self._load_existing_game()

    def _cloud_save_explicit(self):
        """Save the current game to the cloud."""
        if not self.game_state:
            wx.MessageBox("No active game to save.", "Save Game", wx.OK | wx.ICON_INFORMATION)
            return
        if not account_service.is_logged_in():
            wx.MessageBox("You must be signed in to save to the cloud.", "Save Game", wx.OK | wx.ICON_WARNING)
            return
        speak("Saving game to cloud, please wait.")
        wx.Yield()
        try:
            json_str = save_system.serialize_to_json_string(self.game_state)
            result = account_service.upload_save(json_str, save_name="default")
            if result.ok:
                wx.MessageBox("Game saved to cloud successfully.", "Save Game", wx.OK | wx.ICON_INFORMATION)
                speak("Game saved to cloud successfully.")
            else:
                wx.MessageBox(f"Cloud save failed: {result.message}", "Save Game", wx.OK | wx.ICON_ERROR)
                speak(f"Cloud save failed. {result.message}")
        except (OSError, ValueError, TypeError) as exc:
            wx.MessageBox(f"Cloud save error: {exc}", "Save Game", wx.OK | wx.ICON_ERROR)
            speak("Cloud save encountered an error.")

    def show_settings_placeholder(self):
        self._push_nav(self.show_settings_placeholder)
        self.clear()
        self.set_status("Settings")
        self._add_section_heading("Settings", "Game settings, account management, and accessibility options.")
        box_acct = self._add_group("Account", "Manage your online account for cloud saves and multiplayer.")
        if account_service.is_logged_in():
            username = account_service.get_username()
            acct_info = wx.StaticText(self.scroll, label=f"Signed in as: {username}")
            acct_info.SetForegroundColour(self.SUCCESS)
            box_acct.Add(acct_info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            logout_btn = wx.Button(self.scroll, label="&Log Out", size=(200, 42))
            self._style_control(logout_btn)
            logout_btn.Bind(wx.EVT_BUTTON, lambda e: (account_service.logout(), speak("Logged out."), self.show_settings_placeholder()))
            box_acct.Add(logout_btn, 0, wx.ALL, 6)
        else:
            acct_info = wx.StaticText(self.scroll, label="Not signed in. Cloud saves and multiplayer require an account.")
            acct_info.SetForegroundColour(self.WARNING)
            box_acct.Add(acct_info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            login_btn = wx.Button(self.scroll, label="&Log In", size=(200, 42))
            self._style_control(login_btn)
            login_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_login_screen())
            box_acct.Add(login_btn, 0, wx.ALL, 6)
            register_btn = wx.Button(self.scroll, label="&Create Account", size=(200, 42))
            self._style_control(register_btn)
            register_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_register_screen())
            box_acct.Add(register_btn, 0, wx.ALL, 6)
        box = self._add_group("General Settings", "This screen is ready for future expansion.")
        info = self._make_readable_text(
            "Additional settings will be added here later.\n\n"
            "Planned areas include:\n"
            "- Accessibility options\n"
            "- Audio and speech preferences\n"
            "- Multiplayer settings\n"
            "- Visual preferences\n"
            "- Save and data management\n",
            min_height=160,
        )
        box.Add(info, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Main Menu", self.show_main_menu)
        self.scroll.Layout()
        self.scroll.FitInside()

    def show_remote_multiplayer(self):
        self._push_nav(self.show_remote_multiplayer)
        self.clear()
        self.set_status("Multiplayer")
        self._add_section_heading("Multiplayer", "Host or join a one versus one match over the internet.")
        box = self._add_group("Online Match Setup", "One player hosts a session, the other joins using the session code.")
        info = self._make_readable_text(
            "Recommended easy path right now:\n"
            "1. Host creates a session on their machine.\n"
            "2. Host shares the displayed IP:Port with their friend.\n"
            "3. Friend joins that address directly.\n\n"
            "For real frictionless internet play later, the next step is adding a lightweight relay or VPS lobby service.\n",
            min_height=180,
        )
        box.Add(info, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        host_btn = wx.Button(self.scroll, label="&Host Remote Match")
        self._style_control(host_btn)
        host_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_host_remote_match())
        row.Add(host_btn, 0, wx.ALL, 5)
        join_btn = wx.Button(self.scroll, label="&Join Remote Match")
        self._style_control(join_btn)
        join_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_join_remote_match())
        row.Add(join_btn, 0, wx.ALL, 5)
        box.Add(row, 0, wx.ALL, 5)
        self._simple_back("&Back to Welcome Screen", self.show_main_menu)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(host_btn.SetFocus)

    def show_host_remote_match(self):
        self._push_nav(self.show_host_remote_match)
        self.clear()
        self.set_status("Host Remote Match")
        self._add_section_heading("Host Remote Match", "Create a direct one-versus-one match session")
        box = self._add_group("Host Session", "Start listening on your machine and share the session code with your friend.")
        form = wx.FlexGridSizer(cols=2, vgap=10, hgap=12)
        form.AddGrowableCol(1)
        labels = [("Host Club Name:", "host_club_name", "Home United"), ("Country:", None, None), ("Port:", "host_port", str(DEFAULT_PORT))]
        for label, attr, default in labels:
            lbl = wx.StaticText(self.scroll, label=label)
            lbl.SetForegroundColour(self.FG)
            form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            if label == "Country:":
                choice = wx.Choice(self.scroll, choices=list(LEAGUE_DATA.keys()))
                self._style_control(choice)
                choice.SetSelection(0)
                self.host_country = choice
                form.Add(choice, 0)
            else:
                txt = wx.TextCtrl(self.scroll, value=default, size=(280, -1))
                self._style_control(txt)
                setattr(self, attr, txt)
                form.Add(txt, 0, wx.EXPAND)
        box.Add(form, 0, wx.ALL | wx.EXPAND, 10)
        btn = wx.Button(self.scroll, label="Start &Hosting")
        self._style_control(btn)
        btn.Bind(wx.EVT_BUTTON, self._start_hosting_remote_match)
        box.Add(btn, 0, wx.ALL, 6)
        self._simple_back("&Back to Remote Multiplayer", self.show_remote_multiplayer)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _start_hosting_remote_match(self, event):
        club_name = self.host_club_name.GetValue().strip() or "Home United"
        country = self.host_country.GetStringSelection()
        port = int(self.host_port.GetValue() or DEFAULT_PORT)
        session = network_service.host_session(port=port)
        host_club = self._build_quick_match_club(club_name, country, home=True)
        self.show_host_wait_screen(session, host_club, country)

    def show_host_wait_screen(self, session, host_club, country):
        self._push_nav(lambda track=False: self.show_host_wait_screen(session, host_club, country))
        self.clear()
        self.set_status("Waiting for Guest")
        self._add_section_heading("Waiting for Guest", "Share this session code with your friend and wait for them to connect.")
        box = self._add_group("Host Session Active", f"Session Code: {session.code}")
        txt = self._make_readable_text(
            f"Session Code: {session.code}\n\n"
            f"Your friend should join using this address.\n"
            f"If you are across different networks, you may need port forwarding on your router for port {session.port}.\n"
            f"A future VPS relay option will remove that friction.\n",
            min_height=220,
        )
        box.Add(txt, 0, wx.EXPAND | wx.ALL, 10)
        self._host_wait_state = {"host_club": host_club, "country": country, "session": session}
        self.host_wait_label = wx.StaticText(self.scroll, label="Waiting for connection...")
        self.host_wait_label.SetForegroundColour(self.WARNING)
        box.Add(self.host_wait_label, 0, wx.ALL, 10)
        cancel = wx.Button(self.scroll, label="&Cancel Hosting")
        self._style_control(cancel)
        cancel.Bind(wx.EVT_BUTTON, lambda e: (network_service.reset(), self.show_remote_multiplayer()))
        box.Add(cancel, 0, wx.ALL, 5)
        self._host_poll_timer = wx.CallLater(300, self._poll_host_session)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(txt.SetFocus)

    def _poll_host_session(self):
        result = network_service.wait_for_guest()
        if result:
            self.host_wait_label.SetLabel(f"Guest connected from {result['address']}")
            network_service.send_event("host_ready", {"club_name": self._host_wait_state['host_club'].name, "country": self._host_wait_state['country']})
            self.show_remote_host_lobby()
            return
        self._host_poll_timer = wx.CallLater(300, self._poll_host_session)

    def show_remote_host_lobby(self):
        self._push_nav(self.show_remote_host_lobby)
        self.clear()
        self.set_status("Remote Match Lobby")
        self._add_section_heading("Remote Match Lobby", "Connected. Ready to start the quick match.")
        box = self._add_group("Host Lobby", "Waiting for both clubs and then the host can launch the match.")
        self.remote_lobby_text = self._make_readable_text("Connected. Waiting for guest club information...", min_height=220)
        box.Add(self.remote_lobby_text, 0, wx.EXPAND | wx.ALL, 10)
        start_btn = wx.Button(self.scroll, label="&Start Remote Quick Match")
        self._style_control(start_btn)
        start_btn.Bind(wx.EVT_BUTTON, self._start_remote_host_match)
        box.Add(start_btn, 0, wx.ALL, 5)
        self._remote_poll_timer = wx.CallLater(300, self._poll_remote_lobby_host)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _poll_remote_lobby_host(self):
        event = network_service.poll_event()
        if event:
            if event.get("type") == "guest_ready":
                payload = event.get("payload", {})
                self._host_wait_state["guest_club_name"] = payload.get("club_name", "Away Rovers")
                self.remote_lobby_text.SetValue(f"Guest connected with club: {self._host_wait_state['guest_club_name']}\nPress Start Remote Quick Match when ready.")
                return
        self._remote_poll_timer = wx.CallLater(300, self._poll_remote_lobby_host)

    def _start_remote_host_match(self, event):
        state = self._host_wait_state
        home = state["host_club"]
        away = self._build_quick_match_club(state.get("guest_club_name", "Away Rovers"), state["country"], home=False)
        result = game_engine.simulate_match(home, away)
        payload = {
            "score": f"{result.home_team} {result.home_goals} - {result.away_goals} {result.away_team}",
            "attendance": result.attendance,
            "commentary": [ev.commentary for ev in result.events[:18]],
        }
        network_service.send_event("match_result", payload)
        self._show_remote_result(payload, host=True)

    def show_join_remote_match(self):
        self._push_nav(self.show_join_remote_match)
        self.clear()
        self.set_status("Join Remote Match")
        self._add_section_heading("Join Remote Match", "Connect to a host using IP and port")
        box = self._add_group("Join Session", "Enter the host IP address and port, then connect.")
        form = wx.FlexGridSizer(cols=2, vgap=10, hgap=12)
        form.AddGrowableCol(1)
        for label, attr, default in [("Host IP:", "join_host_ip", "127.0.0.1"), ("Port:", "join_port", str(DEFAULT_PORT)), ("Your Club Name:", "join_club_name", "Away Rovers"), ("Country:", None, None)]:
            lbl = wx.StaticText(self.scroll, label=label)
            lbl.SetForegroundColour(self.FG)
            form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            if label == "Country:":
                choice = wx.Choice(self.scroll, choices=list(LEAGUE_DATA.keys()))
                self._style_control(choice)
                choice.SetSelection(0)
                self.join_country = choice
                form.Add(choice, 0)
            else:
                txt = wx.TextCtrl(self.scroll, value=default, size=(280, -1))
                self._style_control(txt)
                setattr(self, attr, txt)
                form.Add(txt, 0, wx.EXPAND)
        box.Add(form, 0, wx.ALL | wx.EXPAND, 10)
        btn = wx.Button(self.scroll, label="&Join Session")
        self._style_control(btn)
        btn.Bind(wx.EVT_BUTTON, self._join_remote_session)
        box.Add(btn, 0, wx.ALL, 6)
        self._simple_back("&Back to Remote Multiplayer", self.show_remote_multiplayer)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _join_remote_session(self, event):
        host = self.join_host_ip.GetValue().strip() or "127.0.0.1"
        port = int(self.join_port.GetValue() or DEFAULT_PORT)
        club_name = self.join_club_name.GetValue().strip() or "Away Rovers"
        country = self.join_country.GetStringSelection()
        network_service.join_session(host, port)
        network_service.send_event("guest_ready", {"club_name": club_name, "country": country})
        self.show_join_wait_screen(club_name)

    def show_join_wait_screen(self, club_name):
        self._push_nav(lambda track=False: self.show_join_wait_screen(club_name))
        self.clear()
        self.set_status("Connected to Host")
        self._add_section_heading("Connected to Host", "Waiting for the host to start the match")
        box = self._add_group("Guest Lobby", f"Your club: {club_name}")
        text = self._make_readable_text("Connected successfully. Waiting for host to start the quick match...", min_height=220)
        box.Add(text, 0, wx.EXPAND | wx.ALL, 10)
        self._guest_poll_timer = wx.CallLater(300, self._poll_guest_wait)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(text.SetFocus)

    def _poll_guest_wait(self):
        event = network_service.poll_event()
        if event:
            if event.get("type") == "match_result":
                self._show_remote_result(event.get("payload", {}), host=False)
                return
        self._guest_poll_timer = wx.CallLater(300, self._poll_guest_wait)

    def _show_remote_result(self, payload, host=False):
        self._push_nav(lambda track=False: self._show_remote_result(payload, host=host))
        self.clear()
        self.set_status("Remote Match Result")
        self._add_section_heading("Remote Match Result", "Completed remote quick match")
        box = self._add_group("Result", "Host and guest both receive the same result summary.")
        lines = [payload.get("score", "No score available"), f"Attendance: {payload.get('attendance', 0):,}", "", "Commentary:"]
        lines.extend(payload.get("commentary", []))
        info = self._make_readable_text("\n".join(lines), min_height=380)
        box.Add(info, 0, wx.EXPAND | wx.ALL, 10)
        if host:
            speak("Remote quick match complete as host.", interrupt=False)
        else:
            speak("Remote quick match result received.", interrupt=False)
        network_service.reset()
        self._simple_back("&Back to Welcome Screen", self.show_main_menu)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(info.SetFocus)

    def _build_quick_match_club(self, name, country, home=False):
        short = ''.join(ch for ch in name.upper() if ch.isalpha())[:3] or ("HOM" if home else "AWY")
        club = Club(
            id=f"mp_{short}_{'h' if home else 'a'}",
            name=name,
            short_name=short,
            country=country,
            league_tier=5,
            reputation=30,
            budget=500000,
            wage_budget_weekly=30000,
            stadium_name=f"{name} Arena",
            stadium_capacity=7000,
            is_player_club=home,
        )
        squad = []
        for pos, count in [(Position.GK, 2), (Position.DEF, 6), (Position.MID, 6), (Position.FWD, 4)]:
            for _ in range(count):
                p = generate_player(country, pos, 5, age=24)
                p.scouting_notes = "Quick multiplayer prototype player."
                squad.append(p)
        club.players = squad
        club.auto_select_squad()
        return club

    def _load_existing_game(self):
        loaded = save_system.load_game()
        if loaded:
            self.game_state = loaded
            self._season_prize_awarded = False
            self.show_dashboard()
            speak("Saved game loaded.", interrupt=False)
        else:
            wx.MessageBox("No saved game found.", "Load Game", wx.OK | wx.ICON_INFORMATION)
            self.show_main_menu()

    def show_cloud_load(self):
        self._push_nav(self.show_cloud_load)
        self.clear()
        self.set_status("Load from Cloud")
        self._add_section_heading("Cloud Saves", "Select a cloud save to download and load.")
        box = self._add_group("Your Cloud Saves", "Choose a save to load or delete.")
        saves = account_service.list_saves()
        if not saves:
            lbl = wx.StaticText(self.scroll, label="No cloud saves found. Play a game and save to upload your first cloud save.")
            lbl.SetForegroundColour(self.MUTED_FG)
            box.Add(lbl, 0, wx.ALL, 10)
        else:
            self._cloud_save_list = wx.ListBox(self.scroll, style=wx.LB_SINGLE)
            self._style_control(self._cloud_save_list, surface=True)
            self._cloud_save_list.SetMinSize((-1, 200))
            self._cloud_save_list.SetName("Cloud Saves")
            self._cloud_save_names = []
            for s in saves:
                name = s.get("save_name", "default")
                updated = s.get("updated_at", "unknown")
                self._cloud_save_list.Append(f"{name} (last saved: {updated})")
                self._cloud_save_names.append(name)
            if self._cloud_save_list.GetCount() > 0:
                self._cloud_save_list.SetSelection(0)
            box.Add(self._cloud_save_list, 0, wx.EXPAND | wx.ALL, 10)
            btn_row = wx.BoxSizer(wx.HORIZONTAL)
            load_btn = wx.Button(self.scroll, label="&Load Selected Save", size=(220, 42))
            self._style_control(load_btn)
            load_btn.Bind(wx.EVT_BUTTON, self._do_cloud_load)
            btn_row.Add(load_btn, 0, wx.ALL, 5)
            del_btn = wx.Button(self.scroll, label="&Delete Selected Save", size=(220, 42))
            self._style_control(del_btn)
            del_btn.Bind(wx.EVT_BUTTON, self._do_cloud_delete)
            btn_row.Add(del_btn, 0, wx.ALL, 5)
            box.Add(btn_row, 0, wx.ALL, 10)
        self._simple_back("&Back to Main Menu", self.show_main_menu)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _do_cloud_load(self, event):
        sel = self._cloud_save_list.GetSelection()
        if sel == wx.NOT_FOUND:
            speak("No save selected.")
            return
        save_name = self._cloud_save_names[sel]
        speak(f"Downloading save {save_name}, please wait.")
        wx.Yield()
        result = account_service.download_save(save_name)
        if result.ok:
            loaded = save_system.deserialize_from_json_string(result.save_data)
            if loaded:
                self.game_state = loaded
                self._season_prize_awarded = False
                save_system.save_game(loaded)
                self.show_dashboard()
                speak(f"Cloud save {save_name} loaded.", interrupt=False)
            else:
                wx.MessageBox("Failed to parse cloud save data.", "Cloud Load", wx.OK | wx.ICON_ERROR)
                speak("Failed to parse cloud save data.")
        else:
            wx.MessageBox(result.message, "Cloud Load", wx.OK | wx.ICON_ERROR)
            speak(f"Cloud load failed. {result.message}")

    def _do_cloud_delete(self, event):
        sel = self._cloud_save_list.GetSelection()
        if sel == wx.NOT_FOUND:
            speak("No save selected.")
            return
        save_name = self._cloud_save_names[sel]
        confirm = wx.MessageBox(
            f"Are you sure you want to delete cloud save '{save_name}'? This cannot be undone.",
            "Confirm Delete", wx.YES_NO | wx.ICON_WARNING,
        )
        if confirm != wx.YES:
            return
        result = account_service.delete_save(save_name)
        if result.ok:
            speak(f"Cloud save {save_name} deleted.")
            self.show_cloud_load()
        else:
            wx.MessageBox(result.message, "Delete Failed", wx.OK | wx.ICON_ERROR)
            speak(f"Delete failed. {result.message}")

    def show_club_creation(self):
        self._push_nav(self.show_club_creation)
        self.clear()
        self.set_status("Create Your Club")
        self._add_section_heading("Create Your Club", "Enter your club details. Use Tab to move between fields.")
        box = self._add_group("Club Setup", "Choose your club name, short name, country and stadium.")
        form = wx.FlexGridSizer(cols=2, vgap=12, hgap=15)
        form.AddGrowableCol(1)
        labels = ["Club Name:", "Short Name (2-4 letters):", "Country:", "League Info:", "Stadium Name:"]
        for text in labels:
            lbl = wx.StaticText(self.scroll, label=text)
            lbl.SetForegroundColour(self.FG)
            form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            if text == "Club Name:":
                self.txt_club_name = wx.TextCtrl(self.scroll, size=(300, -1))
                self._style_control(self.txt_club_name)
                form.Add(self.txt_club_name, 0, wx.EXPAND)
            elif text == "Short Name (2-4 letters):":
                self.txt_short_name = wx.TextCtrl(self.scroll, size=(100, -1))
                self._style_control(self.txt_short_name)
                form.Add(self.txt_short_name, 0)
            elif text == "Country:":
                self.choice_country = wx.Choice(self.scroll, choices=list(LEAGUE_DATA.keys()))
                self._style_control(self.choice_country)
                self.choice_country.SetSelection(0)
                self.choice_country.Bind(wx.EVT_CHOICE, self._on_country_change)
                form.Add(self.choice_country, 0)
            elif text == "League Info:":
                self.lbl_league_info = wx.StaticText(self.scroll, label="")
                self.lbl_league_info.SetForegroundColour(self.MUTED_FG)
                self.lbl_league_info.Wrap(720)
                form.Add(self.lbl_league_info, 0, wx.EXPAND)
                self._update_league_info()
            else:
                self.txt_stadium = wx.TextCtrl(self.scroll, size=(300, -1))
                self._style_control(self.txt_stadium)
                form.Add(self.txt_stadium, 0, wx.EXPAND)
        box.Add(form, 0, wx.ALL | wx.EXPAND, 15)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("&Create Club and Start Game", self._on_create_club), ("&Back to Welcome Screen", lambda e: self.show_main_menu())]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self.txt_club_name.SetFocus)

    def _on_country_change(self, event):
        self._update_league_info()

    def _update_league_info(self):
        country = self.choice_country.GetString(self.choice_country.GetSelection())
        profile = game_engine.get_league_financial_profile(country)
        symbol = "\u00a3" if profile["currency"] == "GBP" else "\u20ac"
        self.lbl_league_info.SetLabel(
            f"{profile['league_name']} (Tier {profile['tier']}) - Currency: {profile['currency']} - "
            f"Average budget: {symbol}{profile['avg_budget']:,} - Weekly wage benchmark: {symbol}{profile['avg_wage']:,}"
        )

    def _on_create_club(self, event):
        name = self.txt_club_name.GetValue().strip()
        short = self.txt_short_name.GetValue().strip().upper()
        country = self.choice_country.GetString(self.choice_country.GetSelection())
        stadium = self.txt_stadium.GetValue().strip() or f"{name} Stadium"
        if not name or len(short) < 2 or len(short) > 4:
            wx.MessageBox("Enter a valid club name and 2-4 character short name.", "Error", wx.OK | wx.ICON_ERROR)
            return
        self.game_state = game_engine.create_new_game(name, short, country, stadium)
        self.autosave()
        self._nav_stack = []
        self.show_dashboard(track=True)

    def show_dashboard(self, track=True):
        if track:
            self._push_nav(self.show_dashboard)
        self.clear()
        gs = self.game_state
        club = gs.clubs[gs.player_club_id]
        table = game_engine.get_league_table(gs)
        position = next((i + 1 for i, c in enumerate(table) if c.id == gs.player_club_id), 0)
        unread = game_engine.get_unread_inbox_count(gs)
        self.set_status(f"Main Menu - {club.name}")
        self._top_header()
        self._add_section_heading(f"{club.name} - Main Menu", "Main club overview and main navigation.")
        box = self._add_group(
            "Club Overview",
            f"League: {gs.league.name} - Position: {position} of {len(table)}\nBudget Available: {club.budget:,} | Transfer Budget: {club.transfer_budget:,} | Weekly Wages: {club.total_wages:,}",
        )
        first_btn = None
        grid = wx.GridSizer(cols=3, vgap=10, hgap=10)
        for label, handler in [
            ("&Club", self.show_club_hub),
            (f"&Inbox ({unread} unread)" if unread else "&Inbox", self.show_inbox),
            ("&Squad", self.show_squad),
            ("&Transfer Market", self.show_transfers),
            ("&Match Day", self.show_match_day),
            ("&League Table", self.show_league_table),
            ("&Competitions", self.show_competitions_overview),
            ("&Welcome Screen", self.show_main_menu),
        ]:
            btn = wx.Button(self.scroll, label=label, size=(220, 44))
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, lambda e, h=handler: h())
            if first_btn is None:
                first_btn = btn
            grid.Add(btn, 0, wx.EXPAND)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        if first_btn:
            wx.CallAfter(first_btn.SetFocus)
        speak(f"Dashboard. {club.name}. Position {position} in {gs.league.name}. Week {gs.league.current_week} of {gs.league.total_weeks}. {unread} unread messages.", interrupt=False)

    def _simple_back(self, label="&Back to Main Menu", handler=None):
        btn = wx.Button(self.scroll, label=label)
        self._style_control(btn)
        btn.Bind(wx.EVT_BUTTON, lambda e: (handler() if handler else self.show_dashboard()))
        self.sizer.Add(btn, 0, wx.ALL, 10)

    def show_inbox(self):
        self._push_nav(self.show_inbox)
        self.clear()
        self._top_header()
        self._add_section_heading("Inbox", "Messages from scouts, finances, transfers and competitions")
        box = self._add_group("Club Inbox", "Open a message to read more or respond to transfer offers.")
        self.inbox_list = wx.ListBox(self.scroll)
        self._style_control(self.inbox_list, surface=True)
        self.inbox_list.SetName("Inbox Messages")
        self._inbox_items = list(self.game_state.inbox)
        unread_count = sum(1 for m in self._inbox_items if not m.read)
        for msg in self._inbox_items:
            prefix = "Unread" if not msg.read else "Read"
            self.inbox_list.Append(f"{prefix} - Week {msg.week} - {msg.message_type.value} - {msg.subject}")
        if self._inbox_items:
            self.inbox_list.SetSelection(0)
        box.Add(self.inbox_list, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        open_btn = wx.Button(self.scroll, label="&Open Message")
        self._style_control(open_btn)
        open_btn.Bind(wx.EVT_BUTTON, self._open_selected_inbox_message)
        row.Add(open_btn, 0, wx.ALL, 5)
        mark_read_btn = wx.Button(self.scroll, label="Mark &All as Read")
        self._style_control(mark_read_btn)
        mark_read_btn.Bind(wx.EVT_BUTTON, self._mark_all_inbox_read)
        row.Add(mark_read_btn, 0, wx.ALL, 5)
        box.Add(row, 0, wx.ALL, 5)
        self._simple_back()
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self.inbox_list.SetFocus)
        speak(f"Inbox. {len(self._inbox_items)} messages, {unread_count} unread. Use arrow keys to navigate, Enter to open.", interrupt=False)

    def _mark_all_inbox_read(self, event=None):
        for msg in self.game_state.inbox:
            msg.read = True
        self.autosave()
        self.show_inbox()
        speak("All messages marked as read.", interrupt=False)

    def _open_selected_inbox_message(self, event=None):
        idx = self.inbox_list.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._inbox_items):
            return
        msg = self._inbox_items[idx]
        msg.read = True
        if msg.action_required and msg.metadata.get("offer_id"):
            self.show_transfer_offer_message(msg)
        else:
            self.show_inbox_message_detail(msg)

    def show_inbox_message_detail(self, msg):
        self._push_nav(lambda track=False: self.show_inbox_message_detail(msg))
        self.clear()
        self._top_header()
        self._add_section_heading(msg.subject, msg.message_type.value)
        box = self._add_group("Message", f"Week {msg.week} - Season {msg.season}")
        text = self._make_readable_text(msg.body, min_height=320)
        box.Add(text, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Inbox", self.show_inbox)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(text.SetFocus)

    def show_transfer_offer_message(self, msg):
        offer_id = msg.metadata.get("offer_id")
        offer = next((o for o in self.game_state.incoming_transfer_offers if o.id == offer_id and o.status == "pending"), None)
        self._push_nav(lambda track=False: self.show_transfer_offer_message(msg))
        self.clear()
        self._top_header()
        self._add_section_heading(msg.subject, "Incoming transfer offer")
        box = self._add_group("Offer Review", "Accept or reject the incoming offer.")
        text = self._make_readable_text(msg.body, min_height=220)
        box.Add(text, 0, wx.EXPAND | wx.ALL, 10)
        if offer:
            player = next((p for p in self.game_state.clubs[self.game_state.player_club_id].players if p.id == offer.player_id), None)
            buyer = self.game_state.clubs.get(offer.buyer_club_id)
            details = self._make_readable_text(
                f"Player: {player.full_name if player else 'Unknown'}\n"
                f"Buying Club: {buyer.name if buyer else 'Unknown'}\n"
                f"Bid: {offer.fee:,}",
                min_height=180,
            )
            box.Add(details, 0, wx.EXPAND | wx.ALL, 10)
            row = wx.BoxSizer(wx.HORIZONTAL)
            accept_btn = wx.Button(self.scroll, label="&Accept Offer")
            self._style_control(accept_btn)
            accept_btn.Bind(wx.EVT_BUTTON, lambda e: self._respond_to_offer(offer.id, True))
            row.Add(accept_btn, 0, wx.ALL, 5)
            reject_btn = wx.Button(self.scroll, label="&Reject Offer")
            self._style_control(reject_btn)
            reject_btn.Bind(wx.EVT_BUTTON, lambda e: self._respond_to_offer(offer.id, False))
            row.Add(reject_btn, 0, wx.ALL, 5)
            box.Add(row, 0, wx.ALL, 5)
        self._simple_back("&Back to Inbox", self.show_inbox)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _respond_to_offer(self, offer_id, accept):
        success, msg = game_engine.respond_to_transfer_offer(self.game_state, offer_id, accept)
        if success:
            self.autosave()
        wx.MessageBox(msg, "Transfer Offer", wx.OK | wx.ICON_INFORMATION)
        self.show_inbox()

    def show_club_hub(self):
        self._push_nav(self.show_club_hub)
        self.clear()
        self._top_header()
        self._add_section_heading("Club", "Trophies, records, finances and infrastructure")
        box = self._add_group("Club Hub", "Review honours, long-term club history, finances and club development.")
        for label, handler in [
            ("&Trophy Cabinet", self.show_trophy_cabinet),
            ("Club &Records", self.show_club_records),
            ("&Finances", self.show_finance_screen),
            ("&Infrastructure", self.show_infrastructure_hub),
        ]:
            btn = wx.Button(self.scroll, label=label, size=(320, 42))
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, lambda e, h=handler: h())
            box.Add(btn, 0, wx.ALL, 6)
        self._simple_back()
        self.scroll.Layout()
        self.scroll.FitInside()

    def show_finance_screen(self):
        self._push_nav(self.show_finance_screen)
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        self._add_section_heading("Club Finances", "Current budget, transfer budget, wage budget and spending control")
        box = self._add_group("Financial Control Centre", "Review how much money is available and set a transfer spending limit.")
        text = self._make_readable_text(
            f"Current Overall Budget: {club.budget:,}\n"
            f"Current Transfer Budget: {club.transfer_budget:,}\n"
            f"Transfer Spending Limit: {club.transfer_spending_limit:,}\n"
            f"Weekly Wage Budget: {club.wage_budget_weekly:,}\n"
            f"Current Weekly Wages: {club.total_wages:,}\n"
            f"Balance: {club.balance:,}\n"
            f"Debt: {club.debt:,}\n"
            f"Players Sold This Season: {club.sold_players_income_season:,}\n"
            f"Players Bought This Season: {club.bought_players_spend_season:,}\n",
            min_height=240,
        )
        box.Add(text, 0, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self.scroll, label="Set Transfer Spending Limit:")
        lbl.SetForegroundColour(self.FG)
        row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.finance_limit = wx.SpinCtrl(self.scroll, min=0, max=max(1000, club.budget * 3), initial=int(club.transfer_spending_limit or club.transfer_budget))
        self._style_control(self.finance_limit)
        row.Add(self.finance_limit, 0, wx.RIGHT, 8)
        save_btn = wx.Button(self.scroll, label="&Apply Limit")
        self._style_control(save_btn)
        save_btn.Bind(wx.EVT_BUTTON, self._apply_finance_limit)
        row.Add(save_btn, 0)
        box.Add(row, 0, wx.ALL, 10)
        self._simple_back("&Back to Club", self.show_club_hub)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(text.SetFocus)

    def _apply_finance_limit(self, event):
        club = self.game_state.clubs[self.game_state.player_club_id]
        club.transfer_spending_limit = max(0, min(int(self.finance_limit.GetValue()), int(club.budget)))
        self.autosave()
        wx.MessageBox(f"Transfer spending limit set to {club.transfer_spending_limit:,}.", "Finances", wx.OK | wx.ICON_INFORMATION)
        self.show_finance_screen()

    def show_club_records(self):
        self._push_nav(self.show_club_records)
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        summary = self._native_records_summary(club)
        self._add_section_heading("Club Records", "Best performances in club history")
        box = self._add_group("Historical Records", "League and match milestones for your club.")
        if summary and not summary.get("error"):
            lines = [
                f"Highest League Finish: {summary.get('highest_league_finish', 'Not set')}",
                f"Most Points: {summary.get('most_points', 0)}",
                f"Most Goals Scored: {summary.get('most_goals_scored', 0)}",
                f"Best Goal Difference: {summary.get('best_goal_difference', 0)}",
                f"Biggest Win: {summary.get('biggest_win', 'None')}",
                f"Biggest Defeat: {summary.get('biggest_defeat', 'None')}",
            ]
        else:
            lines = [
                f"Highest League Finish: {club.records.highest_league_finish if club.records.highest_league_finish != 999 else 'Not set'}",
                f"Most Points: {club.records.most_points}",
                f"Most Goals Scored: {club.records.most_goals_scored}",
                f"Best Goal Difference: {club.records.best_goal_difference if club.records.best_goal_difference != -999 else 0}",
                f"Biggest Win: {club.records.biggest_win}",
                f"Biggest Defeat: {club.records.biggest_defeat}",
            ]
        txt = self._make_readable_text("\n".join(lines), min_height=240)
        box.Add(txt, 0, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Club", self.show_club_hub)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(txt.SetFocus)

    def show_squad(self):
        self._push_nav(self.show_squad)
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        self._add_section_heading("Squad", "Select exactly 11 available players for the next match")
        box = self._add_group("Starting Eleven", "Check exactly 11 available players to set your team before match day. Use Space to check/uncheck.")
        self.squad_check = wx.CheckListBox(self.scroll, choices=[])
        self._style_control(self.squad_check, surface=True)
        self.squad_check.SetName("Squad Selection")
        self._squad_players = list(club.players)
        checked_count = 0
        for i, p in enumerate(self._squad_players):
            self.squad_check.Append(f"{p.position.name} - {p.full_name} - OVR {p.overall} {'(Unavailable)' if not p.is_available else ''}")
            if p.id in club.selected_squad_ids:
                self.squad_check.Check(i)
                checked_count += 1
        box.Add(self.squad_check, 1, wx.EXPAND | wx.ALL, 10)
        squad_info = wx.StaticText(self.scroll, label=f"Currently selected: {checked_count} / 11 players")
        squad_info.SetForegroundColour(self.MUTED_FG)
        box.Add(squad_info, 0, wx.LEFT | wx.BOTTOM, 10)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("&Save Match Squad", self._save_selected_squad), ("Auto Select Best &XI", self._auto_select_squad), ("&Back to Main Menu", lambda e: self.show_dashboard())]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self.squad_check.SetFocus)
        available = sum(1 for p in self._squad_players if p.is_available)
        speak(f"Squad screen. {len(self._squad_players)} players, {available} available. Currently {checked_count} selected. Check exactly 11 players and press Save Match Squad.", interrupt=False)

    def _save_selected_squad(self, event):
        club = self.game_state.clubs[self.game_state.player_club_id]
        selected_ids = [self._squad_players[i].id for i in range(len(self._squad_players)) if self.squad_check.IsChecked(i) and self._squad_players[i].is_available]
        native_result = game_engine.validate_selected_xi_native(self._selected_indices_from_ids(club, selected_ids), self._roster_payload(club))
        if native_result and not native_result.get("ok"):
            wx.MessageBox(native_result.get("message", "Squad validation failed."), "Squad", wx.OK | wx.ICON_INFORMATION)
            return
        ok, msg = game_engine.set_selected_squad(club, selected_ids)
        if ok:
            self.autosave()
        wx.MessageBox(msg, "Squad", wx.OK | wx.ICON_INFORMATION)

    def _auto_select_squad(self, event):
        club = self.game_state.clubs[self.game_state.player_club_id]
        club.auto_select_squad()
        self.autosave()
        self.show_squad()

    def show_pre_kickoff_squad_review(self, fixture=None):
        self._push_nav(lambda track=False: self.show_pre_kickoff_squad_review(fixture))
        self.clear()
        self._top_header()
        gs = self.game_state
        club = gs.clubs[gs.player_club_id]
        fixture = fixture or (self._week_player_fixtures[0] if self._week_player_fixtures else game_engine.get_player_fixture(gs))
        if not fixture:
            self.show_match_day()
            return
        home = gs.clubs[fixture.home_id]
        away = gs.clubs[fixture.away_id]
        selected = game_engine.get_player_selected_squad(club)
        bench = [p for p in club.players if p.id not in club.selected_squad_ids][:7]
        self._add_section_heading("Pre-Kickoff Squad Review", "Review your selected team before starting the match")
        box = self._add_group("Match Preview", f"Fixture: {home.name} vs {away.name}\nCompetition: {game_engine.get_competition_name(gs, fixture)}\nStadium: {home.stadium_name if fixture.home_id == home.id else away.stadium_name}")
        text = self._make_readable_text(
            "Selected XI:\n" + "\n".join([f"- {p.position.value}: {p.full_name} (OVR {p.overall})" for p in selected]) +
            "\n\nBench / Remaining Squad:\n" + ("\n".join([f"- {p.position.value}: {p.full_name} (OVR {p.overall})" for p in bench]) if bench else "No additional players listed."),
            min_height=420,
        )
        box.Add(text, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        play_btn = wx.Button(self.scroll, label="&Play Match")
        self._style_control(play_btn)
        play_btn.Bind(wx.EVT_BUTTON, lambda e: self._start_selected_match_from_review(fixture))
        row.Add(play_btn, 0, wx.ALL, 5)
        back_match_btn = wx.Button(self.scroll, label="&Back to Match Day")
        self._style_control(back_match_btn)
        back_match_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_match_day())
        row.Add(back_match_btn, 0, wx.ALL, 5)
        back_main_btn = wx.Button(self.scroll, label="Back to &Main Menu")
        self._style_control(back_main_btn)
        back_main_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_dashboard())
        row.Add(back_main_btn, 0, wx.ALL, 5)
        box.Add(row, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(text.SetFocus)

    def show_match_day(self):
        self._push_nav(self.show_match_day)
        self.clear()
        self._top_header()
        gs = self.game_state
        if gs.season_over:
            self.show_season_summary()
            return
        club = gs.clubs[gs.player_club_id]
        if len(game_engine.get_player_selected_squad(club)) < 11:
            wx.MessageBox("You need to choose your squad before match day.", "Match Day", wx.OK | wx.ICON_INFORMATION)
            self.show_squad()
            return
        self._week_player_fixtures = game_engine.get_player_fixtures(gs)
        if not self._week_player_fixtures:
            wx.MessageBox("No player fixture this week.", "Match Day", wx.OK)
            self.show_dashboard()
            return
        self._add_section_heading("Match Day", "Review your squad, then play your next fixture and hear the commentary")
        fixture = self._week_player_fixtures[0]
        home_club = gs.clubs[fixture.home_id]
        away_club = gs.clubs[fixture.away_id]
        is_home = fixture.home_id == gs.player_club_id
        opponent = away_club if is_home else home_club
        competition_name = game_engine.get_competition_name(gs, fixture)
        match_preview_lines = [f"You are playing against {opponent.name}."]
        if is_home:
            match_preview_lines.append(f"Venue: {home_club.stadium_name} (Home)")
        else:
            match_preview_lines.append(f"Venue: {away_club.stadium_name} (Away)")
        match_preview_lines.append(f"Competition: {competition_name}")
        preview_box = self._add_group("Match Preview", "\n".join(match_preview_lines))
        speech_text = f"Match Day. You are playing against {opponent.name}."
        if is_home:
            speech_text += f" Playing at home, {home_club.stadium_name}."
        else:
            speech_text += f" Playing away at {away_club.stadium_name}."
        speech_text += f" Competition: {competition_name}."
        speak(speech_text, interrupt=False)
        box = self._add_group("Live Match Centre", "Live commentary is announced and listed as events.")
        squad_names = [p.full_name for p in game_engine.get_player_selected_squad(club)]
        squad_text = wx.StaticText(self.scroll, label="Selected XI: " + ", ".join(squad_names))
        squad_text.SetForegroundColour(self.MUTED_FG)
        box.Add(squad_text, 0, wx.ALL, 10)
        if len(self._week_player_fixtures) > 1:
            self.match_choice = wx.Choice(self.scroll, choices=[self._fixture_label(fx) for fx in self._week_player_fixtures])
            self._style_control(self.match_choice)
            self.match_choice.SetSelection(0)
            box.Add(self.match_choice, 0, wx.ALL | wx.EXPAND, 10)
        else:
            info = wx.StaticText(self.scroll, label=self._fixture_label(self._week_player_fixtures[0]))
            info.SetForegroundColour(self.MUTED_FG)
            box.Add(info, 0, wx.ALL, 10)
        commentary_sizer = self._make_live_commentary_surface()
        box.Add(commentary_sizer, 1, wx.EXPAND | wx.ALL, 10)
        self.match_stats_label = wx.StaticText(self.scroll, label="")
        self.match_stats_label.SetForegroundColour(self.MUTED_FG)
        box.Add(self.match_stats_label, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 10)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        review_btn = wx.Button(self.scroll, label="&Review Selected Squad")
        self._style_control(review_btn)
        review_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_pre_kickoff_squad_review(self._selected_fixture_for_match_day()))
        btns.Add(review_btn, 0, wx.ALL, 5)
        self.btn_play_match = wx.Button(self.scroll, label="&Play Selected Match")
        self._style_control(self.btn_play_match)
        self.btn_play_match.Bind(wx.EVT_BUTTON, self._on_play_match)
        btns.Add(self.btn_play_match, 0, wx.ALL, 5)
        self.btn_continue_match = wx.Button(self.scroll, label="&Back to Main Menu")
        self._style_control(self.btn_continue_match)
        self.btn_continue_match.Bind(wx.EVT_BUTTON, lambda e: self.show_dashboard())
        self.btn_continue_match.Disable()
        btns.Add(self.btn_continue_match, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _selected_fixture_for_match_day(self):
        if hasattr(self, "match_choice"):
            idx = self.match_choice.GetSelection()
            idx = 0 if idx == wx.NOT_FOUND else idx
            return self._week_player_fixtures[idx]
        return self._week_player_fixtures[0]

    def _fixture_label(self, fixture):
        gs = self.game_state
        home = gs.clubs[fixture.home_id]
        away = gs.clubs[fixture.away_id]
        venue = "HOME" if fixture.home_id == gs.player_club_id else "AWAY"
        competition = game_engine.get_competition_name(gs, fixture)
        return f"{home.name} vs {away.name} ({venue}) - {competition}"

    def _start_selected_match_from_review(self, fixture):
        self.show_match_day()
        self._current_match_fixture = fixture
        self._on_play_match(None)

    def _on_play_match(self, event):
        self.btn_play_match.Disable()
        self._full_time_spoken = False
        self._speech_queue = []
        self._match_lines = []
        self.match_commentary_list.Clear()
        self._current_match_fixture = self._selected_fixture_for_match_day()
        play_week = self.game_state.league.current_week
        results = game_engine.play_week(self.game_state)
        selected_result = None
        for fixture, result in results:
            if fixture.home_id == self._current_match_fixture.home_id and fixture.away_id == self._current_match_fixture.away_id and fixture.week == self._current_match_fixture.week and fixture.competition_id == self._current_match_fixture.competition_id:
                selected_result = result
                break
        if selected_result is None:
            self.match_commentary_list.Append("No match result found for the selected fixture.")
            self.btn_continue_match.Enable()
            return
        self._match_events = selected_result.events
        self._match_event_idx = 0
        self._match_result = selected_result
        self._played_week_number = play_week
        self._play_next_event()

    def _event_delay(self, event):
        if event.event_type in (EventType.GOAL, EventType.PENALTY_SCORED):
            return 2600
        if event.event_type in (EventType.RED_CARD, EventType.INJURY):
            return 2200
        if event.event_type in (EventType.HALF_TIME, EventType.FULL_TIME):
            return 2600
        if event.event_type == EventType.KICK_OFF:
            return 1400
        return 900

    def _speak_match_event(self, event):
        if event.event_type == EventType.FULL_TIME:
            if not self._full_time_spoken:
                self._queue_speech(event.commentary)
                self._full_time_spoken = True
            return
        if event.event_type in (EventType.GOAL, EventType.PENALTY_SCORED, EventType.RED_CARD, EventType.INJURY, EventType.HALF_TIME, EventType.KICK_OFF):
            self._queue_speech(event.commentary)

    def _play_next_event(self):
        if self._match_event_idx >= len(self._match_events):
            self._show_match_stats()
            self.autosave()
            self.btn_continue_match.Enable()
            self.btn_continue_match.SetFocus()
            wx.CallLater(500, self.show_post_match_results_screen, self._played_week_number)
            return
        event = self._match_events[self._match_event_idx]
        self._match_event_idx += 1
        self._match_lines.append(event.commentary)
        self.match_commentary_list.Append(event.commentary)
        self.match_commentary_list.SetSelection(self.match_commentary_list.GetCount() - 1)
        self._speak_match_event(event)
        self._commentary_timer = wx.CallLater(self._event_delay(event), self._play_next_event)

    def _show_match_stats(self):
        r = self._match_result
        stadium_name = self.game_state.clubs[self._current_match_fixture.home_id].stadium_name
        self.match_stats_label.SetLabel(f"FULL TIME: {r.home_team} {r.home_goals} - {r.away_goals} {r.away_team}\nShots: {r.home_shots} - {r.away_shots} | Stadium: {stadium_name} | Attendance: {r.attendance:,}")

    def show_post_match_results_screen(self, week):
        self._push_nav(lambda track=False: self.show_post_match_results_screen(week))
        self.clear()
        self._top_header()
        self._add_section_heading("Post-Match Results", "Other results from this round")
        box = self._add_group("Round Results", "After your match, review the rest of the results across the competitions this week.")
        lines = game_engine.get_post_match_other_results(self.game_state, week)
        if not lines:
            lines = ["No additional results available this week."]
        text = self._make_readable_text("\n".join(lines), min_height=340)
        box.Add(text, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Main Menu", self.show_dashboard)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(text.SetFocus)

    def show_league_table(self):
        self._push_nav(self.show_league_table)
        self.clear()
        self._top_header()
        gs = self.game_state
        table = game_engine.get_league_table(gs)
        player_pos = next((i + 1 for i, c in enumerate(table) if c.id == gs.player_club_id), 0)
        self._add_section_heading(f"{gs.league.name} - League Table", "Current standings")
        box = self._add_group("League Table", "Your current league position and standings.")
        table_list = wx.ListCtrl(self.scroll, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._style_control(table_list, surface=True)
        table_list.SetName("League Table")
        for i, (col, w) in enumerate([("Pos", 45), ("Club", 220), ("P", 40), ("W", 40), ("D", 40), ("L", 40), ("GD", 55), ("Pts", 50)]):
            table_list.InsertColumn(i, col, width=w)
        for i, club in enumerate(table, 1):
            idx = table_list.InsertItem(table_list.GetItemCount(), str(i))
            table_list.SetItem(idx, 1, f"{club.name} (YOU)" if club.id == gs.player_club_id else club.name)
            table_list.SetItem(idx, 2, str(club.played))
            table_list.SetItem(idx, 3, str(club.wins))
            table_list.SetItem(idx, 4, str(club.draws))
            table_list.SetItem(idx, 5, str(club.losses))
            table_list.SetItem(idx, 6, f"{club.gd:+d}")
            table_list.SetItem(idx, 7, str(club.points))
        box.Add(table_list, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back()
        self.scroll.Layout()
        self.scroll.FitInside()
        player_club = gs.clubs[gs.player_club_id]
        speak(f"League table. {gs.league.name}. Your position: {player_pos} of {len(table)}. Points: {player_club.points}.", interrupt=False)

    def show_transfers(self):
        self._push_nav(self.show_transfers)
        self.clear()
        self._top_header()
        self._active_negotiation = None
        gs = self.game_state
        club = gs.clubs[gs.player_club_id]
        window = self._native_transfer_window() or game_engine.get_transfer_window_status(gs)
        self._add_section_heading("Transfer Market", "Filter, search, browse and inspect transfer targets")
        box = self._add_group("Transfer Market Browser", f"Current Date: {game_engine.get_current_date(gs).strftime('%d %B %Y')}\nWindow Status: {window['label']}\nTransfer Budget: {club.transfer_budget:,} | Limit: {club.transfer_spending_limit:,} | Wage Budget Weekly: {club.wage_budget_weekly:,}")
        filters = wx.BoxSizer(wx.HORIZONTAL)
        pos_lbl = wx.StaticText(self.scroll, label="Position Filter:")
        pos_lbl.SetForegroundColour(self.FG)
        filters.Add(pos_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.transfer_position_choice = wx.Choice(self.scroll, choices=self.POSITION_FILTERS)
        self._style_control(self.transfer_position_choice)
        self.transfer_position_choice.SetName("Position Filter")
        self.transfer_position_choice.SetSelection(0)
        self.transfer_position_choice.Bind(wx.EVT_CHOICE, lambda e: self._refresh_transfer_market_browser())
        filters.Add(self.transfer_position_choice, 0, wx.RIGHT, 15)
        search_lbl = wx.StaticText(self.scroll, label="Search Player:")
        search_lbl.SetForegroundColour(self.FG)
        filters.Add(search_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.transfer_search = wx.TextCtrl(self.scroll, size=(260, -1))
        self._style_control(self.transfer_search)
        self.transfer_search.SetName("Search Player Name")
        self.transfer_search.Bind(wx.EVT_TEXT, lambda e: self._refresh_transfer_market_browser())
        filters.Add(self.transfer_search, 0, wx.RIGHT, 10)
        box.Add(filters, 0, wx.ALL | wx.EXPAND, 10)
        self.transfer_listbox = wx.ListBox(self.scroll)
        self._style_control(self.transfer_listbox, surface=True)
        self.transfer_listbox.SetName("Transfer Market Players")
        self.transfer_listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._open_selected_transfer_profile)
        self.transfer_listbox.Bind(wx.EVT_KEY_DOWN, self._on_transfer_list_key)
        box.Add(self.transfer_listbox, 1, wx.EXPAND | wx.ALL, 10)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        open_btn = wx.Button(self.scroll, label="&Open Player Sheet")
        self._style_control(open_btn)
        open_btn.Bind(wx.EVT_BUTTON, self._open_selected_transfer_profile)
        btn_row.Add(open_btn, 0, wx.ALL, 5)
        my_squad_btn = wx.Button(self.scroll, label="List &My Player for Sale")
        self._style_control(my_squad_btn)
        my_squad_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_sell_player_screen())
        btn_row.Add(my_squad_btn, 0, wx.ALL, 5)
        back_btn = wx.Button(self.scroll, label="&Back to Main Menu")
        self._style_control(back_btn)
        back_btn.Bind(wx.EVT_BUTTON, lambda e: self.show_dashboard())
        btn_row.Add(back_btn, 0, wx.ALL, 5)
        box.Add(btn_row, 0, wx.ALL, 5)
        self._refresh_transfer_market_browser()
        self.scroll.Layout()
        self.scroll.FitInside()
        window_status = "open" if window["open"] else "closed"
        speak(f"Transfer Market. Window is {window_status}. Transfer budget: {club.transfer_budget:,}. Use Tab to access filters and player list.", interrupt=False)

    def show_sell_player_screen(self):
        self._push_nav(self.show_sell_player_screen)
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        self._add_section_heading("List Player for Sale", "Choose one of your players to put on the market")
        box = self._add_group("Selling Market", "Listed players will receive incoming offers from AI clubs each week.")
        self.sell_list = wx.ListBox(self.scroll)
        self._style_control(self.sell_list, surface=True)
        self.sell_list.SetName("Players Available to List")
        self._sell_players = list(club.players)
        already_listed = sum(1 for p in self._sell_players if p.transfer_listed)
        for p in self._sell_players:
            listed = " [Listed]" if p.transfer_listed else ""
            self.sell_list.Append(f"{p.position.name} - {p.full_name} - OVR {p.overall} - Value {p.value:,}{listed}")
        if self._sell_players:
            self.sell_list.SetSelection(0)
        box.Add(self.sell_list, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        list_btn = wx.Button(self.scroll, label="&List Selected Player")
        self._style_control(list_btn)
        list_btn.Bind(wx.EVT_BUTTON, self._list_selected_player_for_sale)
        row.Add(list_btn, 0, wx.ALL, 5)
        remove_btn = wx.Button(self.scroll, label="&Remove Listing")
        self._style_control(remove_btn)
        remove_btn.Bind(wx.EVT_BUTTON, self._remove_player_listing)
        row.Add(remove_btn, 0, wx.ALL, 5)
        box.Add(row, 0, wx.ALL, 5)
        self._simple_back("&Back to Transfer Market", self.show_transfers)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(self.sell_list.SetFocus)
        speak(f"List player for sale. {len(self._sell_players)} players in squad, {already_listed} currently listed. Select a player and press List Selected Player.", interrupt=False)

    def _remove_player_listing(self, event=None):
        idx = self.sell_list.GetSelection()
        if idx == wx.NOT_FOUND:
            speak("No player selected.", interrupt=False)
            return
        player = self._sell_players[idx]
        if not player.transfer_listed:
            speak(f"{player.full_name} is not currently listed.", interrupt=False)
            return
        player.transfer_listed = False
        player.asking_price_override = 0
        club = self.game_state.clubs[self.game_state.player_club_id]
        self.game_state.transfer_list = [t for t in self.game_state.transfer_list if not (t.player_id == player.id and t.club_id == club.id)]
        self.autosave()
        speak(f"{player.full_name} removed from transfer list.", interrupt=False)
        self.show_sell_player_screen()

    def _list_selected_player_for_sale(self, event):
        idx = self.sell_list.GetSelection()
        if idx == wx.NOT_FOUND:
            speak("No player selected. Use arrow keys to select a player first.", interrupt=False)
            return
        player = self._sell_players[idx]
        if player.transfer_listed:
            speak(f"{player.full_name} is already listed for transfer.", interrupt=False)
            wx.MessageBox(f"{player.full_name} is already listed. Use Remove Listing to delist first.", "Transfer Listing", wx.OK | wx.ICON_INFORMATION)
            return
        min_price = max(1000, player.value // 2)
        max_price = max(min_price + 10000, player.value * 5)
        default_price = max(min_price, player.value)
        asking = wx.GetNumberFromUser(
            f"Set an asking price for {player.full_name}.\nEstimated value: {player.value:,}",
            "Asking Price:",
            "List Player for Sale",
            default_price,
            min_price,
            max_price,
            self,
        )
        if asking == -1:
            return
        success, msg = game_engine.list_player_for_sale(self.game_state, player.id, int(asking))
        if success:
            self.autosave()
            speak(f"{player.full_name} listed for transfer at {asking:,}.", interrupt=False)
        else:
            speak(msg, interrupt=False)
        wx.MessageBox(msg, "Transfer Listing", wx.OK | wx.ICON_INFORMATION)
        self.show_sell_player_screen()

    def _refresh_transfer_market_browser(self):
        position_filter = self.transfer_position_choice.GetStringSelection() if hasattr(self, "transfer_position_choice") else "All"
        search_text = self.transfer_search.GetValue() if hasattr(self, "transfer_search") else ""
        self._transfer_market_items = game_engine.get_transfer_market_players(self.game_state, position_filter=position_filter, search_text=search_text)
        self.transfer_listbox.Clear()
        for listing, player, club in self._transfer_market_items:
            suffix = []
            if player.shortlisted:
                suffix.append("Shortlisted")
            if player.scouted:
                suffix.append("Scouted")
            if player.transfer_listed:
                suffix.append("Listed")
            tag = f" [{', '.join(suffix)}]" if suffix else ""
            self.transfer_listbox.Append(f"{player.position.name} - {player.full_name} - OVR {player.overall} - {club.short_name} - {listing.asking_price:,}{tag}")
        if self._transfer_market_items:
            self.transfer_listbox.SetSelection(0)

    def _on_transfer_list_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._open_selected_transfer_profile()
            return
        event.Skip()

    def _open_selected_transfer_profile(self, event=None):
        idx = self.transfer_listbox.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._transfer_market_items):
            wx.MessageBox("Select a player first.", "Transfer Market", wx.OK | wx.ICON_INFORMATION)
            return
        listing, player, club = self._transfer_market_items[idx]
        self.show_transfer_player_sheet(listing, player, club)

    def show_transfer_player_sheet(self, listing, player, club):
        self._push_nav(lambda track=False: self.show_transfer_player_sheet(listing, player, club))
        self.clear()
        self._top_header()
        profile = game_engine.get_player_market_profile(self.game_state, listing, player, club)
        self._add_section_heading(f"Player Sheet - {profile['name']}", "Detailed player information and market actions")
        box = self._add_group("Transfer Profile", "Inspect the player before making your move.")
        lines = [
            f"Name: {profile['name']}",
            f"Age: {profile['age']}",
            f"Position: {profile['position']}",
            f"Rating: {profile['rating']}/99",
            f"Potential: {profile['potential']}/99",
            f"Nationality: {profile['nationality']}",
            f"Current Club: {profile['current_club']}",
            f"Asking Price: {profile['asking_price']:,}",
            f"Current Wage: {profile['wage']:,} per week",
            f"Contract Years Remaining: {profile['contract_years']}",
            f"Goals This Season: {profile['goals']}",
            f"Assists This Season: {profile['assists']}",
            f"Appearances This Season: {profile['appearances']}",
            f"Career Goals: {profile['career_goals']}",
            f"Career Appearances: {profile['career_appearances']}",
            "",
            "Attributes and Facts:",
        ]
        lines.extend(profile["facts"])
        lines.extend(["", f"Scouting Notes: {profile['scouting_notes']}"])
        data_text = self._make_readable_text("\n".join(lines), min_height=420)
        box.Add(data_text, 1, wx.EXPAND | wx.ALL, 10)
        btns = wx.BoxSizer(wx.VERTICAL)
        for label, handler in [
            ("&Add to Shortlist", lambda e: self._transfer_shortlist_action(player.id)),
            ("&Negotiate Contract", lambda e: self.show_negotiation_screen(listing, player, history=[])),
            ("&Scout Player", lambda e: self._transfer_scout_action(player.id)),
            ("&Back to Transfer Market", lambda e: self.show_transfers()),
        ]:
            btn = wx.Button(self.scroll, label=label, size=(280, 42))
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(data_text.SetFocus)
        speak(f"Player sheet opened for {profile['name']}. Rating {profile['rating']} out of 99. Current club {profile['current_club']}.", interrupt=False)

    def _transfer_shortlist_action(self, player_id):
        success, msg = game_engine.add_player_to_shortlist(self.game_state, player_id)
        if success:
            self.autosave()
        wx.MessageBox(msg, "Shortlist", wx.OK | wx.ICON_INFORMATION)

    def _transfer_scout_action(self, player_id):
        success, msg = game_engine.scout_player(self.game_state, player_id)
        if success:
            self.autosave()
        wx.MessageBox(msg, "Scout Player", wx.OK | wx.ICON_INFORMATION)

    def show_negotiation_screen(self, listing, player, message=None, round_number=1, defaults=None, history=None):
        self._push_nav(lambda track=False: self.show_negotiation_screen(listing, player, message=message, round_number=round_number, defaults=defaults, history=history))
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        demands = game_engine.get_player_contract_demands(player, club)
        self._active_negotiation = {"listing": listing, "player": player, "round": round_number, "history": history or []}
        self._add_section_heading(f"Contract Negotiation - Round {round_number}", "Work toward an agreement with the player")
        info_lines = [
            f"Player: {player.full_name} - {player.position.value} - Overall {player.overall}",
            f"Transfer Fee: {listing.asking_price:,}",
            f"Expected wage: {demands['desired_wage']:,} | Minimum likely wage: {demands['minimum_wage']:,}",
            f"Preferred years: {demands['desired_years']} | Preferred role: {demands['role']}",
            f"Your wage budget weekly: {club.wage_budget_weekly:,}",
        ]
        if message:
            info_lines.append(message)
        box = self._add_group("Negotiation Table", "\n".join(info_lines))
        form = wx.FlexGridSizer(cols=2, vgap=10, hgap=12)
        form.AddGrowableCol(1)
        for label, attr, minv, maxv, initial in [
            ("Weekly Wage Offer:", "neg_wage", 100, max(5000, club.wage_budget_weekly * 3), int((defaults or {}).get("wage", demands["desired_wage"]))),
            ("Contract Length (Years):", "neg_years", 1, 5, int((defaults or {}).get("years", demands["desired_years"])))
        ]:
            lbl = wx.StaticText(self.scroll, label=label)
            lbl.SetForegroundColour(self.FG)
            form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            spin = wx.SpinCtrl(self.scroll, min=minv, max=maxv, initial=initial)
            self._style_control(spin)
            setattr(self, attr, spin)
            form.Add(spin, 0)
        lbl = wx.StaticText(self.scroll, label="Squad Role:")
        lbl.SetForegroundColour(self.FG)
        form.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        self.neg_role = wx.Choice(self.scroll, choices=self.ROLE_OPTIONS)
        self._style_control(self.neg_role)
        role_value = (defaults or {}).get("role", demands["role"])
        self.neg_role.SetSelection(self.ROLE_OPTIONS.index(role_value) if role_value in self.ROLE_OPTIONS else 1)
        form.Add(self.neg_role, 0)
        box.Add(form, 0, wx.ALL, 10)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("&Submit Offer", self._submit_negotiation_offer), ("&Walk Away", lambda e: self.show_transfers())]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _submit_negotiation_offer(self, event):
        if not self._active_negotiation:
            self.show_transfers()
            return
        listing = self._active_negotiation["listing"]
        player = self._active_negotiation["player"]
        round_number = self._active_negotiation["round"]
        history = list(self._active_negotiation.get("history", []))
        wage = int(self.neg_wage.GetValue())
        years = int(self.neg_years.GetValue())
        role = self.neg_role.GetStringSelection()
        buyer = self.game_state.clubs[self.game_state.player_club_id]
        demands = game_engine.get_player_contract_demands(player, buyer)
        role_map = {"Prospect": 35, "Rotation": 50, "Starter": 68, "Key Player": 82}
        insulting_offers = sum(1 for prev in history if prev.get("wage", 0) < demands["minimum_wage"] * 0.75)
        repeated_lowball = sum(1 for prev in history if prev.get("wage", 0) < demands["minimum_wage"])
        if wage < demands["minimum_wage"] * 0.75:
            insulting_offers += 1
        if wage < demands["minimum_wage"]:
            repeated_lowball += 1
        native_eval = self._native_contract_eval({
            "desired_wage": demands["desired_wage"],
            "minimum_wage": demands["minimum_wage"],
            "desired_years": demands["desired_years"],
            "offered_wage": wage,
            "offered_years": years,
            "expected_role_value": role_map.get(player.squad_role_expectation, 50),
            "offered_role_value": role_map.get(role, 50),
            "join_score": game_engine.evaluate_join_decision(player, buyer),
            "repeated_lowball": repeated_lowball,
            "insulting_offers": insulting_offers,
            "player_name": player.full_name,
            "desired_role": player.squad_role_expectation,
            "offered_role": role,
        })
        result = game_engine.negotiate_contract(player, buyer, wage, years, role, negotiation_history=history)
        history.append({"wage": wage, "years": years, "role": role})
        if native_eval and native_eval.get("outcome") != result.get("outcome"):
            self.set_status(f"Native contract kernel differs from Python: {native_eval.get('outcome')} vs {result.get('outcome')}")
        if result["success"]:
            success, msg = game_engine.finalize_transfer_from_negotiation(self.game_state, listing, wage, years, role)
            wx.MessageBox(msg, "Contract Negotiation", wx.OK | wx.ICON_INFORMATION)
            if success:
                self.autosave()
            self.show_transfers()
            return
        if result["outcome"] == "counter":
            self.show_negotiation_screen(
                listing,
                player,
                message=result["message"],
                round_number=round_number + 1,
                defaults={"wage": result.get("counter_wage", wage), "years": result.get("counter_years", years), "role": result.get("counter_role", role)},
                history=history,
            )
            return
        wx.MessageBox(result["message"], "Contract Negotiation", wx.OK | wx.ICON_INFORMATION)
        self.show_transfers()

    def show_infrastructure_hub(self):
        self._push_nav(self.show_infrastructure_hub)
        self.clear()
        self._top_header()
        self._add_section_heading("Infrastructure", "Upgrade the stadium, training and youth systems")
        box = self._add_group("Infrastructure Hub", "Choose one area to improve your club environment.")
        for label, handler in [("&Stadium", self.show_stadium_screen), ("&Training", self.show_training_screen), ("&Youth Academy", self.show_youth_screen)]:
            btn = wx.Button(self.scroll, label=label, size=(320, 42))
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, lambda e, h=handler: h())
            box.Add(btn, 0, wx.ALL, 6)
        self._simple_back("&Back to Club", self.show_club_hub)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _infra_text(self, box, lines):
        txt = self._make_readable_text("\n".join(lines), min_height=220)
        box.Add(txt, 0, wx.EXPAND | wx.ALL, 10)
        return txt

    def _bench(self):
        club = self.game_state.clubs[self.game_state.player_club_id]
        return club, game_engine.get_league_benchmarks(self.game_state, club)

    def show_stadium_screen(self):
        self._push_nav(self.show_stadium_screen)
        self.clear()
        self._top_header()
        club, bench = self._bench()
        self._add_section_heading("Infrastructure - Stadium", "Capacity planning and pitch condition")
        box = self._add_group("Stadium Planning", "Use the combo box or slider to preview a new stadium capacity and hear the cost.")
        target_default = max(club.stadium_capacity + 1000, 5000)
        step_values = [str(v) for v in range(max(1000, club.stadium_capacity), max(club.stadium_capacity + 20000, 20000) + 1, 1000)]
        self._infra_text(box, [
            f"Current Stadium: {club.stadium_name}",
            f"Current Capacity: {club.stadium_capacity:,}",
            f"League Standard Capacity: {int(bench['seating_capacity']):,}",
            f"Pitch Quality: {club.infrastructure.stadium.pitch_quality} ({game_engine.describe_relative(club.infrastructure.stadium.pitch_quality, bench['pitch_quality'])})",
            f"Seating Level: {club.infrastructure.stadium.seating_level} ({game_engine.describe_relative(club.infrastructure.stadium.seating_level, bench['seating_level'])})",
        ])
        row = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self.scroll, label="Target Capacity:")
        lbl.SetForegroundColour(self.FG)
        row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.capacity_combo = wx.ComboBox(self.scroll, choices=step_values, style=wx.CB_DROPDOWN)
        self._style_control(self.capacity_combo)
        self.capacity_combo.SetValue(str(target_default))
        self.capacity_combo.Bind(wx.EVT_TEXT, self._update_capacity_price_label)
        self.capacity_combo.Bind(wx.EVT_COMBOBOX, self._update_capacity_price_label)
        row.Add(self.capacity_combo, 0, wx.RIGHT, 10)
        self.capacity_slider = wx.Slider(self.scroll, minValue=max(1000, club.stadium_capacity), maxValue=max(club.stadium_capacity + 20000, 20000), value=target_default, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self._style_control(self.capacity_slider)
        self.capacity_slider.Bind(wx.EVT_SLIDER, self._on_capacity_slider)
        row.Add(self.capacity_slider, 1)
        box.Add(row, 0, wx.EXPAND | wx.ALL, 10)
        self.capacity_price_label = wx.StaticText(self.scroll, label="")
        self.capacity_price_label.SetForegroundColour(self.MUTED_FG)
        box.Add(self.capacity_price_label, 0, wx.ALL, 10)
        self._update_capacity_price_label()
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("Increase &Capacity", self._confirm_stadium_capacity_upgrade), ("Upgrade &Pitch", lambda e: self._do_infra_upgrade(game_engine.upgrade_pitch, self.show_stadium_screen))]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 10)
        self._simple_back("&Back to Infrastructure", self.show_infrastructure_hub)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _on_capacity_slider(self, event):
        value = self.capacity_slider.GetValue()
        rounded = max(1000, int(round(value / 1000.0) * 1000))
        self.capacity_combo.SetValue(str(rounded))
        self._update_capacity_price_label()

    def _update_capacity_price_label(self, event=None):
        club = self.game_state.clubs[self.game_state.player_club_id]
        try:
            target = int(self.capacity_combo.GetValue())
        except Exception:
            target = club.stadium_capacity
        target = max(club.stadium_capacity, target)
        preview = self._native_stadium_preview(club, target)
        if preview and "cost" in preview:
            label = f"Target Capacity: {preview['target_capacity']:,}. Cost: {preview['cost']:,}. Current Budget: {club.budget:,}."
            self.capacity_price_label.SetLabel(label)
            speak(label, interrupt=False)
        else:
            cost = game_engine.get_stadium_upgrade_cost(club.stadium_capacity, target, club.infrastructure.stadium.seating_level)
            self.capacity_price_label.SetLabel(f"Target Capacity: {target:,}. Cost: {cost:,}. Current Budget: {club.budget:,}.")

    def _confirm_stadium_capacity_upgrade(self, event):
        club = self.game_state.clubs[self.game_state.player_club_id]
        try:
            target = int(self.capacity_combo.GetValue())
        except Exception:
            wx.MessageBox("Enter a valid target capacity.", "Stadium", wx.OK | wx.ICON_WARNING)
            return
        success, msg = game_engine.upgrade_stadium_to_capacity(club, target)
        if success:
            self.autosave()
        wx.MessageBox(msg, "Stadium", wx.OK | wx.ICON_INFORMATION)
        self.show_stadium_screen()

    def show_training_screen(self):
        self._push_nav(self.show_training_screen)
        self.clear()
        self._top_header()
        club, bench = self._bench()
        self._add_section_heading("Infrastructure - Training", "Training, medical and parking")
        box = self._add_group("Training Centre", "Improve player development, injury resistance and club logistics.")
        self._infra_text(box, [
            f"Training Level: {club.infrastructure.training.level} ({game_engine.describe_relative(club.infrastructure.training.level, bench['training_level'])})",
            f"Medical Level: {club.infrastructure.training.medical_level} ({game_engine.describe_relative(club.infrastructure.training.medical_level, bench['medical_level'])})",
            f"Parking Level: {club.infrastructure.stadium.parking_level} ({game_engine.describe_relative(club.infrastructure.stadium.parking_level, bench['parking_level'])})",
            f"Training Intensity: {club.infrastructure.training.intensity}",
        ])
        grid = wx.GridSizer(cols=2, vgap=8, hgap=8)
        for label, fn in [("Upgrade &Training", game_engine.upgrade_training), ("Upgrade &Medical", game_engine.upgrade_medical), ("Upgrade &Parking", game_engine.upgrade_parking), ("Set Training &Intensity", None)]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            if fn is None:
                btn.Bind(wx.EVT_BUTTON, lambda e: self._set_training_intensity(self.show_training_screen))
            else:
                btn.Bind(wx.EVT_BUTTON, lambda e, f=fn: self._do_infra_upgrade(f, self.show_training_screen))
            grid.Add(btn, 0, wx.EXPAND)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Infrastructure", self.show_infrastructure_hub)
        self.scroll.Layout()
        self.scroll.FitInside()

    def show_youth_screen(self):
        self._push_nav(self.show_youth_screen)
        self.clear()
        self._top_header()
        club, bench = self._bench()
        self._add_section_heading("Infrastructure - Youth Academy", "Youth intake, recruitment and scouting")
        box = self._add_group("Youth Academy", "Grow future talent and review your young prospects.")
        youth_summary = self._native_youth_summary(club)
        avg_youth = round(youth_summary.get("average_overall", 0), 1) if youth_summary else (round(sum(p.overall for p in club.youth_team) / len(club.youth_team), 1) if club.youth_team else 0)
        count = youth_summary.get("count", len(club.youth_team)) if youth_summary else len(club.youth_team)
        self._infra_text(box, [
            f"Youth Academy Level: {club.infrastructure.youth.level} ({game_engine.describe_relative(club.infrastructure.youth.level, bench['youth_level'])})",
            f"Youth Recruitment: {club.infrastructure.youth.recruitment_level} ({game_engine.describe_relative(club.infrastructure.youth.recruitment_level, bench['recruitment_level'])})",
            f"Scouting Level: {club.infrastructure.youth.scouting_level} ({game_engine.describe_relative(club.infrastructure.youth.scouting_level, bench['scouting_level'])})",
            f"Current Youth Squad Size: {count} | Average Youth Rating: {avg_youth}",
        ])
        grid = wx.GridSizer(cols=2, vgap=8, hgap=8)
        for label, fn in [("Upgrade &Youth Academy", game_engine.upgrade_youth_academy), ("Upgrade Youth &Recruitment", game_engine.upgrade_youth_recruitment), ("Upgrade &Scouting", game_engine.upgrade_scouting), ("View Current &Youth Squad", None)]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            if fn is None:
                btn.Bind(wx.EVT_BUTTON, lambda e: self.show_youth_team())
            else:
                btn.Bind(wx.EVT_BUTTON, lambda e, f=fn: self._do_infra_upgrade(f, self.show_youth_screen))
            grid.Add(btn, 0, wx.EXPAND)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Infrastructure", self.show_infrastructure_hub)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _do_infra_upgrade(self, fn, return_screen):
        club = self.game_state.clubs[self.game_state.player_club_id]
        success, msg = fn(club)
        if success:
            self.autosave()
        wx.MessageBox(msg, "Infrastructure", wx.OK | wx.ICON_INFORMATION)
        return_screen()

    def _set_training_intensity(self, return_screen):
        club = self.game_state.clubs[self.game_state.player_club_id]
        intensity = wx.GetNumberFromUser("Choose training intensity from 1 to 5", "Intensity:", "Training Intensity", club.infrastructure.training.intensity, 1, 5, self)
        if intensity == -1:
            return
        game_engine.set_training_intensity(club, int(intensity))
        self.autosave()
        return_screen()

    def show_youth_team(self):
        self._push_nav(self.show_youth_team)
        self.clear()
        self._top_header()
        club = self.game_state.clubs[self.game_state.player_club_id]
        self._add_section_heading("Youth Academy", "Current youth players and promotion options")
        box = self._add_group("Youth Squad", "Review youth prospects and offer first-team contracts.")
        self.youth_list = wx.ListCtrl(self.scroll, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._style_control(self.youth_list, surface=True)
        for i, (col, w) in enumerate([("Pos", 45), ("Name", 170), ("Age", 45), ("OVR", 60), ("Potential", 70), ("Desired Wage", 90)]):
            self.youth_list.InsertColumn(i, col, width=w)
        self._youth_players = list(club.youth_team)
        for p in self._youth_players:
            idx = self.youth_list.InsertItem(self.youth_list.GetItemCount(), p.position.name)
            self.youth_list.SetItem(idx, 1, p.full_name)
            self.youth_list.SetItem(idx, 2, str(p.age))
            self.youth_list.SetItem(idx, 3, str(p.overall))
            self.youth_list.SetItem(idx, 4, str(p.potential))
            self.youth_list.SetItem(idx, 5, f"{p.desired_wage:,}")
        box.Add(self.youth_list, 1, wx.EXPAND | wx.ALL, 10)
        btns = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("&Promote and Offer Contract", self._on_promote_youth), ("&Back to Youth Academy", lambda e: self.show_youth_screen())]:
            btn = wx.Button(self.scroll, label=label)
            self._style_control(btn)
            btn.Bind(wx.EVT_BUTTON, handler)
            btns.Add(btn, 0, wx.ALL, 5)
        box.Add(btns, 0, wx.ALL, 5)
        self.scroll.Layout()
        self.scroll.FitInside()

    def _on_promote_youth(self, event):
        sel = self.youth_list.GetFirstSelected()
        if sel < 0:
            wx.MessageBox("Select a youth player first.", "Youth Academy", wx.OK | wx.ICON_WARNING)
            return
        player = self._youth_players[sel]
        club = self.game_state.clubs[self.game_state.player_club_id]
        wage = wx.GetNumberFromUser("Weekly wage offer", "Wage:", "Youth Contract", player.desired_wage, 50, max(1000, club.wage_budget_weekly * 3), self)
        if wage == -1:
            return
        years = wx.GetNumberFromUser("Contract length in years", "Years:", "Youth Contract", max(2, player.desired_contract_length), 1, 5, self)
        if years == -1:
            return
        success, msg = game_engine.promote_youth_player(self.game_state, player.id, int(wage), int(years))
        wx.MessageBox(msg, "Youth Academy", wx.OK | wx.ICON_INFORMATION)
        if success:
            self.autosave()
            self.show_youth_team()

    def show_trophy_cabinet(self):
        self._push_nav(self.show_trophy_cabinet)
        self.clear()
        self._top_header()
        gs = self.game_state
        club = gs.clubs[gs.player_club_id]
        self._add_section_heading(f"{club.name} - Trophy Cabinet", "All trophies won by your club")
        box = self._add_group("Honours List", "Your major achievements across seasons.")
        trophy_list = wx.ListCtrl(self.scroll, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._style_control(trophy_list, surface=True)
        trophy_list.InsertColumn(0, "Season", width=80)
        trophy_list.InsertColumn(1, "Trophy", width=180)
        trophy_list.InsertColumn(2, "Competition", width=260)
        trophy_list.InsertColumn(3, "Tier", width=70)
        for trophy in sorted(gs.trophies, key=lambda t: (t.season, t.league_name)):
            idx = trophy_list.InsertItem(trophy_list.GetItemCount(), str(trophy.season))
            trophy_list.SetItem(idx, 1, trophy.trophy_type.value)
            trophy_list.SetItem(idx, 2, trophy.league_name)
            trophy_list.SetItem(idx, 3, str(trophy.tier))
        box.Add(trophy_list, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Club", self.show_club_hub)
        self.scroll.Layout()
        self.scroll.FitInside()

    def show_season_summary(self):
        self._push_nav(self.show_season_summary)
        self.clear()
        self._top_header()
        gs = self.game_state
        summary = game_engine.get_season_summary(gs)
        self._add_section_heading("End of Season Summary", "Your league finish and season highlights")
        club = summary["player_club"]
        symbol = "\u00a3" if summary["currency"] == "GBP" else "\u20ac"
        box = self._add_group("Season Review", "Your final league standing and reward overview.")
        lines = [f"Final Position: {summary['position']} of {summary['total_clubs']}", f"Points: {club.points} - Goal Difference: {club.gd:+d}", f"Prize Money: {symbol}{summary['prize_money']:,}"]
        if summary.get("messages"):
            lines.append("Messages: " + " | ".join(summary["messages"]))
        info = self._make_readable_text("\n".join(lines), min_height=220)
        box.Add(info, 0, wx.EXPAND | wx.ALL, 10)
        if not self._season_prize_awarded:
            club.budget += summary["prize_money"]
            club.transfer_budget += int(summary["prize_money"] * 0.5)
            self._season_prize_awarded = True
            self.autosave()
        start_btn = wx.Button(self.scroll, label="&Start New Season")
        self._style_control(start_btn)
        start_btn.Bind(wx.EVT_BUTTON, self._start_new_season)
        box.Add(start_btn, 0, wx.ALL, 10)
        self.scroll.Layout()
        self.scroll.FitInside()
        wx.CallAfter(info.SetFocus)
        speak(f"Season over. Final position: {summary['position']} of {summary['total_clubs']}. Press Start New Season to continue.", interrupt=False)

    def _start_new_season(self, event=None):
        self._season_prize_awarded = False
        game_engine.reset_for_new_season(self.game_state)
        self.autosave()
        self._nav_stack = []
        self.show_dashboard(track=True)
        speak("New season started.", interrupt=False)

    def show_competitions_overview(self):
        self._push_nav(self.show_competitions_overview)
        self.clear()
        self._top_header()
        self._add_section_heading("Competitions", "Domestic cups, Europe and current competition progress")
        box = self._add_group("Competitions Overview", "Open a competition to review draws, fixtures and results.")
        self.competition_list = wx.ListBox(self.scroll)
        self._style_control(self.competition_list, surface=True)
        self._competition_items = game_engine.get_competitions_for_ui(self.game_state)
        for comp in self._competition_items:
            scope = "Europe" if comp.country == "Europe" else comp.country
            stage = comp.current_round or "Scheduled"
            self.competition_list.Append(f"{comp.name} - {scope} - {stage}")
        box.Add(self.competition_list, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        open_btn = wx.Button(self.scroll, label="&Open Competition")
        self._style_control(open_btn)
        open_btn.Bind(wx.EVT_BUTTON, self._open_selected_competition)
        row.Add(open_btn, 0, wx.ALL, 5)
        box.Add(row, 0, wx.ALL, 5)
        self._simple_back()
        self.scroll.Layout()
        self.scroll.FitInside()

    def _open_selected_competition(self, event=None):
        idx = self.competition_list.GetSelection()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._competition_items):
            return
        self.show_competition_detail(self._competition_items[idx])

    def show_competition_detail(self, competition):
        self._push_nav(lambda track=False: self.show_competition_detail(competition))
        self.clear()
        self._top_header()
        self._add_section_heading(competition.name, "Competition detail, draw and result views")
        box = self._add_group("Competition Detail", f"Current Round: {competition.current_round or 'Scheduled'}")
        draw_lines = game_engine.get_competition_draw_text(self.game_state, competition.id)
        result_lines = game_engine.get_competition_results(self.game_state, competition.id)
        text = self._make_readable_text("Draws:\n" + "\n".join(draw_lines) + "\n\nResults:\n" + ("\n".join(result_lines) if result_lines else "No results yet."), min_height=460)
        box.Add(text, 1, wx.EXPAND | wx.ALL, 10)
        self._simple_back("&Back to Competitions", self.show_competitions_overview)
        self.scroll.Layout()
        self.scroll.FitInside()

def run():
    app = wx.App(False)
    FootballManagerApp()
    app.MainLoop()

