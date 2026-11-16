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
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from config import Config
from window_manager import WindowManager
from screen import ScreenCapture
from input_controller import InputController
from template_matcher import TemplateMatcher
from ocr_engine import OCREngine
from farmer_bot import FarmerBot
from area_selector import AreaSelectorWindow
from auth import PasswordDialog, hash_password

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class FarmerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Farmer Macro Tool")
        self.geometry("920x700")
        self.minsize(860, 640)

        # Apply dark theme styling
        self._setup_styles()

        # Initialize core components
        self.config = Config("config.json")
        self.wm = WindowManager(self.config)
        self.screen = ScreenCapture(self.wm, self.config)
        self.input = InputController(self.wm, self.config)
        self.matcher = TemplateMatcher(self.config)
        self.ocr = OCREngine(self.config)
        self.bot = FarmerBot(self.wm, self.screen, self.input, self.matcher, self.ocr, self.config)

        self.bot.log_callback = self.append_log
        self.worker_thread = None

        # Build UI layout
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Setup hotkeys
        self._setup_hotkeys()

        # Hide main window until authenticated with password
        self.withdraw()
        self.after(50, self._require_auth)

    def _require_auth(self):
        PasswordDialog(self, self.config, on_success=self._on_auth_success)

    def _on_auth_success(self):
        self.deiconify()
        self.lift()
        self.focus_force()

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

    def _build_header(self):
        header_frame = tk.Frame(self, bg="#202225", height=60, padx=16, pady=10)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="Tantra Auto-Farmer & Inventory Manager",
            font=("Segoe UI", 14, "bold"),
            fg="#58a6ff",
            bg="#202225"
        )
        title_lbl.pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            header_frame,
            text="IDLE (F11 Mulai | F12 Stop)",
            font=("Segoe UI", 10, "bold"),
            fg="#3fb950",
            bg="#161b22",
            padx=12,
            pady=4,
            relief="solid",
            bd=1
        )
        self.status_badge.pack(side=tk.RIGHT)

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

        # Tab 4: Blacklist Gudang
        self.tab_storage_whitelist = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.tab_storage_whitelist, text=" 🚫 Blacklist Gudang ")
        self._build_storage_whitelist_tab()

        # Tab 5: Blacklist Jual Merchant NPC
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

        self.selected_mode = tk.StringVar(value="hunt_auto_deposit")

        modes = [
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

        btn_frame = tk.Frame(container, bg="#222428", pady=6)
        btn_frame.pack(fill=tk.X)

        self.btn_start = tk.Button(
            btn_frame,
            text="▶ MULAI (F11)",
            font=("Segoe UI", 11, "bold"),
            bg="#238636",
            fg="#ffffff",
            activebackground="#2ea043",
            relief="flat",
            padx=20,
            pady=8,
            command=self.start_macro
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_stop = tk.Button(
            btn_frame,
            text="⏹ BERHENTI (F12)",
            font=("Segoe UI", 11, "bold"),
            bg="#da3633",
            fg="#ffffff",
            activebackground="#f85149",
            relief="flat",
            padx=20,
            pady=8,
            command=self.stop_macro
        )
        self.btn_stop.pack(side=tk.LEFT)

        self.btn_find_window = tk.Button(
            btn_frame,
            text="🔍 Cek Jendela Game",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=12,
            pady=8,
            command=self.check_game_window
        )
        self.btn_find_window.pack(side=tk.RIGHT)

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
        container = tk.Frame(self.tab_area, bg="#222428", padx=16, pady=14)
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
        desc.pack(anchor=tk.W, pady=(0, 14))

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
        container = tk.Frame(self.tab_storage_whitelist, bg="#222428", padx=16, pady=14)
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

        # Blacklist Gudang Box (Full Width)
        box_frame = tk.LabelFrame(
            container,
            text=" 🚫 Daftar Item Blacklist Gudang (Ditinggalkan di Tas) ",
            bg="#222428",
            fg="#f85149",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=10
        )
        box_frame.pack(fill=tk.BOTH, expand=True)

        btn_bar = tk.Frame(box_frame, bg="#222428")
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Button(
            btn_bar,
            text="➕ Tambah Ikon Gambar...",
            font=("Segoe UI", 8, "bold"),
            bg="#da3633",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: self.add_whitelist_icon(target="storage_blacklist")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_bar,
            text="✂️ Potong dari Slot Tas...",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
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

        self.storage_blacklist_frame = tk.Frame(box_frame, bg="#161b22", relief="sunken", bd=1)
        self.storage_blacklist_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_storage_blacklist_view()

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
        icons = list(bl_dir.glob("*.png")) + list(bl_dir.glob("*.jpg"))

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
        if messagebox.askyesno("Konfirmasi", f"Hapus '{path.name}' dari Blacklist Gudang?"):
            try:
                path.unlink()
                self.refresh_storage_blacklist_view()
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

        bar = tk.Frame(container, bg="#222428")
        bar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(
            bar,
            text="➕ Tambah Gambar Ikon...",
            font=("Segoe UI", 8, "bold"),
            bg="#da3633",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: self.add_whitelist_icon(target="merchant")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bar,
            text="✂️ Potong Ikon dari Slot Tas...",
            font=("Segoe UI", 8, "bold"),
            bg="#1f6feb",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            command=lambda: self.crop_icon_dialog(target="merchant")
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            bar,
            text="🔄 Refresh Daftar",
            font=("Segoe UI", 8),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.refresh_whitelist_view
        ).pack(side=tk.LEFT)

        self.whitelist_frame = tk.Frame(container, bg="#161b22", relief="sunken", bd=1)
        self.whitelist_frame.pack(fill=tk.BOTH, expand=True)

        self.refresh_whitelist_view()

    def refresh_whitelist_view(self):
        for widget in self.whitelist_frame.winfo_children():
            widget.destroy()

        merchant_bl_dir = self.config.merchant_blacklist_dir
        icons = list(merchant_bl_dir.glob("*.png")) + list(merchant_bl_dir.glob("*.jpg"))

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
        if target == "storage_blacklist":
            return self.config.storage_blacklist_dir, "Blacklist Gudang"
        else:
            return self.config.merchant_blacklist_dir, "Blacklist Jual NPC"

    def add_whitelist_icon(self, target: str = "storage_blacklist"):
        target_dir, target_name = self._get_target_dir_and_title(target)

        f = filedialog.askopenfilename(
            title=f"Pilih Gambar Ikon Item ({target_name})",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if f:
            src = Path(f)
            dest = target_dir / src.name
            try:
                im = Image.open(src)
                im.save(dest)
                if target == "storage_blacklist":
                    self.refresh_storage_blacklist_view()
                else:
                    self.refresh_whitelist_view()
                messagebox.showinfo("Sukses", f"Ikon '{src.name}' berhasil ditambahkan ke {target_name}!")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan ikon: {e}")

    def crop_icon_dialog(self, target: str = "storage_blacklist"):
        target_dir, target_name = self._get_target_dir_and_title(target)

        win = tk.Toplevel(self)
        win.title(f"Potong Ikon Slot Tas ({target_name})")
        win.geometry("400x260")
        win.configure(bg="#222428")

        tk.Label(
            win,
            text=f"Masukkan Posisi Slot Inventaris ({target_name}):",
            font=("Segoe UI", 10, "bold"),
            bg="#222428",
            fg="#58a6ff"
        ).pack(pady=10)

        f_grid = tk.Frame(win, bg="#222428")
        f_grid.pack(pady=5)

        tk.Label(f_grid, text="Kolom (1 - 6):", bg="#222428", fg="#e1e2e6").grid(row=0, column=0, padx=5, pady=5)
        col_entry = tk.Entry(f_grid, width=6)
        col_entry.insert(0, "1")
        col_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(f_grid, text="Baris (1 - 4):", bg="#222428", fg="#e1e2e6").grid(row=1, column=0, padx=5, pady=5)
        row_entry = tk.Entry(f_grid, width=6)
        row_entry.insert(0, "1")
        row_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(f_grid, text="Nama Item:", bg="#222428", fg="#e1e2e6").grid(row=2, column=0, padx=5, pady=5)
        name_entry = tk.Entry(f_grid, width=16)
        name_entry.insert(0, "item_baru")
        name_entry.grid(row=2, column=1, padx=5, pady=5)

        def do_crop():
            try:
                c = int(col_entry.get()) - 1
                r = int(row_entry.get()) - 1
                name = name_entry.get().strip() or f"item_c{c+1}_r{r+1}"

                client_img = self.screen.capture_client()
                crop_img = self.bot.get_inventory_slot_crop(client_img, c, r)

                save_path = target_dir / f"{name}.png"
                crop_img.save(save_path)

                if target == "storage_blacklist":
                    self.refresh_storage_blacklist_view()
                else:
                    self.refresh_whitelist_view()

                win.destroy()
                messagebox.showinfo("Sukses", f"Berhasil memotong ikon slot [{r+1},{c+1}] dan disimpan ke '{target_name}' sebagai '{name}.png'!")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal memotong slot: {e}")

        tk.Button(win, text="Potong & Simpan", bg="#238636", fg="#ffffff", relief="flat", padx=12, pady=6, command=do_crop).pack(pady=10)

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
        container = tk.Frame(self.tab_settings, bg="#222428", padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="Konfigurasi Kecepatan & Delay (NFR-1)", font=("Segoe UI", 11, "bold"), bg="#222428", fg="#58a6ff").pack(anchor=tk.W, pady=(0, 10))

        grid = tk.Frame(container, bg="#222428")
        grid.pack(fill=tk.X, pady=5)

        self.entries = {}
        fields = [
            ("Durasi Drag Mouse (detik):", "delays", "drag_duration_sec"),
            ("Jeda Hover Tooltip NPC (detik):", "delays", "hover_delay_sec"),
            ("Timeout Pop-up Konfirmasi Jual (detik):", "delays", "popup_wait_timeout_sec"),
            ("Sensitivitas Deteksi Kosong (StdDev):", "rules", "empty_slot_threshold"),
            ("Threshold Match Blacklist Jual (0.5 - 1.0):", "rules", "sell_whitelist_match_threshold"),
            ("Interval Cek Auto Hunt (detik):", "delays", "hunt_loop_interval_sec"),
        ]

        for i, (label_text, sec, key) in enumerate(fields):
            tk.Label(grid, text=label_text, bg="#222428", fg="#e1e2e6").grid(row=i, column=0, sticky=tk.W, pady=6, padx=(0, 15))
            val = self.config.get(sec, key)
            e = tk.Entry(grid, bg="#161b22", fg="#e1e2e6", insertbackground="#ffffff", width=12)
            e.insert(0, str(val))
            e.grid(row=i, column=1, sticky=tk.W, pady=6)
            self.entries[(sec, key)] = e

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

    def save_settings(self):
        try:
            for (sec, key), e in self.entries.items():
                val_str = e.get().strip()
                if "." in val_str:
                    val = float(val_str)
                else:
                    val = int(val_str)
                self.config.set(sec, key, val)
            self.config.save()
            messagebox.showinfo("Sukses", "Pengaturan berhasil disimpan!")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan: {e}")

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
        tk.Label(footer, text="Antigravity Tantra Farmer • Resolution Independent • DirectInput Engine", font=("Segoe UI", 8), bg="#161b22", fg="#8b949e").pack(side=tk.LEFT)

    def _setup_hotkeys(self):
        if HAS_KEYBOARD and sys.platform == "win32":
            try:
                start_hk = self.config.get("hotkeys", "start", "f11")
                stop_hk = self.config.get("hotkeys", "stop", "f12")
                abort_hk = self.config.get("hotkeys", "emergency_abort", "esc")
                keyboard.add_hotkey(start_hk, lambda: self.after(0, self.start_macro))
                keyboard.add_hotkey(stop_hk, lambda: self.after(0, self.stop_macro))
                keyboard.add_hotkey(abort_hk, lambda: self.after(0, self.stop_macro))
                self.append_log(f"Global Hotkeys registered: {start_hk.upper()} (Start), {stop_hk.upper()} (Stop), {abort_hk.upper()} (Abort).")
            except Exception as e:
                self.append_log(f"Warning: Failed to hook global keyboard hotkeys: {e}")

    def append_log(self, text: str):
        def _append():
            ts = time.strftime("[%H:%M:%S] ")
            self.txt_log.insert(tk.END, ts + text + "\n")
            self.txt_log.see(tk.END)
        self.after(0, _append)

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

        self._apply_skill_gui_to_config(save_to_disk=False)
        self.bot.input.reset_abort()
        mode = self.selected_mode.get()
        self.status_badge.config(text=f"RUNNING ({mode})", fg="#ffffff", bg="#238636")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        def runner():
            try:
                if mode == "hunt_auto_deposit":
                    self.bot.run_hunt_auto_deposit()
                elif mode == "auto_skill_standalone":
                    self.bot.is_running = True
                    self.bot.skills.start()
                    try:
                        while self.bot.is_running:
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
            finally:
                self.after(0, self._on_macro_finished)

        self.worker_thread = threading.Thread(target=runner, daemon=True)
        self.worker_thread.start()

    def stop_macro(self):
        self.bot.stop()
        self._on_macro_finished()

    def _on_macro_finished(self):
        self.status_badge.config(text="IDLE (F11 Mulai | F12 Stop)", fg="#3fb950", bg="#161b22")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)


if __name__ == "__main__":
    app = FarmerGUI()
    app.mainloop()
