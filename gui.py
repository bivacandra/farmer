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

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Tab 1: Dashboard / Runner
        self.tab_dashboard = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_dashboard, text=" Dashboard & Kontrol ")
        self._build_dashboard_tab()

        # Tab 2: Area Calibration (Select Area)
        self.tab_area = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_area, text=" 🎯 Kalibrasi Area (Select Area) ")
        self._build_area_tab()

        # Tab 3: Visual Slot Inspector (Empty vs Occupied)
        self.tab_inspector = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_inspector, text=" 🔍 Deteksi Slot Kosong ")
        self._build_inspector_tab()

        # Tab 4: Blacklist Simpan Gudang (Tas -> Gudang)
        self.tab_storage_whitelist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_storage_whitelist, text=" 🚫 Blacklist Simpan Gudang ")
        self._build_storage_whitelist_tab()

        # Tab 5: Blacklist Tarik Gudang (Gudang -> Tas)
        self.tab_storage_withdraw_blacklist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_storage_withdraw_blacklist, text=" 🚫 Blacklist Tarik Gudang ")
        self._build_storage_withdraw_blacklist_tab()

        # Tab 6: Blacklist Jual Merchant NPC
        self.tab_whitelist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_whitelist, text=" 🚫 Blacklist Jual NPC ")
        self._build_whitelist_tab()

        # Tab 6: Auto Skill
        self.tab_skill = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_skill, text=" ⚡ Auto Skill ")
        self._build_skill_tab()

        # Tab 7: Settings
        self.tab_settings = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_settings, text=" Pengaturan & Delay ")
        self._build_settings_tab()

    # =========================================================================
    # TAB 1: Dashboard
    # =========================================================================
    def _build_dashboard_tab(self):
        container = tk.Frame(self.tab_dashboard, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        mode_frame = tk.LabelFrame(container, text=" Pilih Mode Operasi ", bg="#222428", fg="#58a6ff", font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        mode_frame.pack(fill=tk.X, pady=(0, 12))

        self.selected_mode = tk.StringVar(value="auto_storage_merchant_loop")

        modes = [
            ("🔄 Full Auto Loop (Tarik Gudang Abahan & Jual ke Jeweler Ashuri)", "auto_storage_merchant_loop"),
            ("⚔️ Auto Hunt Loop (Auto Pindah ke Gudang + Auto Skill sambil Hunt)", "hunt_auto_deposit"),
            ("⚡ Auto Skill Standalone (Hanya Jalankan Auto Skill tanpa pindah tas)", "auto_skill_standalone"),
            ("Inventory -> Storage (Sekali jalan: Simpan ke Gudang dengan Filter Blacklist)", "inv_to_storage"),
            ("Storage -> Inventory (Sekali jalan: Tarik barang ke Slot Kosong Tas)", "storage_to_inv"),
            ("Inventory -> NPC Merchant (Sekali jalan: Jual item tas kecuali Blacklist)", "inv_to_merchant")
        ]

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
                font=("Segoe UI", 10)
            )
            rb.pack(anchor=tk.W, pady=3)

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

        desc = tk.Label(
            container,
            text="Aturan Pemindahan Tas (Inventory) ke Gudang (Storage):\n"
                 "• 🚫 BLACKLIST GUDANG: Item di daftar ini TIDAK AKAN dipindahkan ke gudang (tetap di tas, misal: Potion, Pustika, Gear utama).\n"
                 "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan langsung dipindahkan ke slot kosong di gudang (Storage 120 slot) secara cepat dan aman.",
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        # Checkboxes bar
        cfg_bar = tk.Frame(container, bg="#161b22", padx=12, pady=8, relief="ridge", bd=1)
        cfg_bar.pack(fill=tk.X, pady=(0, 10))

        self.var_storage_blacklist_enabled = tk.BooleanVar(
            value=self.config.get("storage_deposit", "blacklist_enabled", True)
        )
        cb1 = tk.Checkbutton(
            cfg_bar,
            text="Aktifkan Blacklist Gudang (Jangan pindahkan item yang cocok dengan Ikon Blacklist)",
            variable=self.var_storage_blacklist_enabled,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold"),
            command=self._on_toggle_storage_blacklist
        )
        cb1.pack(anchor=tk.W)

        # Filter Pop-up Penutup Storage Box (Issue #6)
        self.box_popup_frame = tk.LabelFrame(
            container,
            text=" 🛡️ Filter Pop-up Penutup Storage (Notice / Lucky Number / Raffle / Quiz) ",
            bg="#222428",
            fg="#d29922",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=8
        )
        self.box_popup_frame.pack(fill=tk.X, pady=(0, 12))

        self.var_auto_dismiss_popup = tk.BooleanVar(value=self.config.get("storage_popup", "auto_dismiss", True))
        cb2 = tk.Checkbutton(
            self.box_popup_frame,
            text="🛡️ Tutup Otomatis Popup yang terdeteksi sebelum proses Storage (Klik judul popup -> Esc 1x)",
            variable=self.var_auto_dismiss_popup,
            bg="#222428",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#222428",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9),
            command=self._on_toggle_auto_dismiss_popup
        )
        cb2.pack(anchor=tk.W, pady=(0, 6))

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

        desc = tk.Label(
            container,
            text="Aturan Penarikan Gudang (Storage) ke Tas (Inventory):\n"
                 "• 🚫 BLACKLIST TARIK GUDANG: Item di daftar ini TIDAK AKAN ditarik ke tas (tetap aman di gudang, misal: Ore, Potion cadangan, Equip simpanan).\n"
                 "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan ditarik ke slot tas kosong sampai tas penuh untuk dijual ke pedagang.",
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        # Checkboxes bar
        cfg_bar = tk.Frame(container, bg="#161b22", padx=12, pady=8, relief="ridge", bd=1)
        cfg_bar.pack(fill=tk.X, pady=(0, 10))

        self.var_storage_withdraw_blacklist_enabled = tk.BooleanVar(
            value=self.config.get("storage_withdraw", "blacklist_enabled", True)
        )
        cb1 = tk.Checkbutton(
            cfg_bar,
            text="Aktifkan Blacklist Tarik Gudang (Jangan tarik item yang cocok dengan Ikon Blacklist)",
            variable=self.var_storage_withdraw_blacklist_enabled,
            bg="#161b22",
            fg="#e1e2e6",
            selectcolor="#0d1117",
            activebackground="#161b22",
            activeforeground="#58a6ff",
            font=("Segoe UI", 9, "bold"),
            command=self._on_toggle_storage_withdraw_blacklist
        )
        cb1.pack(anchor=tk.W)

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
        container = tk.Frame(self.tab_whitelist, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        desc = tk.Label(
            container,
            text="Daftar item yang TIDAK BOLEH dijual ke Merchant NPC (Blacklist Toko):\n"
                 "• 🚫 BLACKLIST JUAL NPC: Item di daftar ini TIDAK AKAN dijual (tetap aman di tas, misal: Potion, Gear utama).\n"
                 "• ⚡ SEMUA ITEM LAIN: Seluruh item selain Blacklist akan langsung dijual ke toko dan dikonfirmasi dengan tombol Enter.",
            font=("Segoe UI", 9),
            bg="#222428",
            fg="#8b949e",
            justify=tk.LEFT
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

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
    # TAB 6: Auto Skill
    # =========================================================================
    def _build_skill_tab(self):
        container = tk.Frame(self.tab_skill, bg="#222428", padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(container, bg="#161b22", padx=12, pady=10, relief="ridge", bd=1)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        skill_cfg = self.config.get("auto_skill", {})
        self.var_skill_enabled = tk.BooleanVar(value=skill_cfg.get("enabled", True))
        self.var_skill_sync_hunt = tk.BooleanVar(value=skill_cfg.get("sync_with_auto_hunt", True))

        tk.Checkbutton(
            top_frame,
            text="⚡ Aktifkan Fitur Auto Skill (Otomatis spam skill sesuai timer detik)",
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
        ).pack(anchor=tk.W, pady=(4, 0))

        btn_bar = tk.Frame(top_frame, bg="#161b22")
        btn_bar.pack(fill=tk.X, pady=(8, 0))

        tk.Button(
            btn_bar,
            text="💾 Simpan Pengaturan Skill",
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
            text="🔄 Reset Countdown (Trigger Ulang)",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self._reset_skill_timers
        ).pack(side=tk.LEFT)

        # Scrollable container for keys
        canvas = tk.Canvas(container, bg="#222428", highlightthickness=0)
        scroll = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#222428")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.skill_vars = {}
        keys_cfg = skill_cfg.get("keys", {})

        def make_section(title, pairs):
            sec_frame = tk.LabelFrame(scrollable_frame, text=f" {title} ", bg="#222428", fg="#d29922", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
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

        # 2. LETTER KEYS
        make_section(
            "LETTER KEYS (E, R, F)",
            [("e", "r"), ("f", None)]
        )

        # 3. FUNCTION KEYS
        make_section(
            "FUNCTION KEYS (F1 - F5 kiri | F6 - F10 kanan)",
            [("f1", "f6"), ("f2", "f7"), ("f3", "f8"), ("f4", "f9"), ("f5", "f10")]
        )

        # Start countdown updater (100ms interval for smooth live countdown)
        self.after(100, self._update_skill_countdowns)

    def _apply_skill_gui_to_config(self, save_to_disk=False):
        if not hasattr(self, "skill_vars") or not self.skill_vars:
            return
        if "auto_skill" not in self.config.data:
            self.config.data["auto_skill"] = {}
        if hasattr(self, "var_skill_enabled"):
            self.config.data["auto_skill"]["enabled"] = self.var_skill_enabled.get()
        if hasattr(self, "var_skill_sync_hunt"):
            self.config.data["auto_skill"]["sync_with_auto_hunt"] = self.var_skill_sync_hunt.get()

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
        for k, widgets in self.skill_vars.items():
            widgets["lbl_countdown"].config(text="-", fg="#8b949e")

    def _update_skill_countdowns(self):
        try:
            is_running = self.bot.skills.is_running
            now = time.time()
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
        except Exception:
            pass
        self.after(100, self._update_skill_countdowns)

    # =========================================================================
    # TAB 7: Settings
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
