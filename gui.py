import threading
import logging
import time
import os
import subprocess
import sys
import importlib
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import OrderedDict
from datetime import datetime
import main

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config-pre-vote.json")

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.log_buffer = []
        self.paused = True
        
    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    def emit(self, record):
        msg = self.format(record)
        self.log_buffer.append(msg)
        if len(self.log_buffer) > 200:
            self.log_buffer.pop(0)
        if not self.paused:
            def append():
                try:
                    self.text_widget.configure(state="normal")
                    self.text_widget.delete("1.0", "end")
                    self.text_widget.insert("end", "\n".join(self.log_buffer[-200:]))
                    self.text_widget.configure(state="disabled")
                    self.text_widget.see("end")
                except:
                    pass
            self.text_widget.after(0, append)


class VotingGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("VoteScript v5.0 - DARK EDITION")
        self.root.geometry("1300x920")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.bot_thread = None
        self.bot_running = False
        self.bot_paused = False
        self.tor_active = False
        self.tor_process = None
        self.history_active = True
        
        self.link_toggle_states = {}
        self.link_toggle_buttons = {}
        
        self.stats = {
            'ip_changes': 0,
            'total_ip_changes': 0,
            'votes_done': 0,
            'total_votes': 0,
            'current_ip': 'N/A',
            'status': 'INACTIVE',
            'votes_per_link': {},
            'timestamp_start': None
        }
        
        self.link_votes = OrderedDict()
        self.link_titles = {}
        self.link_to_idx = {}
        self.vote_cards = {}
        self.vote_labels = {}
        self.title_labels = {}
        
        self.load_preferences()
        self.setup_ui()
        self.setup_logger()
        self.load_initial_config()
        self.bind_mousewheel()
        
        self.handler.paused = True
        self.log_toggle_button.configure(text="SHOW LOG")
        
    def load_preferences(self):
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    self.history_active = prefs.get('history_active', True)
        except Exception as e:
            logging.error(f"Preferences load error: {e}")
    
    def save_preferences(self):
        try:
            prefs = {
                'history_active': self.history_active
            }
            os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
            with open(PREFS_FILE, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=4, ensure_ascii=False)
            logging.info(f"Preferences saved: history={self.history_active}")
        except Exception as e:
            logging.error(f"Preferences save error: {e}")
    
    def bind_mousewheel(self):
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_to_widgets(widget):
            widget.bind("<MouseWheel>", _on_mousewheel, add=True)
            for child in widget.winfo_children():
                _bind_to_widgets(child)
        _bind_to_widgets(self.root)
        
    def setup_ui(self):
        self.main_canvas = ctk.CTkCanvas(self.root, bg="#0f1117", highlightthickness=0)
        self.main_canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ctk.CTkScrollbar(self.root, orientation="vertical", command=self.main_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.main_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.scrollable_frame = ctk.CTkFrame(self.main_canvas, fg_color="#0f1117")
        self.scrollable_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def configure_canvas(event):
            self.main_canvas.itemconfig(1, width=event.width)
        self.main_canvas.bind('<Configure>', configure_canvas)
        
        main_container = ctk.CTkFrame(self.scrollable_frame, fg_color="#0f1117")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # HEADER
        header_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        header_frame.pack(fill="x", pady=(0, 20), padx=0, ipady=10)
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_rowconfigure(0, weight=1)
        title_label = ctk.CTkLabel(header_frame, text="VoteScript v5.0", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00ff9c")
        title_label.grid(row=0, column=0, padx=25, sticky="w")
        self.status_badge = ctk.CTkLabel(header_frame, text=self.stats['status'], font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffaa00", fg_color="#2d2d2d", corner_radius=15, padx=15, pady=5)
        self.status_badge.grid(row=0, column=1, padx=25, sticky="e")
        
        # CONFIG PANEL
        config_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        config_frame.pack(fill="x", pady=(0, 20))
        config_header = ctk.CTkLabel(config_frame, text="CONFIGURATION", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff", anchor="w")
        config_header.pack(anchor="w", padx=15, pady=(10, 5))
        config_content = ctk.CTkFrame(config_frame, fg_color="transparent")
        config_content.pack(fill="x", padx=15, pady=(0, 15))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_config = os.path.join(base_dir, "config", "config.json")
        self.config_path_var = ctk.StringVar(value=default_config)
        self.config_path_var.trace_add("write", lambda *args: self.on_config_changed())
        config_entry = ctk.CTkEntry(config_content, textvariable=self.config_path_var, placeholder_text="Config file path...")
        config_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.browse_btn = ctk.CTkButton(config_content, text="Browse", command=self.browse_config, width=100, fg_color="#00c8ff", hover_color="#0099cc", text_color="#000000", corner_radius=8)
        self.browse_btn.pack(side="left")
        
        # STATS CARDS
        stats_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        for i in range(2):
            stats_frame.grid_columnconfigure(i, weight=1, uniform="stats")
        self.ip_card = self.create_stat_card(stats_frame, "IP CHANGES", f"{self.stats['ip_changes']} / {self.stats['total_ip_changes']}", "#00ff9c", 0, 0)
        self.vote_card = self.create_stat_card(stats_frame, "VOTES", f"{self.stats['votes_done']} / {self.stats['total_votes']}", "#00ff9c", 0, 1)
        self.current_ip_card = self.create_stat_card(stats_frame, "CURRENT IP", self.stats['current_ip'], "#00ff9c", 1, 0)
        self.progress_card = self.create_stat_card(stats_frame, "PROGRESS", f"{self.get_progress_percent()}%", "#00ff9c", 1, 1)
        
        # TOR PANEL
        tor_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        tor_frame.pack(fill="x", pady=(0, 20))
        tor_header = ctk.CTkLabel(tor_frame, text="TOR SERVICE", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff", anchor="w")
        tor_header.pack(anchor="w", padx=15, pady=(10, 5))
        tor_content = ctk.CTkFrame(tor_frame, fg_color="transparent")
        tor_content.pack(fill="x", padx=15, pady=(0, 15))
        self.tor_button = ctk.CTkButton(tor_content, text="Start Tor", command=self.start_tor, width=120, fg_color="#6f42c1", hover_color="#5a32a3", corner_radius=20, font=ctk.CTkFont(size=14, weight="bold"))
        self.tor_button.pack(side="left", padx=(0, 10))
        self.tor_stop_button = ctk.CTkButton(tor_content, text="Stop Tor", command=self.stop_tor, width=120, fg_color="#dc3545", hover_color="#bb2d3b", corner_radius=20, font=ctk.CTkFont(size=14, weight="bold"), state="disabled")
        self.tor_stop_button.pack(side="left", padx=(0, 15))
        self.tor_status = ctk.CTkLabel(tor_content, text="Not started", text_color="#ffc107", font=ctk.CTkFont(size=12))
        self.tor_status.pack(side="left", padx=(0, 15))
        self.tor_progress = ctk.CTkProgressBar(tor_content, width=150, height=8)
        self.tor_progress.pack(side="left", padx=5)
        self.tor_progress.set(0)
        
        # PRE-VOTE NAVIGATION
        switch_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        switch_frame.pack(fill="x", pady=(0, 20))
        switch_header_frame = ctk.CTkFrame(switch_frame, fg_color="transparent")
        switch_header_frame.pack(fill="x", padx=15, pady=(10, 5))
        switch_header = ctk.CTkLabel(switch_header_frame, text="PRE-VOTE NAVIGATION", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff", anchor="w")
        switch_header.pack(side="left")
        self.save_prefs_button = ctk.CTkButton(switch_header_frame, text="Save preferences", command=self.save_preferences, width=120, fg_color="#6c757d", hover_color="#5a6268", corner_radius=15, font=ctk.CTkFont(size=12))
        self.save_prefs_button.pack(side="right")
        switch_content = ctk.CTkFrame(switch_frame, fg_color="transparent")
        switch_content.pack(fill="x", padx=15, pady=(0, 15))
        
        self.history_switch = ctk.CTkSwitch(switch_content, text="Enable random navigation before voting", command=self.toggle_history, onvalue=True, offvalue=False, progress_color="#00ff9c" if self.history_active else "#ff4444", button_color="#00ff9c" if self.history_active else "#ff4444", button_hover_color="#00cc7a" if self.history_active else "#cc3333")
        if self.history_active:
            self.history_switch.select()
        else:
            self.history_switch.deselect()
        self.history_switch.pack(anchor="w")
        
        # REAL-TIME VOTES
        votes_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        votes_frame.pack(fill="x", pady=(0, 20))
        votes_header_frame = ctk.CTkFrame(votes_frame, fg_color="transparent", height=40)
        votes_header_frame.pack(fill="x", padx=15, pady=(5, 5))
        votes_header_frame.pack_propagate(False)
        header_inner = ctk.CTkFrame(votes_header_frame, fg_color="transparent")
        header_inner.pack(side="left", fill="y")
        header_inner.grid_columnconfigure(0, weight=1)
        header_inner.grid_rowconfigure(0, weight=1)
        inner_content = ctk.CTkFrame(header_inner, fg_color="transparent")
        inner_content.grid(row=0, column=0)
        self.votes_expanded = True
        self.votes_toggle_btn = ctk.CTkButton(inner_content, text="▼", command=self.toggle_votes, width=30, height=30, fg_color="#2d2d2d", hover_color="#3d3d3d", corner_radius=15)
        self.votes_toggle_btn.pack(side="left", padx=(0, 10))
        votes_header = ctk.CTkLabel(inner_content, text="REAL-TIME VOTES", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff")
        votes_header.pack(side="left")
        self.votes_content = ctk.CTkFrame(votes_frame, fg_color="transparent")
        self.votes_content.pack(fill="x", padx=15, pady=(0, 15))
        self.votes_cards_frame = ctk.CTkFrame(self.votes_content, fg_color="transparent")
        self.votes_cards_frame.pack(fill="x")
        self.total_votes_label = ctk.CTkLabel(self.votes_content, text="Total votes: 0", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00ff9c")
        self.total_votes_label.pack(anchor="e", pady=(10, 0))
        
        # CONTROL BUTTONS
        control_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        control_frame.pack(fill="x", pady=(0, 20))
        for i in range(5):
            control_frame.grid_columnconfigure(i, weight=1, uniform="buttons")
        self.start_button = ctk.CTkButton(control_frame, text="START BOT", command=self.start_bot, fg_color="#00ff9c", hover_color="#00cc7a", text_color="#000000", corner_radius=25, font=ctk.CTkFont(size=14, weight="bold"), height=45)
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")
        self.stop_button = ctk.CTkButton(control_frame, text="STOP BOT", command=self.stop_bot, fg_color="#ff4444", hover_color="#cc3333", text_color="#ffffff", corner_radius=25, font=ctk.CTkFont(size=14, weight="bold"), height=45, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.pause_button = ctk.CTkButton(control_frame, text="PAUSE BOT", command=self.toggle_pause, fg_color="#ffaa00", hover_color="#cc8800", text_color="#000000", corner_radius=25, font=ctk.CTkFont(size=14, weight="bold"), height=45, state="disabled")
        self.pause_button.grid(row=0, column=2, padx=5, sticky="ew")
        self.log_toggle_button = ctk.CTkButton(control_frame, text="SHOW LOG", command=self.toggle_log, fg_color="#6c757d", hover_color="#5a6268", corner_radius=25, font=ctk.CTkFont(size=14, weight="bold"), height=45)
        self.log_toggle_button.grid(row=0, column=3, padx=5, sticky="ew")
        self.exit_button = ctk.CTkButton(control_frame, text="EXIT", command=self.exit_app, fg_color="#dc3545", hover_color="#bb2d3b", corner_radius=25, font=ctk.CTkFont(size=14, weight="bold"), height=45)
        self.exit_button.grid(row=0, column=4, padx=5, sticky="ew")
        
        # LOG PANEL
        self.log_frame = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10)
        log_header_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        log_header_frame.pack(fill="x", padx=15, pady=(10, 5))
        log_header = ctk.CTkLabel(log_header_frame, text="ACTIVITY LOG", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff")
        log_header.pack(side="left")
        self.clear_log_button = ctk.CTkButton(log_header_frame, text="Clear Log", command=self.clear_log, width=100, fg_color="#6c757d", hover_color="#5a6268", corner_radius=15, font=ctk.CTkFont(size=12))
        self.clear_log_button.pack(side="right")
        self.log_text = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0d0d0d", text_color="#00ff9c", corner_radius=8, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def create_stat_card(self, parent, title, value, color, row, col):
        card = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#2d2d2d")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.configure(height=100)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0)
        title_label = ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=12), text_color="#aaaaaa")
        title_label.pack(anchor="center")
        value_label = ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
        value_label.pack(anchor="center", pady=(5, 0))
        return value_label
        
    def create_vote_card(self, parent, link_idx, votes, row, col, link, initial_title=None):
        card = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#2d2d2d", width=200, height=140)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0)
        title_text = initial_title if initial_title else f"LINK #{link_idx+1}"
        title_label = ctk.CTkLabel(inner, text=title_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#00ff88", wraplength=180)
        title_label.pack(anchor="center", pady=(10, 5))
        self.title_labels[f"title_{link_idx}"] = title_label
        vote_label = ctk.CTkLabel(inner, text=f"{votes} votes", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff")
        vote_label.pack(anchor="center", pady=(0, 5))
        self.vote_labels[f"vote_{link_idx}"] = vote_label
        initial_state = self.link_toggle_states.get(link, True)
        toggle_btn = ctk.CTkButton(inner, text="ON" if initial_state else "OFF", command=lambda: self.toggle_link(link, link_idx), width=60, height=25, fg_color="#00ff9c" if initial_state else "#ff4444", hover_color="#00cc7a" if initial_state else "#cc3333", corner_radius=12, font=ctk.CTkFont(size=10, weight="bold"))
        toggle_btn.pack(anchor="center", pady=(5, 10))
        self.link_toggle_buttons[link] = toggle_btn
        if link not in self.link_toggle_states:
            self.link_toggle_states[link] = True
        return card
    
    def create_vote_cards_from_config(self, config):
        for widget in self.votes_cards_frame.winfo_children():
            widget.destroy()
        self.vote_cards.clear()
        self.vote_labels.clear()
        self.link_votes.clear()
        self.link_to_idx.clear()
        self.title_labels.clear()
        if not config or 'target_urls' not in config or not config['target_urls']:
            ctk.CTkLabel(self.votes_cards_frame, text="No links configured", text_color="#aaaaaa").pack()
            return
        for i in range(2):
            self.votes_cards_frame.grid_columnconfigure(i, weight=1, uniform="vote_cards")
        for idx, link in enumerate(config['target_urls']):
            self.link_votes[link] = 0
            self.link_to_idx[link] = idx
            row = idx // 2
            col = idx % 2
            card = self.create_vote_card(self.votes_cards_frame, idx, 0, row, col, link)
            self.vote_cards[f"card_{idx}"] = card
    
    def get_progress_percent(self):
        if self.stats['total_votes'] > 0:
            return f"{((self.stats['votes_done'] / self.stats['total_votes']) * 100):.1f}"
        return "0.0"
    
    def setup_logger(self):
        self.handler = TextHandler(self.log_text)
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        self.handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
        root_logger.addHandler(self.handler)
        root_logger.setLevel(logging.INFO)
        logging.info("GUI started")
    
    def load_initial_config(self):
        try:
            config_path = self.config_path_var.get()
            if os.path.exists(config_path):
                config = main.load_config(config_path)
                if config and 'target_urls' in config:
                    self.create_vote_cards_from_config(config)
                    logging.info(f"Initial config loaded: {len(config['target_urls'])} links found")
                else:
                    logging.warning("Initial config loaded but no valid links")
            else:
                logging.warning(f"Config file not found: {config_path}")
        except Exception as e:
            logging.error(f"Initial config load error: {e}")
        
    def toggle_log(self):
        paused = self.handler.toggle_pause()
        if paused:
            self.log_toggle_button.configure(text="SHOW LOG")
            self.log_frame.pack_forget()
            logging.info("Log hidden")
        else:
            self.log_toggle_button.configure(text="HIDE LOG")
            self.log_frame.pack(fill="both", expand=True)
            try:
                self.log_text.configure(state="normal")
                self.log_text.delete("1.0", "end")
                self.log_text.insert("end", "\n".join(self.handler.log_buffer[-200:]))
                self.log_text.configure(state="disabled")
                self.log_text.see("end")
            except:
                pass
    
    def update_stats(self):
        self.ip_card.configure(text=f"{self.stats['ip_changes']} / {self.stats['total_ip_changes']}")
        self.vote_card.configure(text=f"{self.stats['votes_done']} / {self.stats['total_votes']}")
        self.current_ip_card.configure(text=self.stats['current_ip'])
        self.progress_card.configure(text=f"{self.get_progress_percent()}%")
        self.status_badge.configure(text=self.stats['status'])
        if "ACTIVE" in self.stats['status']:
            self.status_badge.configure(text_color="#00ff88")
        elif "PAUSED" in self.stats['status']:
            self.status_badge.configure(text_color="#ffaa00")
        else:
            self.status_badge.configure(text_color="#ffaa00")
    
    def toggle_history(self):
        self.history_active = self.history_switch.get()
        state = "active" if self.history_active else "inactive"
        logging.info(f"Pre-vote navigation {state}")
        if self.history_active:
            self.history_switch.configure(progress_color="#00ff9c", button_color="#00ff9c")
        else:
            self.history_switch.configure(progress_color="#ff4444", button_color="#ff4444")
    
    def toggle_link(self, link, idx):
        self.link_toggle_states[link] = not self.link_toggle_states.get(link, True)
        state = "active" if self.link_toggle_states[link] else "inactive"
        btn = self.link_toggle_buttons.get(link)
        if btn:
            if self.link_toggle_states[link]:
                btn.configure(fg_color="#00ff9c", text="ON")
                title_key = f"title_{idx}"
                if title_key in self.title_labels:
                    self.title_labels[title_key].configure(text_color="#00ff88")
            else:
                btn.configure(fg_color="#ff4444", text="OFF")
                title_key = f"title_{idx}"
                if title_key in self.title_labels:
                    self.title_labels[title_key].configure(text_color="#ff4444")
        logging.info(f"Link #{idx+1} vote {state}")
    
    def title_callback(self, link, title, idx):
        def update():
            title_key = f"title_{idx-1}"
            if title_key in self.title_labels:
                self.title_labels[title_key].configure(text=title)
                self.link_titles[link] = title
        self.root.after(0, update)
        
    def toggle_votes(self):
        if self.votes_expanded:
            self.votes_content.pack_forget()
            self.votes_toggle_btn.configure(text="▶")
        else:
            self.votes_content.pack(fill="x", padx=15, pady=(0, 15))
            self.votes_toggle_btn.configure(text="▼")
        self.votes_expanded = not self.votes_expanded
        
    def update_votes_display(self, link=None, votes_before=None, votes_after=None):
        if link and votes_after is not None:
            self.link_votes[link] = votes_after
            self.stats['votes_per_link'][link] = votes_after
            if link in self.link_to_idx:
                idx = self.link_to_idx[link]
                label_key = f"vote_{idx}"
                if label_key in self.vote_labels:
                    self.vote_labels[label_key].configure(text=f"{votes_after} votes")
        if self.link_votes:
            total = sum(self.link_votes.values())
            self.total_votes_label.configure(text=f"Total votes: {total}")
    
    def start_tor(self):
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "start_tor.bat")
        if not os.path.exists(bat_path):
            messagebox.showerror("Error", "start_tor.bat not found!")
            return
        self.tor_button.configure(state="disabled", text="Starting...")
        self.tor_stop_button.configure(state="normal")
        self.tor_progress.set(0.5)
        self.tor_status.configure(text="Starting Tor...", text_color="#ffc107")
        def start():
            try:
                self.tor_process = subprocess.Popen([bat_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(5)
                import requests
                proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
                services = ['https://api.ipify.org', 'https://icanhazip.com', 'https://ifconfig.me/ip']
                ip_found = None
                for service in services:
                    try:
                        ip = requests.get(service, proxies=proxies, timeout=5).text.strip()
                        if ip and "error" not in ip.lower():
                            ip_found = ip
                            break
                    except:
                        continue
                if ip_found:
                    self.tor_active = True
                    self.stats['current_ip'] = ip_found
                    self.root.after(0, self.update_stats)
                    self.root.after(0, lambda: self.tor_status.configure(text="Tor active", text_color="#00ff88"))
                    logging.info(f"Tor started - IP: {ip_found}")
                else:
                    self.tor_active = True
                    self.root.after(0, lambda: self.tor_status.configure(text="Tor active", text_color="#00ff88"))
                    logging.info("Tor started")
                self.root.after(0, lambda: self.tor_progress.set(1.0))
                self.root.after(0, lambda: self.tor_button.configure(text="Restart Tor", state="normal"))
            except Exception as e:
                self.tor_active = False
                self.root.after(0, lambda: self.tor_button.configure(state="normal", text="Start Tor"))
                self.root.after(0, lambda: self.tor_stop_button.configure(state="disabled"))
                logging.error(f"Tor start error: {e}")
        threading.Thread(target=start, daemon=True).start()
    
    def stop_tor(self):
        try:
            if self.tor_process:
                self.tor_process.terminate()
                self.tor_process = None
            subprocess.run(["taskkill", "/F", "/IM", "tor.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.tor_active = False
            self.tor_button.configure(state="normal", text="Start Tor")
            self.tor_stop_button.configure(state="disabled")
            self.tor_status.configure(text="Not started", text_color="#ffc107")
            self.tor_progress.set(0)
            self.stats['current_ip'] = 'N/A'
            self.update_stats()
            logging.info("Tor stopped")
        except Exception as e:
            logging.error(f"Tor stop error: {e}")
    
    def browse_config(self):
        initial_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
        path = filedialog.askopenfilename(title="Select config file", filetypes=[("JSON files", "*.json")], initialdir=initial_dir if os.path.exists(initial_dir) else os.path.dirname(os.path.abspath(__file__)))
        if path:
            self.config_path_var.set(path)
            logging.info(f"Config: {os.path.basename(path)}")
            self.on_config_changed()
    
    def stats_callback(self, ip_changes, votes_done, total_votes, total_ip_changes, ip):
        self.stats['ip_changes'] = ip_changes
        self.stats['votes_done'] = votes_done
        self.stats['total_votes'] = total_votes
        self.stats['total_ip_changes'] = total_ip_changes
        if ip and ip != "N/A" and ip != "Unknown" and "error" not in ip.lower():
            self.stats['current_ip'] = ip
        self.root.after(0, self.update_stats)
    
    def vote_callback(self, link, votes_before, votes_after):
        self.root.after(0, lambda: self.update_votes_display(link, votes_before, votes_after))
    
    def block_callback(self, link, is_blocked):
        if link in self.link_to_idx:
            idx = self.link_to_idx[link]
            title_key = f"title_{idx}"
            if title_key in self.title_labels:
                if is_blocked:
                    self.title_labels[title_key].configure(text_color="#ff4444")
                else:
                    self.title_labels[title_key].configure(text_color="#00ff88")
                title_to_show = self.link_titles.get(link, link[:30])
                if is_blocked:
                    logging.info(f"BLOCKED: {title_to_show}")
                else:
                    logging.info(f"Unblocked: {title_to_show}")
    
    def on_config_changed(self):
        try:
            config_path = self.config_path_var.get()
            if os.path.exists(config_path):
                config = main.load_config(config_path)
                if config and 'target_urls' in config:
                    self.create_vote_cards_from_config(config)
        except:
            pass
    
    def toggle_pause(self):
        if not self.bot_running:
            return
        if self.bot_paused:
            self.pause_event.clear()
            self.bot_paused = False
            self.pause_button.configure(text="PAUSE BOT", fg_color="#ffaa00")
            self.stats['status'] = 'ACTIVE'
            logging.info("Bot resumed")
        else:
            self.pause_event.set()
            self.bot_paused = True
            self.pause_button.configure(text="RESUME BOT", fg_color="#00ff9c")
            self.stats['status'] = 'PAUSED'
            logging.info("Bot paused")
        self.update_stats()
    
    def start_bot(self):
        if not self.tor_active:
            messagebox.showerror("Error", "Tor is not active!\n\nStart Tor before starting the bot.")
            return
        config_path = self.config_path_var.get()
        try:
            config = main.load_config(config_path)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid config: {e}")
            return
        for link, state in self.link_toggle_states.items():
            if link in self.link_to_idx:
                idx = self.link_to_idx[link]
                title_key = f"title_{idx}"
                if title_key in self.title_labels:
                    if state:
                        self.title_labels[title_key].configure(text_color="#00ff88")
                    else:
                        self.title_labels[title_key].configure(text_color="#ff4444")
        self.update_stats()
        self.stats['total_ip_changes'] = config['total_votes']
        self.stats['total_votes'] = len(config['target_urls']) * config['total_votes']
        self.stats['ip_changes'] = 0
        self.stats['votes_done'] = 0
        self.stats['status'] = 'ACTIVE'
        self.stats['timestamp_start'] = datetime.now()
        self.update_stats()
        self.stop_event.clear()
        self.pause_event.clear()
        self.bot_running = True
        self.bot_paused = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.pause_button.configure(state="normal", text="PAUSE BOT", fg_color="#ffaa00")
        logging.info("Bot started")
        def worker():
            try:
                main.run_bot_with_callback(
                    config, self.stop_event, self.stats_callback, 
                    self.vote_callback, self.block_callback, None, self.title_callback,
                    self.pause_event, self.history_active, self.link_toggle_states
                )
            except Exception as exc:
                logging.error(f"Error: {exc}")
            finally:
                self.bot_running = False
                self.bot_paused = False
                self.stats['status'] = 'INACTIVE'
                self.root.after(0, self.update_stats)
                self.root.after(0, lambda: self.start_button.configure(state="normal"))
                self.root.after(0, lambda: self.stop_button.configure(state="disabled"))
                self.root.after(0, lambda: self.pause_button.configure(state="disabled"))
                logging.info("Bot stopped")
        self.bot_thread = threading.Thread(target=worker, daemon=True)
        self.bot_thread.start()
    
    def stop_bot(self):
        if messagebox.askyesno("Confirm", "Stop the bot?"):
            self.stop_event.set()
            logging.info("Stopping...")
            self.stop_button.configure(state="disabled")
            self.start_button.configure(state="normal")
            self.pause_button.configure(state="disabled")
    
    def restart_bot(self):
        if messagebox.askyesno("Confirm", "Restart the bot?"):
            if self.bot_running:
                self.stop_event.set()
                time.sleep(1)
            self.stop_event.clear()
            importlib.reload(main)
            self.start_bot()
    
    def clear_log(self):
        self.handler.log_buffer.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        logging.info("Log cleared")
    
    def exit_app(self):
        confirm = ctk.CTkToplevel(self.root)
        confirm.title("Confirm exit")
        confirm.geometry("350x150")
        confirm.transient(self.root)
        confirm.grab_set()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        confirm.geometry(f"+{x}+{y}")
        ctk.CTkLabel(confirm, text="Do you really want to exit?", font=ctk.CTkFont(size=14)).pack(pady=20)
        ctk.CTkLabel(confirm, text="Tor will be stopped automatically.", font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(pady=(0, 20))
        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=10)
        def on_yes():
            confirm.destroy()
            progress_msg = ctk.CTkToplevel(self.root)
            progress_msg.title("Stopping")
            progress_msg.geometry("300x100")
            progress_msg.transient(self.root)
            progress_msg.grab_set()
            x2 = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
            y2 = self.root.winfo_y() + (self.root.winfo_height() // 2) - 50
            progress_msg.geometry(f"+{x2}+{y2}")
            label = ctk.CTkLabel(progress_msg, text="Stopping Tor...", font=ctk.CTkFont(size=12))
            label.pack(pady=20)
            progress = ctk.CTkProgressBar(progress_msg, width=250)
            progress.pack(pady=10)
            progress.set(0)
            for i in range(1, 101):
                progress.set(i / 100)
                progress_msg.update()
                time.sleep(0.005)
            self.stop_tor()
            progress_msg.destroy()
            if self.bot_running:
                self.stop_event.set()
                time.sleep(1)
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
        def on_no():
            confirm.destroy()
        btn_height = 35
        ctk.CTkButton(btn_frame, text="Yes, exit", command=on_yes, width=80, height=btn_height, fg_color="#dc3545", hover_color="#bb2d3b").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="No, stay", command=on_no, width=80, height=btn_height, fg_color="#6c757d", hover_color="#5a6268").pack(side="left", padx=10)
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VotingGUI()
    app.run()