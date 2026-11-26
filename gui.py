"""
Modern GUI for Tantra Farmer Macro.
Includes:
1. Dashboard & Automation Runner
2. Visual Area Selection (Select Area for Inventory 48 slots, Storage 128 slots, and Merchant)
3. Slot Inspector (Visual 48/128 grid showing empty vs occupied slots with live test)
4. Whitelist Item Manager (FR-5)
5. Speed and Delay Configuration (NFR-1)
"""

import math
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Callable
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from config import Config, APP_VERSION
from updater import check_for_updates, download_update, apply_update_and_restart
from window_manager import WindowManager
from screen import ScreenCapture
from input_controller import InputController
from template_matcher import TemplateMatcher
from ocr_engine import OCREngine
from farmer_bot import FarmerBot
from area_selector import AreaSelectorWindow
from auth import verify_password, hash_password
from pot_controller import PotController, DEFAULT_POT_CONFIG
from skill_controller import SkillController, DEFAULT_SKILL_CONFIG

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class FarmerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config = Config("config.json")
        self.configure(bg="#161b22")
        self.worker_thread = None

        # Start in compact login mode
        self.title(f"🔐 Keamanan Akses - Tantra Farmer {APP_VERSION}")
        self.geometry("440x290")
        self.resizable(False, False)
        self._center_window(440, 290)

        # Build Login UI
        self._build_login_screen()

    def _center_window(self, width, height):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_login_screen(self):
        self.frame_login = tk.Frame(self, bg="#161b22", padx=26, pady=22)
        self.frame_login.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.frame_login,
            text="🔒 TANTRA FARMER MACRO",
            font=("Segoe UI", 13, "bold"),
            bg="#161b22",
            fg="#58a6ff"
        ).pack(anchor=tk.CENTER, pady=(0, 4))

        tk.Label(
            self.frame_login,
            text="Aplikasi ini diproteksi. Masukkan password akses:",
            font=("Segoe UI", 9),
            bg="#161b22",
            fg="#8b949e"
        ).pack(anchor=tk.CENTER, pady=(0, 16))

        frame_input = tk.Frame(self.frame_login, bg="#161b22")
        frame_input.pack(fill=tk.X, pady=(0, 6))

        self.var_login_pwd = tk.StringVar()
        self.show_login_pwd = False

        self.entry_login_pwd = tk.Entry(
            frame_input,
            textvariable=self.var_login_pwd,
            show="●",
            font=("Segoe UI", 11),
            bg="#0d1117",
            fg="#f0f6fc",
            insertbackground="#ffffff",
            relief="solid",
            bd=1
        )
        self.entry_login_pwd.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        self.entry_login_pwd.bind("<Return>", lambda e: self._attempt_login())

        self.btn_eye = tk.Button(
            frame_input,
            text="👁",
            font=("Segoe UI", 10),
            bg="#21262d",
            fg="#c9d1d9",
            activebackground="#30363d",
            activeforeground="#ffffff",
            relief="flat",
            width=3,
            command=self._toggle_show_pwd
        )
        self.btn_eye.pack(side=tk.RIGHT, ipady=2)

        self.lbl_login_status = tk.Label(
            self.frame_login,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#161b22",
            fg="#f85149"
        )
        self.lbl_login_status.pack(anchor=tk.CENTER, pady=(2, 10))

        frame_btns = tk.Frame(self.frame_login, bg="#161b22")
        frame_btns.pack(fill=tk.X, pady=(4, 0))

        tk.Button(
            frame_btns,
            text="🚪 Keluar",
            font=("Segoe UI", 9),
            bg="#21262d",
            fg="#8b949e",
            activebackground="#30363d",
            relief="flat",
            padx=14,
            pady=6,
            command=self.destroy
        ).pack(side=tk.LEFT)

        tk.Button(
            frame_btns,
            text="🔓 Masuk",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            relief="flat",
            padx=20,
            pady=6,
            command=self._attempt_login
        ).pack(side=tk.RIGHT)

        self.entry_login_pwd.focus_set()

    def _toggle_show_pwd(self):
        self.show_login_pwd = not self.show_login_pwd
        if self.show_login_pwd:
            self.entry_login_pwd.config(show="")
            self.btn_eye.config(text="🙈")
        else:
            self.entry_login_pwd.config(show="●")
            self.btn_eye.config(text="👁")

    def _attempt_login(self):
        entered = self.var_login_pwd.get()
        stored_hash = self.config.get("security", "password_hash", None)
        if verify_password(entered, stored_hash):
            self.lbl_login_status.config(text="✓ Akses Diterima!", fg="#3fb950")
            self.after(150, self._unlock_app)
        else:
            self.lbl_login_status.config(text="❌ Password salah! Akses ditolak.")
            self.entry_login_pwd.delete(0, tk.END)
            self.entry_login_pwd.focus_set()

    def _unlock_app(self):
        self.frame_login.destroy()

        # Switch to main dashboard
        self.title(f"Tantra Farmer Macro {APP_VERSION}")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        self.is_compact_mode = bool(self.config.get("ui", "compact_mode", False))
        self.is_character_dead = False

        if self.is_compact_mode:
            default_w = 520
            default_h = min(760, max(560, sh - 70))
            self.minsize(460, 480)
            self.geometry(f"{default_w}x{default_h}")
        else:
            default_w = min(960, max(880, sw - 40))
            default_h = min(780, max(620, sh - 80))
            self.minsize(460, 480)
            self.geometry(f"{default_w}x{default_h}")
            self._center_window(default_w, default_h)

        self.resizable(True, True)

        # Apply dark theme styling
        self._setup_styles()

        # Initialize core components
        self.wm = WindowManager(self.config)
        self.screen = ScreenCapture(self.wm, self.config)
        self.input = InputController(self.wm, self.config)
        self.matcher = TemplateMatcher(self.config)
        self.ocr = OCREngine(self.config)
        self.bot = FarmerBot(self.wm, self.screen, self.input, self.matcher, self.ocr, self.config)
        self.bot.log_callback = self.append_log
        self.bot.on_death_callback = self._on_character_death

        # Initialize responsive collections for compact/normal mode
        self._mode_radiobuttons = []
        self._responsive_labels = []
        self._responsive_checkbuttons = []

        # Build UI layout
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Setup hotkeys
        self._setup_hotkeys()

        # Auto-detect game window on startup/login
        self.after(300, self._auto_detect_game_window)

        # Background update check from GitHub Releases
        self.after(1000, lambda: self._check_update_in_background(silent=True))

        # Check if running in a temporary or unextracted ZIP folder
        self.after(500, self._check_temp_environment)

    def _check_temp_environment(self):
        if not getattr(sys, "frozen", False):
            return

        exe_path = Path(sys.executable).resolve()
        path_str = str(exe_path).lower()
        temp_dir = os.environ.get("TEMP", "").lower()
        tmp_dir = os.environ.get("TMP", "").lower()

        is_in_temp = (
            (temp_dir and temp_dir in path_str)
            or (tmp_dir and tmp_dir in path_str)
            or "\\appdata\\local\\temp\\" in path_str
            or "temp1_" in path_str
        )

        if is_in_temp:
            messagebox.showwarning(
                "Peringatan: Jalankan dari Folder Ekstrak",
                "Aplikasi terdeteksi berjalan langsung dari dalam folder sementara atau preview ZIP.\n\n"
                "Agar pengaturan dan auto-update dapat tersimpan secara permanen,\n"
                "silakan ekstrak seluruh isi file ZIP ke folder tetap (seperti Desktop atau Folder Game) "
                "sebelum menjalankan makro."
            )

    def _auto_detect_game_window(self):
        found = self.wm.find_window()
        if found:
            origin_x, origin_y, w, h = self.wm.client_rect or (0, 0, 0, 0)
            self.append_log(f"Game terhubung: '{self.wm.window_title}' ({w}x{h})")
        else:
            self.append_log("Jendela game belum terdeteksi otomatis. Silakan buka game atau pilih jendela di tombol 'Cek Jendela Game'.")

    def _setup_styles(self):
        self.configure(bg="#18191c")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg_main = "#18191c"
        bg_card = "#222428"
        fg_white = "#e1e2e6"
        accent_blue = "#2a75d3"
        accent_green = "#238636"
        accent_red = "#da3633"

        style.configure("TNotebook", background=bg_main, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2b2d31", foreground=fg_white, padding=[12, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", accent_blue)], foreground=[("selected", "#ffffff")])

        style.configure("Card.TFrame", background=bg_card, relief="flat")
        style.configure("TLabel", background=bg_card, foreground=fg_white, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg_card, foreground="#58a6ff", font=("Segoe UI", 12, "bold"))

    def _create_scrollable_container(self, parent, bg="#222428"):
        """
        Creates a vertical scrollable container inside parent with mousewheel support.
        Returns (outer_container, scrollable_content_frame).
        """
        outer = tk.Frame(parent, bg=bg)
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=bg)

        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(inner_window, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        return outer, inner

    def _build_header(self):
        header_frame = tk.Frame(self, bg="#202225", height=50, padx=12, pady=8)
        header_frame.pack(fill=tk.X)
        self.header_frame = header_frame

        init_title = "Tantra Farmer" if self.is_compact_mode else "Tantra Auto-Farmer & Inventory Manager"
        self.title_lbl = tk.Label(
            header_frame,
            text=init_title,
            font=("Segoe UI", 12 if self.is_compact_mode else 13, "bold"),
            fg="#58a6ff",
            bg="#202225"
        )
        self.title_lbl.pack(side=tk.LEFT)

        self.version_badge = tk.Label(
            header_frame,
            text=f" {APP_VERSION} ",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg="#238636",
            padx=5,
            pady=2,
            relief="solid",
            bd=1
        )
        self.version_badge.pack(side=tk.LEFT, padx=(8, 0))

        btn_compact_txt = "🗖 Normal" if self.is_compact_mode else "🗕 Compact"
        btn_compact_bg = "#1f6feb" if self.is_compact_mode else "#30363d"
        self.btn_toggle_compact = tk.Button(
            header_frame,
            text=btn_compact_txt,
            font=("Segoe UI", 8, "bold"),
            bg=btn_compact_bg,
            fg="#ffffff" if self.is_compact_mode else "#c9d1d9",
            activebackground="#388bfd",
            activeforeground="#ffffff",
            relief="flat",
            padx=8,
            pady=2,
            command=self.toggle_compact_mode
        )
        self.btn_toggle_compact.pack(side=tk.LEFT, padx=(8, 0))

        start_hk = self.config.get("hotkeys", "start", "f11").upper()
        stop_hk = self.config.get("hotkeys", "stop", "f12").upper()
        self.status_badge = tk.Label(
            header_frame,
            text=f"IDLE ({start_hk} | {stop_hk})",
            font=("Segoe UI", 9, "bold"),
            fg="#3fb950",
            bg="#161b22",
            padx=10,
            pady=3,
            relief="solid",
            bd=1
        )
        self.status_badge.pack(side=tk.RIGHT)

    def toggle_compact_mode(self):
        self.is_compact_mode = not self.is_compact_mode
        self._apply_compact_mode(self.is_compact_mode)
        self.config.set("ui", "compact_mode", self.is_compact_mode)
        self.config.save()

    def _apply_compact_mode(self, is_compact: bool):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        if is_compact:
            self.minsize(460, 480)
            compact_w = 520
            compact_h = min(760, max(560, sh - 70))

            # Snap ke samping kanan jendela game Tantra jika ditemukan
            if self.wm.hwnd:
                self.wm.update_bounds()
                game_x, game_y, game_w, game_h = self.wm.client_rect or (0, 0, 800, 600)
                macro_x = min(sw - compact_w - 5, max(0, game_x + game_w + 2))
                macro_y = max(0, game_y)
            else:
                macro_x = max(0, sw - compact_w - 10)
                macro_y = 20

            self.geometry(f"{compact_w}x{compact_h}+{macro_x}+{macro_y}")
            if hasattr(self, "btn_toggle_compact"):
                self.btn_toggle_compact.config(text="🗖 Normal", bg="#1f6feb", fg="#ffffff")
            if hasattr(self, "title_lbl"):
                self.title_lbl.config(text="Tantra Farmer", font=("Segoe UI", 12, "bold"))
            self.append_log("Tampilan dialihkan ke Mode Compact (Lebar 520px - optimal layar 1366x768).")
        else:
            self.minsize(460, 480)
            norm_w = min(960, max(880, sw - 40))
            norm_h = min(780, max(620, sh - 80))
            self.geometry(f"{norm_w}x{norm_h}")
            if hasattr(self, "btn_toggle_compact"):
                self.btn_toggle_compact.config(text="🗕 Compact", bg="#30363d", fg="#c9d1d9")
            if hasattr(self, "title_lbl"):
                self.title_lbl.config(text="Tantra Auto-Farmer & Inventory Manager", font=("Segoe UI", 13, "bold"))
            self.append_log("Tampilan dialihkan ke Mode Normal.")

        self._update_tab_titles(is_compact)
        wrap_val = 450 if is_compact else 840
        if hasattr(self, "_mode_radiobuttons") and self._mode_radiobuttons:
            for rb in self._mode_radiobuttons:
                try:
                    rb.config(wraplength=wrap_val)
                except Exception:
                    pass

        if hasattr(self, "_responsive_labels"):
            for lbl, c_txt, n_txt in self._responsive_labels:
                try:
                    lbl.config(text=c_txt if is_compact else n_txt, wraplength=wrap_val)
                except Exception:
                    pass

        if hasattr(self, "_responsive_checkbuttons"):
            for cb, c_txt, n_txt in self._responsive_checkbuttons:
                try:
                    cb.config(text=c_txt if is_compact else n_txt, wraplength=wrap_val)
                except Exception:
                    pass

    def _update_tab_titles(self, is_compact: bool):
        """Switches notebook tabs between icon-only (compact) and full descriptive titles (normal)."""
        if not hasattr(self, "notebook"):
            return
        tabs = [
            (getattr(self, "tab_dashboard", None), "📊", "📊 Dashboard"),
            (getattr(self, "tab_area", None), "🎯", "🎯 Kalibrasi Area"),
            (getattr(self, "tab_inspector", None), "🔍", "🔍 Deteksi Slot"),
            (getattr(self, "tab_storage_whitelist", None), "📥", "📥 Blacklist Simpan"),
            (getattr(self, "tab_storage_withdraw_blacklist", None), "📤", "📤 Blacklist Tarik"),
            (getattr(self, "tab_whitelist", None), "💰", "💰 Blacklist Jual"),
            (getattr(self, "tab_skill", None), "⚡", "⚡ Auto Skill"),
            (getattr(self, "tab_pot", None), "🧪", "🧪 Auto Pot"),
            (getattr(self, "tab_settings", None), "⚙️", "⚙️ Pengaturan")
        ]
        for frame, icon_txt, full_txt in tabs:
            if frame is None:
                continue
            txt = f" {icon_txt} " if is_compact else f" {full_txt} "
            try:
                self.notebook.tab(frame, text=txt)
            except Exception:
                pass

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Tab 1: Dashboard / Runner
        self.tab_dashboard = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_dashboard, text=" 📊 Dashboard ")
        self._build_dashboard_tab()

        # Tab 2: Area Calibration (Select Area)
        self.tab_area = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_area, text=" 🎯 Kalibrasi Area ")
        self._build_area_tab()

        # Tab 3: Visual Slot Inspector (Empty vs Occupied)
        self.tab_inspector = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_inspector, text=" 🔍 Deteksi Slot ")
        self._build_inspector_tab()

        # Tab 4: Blacklist Simpan Gudang (Tas -> Gudang)
        self.tab_storage_whitelist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_storage_whitelist, text=" 📥 Blacklist Simpan ")
        self._build_storage_whitelist_tab()

        # Tab 5: Blacklist Tarik Gudang (Gudang -> Tas)
        self.tab_storage_withdraw_blacklist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_storage_withdraw_blacklist, text=" 📤 Blacklist Tarik ")
        self._build_storage_withdraw_blacklist_tab()

        # Tab 6: Blacklist Jual Merchant NPC
        self.tab_whitelist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_whitelist, text=" 💰 Blacklist Jual ")
        self._build_whitelist_tab()

        # Tab 7: Auto Skill
        self.tab_skill = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_skill, text=" ⚡ Auto Skill ")
        self._build_skill_tab()

        # Tab 8: Auto Pot
        self.tab_pot = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_pot, text=" 🧪 Auto Pot ")
        self._build_pot_tab()

        # Tab 9: Settings
        self.tab_settings = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_settings, text=" ⚙️ Pengaturan ")
        self._build_settings_tab()

        # Update tab titles according to initial compact mode state
        self._update_tab_titles(self.is_compact_mode)

    # =========================================================================
    # TAB 1: Dashboard
    # =========================================================================
    def _build_dashboard_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_dashboard)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        mode_frame = tk.LabelFrame(container, text=" Pilih Mode Operasi ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        mode_frame.pack(fill=tk.X, pady=(0, 12))

        self.selected_mode = tk.StringVar(value="auto_storage_merchant_loop")

        modes = [
            ("🔄 Full Auto Loop (Tarik Gudang ➔ Jual NPC Ashuri)", "auto_storage_merchant_loop"),
            ("⚔️ Auto Hunt Loop (Auto Simpan Gudang + Auto Skill)", "hunt_auto_deposit"),
            ("⚡ Auto Skill Standalone (Hanya Auto Skill tanpa pindah tas)", "auto_skill_standalone"),
            ("🧪 Auto Pot Standalone (Hanya Auto Pot HP/TP tanpa aksi lain)", "auto_pot_standalone"),
            ("📥 Tas ➔ Gudang (Simpan ke Gudang dengan Filter Blacklist)", "inv_to_storage"),
            ("📤 Gudang ➔ Tas (Tarik barang ke Slot Kosong Tas)", "storage_to_inv"),
            ("💰 Tas ➔ NPC Merchant (Jual item tas kecuali Blacklist)", "inv_to_merchant")
        ]

        self._mode_radiobuttons = []
        wrap_val = 430 if self.is_compact_mode else 820

        for text, val in modes:
            rb = tk.Radiobutton(
                mode_frame,
                text=text,
                value=val,
                variable=self.selected_mode,
                bg="#222428",
                fg="#e1e2e6",
                selectcolor="#161b22",
                activebackground="#222428",
                activeforeground="#58a6ff",
                font=("Segoe UI", 10),
                wraplength=wrap_val,
                justify=tk.LEFT,
                anchor=tk.W
            )
            rb.pack(anchor=tk.W, fill=tk.X, pady=3)
            self._mode_radiobuttons.append(rb)

        # Row 1: Primary Action Buttons (Start / Stop)
        act_row = tk.Frame(container, bg="#222428", pady=4)
        act_row.pack(fill=tk.X)

        start_k = self.config.get("hotkeys", "start", "f11").upper()
        stop_k = self.config.get("hotkeys", "stop", "f12").upper()

        self.btn_start = tk.Button(
            act_row,
            text=f"▶ MULAI ({start_k})",
            font=("Segoe UI", 10, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            relief="flat",
            padx=16,
            pady=7,
            command=self.start_macro
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)

        self.btn_stop = tk.Button(
            act_row,
            text=f"⏹ STOP ({stop_k})",
            font=("Segoe UI", 10, "bold"),
            bg="#da3633",
            fg="#ffffff",
            activebackground="#f85149",
            relief="flat",
            padx=16,
            pady=7,
            command=self.stop_macro
        )
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Row 2: Window Positioning Helpers
        win_row = tk.Frame(container, bg="#222428", pady=3)
        win_row.pack(fill=tk.X)

        self.btn_zeroin = tk.Button(
            win_row,
            text="📍 Zero-In (0, 0)",
            font=("Segoe UI", 8, "bold"),
            bg="#21262d",
            fg="#58a6ff",
            relief="flat",
            padx=6,
            pady=4,
            command=self.zeroin_game_window
        )
        self.btn_zeroin.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self.btn_snap = tk.Button(
            win_row,
            text="🧲 Snap Samping",
            font=("Segoe UI", 8, "bold"),
            bg="#21262d",
            fg="#79c0ff",
            relief="flat",
            padx=6,
            pady=4,
            command=self.snap_macro_beside_game
        )
        self.btn_snap.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self.btn_find_window = tk.Button(
            win_row,
            text="🔍 Cek Window",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=6,
            pady=4,
            command=self.check_game_window
        )
        self.btn_find_window.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Quick Shortcuts Panel
        quick_frame = tk.LabelFrame(container, text=" ⚡ Tombol Aksi Cepat / Shortcut Keyboard Langsung ", bg="#222428", fg="#d29922", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        quick_frame.pack(fill=tk.X, pady=(8, 0))

        q_btn_bar = tk.Frame(quick_frame, bg="#222428")
        q_btn_bar.pack(fill=tk.X)

        s2i_hk = self.config.get("hotkeys", "storage_to_inv", "f9").upper()
        i2n_hk = self.config.get("hotkeys", "inv_to_merchant", "f10").upper()
        pop_hk = self.config.get("hotkeys", "dismiss_popup", "f8").upper()
        loop_hk = self.config.get("hotkeys", "auto_loop", "f7").upper()

        self.btn_quick_loop = tk.Button(
            q_btn_bar,
            text=f"🔄 Auto Loop [{loop_hk}]",
            font=("Segoe UI", 8, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            relief="flat",
            padx=6,
            pady=5,
            command=lambda: self.run_specific_task("auto_storage_merchant_loop")
        )
        self.btn_quick_loop.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self.btn_quick_s2i = tk.Button(
            q_btn_bar,
            text=f"📦 Tarik Storage [{s2i_hk}]",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            relief="flat",
            padx=6,
            pady=5,
            command=lambda: self.run_specific_task("storage_to_inv")
        )
        self.btn_quick_s2i.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self.btn_quick_i2n = tk.Button(
            q_btn_bar,
            text=f"💰 Jual NPC [{i2n_hk}]",
            font=("Segoe UI", 8, "bold"),
            bg="#8957e5",
            fg="#ffffff",
            activebackground="#a371f7",
            relief="flat",
            padx=6,
            pady=5,
            command=lambda: self.run_specific_task("inv_to_merchant")
        )
        self.btn_quick_i2n.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self.btn_quick_popup = tk.Button(
            q_btn_bar,
            text=f"🛡️ Tutup Popup [{pop_hk}]",
            font=("Segoe UI", 8, "bold"),
            bg="#d29922",
            fg="#0d1117",
            activebackground="#e3b341",
            relief="flat",
            padx=6,
            pady=5,
            command=lambda: self.run_specific_task("dismiss_popup")
        )
        self.btn_quick_popup.pack(side=tk.LEFT, fill=tk.X, expand=True)

        log_frame = tk.LabelFrame(container, text=" Aktivitas / Log Eksekusi ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=8, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.txt_log = tk.Text(log_frame, bg="#0d1117", fg="#58a6ff", insertbackground="#ffffff", font=("Consolas", 9), wrap=tk.WORD)
        scrollbar = tk.Scrollbar(log_frame, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # =========================================================================
    # TAB 2: Area Calibration (Select Area)
    # =========================================================================
    def _build_area_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_area)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        desc = tk.Label(
            container,
            text="Fitur Select Area: Menyesuaikan posisi jendela Inventory, Storage, dan Merchant\n"
                 "secara bebas untuk berbagai resolusi layar dan letak window game.",
            font=("Segoe UI", 10),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        # Quick Window Positioning Toolbar
        win_bar = tk.LabelFrame(container, text=" 🖥️ Posisi Window Game & Makro ", bg="#222428", fg="#d29922", font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        win_bar.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            win_bar,
            text="Posisikan game dan makro agar berdampingan rapi tanpa saling tumpang tindih:",
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e"
        ).pack(anchor=tk.W, pady=(0, 6))

        wb_btns = tk.Frame(win_bar, bg="#222428")
        wb_btns.pack(fill=tk.X)

        tk.Button(
            wb_btns,
            text="📍 Zero-In Game (Posisikan ke 0, 0)",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            relief="flat",
            padx=12,
            pady=5,
            command=self.zeroin_game_window
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            wb_btns,
            text="🧲 Snap Makro ke Samping Game",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            relief="flat",
            padx=12,
            pady=5,
            command=self.snap_macro_beside_game
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            wb_btns,
            text="🔍 Cek Jendela Game",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=5,
            command=self.check_game_window
        ).pack(side=tk.LEFT)

        # 1. Inventory Area Box
        inv_box = tk.LabelFrame(container, text=" 🎒 Area Inventory (Tas 24 Slot - 6 Kolom x 4 Baris) ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        inv_box.pack(fill=tk.X, pady=6)

        inv_cfg = self.config.get("inventory")
        self.lbl_inv_coords = tk.Label(
            inv_box,
            text=f"Koordinat Saat Ini: X=[{inv_cfg.get('x1', 537)}..{inv_cfg.get('x2', 758)}], Y=[{inv_cfg.get('y1', 280)}..{inv_cfg.get('y2', 430)}] "
                 f"({inv_cfg.get('cols', 6)}x{inv_cfg.get('rows', 4)} = 24 slot)",
            font=("Consolas", 9),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_inv_coords.pack(side=tk.LEFT, padx=5)

        tk.Button(
            inv_box,
            text="🎯 Pilih Area Inventory dari Layar...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self.launch_area_selector("Inventory (24 Slot)", 6, 4, "inventory")
        ).pack(side=tk.RIGHT)

        # 2. Storage Area Box
        store_box = tk.LabelFrame(container, text=" 🏛️ Area Storage (Gudang 120 Slot - 10 Kolom x 12 Baris) ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        store_box.pack(fill=tk.X, pady=6)

        store_cfg = self.config.get("storage")
        self.lbl_store_coords = tk.Label(
            store_box,
            text=f"Koordinat Saat Ini: X=[{store_cfg.get('x1', 55)}..{store_cfg.get('x2', 467)}], Y=[{store_cfg.get('y1', 233)}..{store_cfg.get('y2', 691)}] "
                 f"({store_cfg.get('cols', 10)}x{store_cfg.get('rows', 12)} = 120 slot)",
            font=("Consolas", 9),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_store_coords.pack(side=tk.LEFT, padx=5)

        tk.Button(
            store_box,
            text="🎯 Pilih Area Storage dari Layar...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self.launch_area_selector("Storage (120 Slot)", 10, 12, "storage")
        ).pack(side=tk.RIGHT)

        # 3. Merchant Area Box
        merch_box = tk.LabelFrame(container, text=" 🏪 Area Toko NPC Merchant (Target Drop Jual) ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        merch_box.pack(fill=tk.X, pady=6)

        merch_cfg = self.config.get("merchant")
        self.lbl_merch_coords = tk.Label(
            merch_box,
            text=f"Koordinat Drop: X=[{merch_cfg.get('x1', 360)}..{merch_cfg.get('x2', 650)}], Y=[{merch_cfg.get('y1', 250)}..{merch_cfg.get('y2', 650)}]",
            font=("Consolas", 9),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_merch_coords.pack(side=tk.LEFT, padx=5)

        tk.Button(
            merch_box,
            text="🎯 Pilih Area Merchant dari Layar...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self.launch_area_selector("Toko Merchant (Drop Area)", 1, 1, "merchant")
        ).pack(side=tk.RIGHT)

    def launch_area_selector(self, section_title: str, cols: int, rows: int, config_key: str):
        # Capture current game screen
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            self.config.set(config_key, "x1", x1)
            self.config.set(config_key, "y1", y1)
            self.config.set(config_key, "x2", x2)
            self.config.set(config_key, "y2", y2)
            self.config.set(config_key, "cols", cols)
            self.config.set(config_key, "rows", rows)
            self.config.save()

            if config_key == "inventory":
                self.lbl_inv_coords.config(text=f"Koordinat: X=[{x1}..{x2}], Y=[{y1}..{y2}] ({cols}x{rows} = {cols * rows} slot)")
            elif config_key == "storage":
                self.lbl_store_coords.config(text=f"Koordinat: X=[{x1}..{x2}], Y=[{y1}..{y2}] ({cols}x{rows} = {cols * rows} slot)")
            elif config_key == "merchant":
                self.lbl_merch_coords.config(text=f"Koordinat: X=[{x1}..{x2}], Y=[{y1}..{y2}]")

            self.append_log(f"Area {section_title} berhasil diperbarui: [{x1},{y1}] s/d [{x2},{y2}].")
            messagebox.showinfo("Area Disimpan", f"Area {section_title} berhasil dikalibrasi dan disimpan ke config!")

        AreaSelectorWindow(self, section_title, cols, rows, client_img, on_saved)

    # =========================================================================
    # TAB 3: Visual Slot Inspector
    # =========================================================================
    def _build_inspector_tab(self):
        container = tk.Frame(self.tab_inspector, bg="#222428", padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        top_bar = tk.Frame(container, bg="#222428")
        top_bar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(
            top_bar,
            text="🔍 PINDAI & TES STATUS SLOT SEKARANG",
            font=("Segoe UI", 10, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            command=self.run_slot_scan_inspector
        ).pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_scan_summary = tk.Label(
            top_bar,
            text="Klik tombol untuk memeriksa status slot Tas (24) dan Gudang (120).",
            font=("Segoe UI", 10),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_scan_summary.pack(side=tk.LEFT)

        # Sensitivity threshold adjustment
        thresh_frame = tk.Frame(container, bg="#21262d", padx=10, pady=6)
        thresh_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(thresh_frame, text="Sensitivitas Deteksi Slot Kosong (Threshold StdDev):", bg="#21262d", fg="#e1e2e6").pack(side=tk.LEFT, padx=(0, 10))
        cur_thresh = self.config.get("rules", "empty_slot_threshold", 18.0)
        self.thresh_entry = tk.Entry(thresh_frame, width=8, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff")
        self.thresh_entry.insert(0, str(cur_thresh))
        self.thresh_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            thresh_frame,
            text="Simpan Sensitivitas",
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=8,
            pady=2,
            command=self.save_empty_threshold
        ).pack(side=tk.LEFT)

        # Notebook for Inventory vs Storage preview
        sub_nb = ttk.Notebook(container)
        sub_nb.pack(fill=tk.BOTH, expand=True)

        self.frame_inv_grid = tk.Frame(sub_nb, bg="#161b22", padx=10, pady=10)
        sub_nb.add(self.frame_inv_grid, text=" Peta Slot Inventaris Tas (24 Slot) ")

        self.frame_store_grid = tk.Frame(sub_nb, bg="#161b22", padx=10, pady=10)
        sub_nb.add(self.frame_store_grid, text=" Peta Slot Gudang Storage (120 Slot) ")

    def save_empty_threshold(self):
        try:
            val = float(self.thresh_entry.get().strip())
            self.config.set("rules", "empty_slot_threshold", val)
            self.config.save()
            messagebox.showinfo("Sukses", f"Threshold sensitivitas slot kosong disimpan: {val}")
        except Exception as e:
            messagebox.showerror("Error", f"Nilai tidak valid: {e}")

    def run_slot_scan_inspector(self):
        client_img = self.screen.capture_client()

        # 1. Scan Inventory
        inv_slots = self.bot.scan_inventory_status(client_img)
        inv_empty = sum(1 for s in inv_slots if s["is_empty"])
        inv_filled = len(inv_slots) - inv_empty

        # 2. Scan Storage
        store_slots = self.bot.scan_storage_status(client_img)
        store_empty = sum(1 for s in store_slots if s["is_empty"])
        store_filled = len(store_slots) - store_empty

        self.lbl_scan_summary.config(
            text=f"🟢 Tas: {inv_empty} Kosong, {inv_filled} Berisi (Total {len(inv_slots)}) | "
                 f"Gudang: {store_empty} Kosong, {store_filled} Berisi (Total {len(store_slots)})",
            fg="#3fb950"
        )

        # Render Inventory Grid (6 cols x 8 rows)
        for w in self.frame_inv_grid.winfo_children():
            w.destroy()

        inv_cols = self.config.get("inventory", "cols", 6)
        for s in inv_slots:
            c = s["col"]
            r = s["row"]
            bg_col = "#238636" if s["is_empty"] else "#da3633"
            txt_status = "KOSONG" if s["is_empty"] else "BERISI"

            cell = tk.Frame(self.frame_inv_grid, bg=bg_col, width=54, height=42, padx=2, pady=2, relief="ridge", bd=1)
            cell.grid(row=r, column=c, padx=3, pady=3)
            cell.pack_propagate(False)

            tk.Label(cell, text=f"#{s['index']}", font=("Segoe UI", 8, "bold"), bg=bg_col, fg="#ffffff").pack()
            tk.Label(cell, text=txt_status, font=("Segoe UI", 7), bg=bg_col, fg="#ffffff").pack()

        # Render Storage Grid (10 cols x 12 rows = 120 slots)
        for w in self.frame_store_grid.winfo_children():
            w.destroy()

        store_cols = self.config.get("storage", "cols", 10)
        for s in store_slots:
            c = s["col"]
            r = s["row"]
            bg_col = "#238636" if s["is_empty"] else "#da3633"

            cell = tk.Frame(self.frame_store_grid, bg=bg_col, width=38, height=32, padx=1, pady=1, relief="ridge", bd=1)
            cell.grid(row=r, column=c, padx=2, pady=2)
            cell.pack_propagate(False)

            tk.Label(cell, text=f"#{s['index']}", font=("Segoe UI", 7, "bold"), bg=bg_col, fg="#ffffff").pack()

    # =========================================================================
    # TAB 4: Blacklist Gudang (Item Ditinggalkan di Tas)
    # =========================================================================
    def _build_storage_whitelist_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_storage_whitelist)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        wrap_val = 450 if self.is_compact_mode else 840
        desc_compact = (
            "Aturan Tas ➔ Gudang:\n"
            "• 🚫 Blacklist: Item di daftar TIDAK dipindahkan (aman di tas).\n"
            "• ⚡ Item Lain: Dipindahkan otomatis ke slot kosong gudang."
        )
        desc_normal = (
            "Aturan Pemindahan Tas (Inventory) ke Gudang (Storage):\n"
            "• 🚫 BLACKLIST GUDANG: Item di daftar ini TIDAK AKAN dipindahkan ke gudang (tetap di tas, misal: Potion, Gear utama).\n"
            "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan langsung dipindahkan ke slot kosong di gudang."
        )
        desc = tk.Label(
            container,
            text=desc_compact if self.is_compact_mode else desc_normal,
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT,
            wraplength=wrap_val
        )
        desc.pack(anchor=tk.W, pady=(0, 10))
        self._responsive_labels.append((desc, desc_compact, desc_normal))

        # Checkboxes bar
        cfg_bar = tk.Frame(container, bg="#161b22", padx=12, pady=8, relief="ridge", bd=1)
        cfg_bar.pack(fill=tk.X, pady=(0, 10))

        self.var_storage_blacklist_enabled = tk.BooleanVar(
            value=self.config.get("storage_deposit", "blacklist_enabled", True)
        )
        cb1_compact = "Aktifkan Blacklist Gudang (Jangan simpan item blacklist)"
        cb1_normal = "Aktifkan Blacklist Gudang (Jangan pindahkan item yang cocok dengan Ikon Blacklist)"
        cb1 = tk.Checkbutton(
            cfg_bar,
            text=cb1_compact if self.is_compact_mode else cb1_normal,
            variable=self.var_storage_blacklist_enabled,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold"),
            command=self._on_toggle_storage_blacklist,
            wraplength=wrap_val,
            justify=tk.LEFT,
            anchor=tk.W
        )
        cb1.pack(anchor=tk.W, fill=tk.X)
        self._responsive_checkbuttons.append((cb1, cb1_compact, cb1_normal))

        # Filter Pop-up Penutup Storage Box (Issue #6)
        self.box_popup_frame = tk.LabelFrame(
            container,
            text=" 🛡️ Filter Pop-up Penutup Storage ",
            bg="#222428",
            fg="#d29922",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=8
        )
        self.box_popup_frame.pack(fill=tk.X, pady=(0, 12))

        self.var_auto_dismiss_popup = tk.BooleanVar(value=self.config.get("storage_popup", "auto_dismiss", True))
        cb2_compact = "🛡️ Tutup otomatis popup yang terdeteksi sebelum proses Storage"
        cb2_normal = "🛡️ Tutup Otomatis Popup yang terdeteksi sebelum proses Storage (Klik judul popup -> Esc 1x)"
        cb2 = tk.Checkbutton(
            self.box_popup_frame,
            text=cb2_compact if self.is_compact_mode else cb2_normal,
            variable=self.var_auto_dismiss_popup,
            bg="#222428",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#222428",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9),
            command=self._on_toggle_auto_dismiss_popup,
            wraplength=wrap_val,
            justify=tk.LEFT,
            anchor=tk.W
        )
        cb2.pack(anchor=tk.W, fill=tk.X, pady=(0, 6))
        self._responsive_checkbuttons.append((cb2, cb2_compact, cb2_normal))

        pop_btn_bar = tk.Frame(self.box_popup_frame, bg="#222428")
        pop_btn_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            pop_btn_bar,
            text="✂️ Potong Judul Popup dari Layar...",
            font=("Segoe UI", 9, "bold"),
            bg="#d29922",
            fg="#0d1117",
            activebackground="#e3b341",
            relief="flat",
            padx=12,
            pady=4,
            command=self.crop_popup_header_dialog
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            pop_btn_bar,
            text="🔄 Refresh Filter",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.refresh_storage_popup_view
        ).pack(side=tk.LEFT)

        self.storage_popup_frame = tk.Frame(self.box_popup_frame, bg="#161b22", relief="sunken", bd=1)
        self.storage_popup_frame.pack(fill=tk.X)

        self.refresh_storage_popup_view()

        # Blacklist Gudang Box (Full Width)
        self.box_storage_frame = tk.LabelFrame(
            container,
            text=" 🚫 Daftar Item Blacklist Gudang (Ditinggalkan di Tas) ",
            bg="#222428",
            fg="#f85149",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=10
        )
        self.box_storage_frame.pack(fill=tk.BOTH, expand=True)

        btn_bar = tk.Frame(self.box_storage_frame, bg="#222428")
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            btn_bar,
            text="✂️ Potong dari Slot Tas...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            command=lambda: self.crop_icon_dialog(target="storage_blacklist")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="🔄 Refresh",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.refresh_storage_blacklist_view
        ).pack(side=tk.LEFT)

        self.storage_blacklist_frame = tk.Frame(self.box_storage_frame, bg="#161b22", relief="sunken", bd=1)
        self.storage_blacklist_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_storage_blacklist_view()

    def crop_popup_header_dialog(self):
        """Allows user to visually select and crop a popup header title from game screen."""
        if not self.wm.hwnd:
            self.wm.find_window()
        if not self.wm.hwnd and sys.platform == "win32":
            messagebox.showerror("Game Tidak Ditemukan", "Jendela game Tantra belum terdeteksi!\nBuka game atau pilih jendela di tombol 'Cek Window'.")
            return

        self.wm.activate_window()
        time.sleep(0.35)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            if x2 <= x1 or y2 <= y1:
                return

            crop = client_img.crop((x1, y1, x2, y2))

            dlg = tk.Toplevel(self)
            dlg.title("Nama / Jenis Popup")
            dlg.geometry("380x160")
            dlg.configure(bg="#222428")
            dlg.resizable(False, False)

            tk.Label(
                dlg,
                text="Beri nama untuk popup ini (misal: Notice, Quiz, Raffle):",
                bg="#222428",
                fg="#e1e2e6",
                font=("Segoe UI", 9)
            ).pack(padx=14, pady=(16, 6), anchor=tk.W)

            e_name = tk.Entry(dlg, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", width=26, font=("Segoe UI", 10))
            e_name.insert(0, "Notice")
            e_name.pack(padx=14, pady=4, anchor=tk.W)
            e_name.focus_set()

            def do_save_popup():
                name = e_name.get().strip() or "popup"
                dest_path = self._get_unique_save_path(self.config.storage_popups_dir, name, ".png")
                crop.save(dest_path)
                dlg.destroy()
                self.refresh_storage_popup_view()
                self.append_log(f"🛡️ Filter popup '{dest_path.name}' berhasil ditambahkan ke daftar.")
                messagebox.showinfo("Sukses", f"Berhasil menambahkan '{dest_path.name}' ke Filter Popup Storage!")

            btn_box = tk.Frame(dlg, bg="#222428")
            btn_box.pack(padx=14, pady=12, fill=tk.X)
            tk.Button(btn_box, text="Simpan", bg="#238636", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=12, pady=4, relief="flat", command=do_save_popup).pack(side=tk.LEFT, padx=(0, 6))
            tk.Button(btn_box, text="Batal", bg="#30363d", fg="#c9d1d9", font=("Segoe UI", 9), padx=10, pady=4, relief="flat", command=dlg.destroy).pack(side=tk.LEFT)

        AreaSelectorWindow(self, "Pilih Judul Popup Storage", 1, 1, client_img, on_saved)

    def refresh_storage_popup_view(self):
        if not hasattr(self, 'storage_popup_frame'):
            return

        for widget in self.storage_popup_frame.winfo_children():
            widget.destroy()

        pop_dir = self.config.storage_popups_dir
        popups = sorted(list(pop_dir.glob("*.png")) + list(pop_dir.glob("*.jpg")), key=lambda p: p.name.lower())

        if hasattr(self, 'box_popup_frame'):
            self.box_popup_frame.config(text=f" 🛡️ Filter Pop-up Penutup Storage ({len(popups)} Pop-up Terdaftar) ")

        if not popups:
            empty_lbl = tk.Label(
                self.storage_popup_frame,
                text="Belum ada filter popup terdaftar. Klik 'Potong Judul Popup dari Layar' untuk menambahkan (Notice, Quiz, dsb).",
                bg="#161b22",
                fg="#8b949e",
                pady=15
            )
            empty_lbl.pack()
            return

        canvas = tk.Canvas(self.storage_popup_frame, bg="#161b22", highlightthickness=0, height=85)
        scroll = tk.Scrollbar(self.storage_popup_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#161b22")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._popup_images = []
        for p in popups:
            row = tk.Frame(scrollable_frame, bg="#21262d", pady=2, padx=6)
            row.pack(fill=tk.X, padx=6, pady=2)

            try:
                pil_img = Image.open(p)
                w, h = pil_img.size
                ratio = min(60 / w, 24 / h, 1.0)
                disp_w = max(10, int(w * ratio))
                disp_h = max(10, int(h * ratio))
                pil_img = pil_img.resize((disp_w, disp_h), Image.Resampling.NEAREST)
                tk_img = ImageTk.PhotoImage(pil_img)
                self._popup_images.append(tk_img)

                img_lbl = tk.Label(row, image=tk_img, bg="#21262d")
                img_lbl.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass

            name_lbl = tk.Label(row, text=p.stem, font=("Segoe UI", 9, "bold"), bg="#21262d", fg="#e1e2e6")
            name_lbl.pack(side=tk.LEFT)

            badge = tk.Label(row, text=" [Auto-Close] ", font=("Segoe UI", 7, "bold"), bg="#d29922", fg="#0d1117", padx=4, pady=1)
            badge.pack(side=tk.LEFT, padx=(8, 0))

            del_btn = tk.Button(
                row,
                text="Hapus",
                font=("Segoe UI", 8),
                bg="#30363d",
                fg="#e1e2e6",
                relief="flat",
                command=lambda path=p: self.delete_storage_popup_template(path)
            )
            del_btn.pack(side=tk.RIGHT)

    def delete_storage_popup_template(self, path: Path):
        if messagebox.askyesno("Konfirmasi", f"Hapus template popup '{path.name}' dari Filter Popup Storage?"):
            try:
                path.unlink()
                self.refresh_storage_popup_view()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus: {e}")

    def _on_toggle_auto_dismiss_popup(self):
        val = self.var_auto_dismiss_popup.get()
        self.config.set("storage_popup", "auto_dismiss", val)
        self.config.save()

    def _on_toggle_storage_blacklist(self):
        val = self.var_storage_blacklist_enabled.get()
        if "storage_deposit" not in self.config.data:
            self.config.data["storage_deposit"] = {}
        self.config.data["storage_deposit"]["blacklist_enabled"] = val
        self.config.save()
        self.append_log(f"Blacklist Gudang diatur ke: {'AKTIF' if val else 'NON-AKTIF'}")

    def refresh_storage_blacklist_view(self):
        for widget in self.storage_blacklist_frame.winfo_children():
            widget.destroy()

        bl_dir = self.config.storage_blacklist_dir
        icons = sorted(list(bl_dir.glob("*.png")) + list(bl_dir.glob("*.jpg")), key=lambda p: p.name.lower())

        if hasattr(self, 'box_storage_frame'):
            self.box_storage_frame.config(text=f" 🚫 Daftar Item Blacklist Gudang ({len(icons)} Item Terdaftar) ")

        if not icons:
            empty_lbl = tk.Label(
                self.storage_blacklist_frame,
                text="Belum ada item dalam Blacklist Gudang.\nItem di sini tidak akan dipindahkan ke gudang (tetap di tas).",
                bg="#161b22",
                fg="#8b949e",
                pady=30
            )
            empty_lbl.pack()
            return

        canvas = tk.Canvas(self.storage_blacklist_frame, bg="#161b22", highlightthickness=0)
        scroll = tk.Scrollbar(self.storage_blacklist_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#161b22")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._storage_bl_images = []
        for p in icons:
            row = tk.Frame(scrollable_frame, bg="#21262d", pady=3, padx=6)
            row.pack(fill=tk.X, padx=6, pady=3)

            try:
                pil_img = Image.open(p).resize((32, 32), Image.Resampling.NEAREST)
                tk_img = ImageTk.PhotoImage(pil_img)
                self._storage_bl_images.append(tk_img)

                img_lbl = tk.Label(row, image=tk_img, bg="#21262d")
                img_lbl.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass

            name_lbl = tk.Label(row, text=p.stem, font=("Segoe UI", 9, "bold"), bg="#21262d", fg="#e1e2e6")
            name_lbl.pack(side=tk.LEFT)

            badge = tk.Label(row, text=" [Ditinggal di Tas] ", font=("Segoe UI", 7, "bold"), bg="#da3633", fg="#ffffff", padx=4, pady=1)
            badge.pack(side=tk.LEFT, padx=(8, 0))

            del_btn = tk.Button(
                row,
                text="Hapus",
                font=("Segoe UI", 8),
                bg="#30363d",
                fg="#e1e2e6",
                relief="flat",
                command=lambda path=p: self.delete_storage_blacklist_icon(path)
            )
            del_btn.pack(side=tk.RIGHT)

    def delete_storage_blacklist_icon(self, path: Path):
        if messagebox.askyesno("Konfirmasi", f"Hapus '{path.name}' dari Blacklist Simpan Gudang?"):
            try:
                path.unlink()
                self.refresh_storage_blacklist_view()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus: {e}")

    # =========================================================================
    # TAB: Blacklist Tarik Gudang (Item Ditinggalkan di Gudang - Storage -> Tas)
    # =========================================================================
    def _build_storage_withdraw_blacklist_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_storage_withdraw_blacklist)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        wrap_val = 450 if self.is_compact_mode else 840
        desc_compact = (
            "Aturan Gudang ➔ Tas:\n"
            "• 🚫 Blacklist: Item di daftar TIDAK ditarik (tetap di gudang).\n"
            "• ⚡ Item Lain: Ditarik ke tas sampai penuh untuk dijual ke NPC."
        )
        desc_normal = (
            "Aturan Penarikan Gudang (Storage) ke Tas (Inventory):\n"
            "• 🚫 BLACKLIST TARIK GUDANG: Item di daftar ini TIDAK AKAN ditarik ke tas (tetap aman di gudang, misal: Ore, Potion cadangan, Equip simpanan).\n"
            "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan ditarik ke slot tas kosong sampai tas penuh untuk dijual ke pedagang."
        )
        desc = tk.Label(
            container,
            text=desc_compact if self.is_compact_mode else desc_normal,
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT,
            wraplength=wrap_val
        )
        desc.pack(anchor=tk.W, pady=(0, 10))
        self._responsive_labels.append((desc, desc_compact, desc_normal))

        # Checkboxes bar
        cfg_bar = tk.Frame(container, bg="#161b22", padx=12, pady=8, relief="ridge", bd=1)
        cfg_bar.pack(fill=tk.X, pady=(0, 10))

        self.var_storage_withdraw_blacklist_enabled = tk.BooleanVar(
            value=self.config.get("storage_withdraw", "blacklist_enabled", True)
        )
        cb1_compact = "Aktifkan Blacklist Tarik (Jangan tarik item blacklist)"
        cb1_normal = "Aktifkan Blacklist Tarik Gudang (Jangan tarik item yang cocok dengan Ikon Blacklist)"
        cb1 = tk.Checkbutton(
            cfg_bar,
            text=cb1_compact if self.is_compact_mode else cb1_normal,
            variable=self.var_storage_withdraw_blacklist_enabled,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold"),
            command=self._on_toggle_storage_withdraw_blacklist,
            wraplength=wrap_val,
            justify=tk.LEFT,
            anchor=tk.W
        )
        cb1.pack(anchor=tk.W, fill=tk.X)
        self._responsive_checkbuttons.append((cb1, cb1_compact, cb1_normal))

        # Blacklist Tarik Gudang Box
        self.box_storage_withdraw_frame = tk.LabelFrame(
            container,
            text=" 🚫 Daftar Item Blacklist Tarik Gudang (Ditinggalkan di Gudang) ",
            bg="#222428",
            fg="#f85149",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=10
        )
        self.box_storage_withdraw_frame.pack(fill=tk.BOTH, expand=True)

        btn_bar = tk.Frame(self.box_storage_withdraw_frame, bg="#222428")
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            btn_bar,
            text="✂️ Potong dari Slot Gudang...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            command=lambda: self.crop_icon_dialog(target="storage_withdraw_blacklist", source_area="storage")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="✂️ Potong dari Slot Tas...",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#e1e2e6",
            relief="flat",
            padx=10,
            pady=5,
            command=lambda: self.crop_icon_dialog(target="storage_withdraw_blacklist", source_area="inventory")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="➕ Tambah Gambar...",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#e1e2e6",
            relief="flat",
            padx=10,
            pady=5,
            command=lambda: self.add_whitelist_icon(target="storage_withdraw_blacklist")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="🔄 Refresh",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.refresh_storage_withdraw_blacklist_view
        ).pack(side=tk.LEFT)

        self.storage_withdraw_blacklist_frame = tk.Frame(self.box_storage_withdraw_frame, bg="#161b22", relief="sunken", bd=1)
        self.storage_withdraw_blacklist_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_storage_withdraw_blacklist_view()

    def _on_toggle_storage_withdraw_blacklist(self):
        val = self.var_storage_withdraw_blacklist_enabled.get()
        if "storage_withdraw" not in self.config.data:
            self.config.data["storage_withdraw"] = {}
        self.config.data["storage_withdraw"]["blacklist_enabled"] = val
        self.config.save()
        self.append_log(f"Blacklist Tarik Gudang diatur ke: {'AKTIF' if val else 'NON-AKTIF'}")

    def refresh_storage_withdraw_blacklist_view(self):
        for widget in self.storage_withdraw_blacklist_frame.winfo_children():
            widget.destroy()

        bl_dir = self.config.storage_withdraw_blacklist_dir
        icons = sorted(list(bl_dir.glob("*.png")) + list(bl_dir.glob("*.jpg")), key=lambda p: p.name.lower())

        if hasattr(self, 'box_storage_withdraw_frame'):
            self.box_storage_withdraw_frame.config(text=f" 🚫 Daftar Item Blacklist Tarik Gudang ({len(icons)} Item Terdaftar) ")

        if not icons:
            empty_lbl = tk.Label(
                self.storage_withdraw_blacklist_frame,
                text="Belum ada item dalam Blacklist Tarik Gudang.\nItem di sini tidak akan ditarik dari gudang ke tas.",
                bg="#161b22",
                fg="#8b949e",
                pady=30
            )
            empty_lbl.pack()
            return

        canvas = tk.Canvas(self.storage_withdraw_blacklist_frame, bg="#161b22", highlightthickness=0)
        scroll = tk.Scrollbar(self.storage_withdraw_blacklist_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#161b22")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._storage_withdraw_bl_images = []
        for p in icons:
            row = tk.Frame(scrollable_frame, bg="#21262d", pady=3, padx=6)
            row.pack(fill=tk.X, padx=6, pady=3)

            try:
                pil_img = Image.open(p).resize((32, 32), Image.Resampling.NEAREST)
                tk_img = ImageTk.PhotoImage(pil_img)
                self._storage_withdraw_bl_images.append(tk_img)

                img_lbl = tk.Label(row, image=tk_img, bg="#21262d")
                img_lbl.pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass

            name_lbl = tk.Label(row, text=p.stem, font=("Segoe UI", 9, "bold"), bg="#21262d", fg="#e1e2e6")
            name_lbl.pack(side=tk.LEFT)

            badge = tk.Label(row, text=" [Ditinggal di Gudang] ", font=("Segoe UI", 7, "bold"), bg="#d29922", fg="#0d1117", padx=4, pady=1)
            badge.pack(side=tk.LEFT, padx=(8, 0))

            del_btn = tk.Button(
                row,
                text="Hapus",
                font=("Segoe UI", 8),
                bg="#30363d",
                fg="#e1e2e6",
                relief="flat",
                command=lambda path=p: self.delete_storage_withdraw_blacklist_icon(path)
            )
            del_btn.pack(side=tk.RIGHT)

    def delete_storage_withdraw_blacklist_icon(self, path: Path):
        if messagebox.askyesno("Konfirmasi", f"Hapus '{path.name}' dari Blacklist Tarik Gudang?"):
            try:
                path.unlink()
                self.refresh_storage_withdraw_blacklist_view()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus: {e}")


    # =========================================================================
    # TAB 5: Blacklist Jual Merchant NPC
    # =========================================================================
    def _build_whitelist_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_whitelist)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        wrap_val = 450 if self.is_compact_mode else 840
        desc_compact = (
            "Aturan Jual ke Merchant NPC:\n"
            "• 🚫 Blacklist: Item di daftar TIDAK dijual (aman di tas).\n"
            "• ⚡ Item Lain: Langsung dijual ke toko NPC."
        )
        desc_normal = (
            "Daftar item yang TIDAK BOLEH dijual ke Merchant NPC (Blacklist Toko):\n"
            "• 🚫 BLACKLIST JUAL NPC: Item di daftar ini TIDAK AKAN dijual (tetap aman di tas, misal: Potion, Gear utama).\n"
            "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan langsung dijual ke toko dan dikonfirmasi dengan tombol Enter."
        )
        desc = tk.Label(
            container,
            text=desc_compact if self.is_compact_mode else desc_normal,
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT,
            wraplength=wrap_val
        )
        desc.pack(anchor=tk.W, pady=(0, 10))
        self._responsive_labels.append((desc, desc_compact, desc_normal))

        self.box_merchant_frame = tk.LabelFrame(
            container,
            text=" 🚫 Daftar Item Blacklist Jual NPC (Ditinggalkan di Tas) ",
            bg="#222428",
            fg="#f85149",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=10
        )
        self.box_merchant_frame.pack(fill=tk.BOTH, expand=True)

        bar = tk.Frame(self.box_merchant_frame, bg="#222428")
        bar.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            bar,
            text="✂️ Potong Ikon dari Slot Tas...",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            command=lambda: self.crop_icon_dialog(target="merchant")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bar,
            text="🔄 Refresh",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.refresh_whitelist_view
        ).pack(side=tk.LEFT)

        self.whitelist_frame = tk.Frame(self.box_merchant_frame, bg="#161b22", relief="sunken", bd=1)
        self.whitelist_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_whitelist_view()

    def refresh_whitelist_view(self):
        for widget in self.whitelist_frame.winfo_children():
            widget.destroy()

        merchant_bl_dir = self.config.merchant_blacklist_dir
        icons = sorted(list(merchant_bl_dir.glob("*.png")) + list(merchant_bl_dir.glob("*.jpg")), key=lambda p: p.name.lower())

        if hasattr(self, 'box_merchant_frame'):
            self.box_merchant_frame.config(text=f" 🚫 Daftar Item Blacklist Jual NPC ({len(icons)} Item Terdaftar) ")

        if not icons:
            empty_lbl = tk.Label(
                self.whitelist_frame,
                text="Belum ada item dalam Blacklist Jual NPC.\nItem di sini tidak akan dijual ke toko (tetap aman di tas).",
                bg="#161b22",
                fg="#8b949e",
                pady=40
            )
            empty_lbl.pack()
            return

        canvas = tk.Canvas(self.whitelist_frame, bg="#161b22", highlightthickness=0)
        scroll = tk.Scrollbar(self.whitelist_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#161b22")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._icon_images = []
        for p in icons:
            row = tk.Frame(scrollable_frame, bg="#21262d", pady=4, padx=8)
            row.pack(fill=tk.X, padx=8, pady=4)

            try:
                pil_img = Image.open(p).resize((36, 36), Image.Resampling.NEAREST)
                tk_img = ImageTk.PhotoImage(pil_img)
                self._icon_images.append(tk_img)

                img_lbl = tk.Label(row, image=tk_img, bg="#21262d")
                img_lbl.pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass

            name_lbl = tk.Label(row, text=p.stem, font=("Segoe UI", 10, "bold"), bg="#21262d", fg="#e1e2e6")
            name_lbl.pack(side=tk.LEFT)

            badge = tk.Label(row, text=" [Ditinggal di Tas] ", font=("Segoe UI", 7, "bold"), bg="#da3633", fg="#ffffff", padx=4, pady=1)
            badge.pack(side=tk.LEFT, padx=(8, 0))

            del_btn = tk.Button(
                row,
                text="Hapus",
                font=("Segoe UI", 8),
                bg="#30363d",
                fg="#e1e2e6",
                relief="flat",
                command=lambda path=p: self.delete_whitelist_icon(path)
            )
            del_btn.pack(side=tk.RIGHT)

    def delete_whitelist_icon(self, path: Path):
        if messagebox.askyesno("Konfirmasi", f"Hapus '{path.name}' dari Blacklist Jual NPC?"):
            try:
                path.unlink()
                self.refresh_whitelist_view()
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus: {e}")

    def _get_target_dir_and_title(self, target: str):
        if target == "storage_withdraw_blacklist":
            return self.config.storage_withdraw_blacklist_dir, "Blacklist Tarik Gudang"
        elif target == "storage_blacklist":
            return self.config.storage_blacklist_dir, "Blacklist Simpan Gudang"
        else:
            return self.config.merchant_blacklist_dir, "Blacklist Jual NPC"

    def _get_unique_save_path(self, target_dir: Path, base_name: str, ext: str = ".png") -> Path:
        """
        Generates a non-overwriting file path.
        If 'base_name.png' exists, produces 'base_name_2.png', 'base_name_3.png', etc.
        Ensures existing blacklist items are never overwritten when adding new ones.
        """
        clean_name = base_name.strip()
        if clean_name.lower().endswith(ext.lower()):
            clean_name = clean_name[:-len(ext)]
        if not clean_name:
            clean_name = "item"

        candidate = target_dir / f"{clean_name}{ext}"
        if not candidate.exists():
            return candidate

        idx = 2
        while True:
            candidate = target_dir / f"{clean_name}_{idx}{ext}"
            if not candidate.exists():
                return candidate
            idx += 1

    def add_whitelist_icon(self, target: str = "storage_blacklist"):
        target_dir, target_name = self._get_target_dir_and_title(target)

        f = filedialog.askopenfilename(
            title=f"Pilih Gambar Ikon Item ({target_name})",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if f:
            src = Path(f)
            dest = self._get_unique_save_path(target_dir, src.stem, src.suffix or ".png")
            try:
                im = Image.open(src)
                im.save(dest)
                if target == "storage_withdraw_blacklist":
                    self.refresh_storage_withdraw_blacklist_view()
                elif target == "storage_blacklist":
                    self.refresh_storage_blacklist_view()
                else:
                    self.refresh_whitelist_view()
                self.append_log(f"Ikon ditambahkan ke {target_name}: '{dest.name}'.")
                messagebox.showinfo("Sukses", f"Ikon '{dest.name}' berhasil ditambahkan ke {target_name}!\n(Data bertambah tanpa menimpa file lama)")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan ikon: {e}")

    def crop_icon_dialog(self, target: str = "storage_blacklist", source_area: str = "inventory"):
        target_dir, target_name = self._get_target_dir_and_title(target)

        is_storage_src = (source_area == "storage")
        if is_storage_src:
            store_cfg = self.config.get("storage", {})
            cols = int(store_cfg.get("cols", 10))
            rows = int(store_cfg.get("rows", 12))
            source_label = "Gudang (Storage)"
        else:
            inv_cfg = self.config.get("inventory", {})
            cols = int(inv_cfg.get("cols", 6))
            rows = int(inv_cfg.get("rows", 4))
            source_label = "Tas (Inventory)"

        win = tk.Toplevel(self)
        win.title(f"Potong Ikon Slot {source_label} ({target_name})")
        win.geometry("450x390")
        win.configure(bg="#222428")
        win.resizable(False, False)

        tk.Label(
            win,
            text=f"Potong Ikon dari Slot {source_label}\n({target_name})",
            font=("Segoe UI", 11, "bold"),
            bg="#222428",
            fg="#58a6ff"
        ).pack(pady=(12, 4))

        tk.Label(
            win,
            text=f"Grid {source_label} Terkalibrasi: {cols} Kolom x {rows} Baris ({cols * rows} Slot)",
            font=("Segoe UI", 8),
            bg="#222428",
            fg="#8b949e"
        ).pack(pady=(0, 8))

        f_grid = tk.Frame(win, bg="#222428")
        f_grid.pack(pady=4)

        tk.Label(f_grid, text=f"Kolom (1 - {cols}):", bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=0, column=0, padx=5, pady=4, sticky=tk.W)
        col_entry = tk.Entry(f_grid, width=8, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", font=("Segoe UI", 9))
        col_entry.insert(0, "1")
        col_entry.grid(row=0, column=1, padx=5, pady=4)

        tk.Label(f_grid, text=f"Baris (1 - {rows}):", bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=1, column=0, padx=5, pady=4, sticky=tk.W)
        row_entry = tk.Entry(f_grid, width=8, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", font=("Segoe UI", 9))
        row_entry.insert(0, "1")
        row_entry.grid(row=1, column=1, padx=5, pady=4)

        tk.Label(f_grid, text="Nama Item:", bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=2, column=0, padx=5, pady=4, sticky=tk.W)
        name_entry = tk.Entry(f_grid, width=18, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", font=("Segoe UI", 9))
        name_entry.insert(0, "item_baru")
        name_entry.grid(row=2, column=1, padx=5, pady=4)

        # Preview Container
        f_prev = tk.Frame(win, bg="#161b22", padx=10, pady=8, relief="ridge", bd=1)
        f_prev.pack(pady=8)

        lbl_img_prev = tk.Label(f_prev, text="[ Belum ada preview ]", bg="#161b22", fg="#8b949e", width=22, height=3)
        lbl_img_prev.pack()

        lbl_status = tk.Label(win, text="Klik 'Ambil / Preview' untuk melihat gambar slot dari game.", font=("Segoe UI", 8), bg="#222428", fg="#8b949e")
        lbl_status.pack(pady=(0, 8))

        current_crop = [None]
        preview_tk = [None]

        def get_active_crop():
            try:
                c = int(col_entry.get().strip()) - 1
                r = int(row_entry.get().strip()) - 1
                if not (0 <= c < cols and 0 <= r < rows):
                    messagebox.showwarning("Rentang Tidak Valid", f"Kolom harus 1..{cols} dan Baris harus 1..{rows}!")
                    return None

                if not self.wm.hwnd:
                    self.wm.find_window()

                if not self.wm.hwnd and sys.platform == "win32":
                    messagebox.showerror("Game Tidak Ditemukan", "Jendela game Tantra belum terdeteksi!\nPastikan game berjalan di layar atau pilih di tombol 'Cek Jendela Game'.")
                    return None

                # Activate game window and wait for DWM render
                self.wm.activate_window()
                time.sleep(0.35)

                client_img = self.screen.capture_client()
                if is_storage_src:
                    crop = self.bot.get_storage_slot_crop(client_img, c, r)
                else:
                    crop = self.bot.get_inventory_slot_crop(client_img, c, r)
                return crop
            except Exception as ex:
                messagebox.showerror("Error", f"Gagal mengambil slot: {ex}")
                return None

        def do_preview():
            crop = get_active_crop()
            if crop is None:
                return

            current_crop[0] = crop
            is_empty = self.matcher.is_slot_empty(crop)

            # Resize for clear visual display
            disp_crop = crop.resize((48, 48), Image.Resampling.NEAREST)
            tk_img = ImageTk.PhotoImage(disp_crop)
            preview_tk[0] = tk_img
            lbl_img_prev.config(image=tk_img, text="", width=48, height=48)

            if is_empty:
                lbl_status.config(text="⚠️ Slot terdeteksi KOSONG / Blank. Pastikan slot ada isinya!", fg="#f85149")
            else:
                lbl_status.config(text="✓ Ikon item berhasil tertangkap!", fg="#3fb950")

        def do_save():
            if current_crop[0] is None:
                do_preview()
            if current_crop[0] is None:
                return

            c = int(col_entry.get().strip())
            r = int(row_entry.get().strip())
            name = name_entry.get().strip() or f"item_c{c}_r{r}"

            save_path = self._get_unique_save_path(target_dir, name, ".png")
            current_crop[0].save(save_path)

            if target == "storage_withdraw_blacklist":
                self.refresh_storage_withdraw_blacklist_view()
            elif target == "storage_blacklist":
                self.refresh_storage_blacklist_view()
            else:
                self.refresh_whitelist_view()

            win.destroy()
            self.append_log(f"✂️ Ikon [{r},{c}] disimpan ke {target_name}: '{save_path.name}'.")
            messagebox.showinfo(
                "Sukses",
                f"Berhasil memotong ikon slot [{r},{c}] dan disimpan ke '{target_name}' sebagai:\n\n"
                f"📄 {save_path.name}\n\n"
                f"✓ Data item lama tidak tertimpa dan jumlah blacklist berhasil bertambah!"
            )

        btn_bar = tk.Frame(win, bg="#222428")
        btn_bar.pack(pady=4)

        tk.Button(
            btn_bar,
            text="🔍 Ambil / Preview Slot",
            bg="#1f6feb",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=5,
            command=do_preview
        ).pack(side=tk.LEFT, padx=6)

        tk.Button(
            btn_bar,
            text="💾 Simpan Ikon",
            bg="#238636",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=5,
            command=do_save
        ).pack(side=tk.LEFT, padx=6)

    # =========================================================================
    # TAB 6: Auto Skill (Smart Combo & Timer Interval)
    # =========================================================================
    def _build_skill_tab(self):
        container = tk.Frame(self.tab_skill, bg="#222428", padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(container, bg="#161b22", padx=12, pady=10, relief="ridge", bd=1)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        skill_cfg = self.config.get("auto_skill", DEFAULT_SKILL_CONFIG)
        self.var_skill_enabled = tk.BooleanVar(value=skill_cfg.get("enabled", True))
        self.var_skill_sync_hunt = tk.BooleanVar(value=skill_cfg.get("sync_with_auto_hunt", True))
        self.var_skill_mode = tk.StringVar(value=skill_cfg.get("mode", "smart_combo"))
        self.var_skill_combo_interval = tk.StringVar(value=str(skill_cfg.get("combo_check_interval_sec", 0.05)))

        tk.Checkbutton(
            top_frame,
            text="⚡ Aktifkan Fitur Auto Skill",
            variable=self.var_skill_enabled,
            bg="#161b22",
            fg="#58a6ff",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W)

        tk.Checkbutton(
            top_frame,
            text="⚔️ Jalankan Auto Skill otomatis saat Mode Auto Hunt berjalan",
            variable=self.var_skill_sync_hunt,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W, pady=(2, 6))

        # Mode Selection Bar (2-row layout: Row 1 Header, Row 2 Options)
        mode_box = tk.Frame(top_frame, bg="#0d1117", padx=8, pady=6, relief="groove", bd=1)
        mode_box.pack(fill=tk.X, pady=(2, 6))

        mode_header_row = tk.Frame(mode_box, bg="#0d1117")
        mode_header_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            mode_header_row,
            text="Pilih Mode Auto Skill:",
            bg="#0d1117",
            fg="#d29922",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        mode_opts_row = tk.Frame(mode_box, bg="#0d1117")
        mode_opts_row.pack(fill=tk.X)

        tk.Radiobutton(
            mode_opts_row,
            text="🎯 Smart Combo (Cooldown Deteksi & Rotasi)",
            variable=self.var_skill_mode,
            value="smart_combo",
            command=self._on_skill_mode_changed,
            bg="#0d1117",
            fg="#58a6ff",
            selectcolor="#161b22",
            activebackground="#0d1117",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 14))

        tk.Radiobutton(
            mode_opts_row,
            text="⏱️ Timer Interval (Spam berkala)",
            variable=self.var_skill_mode,
            value="timer_interval",
            command=self._on_skill_mode_changed,
            bg="#0d1117",
            fg="#c9d1d9",
            selectcolor="#161b22",
            activebackground="#0d1117",
            activeforeground="#c9d1d9",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        btn_bar = tk.Frame(top_frame, bg="#161b22")
        btn_bar.pack(fill=tk.X)

        tk.Button(
            btn_bar,
            text="💾 Simpan Skill",
            font=("Segoe UI", 8, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=self._save_skill_settings
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="🔄 Reset Status",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self._reset_skill_timers
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="🔍 Test Cooldown",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=self._test_detect_combo_skills
        ).pack(side=tk.LEFT)

        # -------------------------------------------------------------
        # Target Monster Awareness (Hold skill when no target)
        # -------------------------------------------------------------
        tgt_cfg = skill_cfg.get("target_monster") or DEFAULT_SKILL_CONFIG.get("target_monster", {})
        self.var_target_monster_enabled = tk.BooleanVar(value=tgt_cfg.get("enabled", True))

        target_frame = tk.LabelFrame(
            container,
            text=" 🎯 Deteksi Target Monster (Cegah Spam Skill saat Target Kosong) ",
            bg="#161b22",
            fg="#e3b341",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
            relief="ridge",
            bd=1
        )
        target_frame.pack(fill=tk.X, pady=(0, 6))

        # Row 1: Checkbox + Live Status Badge
        tgt_r1 = tk.Frame(target_frame, bg="#161b22")
        tgt_r1.pack(fill=tk.X, pady=(0, 4))

        tk.Checkbutton(
            tgt_r1,
            text="Tahan Skill jika Target Kosong (Hanya serang saat ada target)",
            variable=self.var_target_monster_enabled,
            bg="#161b22",
            fg="#58a6ff",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT)

        self.lbl_target_monster_live = tk.Label(
            tgt_r1,
            text="[STOPPED]",
            bg="#161b22",
            fg="#8b949e",
            font=("Segoe UI", 8, "bold")
        )
        self.lbl_target_monster_live.pack(side=tk.RIGHT, padx=4)

        # Row 2: Calibration, Area Info, & Test Button
        tgt_r2 = tk.Frame(target_frame, bg="#161b22")
        tgt_r2.pack(fill=tk.X)

        tk.Button(
            tgt_r2,
            text="🎯 Kalibrasi Kotak Target",
            font=("Segoe UI", 8, "bold"),
            bg="#8957e5",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self.calibrate_target_monster_area
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_target_monster_info = tk.Label(
            tgt_r2,
            text="Kotak: -",
            bg="#161b22",
            fg="#8b949e",
            font=("Consolas", 8)
        )
        self.lbl_target_monster_info.pack(side=tk.LEFT, padx=(0, 10))
        self._update_target_monster_label()

        tk.Button(
            tgt_r2,
            text="🔍 Test Cek Target Sekarang",
            font=("Segoe UI", 8),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self._test_detect_target_monster
        ).pack(side=tk.LEFT)

        # -------------------------------------------------------------
        # Basic Hunting Actions (E, R, F)
        # -------------------------------------------------------------
        hunt_keys_cfg = skill_cfg.get("hunt_keys") or DEFAULT_SKILL_CONFIG.get("hunt_keys", {})
        e_cfg = hunt_keys_cfg.get("e", {})
        r_cfg = hunt_keys_cfg.get("r", {})
        f_cfg = hunt_keys_cfg.get("f", {})

        self.var_hunt_e_en = tk.BooleanVar(value=e_cfg.get("enabled", True))
        self.var_hunt_e_interval = tk.StringVar(value=str(e_cfg.get("interval", 1.5)))
        self.var_hunt_r_en = tk.BooleanVar(value=r_cfg.get("enabled", True))
        self.var_hunt_r_interval = tk.StringVar(value=str(r_cfg.get("interval", 0.8)))
        self.var_hunt_f_en = tk.BooleanVar(value=f_cfg.get("enabled", True))
        self.var_hunt_f_interval = tk.StringVar(value=str(f_cfg.get("interval", 1.0)))

        hunt_frame = tk.LabelFrame(
            container,
            text=" 🗡️ Aksi Hunting Dasar (E: Target, R: Serang, F: Pick Loot) ",
            bg="#161b22",
            fg="#e3b341",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=6,
            relief="ridge",
            bd=1
        )
        hunt_frame.pack(fill=tk.X, pady=(0, 8))

        hunt_inner = tk.Frame(hunt_frame, bg="#161b22")
        hunt_inner.pack(fill=tk.X)

        def make_hunt_col(parent, label_compact, label_normal, var_en, var_sec, cd_attr_name):
            col = tk.Frame(parent, bg="#161b22")
            col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

            cb_text = label_compact if self.is_compact_mode else label_normal
            cb = tk.Checkbutton(
                col,
                text=cb_text,
                variable=var_en,
                bg="#161b22",
                fg="#58a6ff",
                selectcolor="#0d1117",
                activebackground="#161b22",
                activeforeground="#58a6ff",
                font=("Segoe UI", 8, "bold")
            )
            cb.pack(side=tk.LEFT, padx=(0, 2))
            self._responsive_checkbuttons.append((cb, label_compact, label_normal))

            ent = tk.Entry(col, textvariable=var_sec, width=4, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Consolas", 8))
            ent.pack(side=tk.LEFT, padx=(0, 3))

            lbl_sec = tk.Label(col, text="s", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8))
            lbl_sec.pack(side=tk.LEFT, padx=(0, 3))

            lbl_cd = tk.Label(col, text="-", bg="#161b22", fg="#8b949e", font=("Consolas", 8, "bold"), width=5, anchor=tk.W)
            lbl_cd.pack(side=tk.LEFT)
            setattr(self, cd_attr_name, lbl_cd)

        make_hunt_col(hunt_inner, "🎯 E", "🎯 Target (E)", self.var_hunt_e_en, self.var_hunt_e_interval, "lbl_hunt_e_cd")
        make_hunt_col(hunt_inner, "⚔️ R", "⚔️ Serang (R)", self.var_hunt_r_en, self.var_hunt_r_interval, "lbl_hunt_r_cd")
        make_hunt_col(hunt_inner, "📦 F", "📦 Pick Loot (F)", self.var_hunt_f_en, self.var_hunt_f_interval, "lbl_hunt_f_cd")

        # Body container
        self.skill_body_container = tk.Frame(container, bg="#222428")
        self.skill_body_container.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------------
        # 1. SMART COMBO MODE VIEW (Combo Serang & Auto Buff)
        # -------------------------------------------------------------
        self.frame_combo_mode = tk.Frame(self.skill_body_container, bg="#222428")

        self.combo_notebook = ttk.Notebook(self.frame_combo_mode)
        self.tab_combo_attack = tk.Frame(self.combo_notebook, bg="#222428")
        self.tab_combo_buff = tk.Frame(self.combo_notebook, bg="#222428")
        self.combo_notebook.add(self.tab_combo_attack, text=" ⚔️ Combo Skill Serang ")
        self.combo_notebook.add(self.tab_combo_buff, text=" 🛡️ Auto Buff (Floating Bar) ")
        self.combo_notebook.pack(fill=tk.BOTH, expand=True)

        # --- SUB-TAB 1: COMBO SERANG ---
        combo_bar_ctrl = tk.Frame(self.tab_combo_attack, bg="#161b22", padx=10, pady=8, relief="ridge", bd=1)
        combo_bar_ctrl.pack(fill=tk.X, pady=(0, 6))

        # Row 1: Kalibrasi bar & label info
        cbar_r1 = tk.Frame(combo_bar_ctrl, bg="#161b22")
        cbar_r1.pack(fill=tk.X, pady=(0, 4))

        bar_btn = tk.Button(
            cbar_r1,
            text="🎯 Kalibrasi Bar Skill (10 Slot)",
            font=("Segoe UI", 8, "bold"),
            bg="#8957e5",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self.calibrate_quickslot_bar
        )
        bar_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_quickslot_bar_info = tk.Label(
            cbar_r1,
            text="Bar: -",
            bg="#161b22",
            fg="#8b949e",
            font=("Consolas", 8)
        )
        self.lbl_quickslot_bar_info.pack(side=tk.LEFT)
        self._update_quickslot_bar_label()

        # Row 2: Tambah skill & interval
        cbar_r2 = tk.Frame(combo_bar_ctrl, bg="#161b22")
        cbar_r2.pack(fill=tk.X)

        tk.Button(
            cbar_r2,
            text="➕ Tambah Skill ke Combo",
            font=("Segoe UI", 8, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self._add_combo_skill
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            cbar_r2,
            text="Interval Cek (detik):",
            bg="#161b22",
            fg="#8b949e",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Entry(
            cbar_r2,
            textvariable=self.var_skill_combo_interval,
            width=5,
            bg="#0d1117",
            fg="#e1e2e6",
            insertbackground="#ffffff",
            font=("Consolas", 8)
        ).pack(side=tk.LEFT)

        guide_lbl = tk.Label(
            self.tab_combo_attack,
            text="💡 Rotasi combo dicek berurutan (1 ➔ 2 ➔ 3...). Jika skill Cooldown (gelap), otomatis dilewati ke skill berikutnya.",
            bg="#222428",
            fg="#7ee787",
            font=("Segoe UI", 8, "italic")
        )
        guide_lbl.pack(anchor=tk.W, pady=(0, 6))

        canvas_combo = tk.Canvas(self.tab_combo_attack, bg="#222428", highlightthickness=0)
        scroll_combo = tk.Scrollbar(self.tab_combo_attack, orient="vertical", command=canvas_combo.yview)
        self.frame_combo_list = tk.Frame(canvas_combo, bg="#222428")

        self.frame_combo_list.bind("<Configure>", lambda e: canvas_combo.configure(scrollregion=canvas_combo.bbox("all")))
        canvas_combo.create_window((0, 0), window=self.frame_combo_list, anchor="nw")
        canvas_combo.configure(yscrollcommand=scroll_combo.set)

        canvas_combo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_combo.pack(side=tk.RIGHT, fill=tk.Y)

        self._combo_thumbnails = []
        self._combo_row_vars = []
        self._combo_status_labels = []

        # --- SUB-TAB 2: AUTO BUFF ---
        buffs_cfg = skill_cfg.get("buffs") or DEFAULT_SKILL_CONFIG.get("buffs", {})
        self.var_buff_enabled = tk.BooleanVar(value=buffs_cfg.get("enabled", True))
        self.var_buff_check_interval = tk.StringVar(value=str(buffs_cfg.get("check_interval_sec", 0.5)))

        buff_bar_ctrl = tk.Frame(self.tab_combo_buff, bg="#161b22", padx=10, pady=8, relief="ridge", bd=1)
        buff_bar_ctrl.pack(fill=tk.X, pady=(0, 6))

        # Row 1: Checkbox & Calibration & Area Info
        bbar_r1 = tk.Frame(buff_bar_ctrl, bg="#161b22")
        bbar_r1.pack(fill=tk.X, pady=(0, 4))

        tk.Checkbutton(
            bbar_r1,
            text="🛡️ Aktifkan Auto Buff",
            variable=self.var_buff_enabled,
            bg="#161b22",
            fg="#7ee787",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#7ee787",
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bbar_r1,
            text="🎯 Kalibrasi Floating Area",
            font=("Segoe UI", 8, "bold"),
            bg="#8957e5",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self.calibrate_floating_buff_area
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_floating_buff_info = tk.Label(
            bbar_r1,
            text="Floating Area: -",
            bg="#161b22",
            fg="#8b949e",
            font=("Consolas", 8)
        )
        self.lbl_floating_buff_info.pack(side=tk.LEFT)
        self._update_floating_buff_label()

        # Row 2: Tambah buff, interval & test
        bbar_r2 = tk.Frame(buff_bar_ctrl, bg="#161b22")
        bbar_r2.pack(fill=tk.X)

        tk.Button(
            bbar_r2,
            text="➕ Tambah Buff",
            font=("Segoe UI", 8, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self._add_buff_item
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            bbar_r2,
            text="Interval (s):",
            bg="#161b22",
            fg="#8b949e",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(0, 2))

        tk.Entry(
            bbar_r2,
            textvariable=self.var_buff_check_interval,
            width=5,
            bg="#0d1117",
            fg="#e1e2e6",
            insertbackground="#ffffff",
            font=("Consolas", 8)
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bbar_r2,
            text="🔍 Test Cek Floating Buff",
            font=("Segoe UI", 8),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=8,
            pady=3,
            command=self._test_detect_buffs
        ).pack(side=tk.LEFT)

        buff_guide_lbl = tk.Label(
            self.tab_combo_buff,
            text="💡 Macro memonitor icon di Floating Buff Area. Jika icon buff hilang dari layar (durasi habis), skill buff otomatis di-cast ulang.",
            bg="#222428",
            fg="#7ee787",
            font=("Segoe UI", 8, "italic")
        )
        buff_guide_lbl.pack(anchor=tk.W, pady=(0, 6))

        canvas_buff = tk.Canvas(self.tab_combo_buff, bg="#222428", highlightthickness=0)
        scroll_buff = tk.Scrollbar(self.tab_combo_buff, orient="vertical", command=canvas_buff.yview)
        self.frame_buff_list = tk.Frame(canvas_buff, bg="#222428")

        self.frame_buff_list.bind("<Configure>", lambda e: canvas_buff.configure(scrollregion=canvas_buff.bbox("all")))
        canvas_buff.create_window((0, 0), window=self.frame_buff_list, anchor="nw")
        canvas_buff.configure(yscrollcommand=scroll_buff.set)

        canvas_buff.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_buff.pack(side=tk.RIGHT, fill=tk.Y)

        self._buff_thumbnails = []
        self._buff_row_vars = []
        self._buff_status_labels = []

        # -------------------------------------------------------------
        # 2. TIMER INTERVAL MODE VIEW
        # -------------------------------------------------------------
        self.frame_timer_mode = tk.Frame(self.skill_body_container, bg="#222428")

        canvas_timer = tk.Canvas(self.frame_timer_mode, bg="#222428", highlightthickness=0)
        scroll_timer = tk.Scrollbar(self.frame_timer_mode, orient="vertical", command=canvas_timer.yview)
        scrollable_timer_frame = tk.Frame(canvas_timer, bg="#222428")

        scrollable_timer_frame.bind("<Configure>", lambda e: canvas_timer.configure(scrollregion=canvas_timer.bbox("all")))
        canvas_timer.create_window((0, 0), window=scrollable_timer_frame, anchor="nw")
        canvas_timer.configure(yscrollcommand=scroll_timer.set)

        canvas_timer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_timer.pack(side=tk.RIGHT, fill=tk.Y)

        self.skill_vars = {}
        keys_cfg = skill_cfg.get("keys", {})

        def make_section(title, pairs):
            sec_frame = tk.LabelFrame(scrollable_timer_frame, text=f" {title} ", bg="#222428", fg="#d29922", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
            sec_frame.pack(fill=tk.X, pady=(0, 8))

            col_left = tk.Frame(sec_frame, bg="#222428")
            col_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            col_right = tk.Frame(sec_frame, bg="#222428")
            col_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            def add_header(parent):
                hdr = tk.Frame(parent, bg="#222428", pady=2)
                hdr.pack(fill=tk.X)
                tk.Label(hdr, text="Key", bg="#222428", fg="#8b949e", font=("Segoe UI", 8, "bold"), width=5, anchor=tk.W).pack(side=tk.LEFT)
                tk.Label(hdr, text="Detik", bg="#222428", fg="#8b949e", font=("Segoe UI", 8, "bold"), width=9, anchor=tk.W).pack(side=tk.LEFT)
                tk.Label(hdr, text="Countdown", bg="#222428", fg="#58a6ff", font=("Segoe UI", 8, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT)

            add_header(col_left)
            add_header(col_right)

            def add_key_row(parent, key_name):
                row = tk.Frame(parent, bg="#222428", pady=2)
                row.pack(fill=tk.X)

                k_info = keys_cfg.get(key_name, {})
                var_en = tk.BooleanVar(value=k_info.get("enabled", False))
                var_sec = tk.StringVar(value=str(k_info.get("interval", 10.0)))

                cb = tk.Checkbutton(
                    row,
                    text=f"{key_name.upper()}",
                    variable=var_en,
                    bg="#222428",
                    fg="#e1e2e6",
                    selectcolor="#161b22",
                    activebackground="#222428",
                    activeforeground="#58a6ff",
                    font=("Segoe UI", 9, "bold"),
                    width=4,
                    anchor=tk.W
                )
                cb.pack(side=tk.LEFT)

                tk.Label(row, text="Sec:", bg="#222428", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 2))
                entry = tk.Entry(row, textvariable=var_sec, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", width=6, font=("Consolas", 9))
                entry.pack(side=tk.LEFT, padx=(0, 6))

                lbl_countdown = tk.Label(row, text="-", bg="#222428", fg="#8b949e", font=("Consolas", 9, "bold"), width=8, anchor=tk.W)
                lbl_countdown.pack(side=tk.LEFT)

                self.skill_vars[key_name] = {
                    "enabled": var_en,
                    "interval": var_sec,
                    "lbl_countdown": lbl_countdown
                }

            for left_k, right_k in pairs:
                if left_k:
                    add_key_row(col_left, left_k)
                if right_k:
                    add_key_row(col_right, right_k)

        # 1. NUMBER KEYS
        make_section(
            "NUMBER KEYS (1 - 5 kiri | 6 - 0 kanan)",
            [("1", "6"), ("2", "7"), ("3", "8"), ("4", "9"), ("5", "0")]
        )

        # 2. FUNCTION KEYS
        make_section(
            "FUNCTION KEYS (F1 - F5 kiri | F6 - F10 kanan)",
            [("f1", "f6"), ("f2", "f7"), ("f3", "f8"), ("f4", "f9"), ("f5", "f10")]
        )

        # Render combo & buff items initially
        self._render_combo_items()
        self._render_buff_items()

        # Show appropriate view based on initial mode
        self._on_skill_mode_changed()

        # Start countdown / status updater
        self.after(100, self._update_skill_countdowns)

    def _on_skill_mode_changed(self):
        mode = self.var_skill_mode.get()
        if mode == "smart_combo":
            self.frame_timer_mode.pack_forget()
            self.frame_combo_mode.pack(fill=tk.BOTH, expand=True)
        else:
            self.frame_combo_mode.pack_forget()
            self.frame_timer_mode.pack(fill=tk.BOTH, expand=True)

    def _update_quickslot_bar_label(self):
        bar = self.config.get("auto_skill", {}).get("quickslot_bar", {})
        if bar and "x" in bar:
            self.lbl_quickslot_bar_info.config(
                text=f"Bar 2x10 Slot: X={bar.get('x')} Y={bar.get('y')} W={bar.get('w')} H={bar.get('h')}",
                fg="#3fb950"
            )
        else:
            self.lbl_quickslot_bar_info.config(
                text="Bar 2x10 Slot: Belum Dikalibrasi",
                fg="#f85149"
            )

    def _add_combo_skill(self):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.setdefault("auto_skill", {}).setdefault("combo_list", [])
        new_idx = len(combo_list) + 1
        if new_idx <= 10:
            num_k = new_idx if new_idx < 10 else 0
            default_slot_str = f"Atas: Slot {new_idx} ({num_k})"
            default_hk = str(num_k)
        else:
            f_num = min(10, new_idx - 10)
            default_slot_str = f"Bawah: Slot F{f_num}"
            default_hk = f"f{f_num}"

        combo_list.append({
            "id": f"skill_{int(time.time() * 1000)}",
            "name": f"Skill {new_idx}",
            "hotkey": default_hk,
            "slot_str": default_slot_str,
            "slot_index": new_idx,
            "slot_box": None,
            "template_path": "",
            "similarity_threshold": 0.75,
            "brightness_ratio_threshold": 0.70,
            "cast_delay_sec": 0.30,
            "enabled": True
        })
        self._render_combo_items()

    def _delete_combo_item(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
        if 0 <= idx < len(combo_list):
            del combo_list[idx]
            self._render_combo_items()

    def _move_combo_item(self, idx: int, direction: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
        target_idx = idx + direction
        if 0 <= idx < len(combo_list) and 0 <= target_idx < len(combo_list):
            combo_list[idx], combo_list[target_idx] = combo_list[target_idx], combo_list[idx]
            self._render_combo_items()

    def _render_combo_items(self):
        for widget in self.frame_combo_list.winfo_children():
            widget.destroy()

        self._combo_thumbnails = []
        self._combo_row_vars = []
        self._combo_status_labels = []

        combo_list = self.config.get("auto_skill", {}).get("combo_list", [])
        if not combo_list:
            empty_lbl = tk.Label(
                self.frame_combo_list,
                text="Belum ada skill dalam combo list.\nKlik tombol '➕ Tambah Skill ke Combo' di atas untuk memulai.",
                bg="#222428",
                fg="#8b949e",
                font=("Segoe UI", 10),
                pady=20
            )
            empty_lbl.pack()
            return

        hotkey_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "e", "r", "f",
                          "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10"]
        slot_options = [
            "Atas: Slot 1 (1)",
            "Atas: Slot 2 (2)",
            "Atas: Slot 3 (3)",
            "Atas: Slot 4 (4)",
            "Atas: Slot 5 (5)",
            "Atas: Slot 6 (6)",
            "Atas: Slot 7 (7)",
            "Atas: Slot 8 (8)",
            "Atas: Slot 9 (9)",
            "Atas: Slot 10 (0)",
            "Bawah: Slot F1",
            "Bawah: Slot F2",
            "Bawah: Slot F3",
            "Bawah: Slot F4",
            "Bawah: Slot F5",
            "Bawah: Slot F6",
            "Bawah: Slot F7",
            "Bawah: Slot F8",
            "Bawah: Slot F9",
            "Bawah: Slot F10",
            "Custom Area"
        ]

        for idx, item in enumerate(combo_list):
            card = tk.LabelFrame(
                self.frame_combo_list,
                text=f" #{idx + 1} - {item.get('name', f'Skill {idx+1}')} ",
                bg="#161b22",
                fg="#58a6ff",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=6,
                relief="ridge",
                bd=1
            )
            card.pack(fill=tk.X, pady=(0, 6))

            # Row 1: Controls
            r1 = tk.Frame(card, bg="#161b22")
            r1.pack(fill=tk.X, pady=(0, 4))

            var_en = tk.BooleanVar(value=item.get("enabled", True))
            tk.Checkbutton(
                r1,
                text="Aktif",
                variable=var_en,
                bg="#161b22",
                fg="#7ee787",
                selectcolor="#0d1117",
                activebackground="#161b22",
                activeforeground="#7ee787",
                font=("Segoe UI", 8, "bold")
            ).pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(r1, text="Nama:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_name = tk.StringVar(value=item.get("name", f"Skill {idx+1}"))
            tk.Entry(r1, textvariable=var_name, width=10, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 8))

            tk.Label(r1, text="Slot:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            init_slot_str = item.get("slot_str")
            if not init_slot_str or init_slot_str not in slot_options:
                cur_slot = item.get("slot_index", 1)
                cur_hk = str(item.get("hotkey", "")).lower()
                if cur_hk.startswith("f"):
                    init_slot_str = f"Bawah: Slot {cur_hk.upper()}"
                elif 1 <= cur_slot <= 10:
                    num_k = cur_slot if cur_slot < 10 else 0
                    init_slot_str = f"Atas: Slot {cur_slot} ({num_k})"
                else:
                    init_slot_str = "Custom Area"
                if init_slot_str not in slot_options:
                    init_slot_str = "Custom Area"

            var_slot = tk.StringVar(value=init_slot_str)
            cb_slot = ttk.Combobox(r1, textvariable=var_slot, values=slot_options, width=17, state="readonly", font=("Segoe UI", 8))
            cb_slot.pack(side=tk.LEFT, padx=(2, 8))

            tk.Label(r1, text="Hotkey:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_hotkey = tk.StringVar(value=str(item.get("hotkey", "1")).lower())
            cb_hotkey = ttk.Combobox(r1, textvariable=var_hotkey, values=hotkey_options, width=5, state="readonly", font=("Segoe UI", 8))
            cb_hotkey.pack(side=tk.LEFT, padx=(2, 8))

            def _on_slot_change(event, vs=var_slot, vh=var_hotkey):
                val = vs.get()
                if val.startswith("Atas: Slot "):
                    import re
                    m = re.search(r"\((\d+)\)", val)
                    if m:
                        vh.set(m.group(1))
                elif val.startswith("Bawah: Slot "):
                    import re
                    m = re.search(r"(F\d+)", val, re.IGNORECASE)
                    if m:
                        vh.set(m.group(1).lower())
            cb_slot.bind("<<ComboboxSelected>>", _on_slot_change)

            tk.Label(r1, text="Cast Delay (s):", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_delay = tk.StringVar(value=str(item.get("cast_delay_sec", 0.30)))
            tk.Entry(r1, textvariable=var_delay, width=5, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Consolas", 8)).pack(side=tk.LEFT, padx=(2, 8))

            # Move & Delete buttons
            btn_up = tk.Button(r1, text="⬆️", font=("Segoe UI", 7), bg="#30363d", fg="#c9d1d9", relief="flat", padx=4, command=lambda i=idx: self._move_combo_item(i, -1))
            btn_up.pack(side=tk.RIGHT, padx=2)
            btn_down = tk.Button(r1, text="⬇️", font=("Segoe UI", 7), bg="#30363d", fg="#c9d1d9", relief="flat", padx=4, command=lambda i=idx: self._move_combo_item(i, 1))
            btn_down.pack(side=tk.RIGHT, padx=2)
            btn_del = tk.Button(r1, text="🗑️", font=("Segoe UI", 7), bg="#da3633", fg="#ffffff", relief="flat", padx=4, command=lambda i=idx: self._delete_combo_item(i))
            btn_del.pack(side=tk.RIGHT, padx=4)

            # Row 2: Template icon, capture actions, and live status
            r2 = tk.Frame(card, bg="#161b22")
            r2.pack(fill=tk.X, pady=(2, 0))

            # Thumbnail preview
            tpl_path = item.get("template_path", "")
            img_displayed = False
            if tpl_path:
                full_tpl_path = Path(tpl_path) if Path(tpl_path).is_absolute() else Path(self.config.base_dir) / tpl_path
                if full_tpl_path.exists():
                    try:
                        pil_img = Image.open(full_tpl_path).convert("RGB")
                        pil_img.thumbnail((32, 32))
                        tk_thumb = ImageTk.PhotoImage(pil_img)
                        self._combo_thumbnails.append(tk_thumb)
                        lbl_icon = tk.Label(r2, image=tk_thumb, bg="#0d1117", bd=1, relief="solid")
                        lbl_icon.pack(side=tk.LEFT, padx=(0, 6))
                        img_displayed = True
                    except Exception:
                        pass

            if not img_displayed:
                lbl_no_icon = tk.Label(r2, text="[No Icon]", bg="#0d1117", fg="#8b949e", font=("Consolas", 7), width=8, height=2, bd=1, relief="solid")
                lbl_no_icon.pack(side=tk.LEFT, padx=(0, 6))

            tk.Button(
                r2,
                text="📸 Ambil Icon dari Slot",
                font=("Segoe UI", 7, "bold"),
                bg="#238636",
                fg="#ffffff",
                relief="flat",
                padx=6,
                pady=2,
                command=lambda i=idx: self.capture_skill_icon_from_slot(i)
            ).pack(side=tk.LEFT, padx=(0, 4))

            tk.Button(
                r2,
                text="✂️ Crop Manual",
                font=("Segoe UI", 7),
                bg="#30363d",
                fg="#c9d1d9",
                relief="flat",
                padx=6,
                pady=2,
                command=lambda i=idx: self.capture_skill_icon_manual(i)
            ).pack(side=tk.LEFT, padx=(0, 4))

            tk.Button(
                r2,
                text="📍 Kalibrasi Slot Ini",
                font=("Segoe UI", 7),
                bg="#30363d",
                fg="#c9d1d9",
                relief="flat",
                padx=6,
                pady=2,
                command=lambda i=idx: self.calibrate_single_skill_slot(i)
            ).pack(side=tk.LEFT, padx=(0, 10))

            # Slot box / position info
            slot_box = item.get("slot_box")
            if slot_box:
                box_str = f"Box: X={slot_box.get('x')} Y={slot_box.get('y')} W={slot_box.get('w')} H={slot_box.get('h')}"
            else:
                box_str = f"Auto: {init_slot_str}"
            tk.Label(r2, text=box_str, bg="#161b22", fg="#8b949e", font=("Consolas", 7)).pack(side=tk.LEFT, padx=(0, 10))

            # Live status badge
            lbl_status = tk.Label(
                r2,
                text="[READY]" if tpl_path else "[BELUM DI-CAPTURE]",
                bg="#161b22",
                fg="#3fb950" if tpl_path else "#8b949e",
                font=("Segoe UI", 8, "bold")
            )
            lbl_status.pack(side=tk.RIGHT, padx=4)
            self._combo_status_labels.append(lbl_status)

            self._combo_row_vars.append({
                "id": item.get("id", f"skill_{idx+1}"),
                "enabled": var_en,
                "name": var_name,
                "slot_str": var_slot,
                "hotkey": var_hotkey,
                "delay": var_delay,
                "slot_box": slot_box,
                "template_path": tpl_path,
                "similarity_threshold": item.get("similarity_threshold", 0.75),
                "brightness_ratio_threshold": item.get("brightness_ratio_threshold", 0.70)
            })

    def calibrate_quickslot_bar(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(10, x2 - x1)
            h = max(10, y2 - y1)
            if "auto_skill" not in self.config.data:
                self.config.data["auto_skill"] = dict(DEFAULT_SKILL_CONFIG)
            self.config.data["auto_skill"]["quickslot_bar"] = {
                "x": x1, "y": y1, "w": w, "h": h, "cols": 10, "rows": 2
            }
            self.config.save()
            self._update_quickslot_bar_label()
            self.append_log(f"⚡ [Auto Skill] Bar Quickslot (2 Baris x 10 Kolom) dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}.")
            messagebox.showinfo(
                "Kalibrasi Berhasil",
                f"Bar Quickslot (2 Baris x 10 Slot) berhasil disimpan!\nKoordinat: X={x1}, Y={y1}, W={w}, H={h}\n\n"
                f"• Baris Atas: Tombol 1 s/d 0 (10 slot)\n"
                f"• Baris Bawah: Tombol F1 s/d F10 (10 slot)\n\n"
                f"Setiap slot sekarang otomatis terpotong 1 grid (hanya barisnya masing-masing)."
            )

        AreaSelectorWindow(self, "Pilih Seluruh Bar Quickslot (2 Baris x 10 Kolom: Atas 1-0, Bawah F1-F10)", 10, 2, client_img, on_saved)

    def calibrate_single_skill_slot(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(5, x2 - x1)
            h = max(5, y2 - y1)
            combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
            if 0 <= idx < len(combo_list):
                combo_list[idx]["slot_box"] = {"x": x1, "y": y1, "w": w, "h": h}
                self.config.save()
                self._render_combo_items()
                self.append_log(f"⚡ [Auto Skill] Slot #{idx+1} box dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}")
                messagebox.showinfo("Sukses", f"Area Slot #{idx+1} berhasil disimpan:\nX={x1}, Y={y1}, W={w}, H={h}")

        AreaSelectorWindow(self, f"Pilih Kotak Slot untuk Combo #{idx+1}", 1, 1, client_img, on_saved)

    def capture_skill_icon_from_slot(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
        if not (0 <= idx < len(combo_list)):
            return
        item = combo_list[idx]
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        crop_img = self.bot.skills.get_skill_slot_crop(client_img, item)
        if not crop_img:
            messagebox.showwarning(
                "Slot Belum Dikalibrasi",
                f"Kotak slot untuk #{idx+1} belum diketahui.\n"
                f"Silakan Kalibrasi Bar Skill (10 Slot) terlebih dahulu, atau gunakan tombol '✂️ Crop Manual'."
            )
            return

        skills_dir = self.config.skills_dir
        skills_dir.mkdir(parents=True, exist_ok=True)
        filename = f"skill_{item.get('id', f'idx_{idx}')}_{int(time.time())}.png"
        save_path = skills_dir / filename
        crop_img.save(save_path)

        rel_path = f"assets/skills/{filename}"
        item["template_path"] = rel_path
        self.config.save()
        self._render_combo_items()
        self.append_log(f"⚡ [Auto Skill] Icon aktif #{idx+1} berhasil dicapture dari slot ke {rel_path}.")
        messagebox.showinfo("Capture Berhasil", f"Icon aktif #{idx+1} berhasil dicapture!\nTersimpan di: {rel_path}")

    def capture_skill_icon_manual(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
        if not (0 <= idx < len(combo_list)):
            return
        item = combo_list[idx]
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(5, x2 - x1)
            h = max(5, y2 - y1)
            crop_img = client_img.crop(rect)
            skills_dir = self.config.skills_dir
            skills_dir.mkdir(parents=True, exist_ok=True)
            filename = f"skill_{item.get('id', f'idx_{idx}')}_{int(time.time())}.png"
            save_path = skills_dir / filename
            crop_img.save(save_path)

            rel_path = f"assets/skills/{filename}"
            item["template_path"] = rel_path
            item["slot_box"] = {"x": x1, "y": y1, "w": w, "h": h}
            self.config.save()
            self._render_combo_items()
            self.append_log(f"⚡ [Auto Skill] Icon aktif #{idx+1} manual crop berhasil ke {rel_path}.")
            messagebox.showinfo("Capture Berhasil", f"Icon aktif #{idx+1} berhasil disimpan!\nArea Slot: X={x1}, Y={y1}, W={w}, H={h}\nFile: {rel_path}")

        AreaSelectorWindow(self, f"Crop Icon Skill Aktif #{idx+1} (Drag Kotak Icon)", 1, 1, client_img, on_saved)

    def _test_detect_combo_skills(self):
        self._apply_skill_gui_to_config(save_to_disk=False)
        combo_list = self.config.data.get("auto_skill", {}).get("combo_list", [])
        if not combo_list:
            messagebox.showinfo("Info", "Belum ada skill dalam combo list.")
            return

        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        summary_lines = []
        for idx, item in enumerate(combo_list):
            name = item.get("name", f"Skill {idx+1}")
            hotkey = item.get("hotkey", "?")
            tpl_path = item.get("template_path", "")

            if not tpl_path:
                status_str = "BELUM CAPTURE ICON"
                summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
                if idx < len(self._combo_status_labels):
                    self._combo_status_labels[idx].config(text=f"[{status_str}]", fg="#8b949e")
                continue

            crop = self.bot.skills.get_skill_slot_crop(client_img, item)
            if not crop:
                status_str = "SLOT TIDAK DITEMUKAN"
                summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
                if idx < len(self._combo_status_labels):
                    self._combo_status_labels[idx].config(text=f"[{status_str}]", fg="#f85149")
                continue

            tpl_img = self.bot.skills.load_skill_template(tpl_path)
            if not tpl_img:
                status_str = "FILE TEMPLATE HILANG"
                summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
                if idx < len(self._combo_status_labels):
                    self._combo_status_labels[idx].config(text=f"[{status_str}]", fg="#f85149")
                continue

            is_active = self.bot.skills.is_skill_active(client_img, item, tpl_img)
            if is_active:
                status_str = "READY / AKTIF"
                color = "#3fb950"
            else:
                status_str = "COOLDOWN (GELAP)"
                color = "#f85149"

            summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
            if idx < len(self._combo_status_labels):
                self._combo_status_labels[idx].config(text=f"[{status_str}]", fg=color)

        res_text = "\n".join(summary_lines)
        self.append_log(f"⚡ [Auto Skill Test Cooldown]:\n{res_text}")
        messagebox.showinfo("Hasil Cek Cooldown Real-time", f"Hasil deteksi saat ini:\n\n{res_text}")

    # =========================================================================
    # Target Monster Detection Handlers
    # =========================================================================
    def _update_target_monster_label(self):
        area = self.config.get("auto_skill", {}).get("target_monster", {}).get("area", {})
        if area and "x" in area:
            self.lbl_target_monster_info.config(
                text=f"Kotak: X={area.get('x')} Y={area.get('y')} W={area.get('w')} H={area.get('h')}",
                fg="#3fb950"
            )
        else:
            self.lbl_target_monster_info.config(
                text="Kotak: Belum Dikalibrasi",
                fg="#f85149"
            )

    def calibrate_target_monster_area(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(10, x2 - x1)
            h = max(10, y2 - y1)
            if "auto_skill" not in self.config.data:
                self.config.data["auto_skill"] = dict(DEFAULT_SKILL_CONFIG)
            tgt_cfg = self.config.data["auto_skill"].setdefault("target_monster", dict(DEFAULT_SKILL_CONFIG["target_monster"]))
            tgt_cfg["area"] = {
                "x": x1, "y": y1, "w": w, "h": h
            }
            self.config.save()
            self._update_target_monster_label()
            self.append_log(f"🎯 [Target Monster] Kotak target monster dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}.")
            messagebox.showinfo(
                "Kalibrasi Berhasil",
                f"Kotak Target Monster berhasil disimpan!\nKoordinat: X={x1}, Y={y1}, W={w}, H={h}\n\n"
                f"Macro akan memonitor HP bar dan status target di area ini agar tidak spam skill saat target kosong."
            )

        AreaSelectorWindow(self, "Pilih Kotak Target Monster (Tempat Nama & HP Monster Muncul di Layar)", 1, 1, client_img, on_saved)

    def _test_detect_target_monster(self):
        self._apply_skill_gui_to_config(save_to_disk=False)
        tgt_cfg = self.config.data.get("auto_skill", {}).get("target_monster", {})
        area = tgt_cfg.get("area")
        if not area or "x" not in area:
            messagebox.showwarning("Perhatian", "Area Target Monster belum dikalibrasi.\nSilakan klik '🎯 Kalibrasi Kotak Target Monster' terlebih dahulu.")
            return

        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()
        if client_img is None:
            messagebox.showerror("Error", "Gagal mengambil capture layar game.")
            return

        is_targeted = self.bot.skills.has_target_monster(client_img, tgt_cfg)
        if is_targeted:
            res_str = "🎯 TARGET MONSTER TERDETEKSI!\n\nStatus: HP Bar / Frame Target Monster AKTIF.\nSkill akan dieksekusi normal saat kondisi ini."
            self.append_log("🎯 [Test Target Monster]: TARGET TERDETEKSI (HP Bar Monster Aktif).")
            messagebox.showinfo("Hasil Cek Target Monster", res_str)
        else:
            res_str = "⚪ TARGET KOSONG / HILANG.\n\nStatus: Tidak ada target monster yang terdeteksi.\nSkill akan di-HOLD (tidak spam) sampai target monster baru muncul."
            self.append_log("⚪ [Test Target Monster]: TARGET KOSONG (Skill di-HOLD).")
            messagebox.showinfo("Hasil Cek Target Monster", res_str)

    # =========================================================================
    # Auto Buff (Floating Bar) Handlers
    # =========================================================================
    def _update_floating_buff_label(self):
        area = self.config.get("auto_skill", {}).get("buffs", {}).get("floating_area", {})
        if area and "x" in area:
            self.lbl_floating_buff_info.config(
                text=f"Area: X={area.get('x')} Y={area.get('y')} W={area.get('w')} H={area.get('h')}",
                fg="#3fb950"
            )
        else:
            self.lbl_floating_buff_info.config(
                text="Area: Belum Dikalibrasi",
                fg="#f85149"
            )

    def calibrate_floating_buff_area(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(10, x2 - x1)
            h = max(10, y2 - y1)
            if "auto_skill" not in self.config.data:
                self.config.data["auto_skill"] = dict(DEFAULT_SKILL_CONFIG)
            buffs_cfg = self.config.data["auto_skill"].setdefault("buffs", dict(DEFAULT_SKILL_CONFIG["buffs"]))
            buffs_cfg["floating_area"] = {
                "x": x1, "y": y1, "w": w, "h": h
            }
            self.config.save()
            self._update_floating_buff_label()
            self.append_log(f"🛡️ [Auto Buff] Floating Buff Area dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}.")
            messagebox.showinfo(
                "Kalibrasi Berhasil",
                f"Floating Buff Area berhasil disimpan!\nKoordinat: X={x1}, Y={y1}, W={w}, H={h}\n\n"
                f"Macro akan memonitor kemunculan icon buff di area ini."
            )

        AreaSelectorWindow(self, "Pilih Area Floating Buff (Tempat Icon Buff Muncul di Layar)", 1, 1, client_img, on_saved)

    def _add_buff_item(self):
        self._apply_skill_gui_to_config(save_to_disk=False)
        buffs_cfg = self.config.data.setdefault("auto_skill", {}).setdefault("buffs", dict(DEFAULT_SKILL_CONFIG["buffs"]))
        buff_list = buffs_cfg.setdefault("list", [])
        new_idx = len(buff_list) + 1
        default_slot_str = "Custom Area"
        default_hk = "1"
        if new_idx <= 10:
            num_k = new_idx if new_idx < 10 else 0
            default_slot_str = f"Atas: Slot {new_idx} ({num_k})"
            default_hk = str(num_k)
        else:
            f_num = min(10, new_idx - 10)
            default_slot_str = f"Bawah: Slot F{f_num}"
            default_hk = f"f{f_num}"

        buff_list.append({
            "id": f"buff_{int(time.time() * 1000)}",
            "name": f"Buff {new_idx}",
            "hotkey": default_hk,
            "slot_str": default_slot_str,
            "slot_index": new_idx,
            "recast_cooldown_sec": 5.0,
            "cast_delay_sec": 1.0,
            "template_path": "",
            "enabled": True
        })
        self._render_buff_items()

    def _delete_buff_item(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        buff_list = self.config.data.get("auto_skill", {}).get("buffs", {}).get("list", [])
        if 0 <= idx < len(buff_list):
            del buff_list[idx]
            self._render_buff_items()

    def _render_buff_items(self):
        for widget in self.frame_buff_list.winfo_children():
            widget.destroy()

        self._buff_thumbnails = []
        self._buff_row_vars = []
        self._buff_status_labels = []

        buff_list = self.config.get("auto_skill", {}).get("buffs", {}).get("list", [])
        if not buff_list:
            empty_lbl = tk.Label(
                self.frame_buff_list,
                text="Belum ada buff terdaftar.\nKlik tombol '➕ Tambah Buff' di atas untuk menambahkan buff yang ingin dimonitor.",
                bg="#222428",
                fg="#8b949e",
                font=("Segoe UI", 10),
                pady=20
            )
            empty_lbl.pack()
            return

        hotkey_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                          "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "e", "r", "f"]
        slot_options = [
            "Atas: Slot 1 (1)",
            "Atas: Slot 2 (2)",
            "Atas: Slot 3 (3)",
            "Atas: Slot 4 (4)",
            "Atas: Slot 5 (5)",
            "Atas: Slot 6 (6)",
            "Atas: Slot 7 (7)",
            "Atas: Slot 8 (8)",
            "Atas: Slot 9 (9)",
            "Atas: Slot 10 (0)",
            "Bawah: Slot F1",
            "Bawah: Slot F2",
            "Bawah: Slot F3",
            "Bawah: Slot F4",
            "Bawah: Slot F5",
            "Bawah: Slot F6",
            "Bawah: Slot F7",
            "Bawah: Slot F8",
            "Bawah: Slot F9",
            "Bawah: Slot F10",
            "Custom Area"
        ]

        for idx, item in enumerate(buff_list):
            card = tk.LabelFrame(
                self.frame_buff_list,
                text=f" 🛡️ Buff #{idx + 1} - {item.get('name', f'Buff {idx+1}')} ",
                bg="#161b22",
                fg="#58a6ff",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=6,
                relief="ridge",
                bd=1
            )
            card.pack(fill=tk.X, pady=(0, 6))

            r1 = tk.Frame(card, bg="#161b22")
            r1.pack(fill=tk.X, pady=(0, 4))

            var_en = tk.BooleanVar(value=item.get("enabled", True))
            tk.Checkbutton(
                r1,
                text="Aktif",
                variable=var_en,
                bg="#161b22",
                fg="#7ee787",
                selectcolor="#0d1117",
                activebackground="#161b22",
                activeforeground="#7ee787",
                font=("Segoe UI", 8, "bold")
            ).pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(r1, text="Nama:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_name = tk.StringVar(value=item.get("name", f"Buff {idx+1}"))
            tk.Entry(r1, textvariable=var_name, width=12, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 8))

            tk.Label(r1, text="Slot Buff:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            init_slot_str = item.get("slot_str")
            if not init_slot_str or init_slot_str not in slot_options:
                cur_slot = item.get("slot_index", 1)
                cur_hk = str(item.get("hotkey", "")).lower()
                if cur_hk.startswith("f"):
                    init_slot_str = f"Bawah: Slot {cur_hk.upper()}"
                elif 1 <= cur_slot <= 10:
                    num_k = cur_slot if cur_slot < 10 else 0
                    init_slot_str = f"Atas: Slot {cur_slot} ({num_k})"
                else:
                    init_slot_str = "Custom Area"
                if init_slot_str not in slot_options:
                    init_slot_str = "Custom Area"

            var_slot = tk.StringVar(value=init_slot_str)
            cb_slot = ttk.Combobox(r1, textvariable=var_slot, values=slot_options, width=16, state="readonly", font=("Segoe UI", 8))
            cb_slot.pack(side=tk.LEFT, padx=(2, 8))

            tk.Label(r1, text="Hotkey:", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_hotkey = tk.StringVar(value=str(item.get("hotkey", "1")).lower())
            cb_hotkey = ttk.Combobox(r1, textvariable=var_hotkey, values=hotkey_options, width=5, state="readonly", font=("Segoe UI", 8))
            cb_hotkey.pack(side=tk.LEFT, padx=(2, 8))

            def _on_buff_slot_change(event, vs=var_slot, vh=var_hotkey):
                val = vs.get()
                if val.startswith("Atas: Slot "):
                    import re
                    m = re.search(r"\((\d+)\)", val)
                    if m:
                        vh.set(m.group(1))
                elif val.startswith("Bawah: Slot "):
                    import re
                    m = re.search(r"(F\d+)", val, re.IGNORECASE)
                    if m:
                        vh.set(m.group(1).lower())
            cb_slot.bind("<<ComboboxSelected>>", _on_buff_slot_change)

            tk.Label(r1, text="Recast Cooldown (s):", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_recast_cd = tk.StringVar(value=str(item.get("recast_cooldown_sec", 5.0)))
            tk.Entry(r1, textvariable=var_recast_cd, width=5, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Consolas", 8)).pack(side=tk.LEFT, padx=(2, 8))

            tk.Label(r1, text="Cast Delay (s):", bg="#161b22", fg="#8b949e", font=("Segoe UI", 8)).pack(side=tk.LEFT)
            var_delay = tk.StringVar(value=str(item.get("cast_delay_sec", 1.0)))
            tk.Entry(r1, textvariable=var_delay, width=5, bg="#0d1117", fg="#e1e2e6", insertbackground="#fff", font=("Consolas", 8)).pack(side=tk.LEFT, padx=(2, 8))

            btn_del = tk.Button(r1, text="🗑️", font=("Segoe UI", 7), bg="#da3633", fg="#ffffff", relief="flat", padx=4, command=lambda i=idx: self._delete_buff_item(i))
            btn_del.pack(side=tk.RIGHT, padx=4)

            # Row 2: Template icon, capture actions, status
            r2 = tk.Frame(card, bg="#161b22")
            r2.pack(fill=tk.X, pady=(2, 0))

            tpl_path = item.get("template_path") or item.get("icon_filename", "")
            img_displayed = False
            if tpl_path:
                full_tpl_path = Path(tpl_path) if Path(tpl_path).is_absolute() else Path(self.config.base_dir) / tpl_path
                if full_tpl_path.exists():
                    try:
                        pil_img = Image.open(full_tpl_path).convert("RGB")
                        pil_img.thumbnail((32, 32))
                        tk_thumb = ImageTk.PhotoImage(pil_img)
                        self._buff_thumbnails.append(tk_thumb)
                        lbl_icon = tk.Label(r2, image=tk_thumb, bg="#0d1117", bd=1, relief="solid")
                        lbl_icon.pack(side=tk.LEFT, padx=(0, 6))
                        img_displayed = True
                    except Exception:
                        pass

            if not img_displayed:
                lbl_no_icon = tk.Label(r2, text="[No Icon]", bg="#0d1117", fg="#8b949e", font=("Consolas", 7), width=8, height=2, bd=1, relief="solid")
                lbl_no_icon.pack(side=tk.LEFT, padx=(0, 6))

            tk.Button(
                r2,
                text="📸 Ambil Icon dari Slot",
                font=("Segoe UI", 7, "bold"),
                bg="#238636",
                fg="#ffffff",
                relief="flat",
                padx=6,
                pady=2,
                command=lambda i=idx: self.capture_buff_icon_from_slot(i)
            ).pack(side=tk.LEFT, padx=(0, 4))

            tk.Button(
                r2,
                text="✂️ Crop dari Floating Buff",
                font=("Segoe UI", 7),
                bg="#30363d",
                fg="#c9d1d9",
                relief="flat",
                padx=6,
                pady=2,
                command=lambda i=idx: self.capture_buff_icon_from_floating(i)
            ).pack(side=tk.LEFT, padx=(0, 10))

            lbl_status = tk.Label(
                r2,
                text="[READY]" if tpl_path else "[BELUM DI-CAPTURE]",
                bg="#161b22",
                fg="#3fb950" if tpl_path else "#8b949e",
                font=("Segoe UI", 8, "bold")
            )
            lbl_status.pack(side=tk.RIGHT, padx=4)
            self._buff_status_labels.append(lbl_status)

            self._buff_row_vars.append({
                "id": item.get("id", f"buff_{idx+1}"),
                "enabled": var_en,
                "name": var_name,
                "slot_str": var_slot,
                "hotkey": var_hotkey,
                "recast_cooldown_sec": var_recast_cd,
                "cast_delay_sec": var_delay,
                "template_path": tpl_path
            })

    def capture_buff_icon_from_slot(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        buff_list = self.config.data.get("auto_skill", {}).get("buffs", {}).get("list", [])
        if not (0 <= idx < len(buff_list)):
            return
        item = buff_list[idx]
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        crop_img = self.bot.skills.get_skill_slot_crop(client_img, item)
        if not crop_img:
            messagebox.showwarning(
                "Slot Belum Dikalibrasi",
                f"Kotak slot untuk Buff #{idx+1} belum diketahui.\n"
                f"Silakan Kalibrasi Bar Skill terlebih dahulu pada tab Combo Serang, atau gunakan tombol '✂️ Crop dari Floating Buff'."
            )
            return

        skills_dir = self.config.skills_dir
        skills_dir.mkdir(parents=True, exist_ok=True)
        filename = f"buff_{item.get('id', f'idx_{idx}')}_{int(time.time())}.png"
        save_path = skills_dir / filename
        crop_img.save(save_path)

        rel_path = f"assets/skills/{filename}"
        item["template_path"] = rel_path
        self.config.save()
        self._render_buff_items()
        self.append_log(f"🛡️ [Auto Buff] Icon buff #{idx+1} berhasil dicapture dari slot ke {rel_path}.")
        messagebox.showinfo("Capture Berhasil", f"Icon Buff #{idx+1} berhasil dicapture dari slot!\nTersimpan di: {rel_path}")

    def capture_buff_icon_from_floating(self, idx: int):
        self._apply_skill_gui_to_config(save_to_disk=False)
        buff_list = self.config.data.get("auto_skill", {}).get("buffs", {}).get("list", [])
        if not (0 <= idx < len(buff_list)):
            return
        item = buff_list[idx]
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(5, x2 - x1)
            h = max(5, y2 - y1)
            crop_img = client_img.crop(rect)
            skills_dir = self.config.skills_dir
            skills_dir.mkdir(parents=True, exist_ok=True)
            filename = f"buff_{item.get('id', f'idx_{idx}')}_{int(time.time())}.png"
            save_path = skills_dir / filename
            crop_img.save(save_path)

            rel_path = f"assets/skills/{filename}"
            item["template_path"] = rel_path
            self.config.save()
            self._render_buff_items()
            self.append_log(f"🛡️ [Auto Buff] Icon buff #{idx+1} berhasil di-crop dari floating area ke {rel_path}.")
            messagebox.showinfo("Capture Berhasil", f"Icon Buff #{idx+1} berhasil disimpan!\nFile: {rel_path}")

        AreaSelectorWindow(self, f"Crop Icon Buff #{idx+1} dari Floating Buff Bar", 1, 1, client_img, on_saved)

    def _test_detect_buffs(self):
        self._apply_skill_gui_to_config(save_to_disk=False)
        buffs_cfg = self.config.data.get("auto_skill", {}).get("buffs", {})
        buff_list = buffs_cfg.get("list", [])
        if not buff_list:
            messagebox.showinfo("Info", "Belum ada buff dalam daftar Auto Buff.")
            return

        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()
        if client_img is None:
            messagebox.showerror("Error", "Gagal mengambil capture layar game.")
            return

        summary_lines = []
        for idx, item in enumerate(buff_list):
            name = item.get("name", f"Buff {idx+1}")
            hotkey = item.get("hotkey", "?")
            tpl_path = item.get("template_path") or item.get("icon_filename", "")

            if not tpl_path:
                status_str = "BELUM CAPTURE ICON"
                summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
                if idx < len(self._buff_status_labels):
                    self._buff_status_labels[idx].config(text=f"[{status_str}]", fg="#8b949e")
                continue

            is_present = self.bot.skills.is_buff_present_in_floating_area(client_img, item)
            if is_present:
                status_str = "AKTIF DI FLOATING BAR"
                color = "#3fb950"
            else:
                status_str = "HILANG / EXPIRED (PERLU RECAST)"
                color = "#f85149"

            summary_lines.append(f"• #{idx+1} ({name}, Key {hotkey.upper()}): {status_str}")
            if idx < len(self._buff_status_labels):
                self._buff_status_labels[idx].config(text=f"[{status_str}]", fg=color)

        res_text = "\n".join(summary_lines)
        self.append_log(f"🛡️ [Auto Buff Test]:\n{res_text}")
        messagebox.showinfo("Hasil Cek Floating Buff", f"Status buff saat ini di Floating Buff Area:\n\n{res_text}")

    def _apply_skill_gui_to_config(self, save_to_disk=False):
        if "auto_skill" not in self.config.data:
            self.config.data["auto_skill"] = dict(DEFAULT_SKILL_CONFIG)

        if hasattr(self, "var_skill_enabled"):
            self.config.data["auto_skill"]["enabled"] = self.var_skill_enabled.get()
        if hasattr(self, "var_skill_sync_hunt"):
            self.config.data["auto_skill"]["sync_with_auto_hunt"] = self.var_skill_sync_hunt.get()
        if hasattr(self, "var_skill_mode"):
            self.config.data["auto_skill"]["mode"] = self.var_skill_mode.get()
        if hasattr(self, "var_skill_combo_interval"):
            try:
                self.config.data["auto_skill"]["combo_check_interval_sec"] = max(0.01, float(self.var_skill_combo_interval.get().strip()))
            except ValueError:
                self.config.data["auto_skill"]["combo_check_interval_sec"] = 0.05

        # Save target monster awareness
        if hasattr(self, "var_target_monster_enabled"):
            tgt_cfg = self.config.data["auto_skill"].setdefault("target_monster", dict(DEFAULT_SKILL_CONFIG.get("target_monster", {})))
            tgt_cfg["enabled"] = self.var_target_monster_enabled.get()

        # Save hunt keys (E, R, F)
        if hasattr(self, "var_hunt_e_en"):
            try:
                e_int = max(0.1, float(self.var_hunt_e_interval.get().strip()))
            except ValueError:
                e_int = 1.5
            try:
                r_int = max(0.1, float(self.var_hunt_r_interval.get().strip()))
            except ValueError:
                r_int = 0.8
            try:
                f_int = max(0.1, float(self.var_hunt_f_interval.get().strip()))
            except ValueError:
                f_int = 1.0

            self.config.data["auto_skill"]["hunt_keys"] = {
                "e": {"enabled": self.var_hunt_e_en.get(), "interval": e_int, "desc": "Target Monster (E)"},
                "r": {"enabled": self.var_hunt_r_en.get(), "interval": r_int, "desc": "Serang Monster (R)"},
                "f": {"enabled": self.var_hunt_f_en.get(), "interval": f_int, "desc": "Pick Loot Drop (F)"}
            }

        # Save combo items from UI
        if hasattr(self, "_combo_row_vars") and self._combo_row_vars:
            combo_list = []
            for item_vars in self._combo_row_vars:
                slot_str = item_vars["slot_str"].get()
                import re
                m = re.search(r"\d+", slot_str)
                slot_idx = int(m.group(0)) if m else 1

                try:
                    delay_val = max(0.05, float(item_vars["delay"].get().strip()))
                except ValueError:
                    delay_val = 0.30

                combo_list.append({
                    "id": item_vars["id"],
                    "enabled": item_vars["enabled"].get(),
                    "name": item_vars["name"].get().strip(),
                    "slot_str": slot_str,
                    "slot_index": slot_idx,
                    "hotkey": item_vars["hotkey"].get().strip().lower(),
                    "cast_delay_sec": delay_val,
                    "slot_box": item_vars["slot_box"],
                    "template_path": item_vars["template_path"],
                    "similarity_threshold": item_vars["similarity_threshold"],
                    "brightness_ratio_threshold": item_vars["brightness_ratio_threshold"]
                })
            self.config.data["auto_skill"]["combo_list"] = combo_list

        # Save buffs configuration
        if hasattr(self, "var_buff_enabled"):
            buffs_cfg = self.config.data["auto_skill"].setdefault("buffs", dict(DEFAULT_SKILL_CONFIG["buffs"]))
            buffs_cfg["enabled"] = self.var_buff_enabled.get()
            try:
                buffs_cfg["check_interval_sec"] = max(0.05, float(self.var_buff_check_interval.get().strip()))
            except ValueError:
                buffs_cfg["check_interval_sec"] = 0.5

            if hasattr(self, "_buff_row_vars") and self._buff_row_vars:
                buff_list = []
                for item_vars in self._buff_row_vars:
                    slot_str = item_vars["slot_str"].get()
                    import re
                    m = re.search(r"\d+", slot_str)
                    slot_idx = int(m.group(0)) if m else 1

                    try:
                        recast_cd = max(1.0, float(item_vars["recast_cooldown_sec"].get().strip()))
                    except ValueError:
                        recast_cd = 5.0

                    try:
                        cast_delay = max(0.1, float(item_vars["cast_delay_sec"].get().strip()))
                    except ValueError:
                        cast_delay = 1.0

                    buff_list.append({
                        "id": item_vars["id"],
                        "enabled": item_vars["enabled"].get(),
                        "name": item_vars["name"].get().strip(),
                        "slot_str": slot_str,
                        "slot_index": slot_idx,
                        "hotkey": item_vars["hotkey"].get().strip().lower(),
                        "recast_cooldown_sec": recast_cd,
                        "cast_delay_sec": cast_delay,
                        "template_path": item_vars["template_path"]
                    })
                buffs_cfg["list"] = buff_list

        # Save timer interval keys from UI
        if hasattr(self, "skill_vars") and self.skill_vars:
            if "keys" not in self.config.data["auto_skill"]:
                self.config.data["auto_skill"]["keys"] = {}
            for k, widgets in self.skill_vars.items():
                try:
                    sec_val = float(widgets["interval"].get().strip())
                except ValueError:
                    sec_val = 10.0
                self.config.data["auto_skill"]["keys"][k] = {
                    "enabled": widgets["enabled"].get(),
                    "interval": max(0.1, sec_val)
                }

        if save_to_disk:
            self.config.save()

    def _save_skill_settings(self):
        try:
            self._apply_skill_gui_to_config(save_to_disk=True)
            messagebox.showinfo("Sukses", "Pengaturan Auto Skill berhasil disimpan!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan skill: {e}")

    def _reset_skill_timers(self):
        self.bot.skills.reset_timers()
        if hasattr(self, "skill_vars") and self.skill_vars:
            for k, widgets in self.skill_vars.items():
                widgets["lbl_countdown"].config(text="-", fg="#8b949e")
        if hasattr(self, "lbl_hunt_e_cd"):
            self.lbl_hunt_e_cd.config(text="-", fg="#8b949e")
            self.lbl_hunt_r_cd.config(text="-", fg="#8b949e")
            self.lbl_hunt_f_cd.config(text="-", fg="#8b949e")
        if hasattr(self, "lbl_target_monster_live"):
            self.lbl_target_monster_live.config(text="[RESET]", fg="#8b949e")
        if hasattr(self, "_combo_status_labels"):
            for lbl in self._combo_status_labels:
                lbl.config(text="[RESET]", fg="#8b949e")
        if hasattr(self, "_buff_status_labels"):
            for lbl in self._buff_status_labels:
                lbl.config(text="[RESET]", fg="#8b949e")

    def _update_skill_countdowns(self):
        try:
            is_running = self.bot.skills.is_running
            now = time.time()

            # Target Monster live status indicator
            if hasattr(self, "lbl_target_monster_live"):
                if not is_running:
                    self.lbl_target_monster_live.config(text="[STOPPED]", fg="#8b949e")
                elif hasattr(self, "var_target_monster_enabled") and not self.var_target_monster_enabled.get():
                    self.lbl_target_monster_live.config(text="[DETEKSI NONAKTIF]", fg="#8b949e")
                else:
                    has_tgt = getattr(self.bot.skills, "has_target", False)
                    if has_tgt:
                        self.lbl_target_monster_live.config(text="🎯 [TARGET AKTIF]", fg="#3fb950")
                    else:
                        self.lbl_target_monster_live.config(text="⏸️ [HOLD - MENUNGGU TARGET]", fg="#e3b341")

            # Hunt keys (E, R, F) countdown updates
            if hasattr(self, "lbl_hunt_e_cd"):
                for k, en_var, cd_var, lbl in [
                    ("e", self.var_hunt_e_en, self.var_hunt_e_interval, self.lbl_hunt_e_cd),
                    ("r", self.var_hunt_r_en, self.var_hunt_r_interval, self.lbl_hunt_r_cd),
                    ("f", self.var_hunt_f_en, self.var_hunt_f_interval, self.lbl_hunt_f_cd)
                ]:
                    if not is_running or not en_var.get():
                        lbl.config(text="-", fg="#8b949e")
                        continue
                    try:
                        iv = float(cd_var.get().strip())
                    except ValueError:
                        iv = 1.0
                    last_t = self.bot.skills.last_hunt_press_times.get(k, 0.0)
                    if last_t <= 0.0:
                        lbl.config(text="0.0s", fg="#e3b341")
                    else:
                        rem = max(0.0, iv - (now - last_t))
                        lbl.config(text=f"{rem:.1f}s", fg="#e3b341" if rem <= 0.3 else "#7ee787")

            # Timer mode countdown updates
            if hasattr(self, "skill_vars") and self.skill_vars:
                for k, widgets in self.skill_vars.items():
                    is_enabled = widgets["enabled"].get()
                    lbl = widgets["lbl_countdown"]

                    if not is_running or not is_enabled:
                        lbl.config(text="-", fg="#8b949e")
                        continue

                    try:
                        interval = float(widgets["interval"].get().strip())
                    except ValueError:
                        interval = 10.0

                    last_t = self.bot.skills.last_press_times.get(k, 0.0)
                    if last_t <= 0.0:
                        disp = "0.0s"
                        fg_color = "#e3b341"
                    else:
                        elapsed = now - last_t
                        remaining = max(0.0, interval - elapsed)
                        if remaining >= 10.0:
                            disp = f"{int(math.ceil(remaining))}s"
                        elif remaining > 0.0:
                            disp = f"{remaining:.1f}s"
                        else:
                            disp = "0.0s"
                        fg_color = "#e3b341" if remaining <= 1.0 else "#7ee787"

                    lbl.config(text=disp, fg=fg_color)

            # Smart combo mode live status indicator
            if is_running and hasattr(self, "var_skill_mode") and self.var_skill_mode.get() == "smart_combo":
                active_combo_idx = self.bot.skills.current_combo_index
                if hasattr(self, "_combo_status_labels"):
                    for idx, lbl in enumerate(self._combo_status_labels):
                        if idx == active_combo_idx:
                            lbl.config(text="▶ [RUNNING]", fg="#58a6ff")

            # Auto Buff live status badges
            if hasattr(self, "_buff_status_labels") and self._buff_status_labels:
                buff_statuses = dict(getattr(self.bot.skills, "buff_status", {}))
                for idx, lbl in enumerate(self._buff_status_labels):
                    if idx < len(self._buff_row_vars):
                        b_id = self._buff_row_vars[idx]["id"]
                        if not is_running:
                            lbl.config(text="[STOPPED]", fg="#8b949e")
                        elif b_id in buff_statuses:
                            is_act = buff_statuses[b_id].get("is_active", False)
                            if is_act:
                                lbl.config(text="[AKTIF]", fg="#3fb950")
                            else:
                                lbl.config(text="[HILANG/RECAST]", fg="#f85149")
        except Exception:
            pass
        self.after(100, self._update_skill_countdowns)

    # =========================================================================
    # TAB 8: Auto Pot (HP & TP)
    # =========================================================================
    def _make_coord_entry(self, parent, label_text: str, default_val: int) -> tk.Entry:
        tk.Label(parent, text=label_text, font=("Segoe UI", 8), bg="#222428", fg="#8b949e").pack(side=tk.LEFT, padx=(4, 2))
        entry = tk.Entry(parent, width=5, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", font=("Consolas", 8))
        entry.insert(0, str(default_val))
        entry.pack(side=tk.LEFT, padx=(0, 6))
        return entry

    def _build_pot_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_pot)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        pot_cfg = self.config.get("auto_pot", DEFAULT_POT_CONFIG)
        hp_cfg = pot_cfg.get("hp", DEFAULT_POT_CONFIG["hp"])
        tp_cfg = pot_cfg.get("tp", DEFAULT_POT_CONFIG["tp"])

        # 1. Top Control Header
        top_frame = tk.Frame(container, bg="#161b22", padx=12, pady=10, relief="ridge", bd=1)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.var_pot_enabled = tk.BooleanVar(value=pot_cfg.get("enabled", True))
        self.var_pot_sync_hunt = tk.BooleanVar(value=pot_cfg.get("sync_with_auto_hunt", True))

        tk.Checkbutton(
            top_frame,
            text="🧪 Aktifkan Fitur Auto Pot (Otomatis gunakan pot jika HP / TP berkurang di bawah persentase)",
            variable=self.var_pot_enabled,
            bg="#161b22",
            fg="#58a6ff",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W)

        tk.Checkbutton(
            top_frame,
            text="⚔️ Jalankan Auto Pot otomatis saat Mode Auto Hunt berjalan",
            variable=self.var_pot_sync_hunt,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W, pady=(4, 6))

        # Timing inputs
        timing_row = tk.Frame(top_frame, bg="#161b22")
        timing_row.pack(fill=tk.X, pady=(2, 6))

        tk.Label(timing_row, text="⏱️ Cooldown Pot HP/TP (detik):", font=("Segoe UI", 9), bg="#161b22", fg="#8b949e").pack(side=tk.LEFT)
        self.entry_pot_cooldown = tk.Entry(timing_row, width=5, bg="#0d1117", fg="#58a6ff", insertbackground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.entry_pot_cooldown.insert(0, str(hp_cfg.get("cooldown_sec", 1.0)))
        self.entry_pot_cooldown.pack(side=tk.LEFT, padx=(4, 16))

        tk.Label(timing_row, text="🔍 Interval Cek Bar (detik):", font=("Segoe UI", 9), bg="#161b22", fg="#8b949e").pack(side=tk.LEFT)
        self.entry_pot_interval = tk.Entry(timing_row, width=5, bg="#0d1117", fg="#58a6ff", insertbackground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.entry_pot_interval.insert(0, str(pot_cfg.get("check_interval_sec", 0.20)))
        self.entry_pot_interval.pack(side=tk.LEFT, padx=(4, 0))

        # Buttons bar
        btn_bar = tk.Frame(top_frame, bg="#161b22")
        btn_bar.pack(fill=tk.X, pady=(6, 0))

        tk.Button(
            btn_bar,
            text="💾 Simpan Pengaturan Pot",
            font=("Segoe UI", 8, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=self._save_pot_settings
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.btn_pot_toggle = tk.Button(
            btn_bar,
            text="▶️ Mulai Auto Pot (Standalone)",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=self._toggle_pot_standalone
        )
        self.btn_pot_toggle.pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="🔍 Cek Bacaan HP & TP (Shift+End)",
            font=("Segoe UI", 8),
            bg="#d29922",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: self.test_pot_reading(show_dialog=True)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_pot_running_status = tk.Label(btn_bar, text="○ NONAKTIF", font=("Segoe UI", 8, "bold"), bg="#161b22", fg="#8b949e")
        self.lbl_pot_running_status.pack(side=tk.LEFT, padx=6)

        # 2. HP Section
        hp_box = hp_cfg.get("box", {"x": 4, "y": 54, "w": 214, "h": 14})
        hp_frame = tk.LabelFrame(container, text=" ❤️ Pengaturan HP Auto Pot (Karakter) ", bg="#222428", fg="#f85149", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        hp_frame.pack(fill=tk.X, pady=6)

        hp_top = tk.Frame(hp_frame, bg="#222428")
        hp_top.pack(fill=tk.X, pady=(0, 6))

        self.lbl_hp_coords = tk.Label(
            hp_top,
            text=f"HP box: X={hp_box.get('x', 4)} Y={hp_box.get('y', 54)} W={hp_box.get('w', 214)} H={hp_box.get('h', 14)}",
            font=("Consolas", 9, "bold"),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_hp_coords.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            hp_top,
            text="🎯 Calibrate HP Box",
            font=("Segoe UI", 9, "bold"),
            bg="#b62324",
            fg="#ffffff",
            activebackground="#da3633",
            relief="flat",
            padx=12,
            pady=3,
            command=self.calibrate_hp_box
        ).pack(side=tk.RIGHT)

        tk.Button(
            hp_top,
            text="🔍 Auto Detect dari Layar",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=3,
            command=self.auto_detect_pot_bars
        ).pack(side=tk.RIGHT, padx=(0, 6))

        # HP Trigger controls
        hp_ctrl = tk.Frame(hp_frame, bg="#222428")
        hp_ctrl.pack(fill=tk.X, pady=4)

        self.var_hp_enabled = tk.BooleanVar(value=hp_cfg.get("enabled", True))
        tk.Checkbutton(
            hp_ctrl,
            text="Aktifkan HP Auto Pot",
            variable=self.var_hp_enabled,
            bg="#222428",
            fg="#e1e2e6",
            selectcolor="#161b22",
            activebackground="#222428",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(hp_ctrl, text="HP Trigger Threshold (%):", font=("Segoe UI", 9), bg="#222428", fg="#8b949e").pack(side=tk.LEFT)
        self.entry_hp_threshold = tk.Entry(hp_ctrl, width=5, bg="#161b22", fg="#f85149", insertbackground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.entry_hp_threshold.insert(0, str(hp_cfg.get("threshold_pct", 50)))
        self.entry_hp_threshold.pack(side=tk.LEFT, padx=(4, 16))

        tk.Label(hp_ctrl, text="Tombol Hotkey HP:", font=("Segoe UI", 9), bg="#222428", fg="#8b949e").pack(side=tk.LEFT)
        valid_keys = ["f9", "f10", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "e", "r", "f"]
        self.combo_hp_key = ttk.Combobox(hp_ctrl, values=valid_keys, width=5, state="readonly", font=("Segoe UI", 9))
        current_hp_k = str(hp_cfg.get("key", "f9")).lower()
        self.combo_hp_key.set(current_hp_k if current_hp_k in valid_keys else "f9")
        self.combo_hp_key.pack(side=tk.LEFT, padx=(4, 0))

        # HP Status row
        hp_stat = tk.Frame(hp_frame, bg="#161b22", padx=8, pady=4)
        hp_stat.pack(fill=tk.X, pady=(6, 0))

        self.lbl_hp_status = tk.Label(hp_stat, text="HP: Belum dibaca", font=("Segoe UI", 9, "bold"), bg="#161b22", fg="#8b949e")
        self.lbl_hp_status.pack(side=tk.LEFT)

        self.lbl_hp_count = tk.Label(hp_stat, text="Total Pot Diminum: 0", font=("Segoe UI", 9), bg="#161b22", fg="#c9d1d9")
        self.lbl_hp_count.pack(side=tk.RIGHT)

        # 3. TP Section
        tp_box = tp_cfg.get("box", {"x": 4, "y": 69, "w": 214, "h": 14})
        tp_frame = tk.LabelFrame(container, text=" 💙 Pengaturan TP/MP Auto Pot (Prana / Mana) ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        tp_frame.pack(fill=tk.X, pady=6)

        tp_top = tk.Frame(tp_frame, bg="#222428")
        tp_top.pack(fill=tk.X, pady=(0, 6))

        self.lbl_tp_coords = tk.Label(
            tp_top,
            text=f"TP box: X={tp_box.get('x', 4)} Y={tp_box.get('y', 69)} W={tp_box.get('w', 214)} H={tp_box.get('h', 14)}",
            font=("Consolas", 9, "bold"),
            bg="#222428",
            fg="#e1e2e6"
        )
        self.lbl_tp_coords.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            tp_top,
            text="🎯 Calibrate MP Box",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#388bfd",
            relief="flat",
            padx=12,
            pady=3,
            command=self.calibrate_tp_box
        ).pack(side=tk.RIGHT)

        tk.Button(
            tp_top,
            text="🔍 Auto Detect dari Layar",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=3,
            command=self.auto_detect_pot_bars
        ).pack(side=tk.RIGHT, padx=(0, 6))

        # TP Trigger controls
        tp_ctrl = tk.Frame(tp_frame, bg="#222428")
        tp_ctrl.pack(fill=tk.X, pady=4)

        self.var_tp_enabled = tk.BooleanVar(value=tp_cfg.get("enabled", True))
        tk.Checkbutton(
            tp_ctrl,
            text="Aktifkan TP Auto Pot",
            variable=self.var_tp_enabled,
            bg="#222428",
            fg="#e1e2e6",
            selectcolor="#161b22",
            activebackground="#222428",
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(tp_ctrl, text="TP Trigger Threshold (%):", font=("Segoe UI", 9), bg="#222428", fg="#8b949e").pack(side=tk.LEFT)
        self.entry_tp_threshold = tk.Entry(tp_ctrl, width=5, bg="#161b22", fg="#58a6ff", insertbackground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.entry_tp_threshold.insert(0, str(tp_cfg.get("threshold_pct", 50)))
        self.entry_tp_threshold.pack(side=tk.LEFT, padx=(4, 16))

        tk.Label(tp_ctrl, text="Tombol Hotkey TP:", font=("Segoe UI", 9), bg="#222428", fg="#8b949e").pack(side=tk.LEFT)
        self.combo_tp_key = ttk.Combobox(tp_ctrl, values=valid_keys, width=5, state="readonly", font=("Segoe UI", 9))
        current_tp_k = str(tp_cfg.get("key", "f10")).lower()
        self.combo_tp_key.set(current_tp_k if current_tp_k in valid_keys else "f10")
        self.combo_tp_key.pack(side=tk.LEFT, padx=(4, 0))

        # TP Status row
        tp_stat = tk.Frame(tp_frame, bg="#161b22", padx=8, pady=4)
        tp_stat.pack(fill=tk.X, pady=(6, 0))

        self.lbl_tp_status = tk.Label(tp_stat, text="TP: Belum dibaca", font=("Segoe UI", 9, "bold"), bg="#161b22", fg="#8b949e")
        self.lbl_tp_status.pack(side=tk.LEFT)

        self.lbl_tp_count = tk.Label(tp_stat, text="Total Pot Diminum: 0", font=("Segoe UI", 9), bg="#161b22", fg="#c9d1d9")
        self.lbl_tp_count.pack(side=tk.RIGHT)

        # 4. Manual Coordinate Fine-Tuning Box
        manual_frame = tk.LabelFrame(container, text=" 🛠️ Penyesuaian Manual Koordinat Bar (Fine-Tuning) ", bg="#222428", fg="#8b949e", font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        manual_frame.pack(fill=tk.X, pady=6)

        m_desc = tk.Label(manual_frame, text="Masukkan angka X, Y, W, H langsung jika ingin mengatur pergeseran per-pixel:", font=("Segoe UI", 8), bg="#222428", fg="#8b949e")
        m_desc.pack(anchor=tk.W, pady=(0, 6))

        # HP manual entries
        hp_m_row = tk.Frame(manual_frame, bg="#222428")
        hp_m_row.pack(fill=tk.X, pady=2)
        tk.Label(hp_m_row, text="HP Box:", font=("Segoe UI", 8, "bold"), bg="#222428", fg="#f85149", width=8, anchor=tk.W).pack(side=tk.LEFT)
        self.e_hp_x = self._make_coord_entry(hp_m_row, "X:", hp_box.get("x", 4))
        self.e_hp_y = self._make_coord_entry(hp_m_row, "Y:", hp_box.get("y", 54))
        self.e_hp_w = self._make_coord_entry(hp_m_row, "W:", hp_box.get("w", 214))
        self.e_hp_h = self._make_coord_entry(hp_m_row, "H:", hp_box.get("h", 14))

        # TP manual entries
        tp_m_row = tk.Frame(manual_frame, bg="#222428")
        tp_m_row.pack(fill=tk.X, pady=2)
        tk.Label(tp_m_row, text="TP Box:", font=("Segoe UI", 8, "bold"), bg="#222428", fg="#58a6ff", width=8, anchor=tk.W).pack(side=tk.LEFT)
        self.e_tp_x = self._make_coord_entry(tp_m_row, "X:", tp_box.get("x", 4))
        self.e_tp_y = self._make_coord_entry(tp_m_row, "Y:", tp_box.get("y", 69))
        self.e_tp_w = self._make_coord_entry(tp_m_row, "W:", tp_box.get("w", 214))
        self.e_tp_h = self._make_coord_entry(tp_m_row, "H:", tp_box.get("h", 14))

        tk.Button(
            manual_frame,
            text="📐 Terapkan Koordinat Manual",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=3,
            command=self._save_manual_coords
        ).pack(anchor=tk.W, pady=(6, 0))

        # Start periodic update for Pot tab
        self.after(300, self._update_pot_status)

    def _save_pot_settings(self, silent: bool = False):
        try:
            cooldown = max(0.2, float(self.entry_pot_cooldown.get().strip()))
            interval = max(0.05, float(self.entry_pot_interval.get().strip()))
            hp_thresh = max(1.0, min(99.0, float(self.entry_hp_threshold.get().strip())))
            tp_thresh = max(1.0, min(99.0, float(self.entry_tp_threshold.get().strip())))

            hp_k = self.combo_hp_key.get().strip().lower() or "f9"
            tp_k = self.combo_tp_key.get().strip().lower() or "f10"

            if "auto_pot" not in self.config.data:
                self.config.data["auto_pot"] = dict(DEFAULT_POT_CONFIG)

            self.config.data["auto_pot"]["enabled"] = self.var_pot_enabled.get()
            self.config.data["auto_pot"]["sync_with_auto_hunt"] = self.var_pot_sync_hunt.get()
            self.config.data["auto_pot"]["check_interval_sec"] = interval

            if "hp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["hp"] = dict(DEFAULT_POT_CONFIG["hp"])
            self.config.data["auto_pot"]["hp"]["enabled"] = self.var_hp_enabled.get()
            self.config.data["auto_pot"]["hp"]["threshold_pct"] = hp_thresh
            self.config.data["auto_pot"]["hp"]["key"] = hp_k
            self.config.data["auto_pot"]["hp"]["cooldown_sec"] = cooldown

            if "tp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["tp"] = dict(DEFAULT_POT_CONFIG["tp"])
            self.config.data["auto_pot"]["tp"]["enabled"] = self.var_tp_enabled.get()
            self.config.data["auto_pot"]["tp"]["threshold_pct"] = tp_thresh
            self.config.data["auto_pot"]["tp"]["key"] = tp_k
            self.config.data["auto_pot"]["tp"]["cooldown_sec"] = cooldown

            self.config.save()
            if not silent:
                self.append_log("Pengaturan Auto Pot berhasil disimpan.")
                messagebox.showinfo("Sukses", "Pengaturan Auto Pot berhasil disimpan ke konfigurasi!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Gagal menyimpan pengaturan Auto Pot: {e}")

    def _toggle_pot_standalone(self):
        if self.bot.pots.is_running:
            self.bot.pots.stop()
            self.append_log("🧪 [Auto Pot] Mode Standalone dihentikan.")
        else:
            self._save_pot_settings(silent=True)
            self.bot.pots.reset_counts()
            self.bot.pots.start()
            self.append_log("🧪 [Auto Pot] Mode Standalone dimulai.")

    def test_pot_reading(self, show_dialog: bool = True):
        try:
            self.wm.activate_window()
            time.sleep(0.2)
            client_img = self.screen.capture_client()
            hp_pct, tp_pct = self.bot.pots.get_current_readings(client_img)

            hp_str = f"{hp_pct:.1f}%" if hp_pct is not None else "Gagal dibaca"
            tp_str = f"{tp_pct:.1f}%" if tp_pct is not None else "Gagal dibaca"

            self.append_log(f"🧪 [Auto Pot Reading] HP: {hp_str} | TP: {tp_str}")
            self._update_pot_labels_with_values(hp_pct, tp_pct)

            if show_dialog:
                messagebox.showinfo(
                    "Hasil Pembacaan HP & TP",
                    f"Pembacaan Bar Karakter Saat Ini:\n\n"
                    f"❤️ HP Karakter : {hp_str}\n"
                    f"💙 TP Karakter : {tp_str}\n\n"
                    f"Pastikan jendela game terlihat jelas dan kotak HP/TP sudah dikalibrasi dengan benar."
                )
        except Exception as e:
            self.append_log(f"🧪 [Auto Pot Reading Error]: {e}")
            if show_dialog:
                messagebox.showerror("Error", f"Gagal membaca layar game: {e}")

    def calibrate_hp_box(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            if "auto_pot" not in self.config.data:
                self.config.data["auto_pot"] = dict(DEFAULT_POT_CONFIG)
            if "hp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["hp"] = dict(DEFAULT_POT_CONFIG["hp"])
            self.config.data["auto_pot"]["hp"]["box"] = {"x": x1, "y": y1, "w": w, "h": h}
            self.config.save()
            self._sync_pot_ui_from_config()
            self.append_log(f"🧪 [Auto Pot] Kotak HP berhasil dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}.")
            messagebox.showinfo("Kalibrasi Berhasil", f"Area HP Bar berhasil disimpan:\nX={x1}, Y={y1}, W={w}, H={h}")

        AreaSelectorWindow(self, "Pilih Kotak HP Bar (Drag dari Kiri-Atas ke Kanan-Bawah)", 1, 1, client_img, on_saved)

    def calibrate_tp_box(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()

        def on_saved(rect):
            x1, y1, x2, y2 = rect
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            if "auto_pot" not in self.config.data:
                self.config.data["auto_pot"] = dict(DEFAULT_POT_CONFIG)
            if "tp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["tp"] = dict(DEFAULT_POT_CONFIG["tp"])
            self.config.data["auto_pot"]["tp"]["box"] = {"x": x1, "y": y1, "w": w, "h": h}
            self.config.save()
            self._sync_pot_ui_from_config()
            self.append_log(f"🧪 [Auto Pot] Kotak TP berhasil dikalibrasi: X={x1}, Y={y1}, W={w}, H={h}.")
            messagebox.showinfo("Kalibrasi Berhasil", f"Area TP Bar berhasil disimpan:\nX={x1}, Y={y1}, W={w}, H={h}")

        AreaSelectorWindow(self, "Pilih Kotak TP Bar (Drag dari Kiri-Atas ke Kanan-Bawah)", 1, 1, client_img, on_saved)

    def auto_detect_pot_bars(self):
        self.wm.activate_window()
        time.sleep(0.3)
        client_img = self.screen.capture_client()
        hp_box, tp_box = PotController.auto_detect_hud_bars(client_img)
        if not hp_box and not tp_box:
            messagebox.showwarning("Auto Detect Gagal", "Tidak dapat mendeteksi bar HP/TP secara otomatis.\nPastikan game berada di layar dan tidak tertutup window lain, atau gunakan tombol Calibrate manual.")
            return

        msg = "Hasil Deteksi Otomatis Bar Karakter:\n\n"
        if "auto_pot" not in self.config.data:
            self.config.data["auto_pot"] = dict(DEFAULT_POT_CONFIG)

        if hp_box:
            if "hp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["hp"] = dict(DEFAULT_POT_CONFIG["hp"])
            self.config.data["auto_pot"]["hp"]["box"] = hp_box
            msg += f"❤️ HP Box: X={hp_box['x']}, Y={hp_box['y']}, W={hp_box['w']}, H={hp_box['h']}\n"

        if tp_box:
            if "tp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["tp"] = dict(DEFAULT_POT_CONFIG["tp"])
            self.config.data["auto_pot"]["tp"]["box"] = tp_box
            msg += f"💙 TP Box: X={tp_box['x']}, Y={tp_box['y']}, W={tp_box['w']}, H={tp_box['h']}\n"

        self.config.save()
        self._sync_pot_ui_from_config()
        self.append_log("🧪 [Auto Pot] Deteksi otomatis berhasil memperbarui koordinat HP/TP.")
        messagebox.showinfo("Auto Detect Berhasil", msg + "\nKoordinat telah otomatis disimpan ke konfigurasi!")

    def _save_manual_coords(self):
        try:
            hx = int(self.e_hp_x.get().strip())
            hy = int(self.e_hp_y.get().strip())
            hw = max(1, int(self.e_hp_w.get().strip()))
            hh = max(1, int(self.e_hp_h.get().strip()))

            tx = int(self.e_tp_x.get().strip())
            ty = int(self.e_tp_y.get().strip())
            tw = max(1, int(self.e_tp_w.get().strip()))
            th = max(1, int(self.e_tp_h.get().strip()))

            if "auto_pot" not in self.config.data:
                self.config.data["auto_pot"] = dict(DEFAULT_POT_CONFIG)
            if "hp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["hp"] = dict(DEFAULT_POT_CONFIG["hp"])
            if "tp" not in self.config.data["auto_pot"]:
                self.config.data["auto_pot"]["tp"] = dict(DEFAULT_POT_CONFIG["tp"])

            self.config.data["auto_pot"]["hp"]["box"] = {"x": hx, "y": hy, "w": hw, "h": hh}
            self.config.data["auto_pot"]["tp"]["box"] = {"x": tx, "y": ty, "w": tw, "h": th}
            self.config.save()
            self._sync_pot_ui_from_config()
            self.append_log(f"🧪 [Auto Pot] Koordinat manual diterapkan: HP=({hx},{hy},{hw},{hh}), TP=({tx},{ty},{tw},{th}).")
            messagebox.showinfo("Sukses", "Koordinat manual HP & TP berhasil disimpan ke config!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menerapkan koordinat manual: {e}")

    def _sync_pot_ui_from_config(self):
        pot_cfg = self.config.get("auto_pot", DEFAULT_POT_CONFIG)
        hp_box = pot_cfg.get("hp", {}).get("box", {"x": 4, "y": 54, "w": 214, "h": 14})
        tp_box = pot_cfg.get("tp", {}).get("box", {"x": 4, "y": 69, "w": 214, "h": 14})

        self.lbl_hp_coords.config(text=f"HP box: X={hp_box.get('x', 4)} Y={hp_box.get('y', 54)} W={hp_box.get('w', 214)} H={hp_box.get('h', 14)}")
        self.lbl_tp_coords.config(text=f"TP box: X={tp_box.get('x', 4)} Y={tp_box.get('y', 69)} W={tp_box.get('w', 214)} H={tp_box.get('h', 14)}")

        for entry, val in [(self.e_hp_x, hp_box.get("x", 4)), (self.e_hp_y, hp_box.get("y", 54)),
                           (self.e_hp_w, hp_box.get("w", 214)), (self.e_hp_h, hp_box.get("h", 14)),
                           (self.e_tp_x, tp_box.get("x", 4)), (self.e_tp_y, tp_box.get("y", 69)),
                           (self.e_tp_w, tp_box.get("w", 214)), (self.e_tp_h, tp_box.get("h", 14))]:
            entry.delete(0, tk.END)
            entry.insert(0, str(val))

    def _update_pot_labels_with_values(self, hp_pct: Optional[float], tp_pct: Optional[float]):
        try:
            hp_thresh = float(self.entry_hp_threshold.get().strip() or "50")
        except ValueError:
            hp_thresh = 50.0

        try:
            tp_thresh = float(self.entry_tp_threshold.get().strip() or "50")
        except ValueError:
            tp_thresh = 50.0

        if hp_pct is not None:
            if hp_pct <= hp_thresh:
                color = "#f85149"
                tag = "[MINUM POT]"
            elif hp_pct <= 75.0:
                color = "#e3b341"
                tag = "[Waspada]"
            else:
                color = "#7ee787"
                tag = "[Aman]"
            self.lbl_hp_status.config(text=f"❤️ HP Saat Ini: {hp_pct:.1f}% {tag}", fg=color)
        else:
            self.lbl_hp_status.config(text="❤️ HP: Tidak terbaca", fg="#8b949e")

        if tp_pct is not None:
            if tp_pct <= tp_thresh:
                color = "#f85149"
                tag = "[MINUM POT]"
            elif tp_pct <= 75.0:
                color = "#e3b341"
                tag = "[Waspada]"
            else:
                color = "#58a6ff"
                tag = "[Aman]"
            self.lbl_tp_status.config(text=f"💙 TP Saat Ini: {tp_pct:.1f}% {tag}", fg=color)
        else:
            self.lbl_tp_status.config(text="💙 TP: Tidak terbaca", fg="#8b949e")

    def _update_pot_status(self):
        try:
            is_running = self.bot.pots.is_running
            hp_cnt = self.bot.pots.hp_pot_count
            tp_cnt = self.bot.pots.tp_pot_count
            hp_pct = self.bot.pots.current_hp_pct
            tp_pct = self.bot.pots.current_tp_pct

            if is_running:
                self.btn_pot_toggle.config(text="⏹️ Hentikan Auto Pot", bg="#da3633", fg="#ffffff")
                self.lbl_pot_running_status.config(text="● AUTO POT AKTIF", fg="#7ee787")
            else:
                self.btn_pot_toggle.config(text="▶️ Mulai Auto Pot (Standalone)", bg="#1f6feb", fg="#ffffff")
                self.lbl_pot_running_status.config(text="○ NONAKTIF", fg="#8b949e")

            self.lbl_hp_count.config(text=f"Total Diminum: {hp_cnt}")
            self.lbl_tp_count.config(text=f"Total Diminum: {tp_cnt}")

            if is_running and hp_pct is not None and tp_pct is not None:
                self._update_pot_labels_with_values(hp_pct, tp_pct)
        except Exception:
            pass
        self.after(300, self._update_pot_status)

    # =========================================================================
    # TAB 9: Settings
    # =========================================================================
    def _build_settings_tab(self):
        _, scroll_inner = self._create_scrollable_container(self.tab_settings)
        container = tk.Frame(scroll_inner, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Konfigurasi Kecepatan & Delay (NFR-1)", font=("Segoe UI", 11, "bold"), bg="#222428", fg="#58a6ff").pack(anchor=tk.W, pady=(0, 6))

        # Slider Box: Pengaturan Kecepatan Pergerakan Mouse (Issue #13)
        speed_box = tk.LabelFrame(
            container,
            text=" ⚡ Kecepatan Pergerakan Mouse & Pemindahan Item ",
            bg="#222428",
            fg="#58a6ff",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=10
        )
        speed_box.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            speed_box,
            text="Geser ke kiri untuk pergerakan pelan (stabil), atau ke kanan untuk kecepatan maksimal (hingga 10x lebih cepat):",
            bg="#222428",
            fg="#8b949e",
            font=("Segoe UI", 8),
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 6))

        slider_frame = tk.Frame(speed_box, bg="#222428")
        slider_frame.pack(fill=tk.X, pady=2)

        tk.Label(slider_frame, text="🐢 Pelan", font=("Segoe UI", 9, "bold"), bg="#222428", fg="#8b949e").pack(side=tk.LEFT, padx=(0, 10))

        cur_sp = int(self.config.get("delays", "speed_level", 5))

        self.speed_scale = tk.Scale(
            slider_frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            bg="#161b22",
            fg="#58a6ff",
            troughcolor="#0d1117",
            activebackground="#1f6feb",
            highlightthickness=0,
            font=("Segoe UI", 8),
            command=self._on_speed_slider_change
        )
        self.speed_scale.set(cur_sp)
        self.speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(slider_frame, text="⚡ 10x Maksimal", font=("Segoe UI", 9, "bold"), bg="#222428", fg="#3fb950").pack(side=tk.LEFT, padx=(10, 0))

        self.speed_status_lbl = tk.Label(
            speed_box,
            text="",
            bg="#222428",
            fg="#3fb950",
            font=("Segoe UI", 9, "bold")
        )
        self.speed_status_lbl.pack(anchor=tk.W, pady=(6, 0))
        self._update_speed_label(cur_sp)

        # Advanced Fields Box
        adv_box = tk.LabelFrame(
            container,
            text=" ⚙️ Pengaturan Delay & Parameter Tambahan ",
            bg="#222428",
            fg="#8b949e",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=8
        )
        adv_box.pack(fill=tk.X, pady=(0, 5))

        grid = tk.Frame(adv_box, bg="#222428")
        grid.pack(fill=tk.X, pady=4)

        self.entries = {}
        fields = [
            ("Jeda Hover Tooltip NPC (detik):", "delays", "hover_delay_sec"),
            ("Timeout Pop-up Konfirmasi Jual (detik):", "delays", "popup_wait_timeout_sec"),
            ("Timeout Tunggu Item Terjual (detik):", "delays", "sell_wait_timeout_sec"),
            ("Jeda Pasca Jual NPC (detik):", "delays", "sell_post_delay_sec"),
            ("Sensitivitas Deteksi Kosong (StdDev):", "rules", "empty_slot_threshold"),
            ("Threshold Match Blacklist Jual (0.5 - 1.0):", "rules", "sell_whitelist_match_threshold"),
            ("Threshold Match Blacklist Simpan Gudang (0.5 - 1.0):", "rules", "storage_blacklist_match_threshold"),
            ("Threshold Match Blacklist Tarik Gudang (0.5 - 1.0):", "rules", "storage_withdraw_blacklist_match_threshold"),
            ("Threshold Match Popup Storage (0.5 - 1.0):", "storage_popup", "match_threshold"),
            ("Interval Cek Auto Hunt (detik):", "delays", "hunt_loop_interval_sec"),
            ("Waktu Jalan ke Merchant (detik 'W'):", "auto_nav", "walk_to_merchant_sec"),
            ("Waktu Jalan ke Gudang (detik 'S'):", "auto_nav", "walk_to_storage_sec"),
            ("Klik Offset NPC Y (bawah tag kuning):", "auto_nav", "npc_click_y_offset"),
            ("Klik Popup Storage X (Teks Kiri Atas):", "storage_popup", "click_x"),
            ("Klik Popup Storage Y (Teks Kiri Atas):", "storage_popup", "click_y"),
        ]

        for i, (label_text, sec, key) in enumerate(fields):
            tk.Label(grid, text=label_text, bg="#222428", fg="#e1e2e6").grid(row=i, column=0, sticky=tk.W, pady=6, padx=(0, 15))
            val = self.config.get(sec, key)
            if val is None and key in ("storage_blacklist_match_threshold", "storage_withdraw_blacklist_match_threshold"):
                val = self.config.get("rules", "sell_whitelist_match_threshold", 0.50)
            if val is None and key == "match_threshold":
                val = 0.70
            if val is None and key == "sell_wait_timeout_sec":
                val = 2.0
            if val is None and key == "sell_post_delay_sec":
                val = 0.35
            e = tk.Entry(grid, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", width=12)
            e.insert(0, str(val))
            e.grid(row=i, column=1, sticky=tk.W, pady=6)
            self.entries[(sec, key)] = e

        # Low-Spec Mode Checkbox (Issue #14)
        low_spec_box = tk.LabelFrame(container, text=" 🐢 Optimasi Performa PC (Low-End / Mini-PC Wearnes MP-8101) ", bg="#222428", fg="#d29922", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        low_spec_box.pack(fill=tk.X, pady=(15, 0))

        self.var_low_spec_mode = tk.BooleanVar(value=bool(self.config.get("auto_nav", "low_spec_mode", False)))
        tk.Checkbutton(
            low_spec_box,
            text="Aktifkan Mode PC Low-Spec (Core i3, RAM 4GB)\n"
                 "• Memperpanjang jeda rotasi kamera dan render frame agar tidak blur / drop FPS.\n"
                 "• Mengatasi masalah kamera berputar-putar tanpa henti saat mencari NPC Ashuri.",
            variable=self.var_low_spec_mode,
            bg="#222428",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#222428",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9),
            justify=tk.LEFT,
            command=self._on_toggle_low_spec_mode
        ).pack(anchor=tk.W)

        # Hotkeys Configuration Box
        hk_box = tk.LabelFrame(container, text=" ⌨️ Pengaturan Shortcut / Global Hotkeys ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        hk_box.pack(fill=tk.X, pady=(15, 0))

        tk.Label(
            hk_box,
            text="Ganti tombol shortcut di bawah ini jika menggunakan Remote Desktop (AnyDesk/TeamViewer/RDP):",
            bg="#222428",
            fg="#8b949e",
            font=("Segoe UI", 8)
        ).pack(anchor=tk.W, pady=(0, 6))

        hk_grid = tk.Frame(hk_box, bg="#222428")
        hk_grid.pack(anchor=tk.W)

        hk_fields = [
            ("Mulai Makro (Start):", "start", "f11"),
            ("Hentikan Makro (Stop):", "stop", "f12"),
            ("Shortcut Auto Tarik & Jual Loop:", "auto_loop", "f7"),
            ("Shortcut Storage -> Tas:", "storage_to_inv", "f9"),
            ("Shortcut Tas -> NPC Merchant:", "inv_to_merchant", "f10"),
            ("Shortcut Tutup Popup Storage:", "dismiss_popup", "f8"),
        ]

        self.hk_entries = {}
        for idx, (label_text, hk_key, def_val) in enumerate(hk_fields):
            tk.Label(hk_grid, text=label_text, bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=idx, column=0, sticky=tk.W, pady=4, padx=(0, 15))
            cur_val = self.config.get("hotkeys", hk_key, def_val)
            e = tk.Entry(hk_grid, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", width=14, font=("Segoe UI", 9))
            e.insert(0, str(cur_val))
            e.grid(row=idx, column=1, sticky=tk.W, pady=4)
            self.hk_entries[hk_key] = e

        tk.Button(
            container,
            text="💾 Simpan Pengaturan",
            font=("Segoe UI", 10, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            command=self.save_settings
        ).pack(anchor=tk.W, pady=15)

        # Security & Password Change
        sec_box = tk.LabelFrame(container, text=" 🔐 Keamanan & Ganti Password Akses ", bg="#222428", fg="#d29922", font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        sec_box.pack(fill=tk.X, pady=(15, 0))

        sec_grid = tk.Frame(sec_box, bg="#222428")
        sec_grid.pack(anchor=tk.W)

        tk.Label(sec_grid, text="Password Baru:", bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        self.entry_new_pwd = tk.Entry(sec_grid, bg="#161b22", fg="#e1e2e6", show="●", insertbackground="#ffffff", width=20, font=("Segoe UI", 9))
        self.entry_new_pwd.grid(row=0, column=1, sticky=tk.W, pady=4)

        tk.Label(sec_grid, text="Konfirmasi Password:", bg="#222428", fg="#e1e2e6", font=("Segoe UI", 9)).grid(row=1, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        self.entry_confirm_pwd = tk.Entry(sec_grid, bg="#161b22", fg="#e1e2e6", show="●", insertbackground="#ffffff", width=20, font=("Segoe UI", 9))
        self.entry_confirm_pwd.grid(row=1, column=1, sticky=tk.W, pady=4)

        tk.Button(
            sec_box,
            text="🔑 Perbarui Password Akses",
            font=("Segoe UI", 9, "bold"),
            bg="#30363d",
            fg="#58a6ff",
            relief="flat",
            padx=12,
            pady=4,
            command=self._change_password
        ).pack(anchor=tk.W, pady=(8, 0))

        # App Info & Version Card
        info_box = tk.LabelFrame(container, text=f" ℹ️ Informasi Aplikasi ({APP_VERSION}) ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        info_box.pack(fill=tk.X, pady=(15, 0))

        start_k = self.config.get("hotkeys", "start", "f11").upper()
        stop_k = self.config.get("hotkeys", "stop", "f12").upper()
        s2i_k = self.config.get("hotkeys", "storage_to_inv", "f9").upper()
        i2n_k = self.config.get("hotkeys", "inv_to_merchant", "f10").upper()
        pop_k = self.config.get("hotkeys", "dismiss_popup", "f8").upper()

        info_text = (
            f"TantraFarmer Macro Versi: {APP_VERSION}\n"
            f"Daftar Global Shortcut Aktif:\n"
            f"  • [{start_k}]        : Jalankan Macro (Sesuai mode yang dipilih di Dashboard)\n"
            f"  • [{stop_k}]        : Hentikan / Stop Macro\n"
            f"  • [{s2i_k}]         : Langsung Tarik Item dari Storage ke Tas (Storage -> Inventory)\n"
            f"  • [{i2n_k}]        : Langsung Jual Item dari Tas ke NPC Merchant (Inventory -> NPC)\n"
            f"  • [{pop_k}]         : Tutup Popup Modal Storage (Notice, Quiz, Raffle, Lucky Number)"
        )
        self.lbl_info_shortcuts = tk.Label(info_box, text=info_text, bg="#222428", fg="#c9d1d9", font=("Segoe UI", 9), justify=tk.LEFT)
        self.lbl_info_shortcuts.pack(anchor=tk.W)

        btn_info_row = tk.Frame(info_box, bg="#222428")
        btn_info_row.pack(anchor=tk.W, pady=(8, 0))

        tk.Button(
            btn_info_row,
            text=f"🛡️ Tes Tutup Popup Storage Sekarang [{pop_k}]",
            font=("Segoe UI", 9, "bold"),
            bg="#d29922",
            fg="#0d1117",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self.run_specific_task("dismiss_popup")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_info_row,
            text="🔄 Cek Pembaruan (Auto-Update)",
            font=("Segoe UI", 9, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: self._check_update_in_background(silent=False)
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_info_row,
            text="💬 Laporkan Bug / Masukan",
            font=("Segoe UI", 9, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            command=lambda: webbrowser.open("https://github.com/bivacandra/farmer/issues")
        ).pack(side=tk.LEFT)

    def _on_speed_slider_change(self, val):
        try:
            sp = int(val)
        except Exception:
            sp = 5
        self._update_speed_label(sp)

    def _update_speed_label(self, sp: int):
        if not hasattr(self, "speed_status_lbl"):
            return
        desc_map = {
            1: "Level 1: 🐢 Paling Pelan (~0.8s/item) - Sangat stabil, aman untuk PC/koneksi berat",
            2: "Level 2: 🐢 Pelan (~0.65s/item)",
            3: "Level 3: 🟢 Agak Pelan (~0.5s/item)",
            4: "Level 4: 🟢 Normal Ringan (~0.4s/item)",
            5: "Level 5: ⚖️ Standar / Seimbang (~0.35s/item) - Rekomendasi bawaan",
            6: "Level 6: ⚡ Cepat (~0.25s/item)",
            7: "Level 7: ⚡ Sangat Cepat (~0.18s/item)",
            8: "Level 8: 🚀 Super Cepat (~0.12s/item)",
            9: "Level 9: 🚀 Ultra Cepat (~0.09s/item)",
            10: "Level 10: ⚡⚡ MAKSIMAL 10X (~0.05s/item) - Kecepatan transfer item tertinggi!"
        }
        self.speed_status_lbl.config(text=desc_map.get(sp, f"Level {sp}"))

    def _on_toggle_low_spec_mode(self):
        val = self.var_low_spec_mode.get()
        self.config.set("auto_nav", "low_spec_mode", val)
        self.config.save()
        status_text = "AKTIF (Optimasi Core i3 / RAM 4GB)" if val else "NON-AKTIF"
        self.append_log(f"🐢 Mode PC Low-Spec diatur ke: {status_text}")

    def save_settings(self):
        try:
            for (sec, key), e in self.entries.items():
                val_str = e.get().strip()
                if "." in val_str:
                    val = float(val_str)
                else:
                    val = int(val_str)
                self.config.set(sec, key, val)

            # Simpan Slider Kecepatan Mouse (Issue #13)
            if hasattr(self, "speed_scale"):
                sp = int(self.speed_scale.get())
                self.config.set("delays", "speed_level", sp)
                drag_dur = round(max(0.02, 0.35 - (sp - 1) * 0.036), 3)
                post_dur = round(max(0.02, 0.25 - (sp - 1) * 0.025), 3)
                self.config.set("delays", "drag_duration_sec", drag_dur)
                self.config.set("delays", "post_action_delay_sec", post_dur)

            # Simpan Mode PC Low-Spec (Issue #14)
            if hasattr(self, "var_low_spec_mode"):
                self.config.set("auto_nav", "low_spec_mode", bool(self.var_low_spec_mode.get()))

            # Simpan Shortcut Keyboard
            if hasattr(self, "hk_entries"):
                if "hotkeys" not in self.config.data:
                    self.config.data["hotkeys"] = {}
                for hk_key, entry in self.hk_entries.items():
                    val = entry.get().strip().lower()
                    if val:
                        self.config.data["hotkeys"][hk_key] = val
                self._setup_hotkeys()

            self.config.save()
            messagebox.showinfo("Sukses", "Pengaturan kecepatan dan shortcut berhasil disimpan!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan: {e}")

    def _change_password(self):
        p1 = self.entry_new_pwd.get().strip()
        p2 = self.entry_confirm_pwd.get().strip()
        if not p1:
            messagebox.showwarning("Peringatan", "Password baru tidak boleh kosong!")
            return
        if p1 != p2:
            messagebox.showerror("Error", "Password baru dan konfirmasi tidak cocok!")
            return

        new_hash = hash_password(p1)
        self.config.set("security", "password_hash", new_hash)
        self.config.save()
        self.entry_new_pwd.delete(0, tk.END)
        self.entry_confirm_pwd.delete(0, tk.END)
        messagebox.showinfo("Sukses", "Password akses aplikasi berhasil diperbarui!")

    def _build_footer(self):
        footer = tk.Frame(self, bg="#161b22", height=24, padx=12, pady=4)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(footer, text=f"Antigravity Tantra Farmer {APP_VERSION} • Resolution Independent • DirectInput Engine", font=("Segoe UI", 8), bg="#161b22", fg="#8b949e").pack(side=tk.LEFT)

    def _setup_hotkeys(self, verbose: bool = True):
        if HAS_KEYBOARD and sys.platform == "win32":
            try:
                try:
                    keyboard.unhook_all_hotkeys()
                except Exception:
                    pass

                start_hk = self.config.get("hotkeys", "start", "f11")
                stop_hk = self.config.get("hotkeys", "stop", "f12")
                abort_hk = self.config.get("hotkeys", "emergency_abort", None)
                s2i_hk = self.config.get("hotkeys", "storage_to_inv", "f9")
                i2n_hk = self.config.get("hotkeys", "inv_to_merchant", "f10")
                pop_hk = self.config.get("hotkeys", "dismiss_popup", "f8")
                loop_hk = self.config.get("hotkeys", "auto_loop", "f7")

                if start_hk:
                    keyboard.add_hotkey(start_hk, lambda: self.after(0, self.start_macro))
                if stop_hk:
                    keyboard.add_hotkey(stop_hk, lambda: self.after(0, self.stop_macro))
                if abort_hk and abort_hk.lower() not in ["esc", "escape"]:
                    keyboard.add_hotkey(abort_hk, lambda: self.after(0, self.stop_macro))
                if s2i_hk:
                    keyboard.add_hotkey(s2i_hk, lambda: self.after(0, self.run_specific_task, "storage_to_inv"))
                if i2n_hk:
                    keyboard.add_hotkey(i2n_hk, lambda: self.after(0, self.run_specific_task, "inv_to_merchant"))
                if pop_hk:
                    keyboard.add_hotkey(pop_hk, lambda: self.after(0, self.run_specific_task, "dismiss_popup"))
                if loop_hk:
                    keyboard.add_hotkey(loop_hk, lambda: self.after(0, self.run_specific_task, "auto_storage_merchant_loop"))

                try:
                    keyboard.add_hotkey("shift+end", lambda: self.after(0, self.test_pot_reading, False))
                except Exception:
                    pass

                if verbose:
                    self.append_log(
                        f"Global Hotkeys aktif: {start_hk.upper()} (Start), {stop_hk.upper()} (Stop), {loop_hk.upper()} (Auto Loop), "
                        f"{s2i_hk.upper()} (Storage->Tas), {i2n_hk.upper()} (Tas->NPC), {pop_hk.upper()} (Tutup Popup)."
                    )
                self._update_hotkey_labels()
            except Exception as e:
                if verbose:
                    self.append_log(f"Warning: Failed to hook global keyboard hotkeys: {e}")

    def _update_hotkey_labels(self):
        start_hk = self.config.get("hotkeys", "start", "f11").upper()
        stop_hk = self.config.get("hotkeys", "stop", "f12").upper()
        s2i_hk = self.config.get("hotkeys", "storage_to_inv", "f9").upper()
        i2n_hk = self.config.get("hotkeys", "inv_to_merchant", "f10").upper()
        pop_hk = self.config.get("hotkeys", "dismiss_popup", "f8").upper()
        loop_hk = self.config.get("hotkeys", "auto_loop", "f7").upper()

        if hasattr(self, "status_badge") and not getattr(self, "is_character_dead", False) and not self.bot.is_running:
            self.status_badge.config(text=f"IDLE ({start_hk} | {stop_hk})")
        if hasattr(self, "btn_start"):
            self.btn_start.config(text=f"▶ MULAI ({start_hk})")
        if hasattr(self, "btn_stop"):
            self.btn_stop.config(text=f"⏹ STOP ({stop_hk})")
        if hasattr(self, "btn_quick_loop"):
            self.btn_quick_loop.config(text=f"🔄 Auto Loop [{loop_hk}]")
        if hasattr(self, "btn_quick_s2i"):
            self.btn_quick_s2i.config(text=f"📦 Tarik Storage [{s2i_hk}]")
        if hasattr(self, "btn_quick_i2n"):
            self.btn_quick_i2n.config(text=f"💰 Jual NPC [{i2n_hk}]")
        if hasattr(self, "btn_quick_popup"):
            self.btn_quick_popup.config(text=f"🛡️ Tutup Popup [{pop_hk}]")
        if hasattr(self, "lbl_info_shortcuts"):
            info_text = (
                f"TantraFarmer Macro Versi: {APP_VERSION}\n"
                f"Daftar Global Shortcut Aktif:\n"
                f"  • [{start_hk}]        : Jalankan Macro (Sesuai mode yang dipilih di Dashboard)\n"
                f"  • [{stop_hk}]        : Hentikan / Stop Macro\n"
                f"  • [{s2i_hk}]         : Langsung Tarik Item dari Storage ke Tas (Storage -> Inventory)\n"
                f"  • [{i2n_hk}]        : Langsung Jual Item dari Tas ke NPC Merchant (Inventory -> NPC)\n"
                f"  • [{pop_hk}]         : Tutup Popup Modal Storage (Notice, Quiz, Raffle, Lucky Number)"
            )
            self.lbl_info_shortcuts.config(text=info_text)

    def append_log(self, text: str):
        def _append():
            ts = time.strftime("[%H:%M:%S] ")
            self.txt_log.insert(tk.END, ts + text + "\n")
            self.txt_log.see(tk.END)
        self.after(0, _append)

    def zeroin_game_window(self):
        """Move the game window to screen coordinate (0, 0)."""
        if not self.wm.hwnd:
            self.wm.find_window()

        if not self.wm.hwnd:
            self.append_log("⚠️ Jendela game belum terdeteksi. Buka game atau pilih jendela via 'Cek Window'.")
            self.open_window_picker()
            return

        success = self.wm.zero_in_window()
        if success:
            self.append_log(f"📍 Window game '{self.wm.window_title}' berhasil diposisikan ke koordinat (0, 0).")
        else:
            self.append_log("⚠️ Gagal memposisikan window game ke (0, 0).")

    def snap_macro_beside_game(self):
        """Snaps the macro window right beside the game window so they don't overlap."""
        if not self.wm.hwnd:
            self.wm.find_window()

        if not self.wm.hwnd:
            self.append_log("⚠️ Jendela game belum terdeteksi. Buka game atau pilih jendela via 'Cek Window'.")
            self.open_window_picker()
            return

        self.wm.update_bounds()
        if not self.wm.window_rect:
            self.append_log("⚠️ Gagal membaca batas koordinat jendela game.")
            return

        left, top, right, bottom = self.wm.window_rect
        self.update_idletasks()
        cur_w = self.winfo_width()
        cur_h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        target_x = right
        target_y = max(0, top)

        # Ensure macro window stays nicely visible on screen
        if target_x + cur_w > sw:
            if sw > right:
                # Align as close to right edge of screen as possible
                target_x = max(0, sw - cur_w)
            elif left >= cur_w:
                # If there's room on the left side of the game window
                target_x = max(0, left - cur_w)

        # Ensure target_y does not push window below taskbar/screen bottom
        if target_y + cur_h > sh:
            target_y = max(0, sh - cur_h - 40)

        self.geometry(f"{cur_w}x{cur_h}+{target_x}+{target_y}")
        self.append_log(f"🧲 Makro ditempelkan di samping game: X={target_x}, Y={target_y}")

    def check_game_window(self):
        found = self.wm.find_window()
        if found:
            origin_x, origin_y, w, h = self.wm.client_rect or (0, 0, 0, 0)
            messagebox.showinfo(
                "Jendela Game Ditemukan",
                f"Jendela game terdeteksi!\n\n"
                f"Judul: '{self.wm.window_title}'\n"
                f"Posisi Klien: ({origin_x}, {origin_y})\n"
                f"Ukuran Klien: {w}x{h}"
            )
            self.append_log(f"Game terhubung: '{self.wm.window_title}' ({w}x{h})")
        else:
            self.open_window_picker()

    def open_window_picker(self):
        win = tk.Toplevel(self)
        win.title("Pilih Jendela Game dari Daftar")
        win.geometry("580x430")
        win.configure(bg="#222428")

        tk.Label(
            win,
            text="Jendela game otomatis belum cocok dengan kata kunci ('Kathana' / 'Tantra').\nSilakan pilih jendela game Anda dari daftar aktif di bawah:",
            font=("Segoe UI", 10),
            bg="#222428",
            fg="#e1e2e6",
            justify=tk.LEFT
        ).pack(padx=12, pady=(12, 6), anchor=tk.W)

        frame_list = tk.Frame(win, bg="#161b22")
        frame_list.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        scroll = tk.Scrollbar(frame_list)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        lb = tk.Listbox(
            frame_list,
            bg="#0d1117",
            fg="#58a6ff",
            selectbackground="#2a75d3",
            selectforeground="#ffffff",
            font=("Consolas", 10),
            yscrollcommand=scroll.set
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=lb.yview)

        windows = self.wm.get_visible_windows()
        for hwnd, title in windows:
            lb.insert(tk.END, f"[{hwnd}] {title}")

        def on_select():
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("Perhatian", "Pilih salah satu jendela dari daftar terlebih dahulu.", parent=win)
                return
            idx = sel[0]
            chosen_hwnd, chosen_title = windows[idx]
            self.wm.find_window(exact_hwnd=chosen_hwnd)
            self.wm.window_title = chosen_title

            patterns = self.config.get("window", "title_patterns", [])
            if chosen_title not in patterns:
                patterns.insert(0, chosen_title)
                self.config.set("window", "title_patterns", patterns)
                self.config.save()

            origin_x, origin_y, w, h = self.wm.client_rect or (0, 0, 0, 0)
            self.append_log(f"Jendela berhasil dihubungkan: '{chosen_title}' ({w}x{h})")
            win.destroy()
            messagebox.showinfo("Sukses Terhubung", f"Jendela game berhasil dihubungkan!\n\nJudul: {chosen_title}\nUkuran Klien: {w}x{h}")

        btn_bar = tk.Frame(win, bg="#222428")
        btn_bar.pack(fill=tk.X, padx=12, pady=10)

        tk.Button(
            btn_bar,
            text="✔ Hubungkan Jendela Terpilih",
            font=("Segoe UI", 10, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            command=on_select
        ).pack(side=tk.LEFT)

        def refresh_list():
            nonlocal windows
            lb.delete(0, tk.END)
            windows = self.wm.get_visible_windows()
            for hwnd, title in windows:
                lb.insert(tk.END, f"[{hwnd}] {title}")

        tk.Button(
            btn_bar,
            text="🔄 Segarkan Daftar",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=6,
            command=refresh_list
        ).pack(side=tk.RIGHT)

    def start_macro(self):
        if self.bot.is_running:
            return

        self.is_character_dead = False
        self._apply_skill_gui_to_config(save_to_disk=False)
        self.bot.input.reset_abort()
        mode = self.selected_mode.get()
        self.status_badge.config(text=f"RUNNING ({mode})", fg="#ffffff", bg="#238636")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        def runner():
            try:
                # Bawa game window ke foreground sebelum macro mulai berinteraksi
                self.wm.activate_window()
                time.sleep(0.3)

                if mode == "hunt_auto_deposit":
                    self.bot.run_hunt_auto_deposit()
                elif mode == "auto_skill_standalone":
                    self.bot.is_running = True
                    self.bot.skills.start()
                    pot_cfg = self.config.get("auto_pot", {})
                    if pot_cfg.get("enabled", True) and pot_cfg.get("sync_with_auto_hunt", True):
                        self.bot.pots.start()
                    try:
                        last_death_check = 0.0
                        while self.bot.is_running:
                            now = time.time()
                            if now - last_death_check >= 1.5:
                                last_death_check = now
                                client_img = self.screen.capture_client()
                                if self.matcher.detect_death_popup(client_img):
                                    self.append_log("🚨 [SAFETY STOP] Karakter mati terdeteksi! Menghentikan Auto Skill.")
                                    self._on_character_death()
                                    break
                            time.sleep(0.2)
                    finally:
                        self.bot.skills.stop()
                        self.bot.pots.stop()
                        self.bot.is_running = False
                elif mode == "auto_pot_standalone":
                    self.bot.is_running = True
                    self.bot.pots.start()
                    try:
                        last_death_check = 0.0
                        while self.bot.is_running:
                            now = time.time()
                            if now - last_death_check >= 1.5:
                                last_death_check = now
                                client_img = self.screen.capture_client()
                                if self.matcher.detect_death_popup(client_img):
                                    self.append_log("🚨 [SAFETY STOP] Karakter mati terdeteksi! Menghentikan Auto Pot.")
                                    self._on_character_death()
                                    break
                            time.sleep(0.2)
                    finally:
                        self.bot.pots.stop()
                        self.bot.is_running = False
                elif mode == "inv_to_storage":
                    self.bot.run_inventory_to_storage()
                elif mode == "storage_to_inv":
                    self.bot.run_storage_to_inventory()
                elif mode == "inv_to_merchant":
                    self.bot.run_inventory_to_npc()
                elif mode == "auto_storage_merchant_loop":
                    self.bot.run_auto_storage_merchant_loop()
            finally:
                self.after(0, self._on_macro_finished)

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def run_specific_task(self, task_name: str):
        if self.bot.is_running:
            if hasattr(self, 'worker_thread') and self.worker_thread and not self.worker_thread.is_alive():
                self.bot.is_running = False
            else:
                stop_k = self.config.get("hotkeys", "stop", "f12").upper()
                self.append_log(f"Peringatan: Macro sedang berjalan. Tekan {stop_k} terlebih dahulu untuk menghentikan.")
                return

        self._apply_skill_gui_to_config(save_to_disk=False)
        self.bot.input.reset_abort()
        self.status_badge.config(text=f"RUNNING ({task_name})", fg="#ffffff", bg="#238636")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        def runner():
            try:
                self.wm.activate_window()
                time.sleep(0.3)

                if task_name == "storage_to_inv":
                    self.bot.run_storage_to_inventory()
                elif task_name == "inv_to_merchant":
                    self.bot.run_inventory_to_npc()
                elif task_name == "inv_to_storage":
                    self.bot.run_inventory_to_storage()
                elif task_name == "dismiss_popup":
                    self.bot.dismiss_storage_popup()
                elif task_name == "auto_storage_merchant_loop":
                    self.bot.run_auto_storage_merchant_loop()
            finally:
                self.after(0, self._on_macro_finished)

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def stop_macro(self):
        self.bot.stop()
        self._on_macro_finished()
        self._setup_hotkeys(verbose=False)

    def _on_macro_finished(self):
        if getattr(self, "is_character_dead", False):
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
            return

        start_hk = self.config.get("hotkeys", "start", "f11").upper()
        stop_hk = self.config.get("hotkeys", "stop", "f12").upper()
        self.status_badge.config(text=f"IDLE ({start_hk} | {stop_hk})", fg="#3fb950", bg="#161b22")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        # Re-register global hotkeys to refresh hooks dropped by Windows during active simulation (Issue #12)
        self._setup_hotkeys(verbose=False)

    def _on_character_death(self):
        self.is_character_dead = True
        def _update():
            self.bot.stop()
            self.status_badge.config(
                text="🚨 KARAKTER MATI (Makro Dihentikan)",
                bg="#da3633",
                fg="#ffffff"
            )
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
            self.append_log("🚨 [PERINGATAN] Makro dihentikan otomatis karena mendeteksi popup respawn (Karakter Telah Mati)!")
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                try:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                except Exception:
                    pass
        self.after(0, _update)

    # =========================================================================
    # AUTO-UPDATER & NOTIFIKASI PEMBARUAN
    # =========================================================================
    def _check_update_in_background(self, silent: bool = True):
        def _bg():
            try:
                info = check_for_updates(APP_VERSION)
                if info:
                    self.after(0, lambda: self._on_update_found(info, silent=silent))
                elif not silent:
                    self.after(0, lambda: messagebox.showinfo("Pembaruan", f"Aplikasi Anda sudah versi terbaru ({APP_VERSION})."))
            except Exception as e:
                if not silent:
                    self.after(0, lambda: messagebox.showerror("Gagal Cek Update", f"Terjadi kesalahan saat memeriksa update: {e}"))

        threading.Thread(target=_bg, daemon=True).start()

    def _on_update_found(self, update_info: dict, silent: bool = False):
        latest = update_info.get("latest_version", "")
        # Tampilkan badge/tombol update di header jika belum ada
        if hasattr(self, "header_frame") and self.header_frame.winfo_exists():
            if not hasattr(self, "btn_update_pill") or not self.btn_update_pill.winfo_exists():
                self.btn_update_pill = tk.Button(
                    self.header_frame,
                    text=f"⚡ Update {latest} Tersedia!",
                    font=("Segoe UI", 9, "bold"),
                    bg="#d29922",
                    fg="#0d1117",
                    activebackground="#e3b341",
                    relief="flat",
                    padx=8,
                    pady=2,
                    command=lambda: self.prompt_update(update_info)
                )
                self.btn_update_pill.pack(side=tk.LEFT, padx=(10, 0))

        self.append_log(f"🔔 Pembaruan tersedia: {latest} (versi saat ini: {APP_VERSION}).")

        # Tampilkan pop-up dialog konfirmasi update
        self.prompt_update(update_info)

    def prompt_update(self, update_info: dict):
        latest = update_info.get("latest_version", "")
        size_mb = update_info.get("asset_size", 0) / (1024 * 1024)
        notes = update_info.get("release_notes", "").strip()
        if len(notes) > 220:
            notes = notes[:217] + "..."

        msg = (
            f"Versi Baru Tersedia: {latest}\n"
            f"Versi Anda Saat Ini: {APP_VERSION}\n"
            f"Ukuran File: {size_mb:.1f} MB\n\n"
        )
        if notes:
            msg += f"Catatan Rilis:\n{notes}\n\n"
        msg += "Apakah Anda ingin memperbarui secara otomatis sekarang?\n(Pengaturan & Ikon kalibrasi Anda tetap aman)."

        ans = messagebox.askyesno("Pembaruan Tersedia", msg)
        if ans:
            self.start_download_update(update_info)

    def start_download_update(self, update_info: dict):
        latest = update_info.get("latest_version", "")
        url = update_info.get("download_url", "")
        if not url:
            messagebox.showerror("Error", "URL unduhan pembaruan tidak ditemukan.")
            return

        # Modal dialog progres unduh
        dlg = tk.Toplevel(self)
        dlg.title(f"Mengunduh Pembaruan {latest}")
        dlg.geometry("450x180")
        dlg.configure(bg="#222428")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"450x180+{(sw - 450) // 2}+{(sh - 180) // 2}")

        tk.Label(
            dlg,
            text=f"Mengunduh TantraFarmer {latest}...",
            font=("Segoe UI", 11, "bold"),
            bg="#222428",
            fg="#58a6ff"
        ).pack(pady=(16, 6))

        pbar = ttk.Progressbar(dlg, orient="horizontal", length=380, mode="determinate")
        pbar.pack(pady=8)

        lbl_status = tk.Label(
            dlg,
            text="Menghubungkan ke server GitHub...",
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#c9d1d9"
        )
        lbl_status.pack(pady=4)

        is_cancelled = False

        def on_cancel():
            nonlocal is_cancelled
            is_cancelled = True
            dlg.destroy()

        btn_cancel = tk.Button(dlg, text="Batal", bg="#30363d", fg="#e1e2e6", relief="flat", padx=12, pady=4, command=on_cancel)
        btn_cancel.pack(pady=(6, 0))

        def _download_thread():
            try:
                def progress_cb(dl, total):
                    if is_cancelled:
                        return
                    pct = int((dl / total) * 100) if total > 0 else 0
                    dl_mb = dl / (1024 * 1024)
                    tot_mb = total / (1024 * 1024)

                    def update_ui():
                        pbar["value"] = pct
                        lbl_status.config(text=f"{dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%)")

                    dlg.after(0, update_ui)

                if getattr(sys, "frozen", False):
                    target_dir = Path(sys.executable).resolve().parent
                else:
                    target_dir = self.config.base_dir
                new_file = download_update(url, target_dir, progress_callback=progress_cb, cancel_flag=lambda: is_cancelled)

                if is_cancelled:
                    return

                def on_done():
                    lbl_status.config(text="✓ Unduhan selesai! Menerapkan pembaruan & restart...", fg="#7ee787")
                    btn_cancel.config(state=tk.DISABLED)
                    dlg.after(600, lambda: apply_update_and_restart(new_file))

                dlg.after(0, on_done)
            except InterruptedError:
                pass
            except Exception as e:
                def on_err():
                    if dlg.winfo_exists():
                        dlg.destroy()
                    messagebox.showerror("Gagal Update", f"Error saat mengunduh pembaruan: {e}")

                dlg.after(0, on_err)

        threading.Thread(target=_download_thread, daemon=True).start()


if __name__ == "__main__":
    import traceback
    try:
        app = FarmerGUI()
        app.mainloop()
    except Exception as e:
        with open("crash.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Tantra Farmer - Error",
                f"Aplikasi gagal dimulai:\n\n{traceback.format_exc()}\n\nDetail error telah dicatat di file crash.log"
            )
        except Exception:
            pass
