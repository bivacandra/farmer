"""
Interactive Area Selector tool for Tantra Farmer Macro.
Allows selecting bounding boxes for Inventory (48 slots), Storage (128 slots),
and Merchant drop areas with live visual grid alignment.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk


class AreaSelectorWindow(tk.Toplevel):
    def __init__(self, parent, title_text: str, cols: int, rows: int, screenshot_img: Image.Image, on_save_cb):
        super().__init__(parent)
        self.title(f"Kalibrasi Area: {title_text}")
        self.configure(bg="#18191c")

        self.cols = cols
        self.rows = rows
        self.orig_img = screenshot_img
        self.on_save_cb = on_save_cb

        # Calculate display scale if image is larger than screen
        screen_w = self.winfo_screenwidth() - 80
        screen_h = self.winfo_screenheight() - 140

        img_w, img_h = self.orig_img.size
        self.scale = min(1.0, screen_w / img_w, screen_h / img_h)

        self.disp_w = int(img_w * self.scale)
        self.disp_h = int(img_h * self.scale)

        self.disp_img = self.orig_img.resize((self.disp_w, self.disp_h), Image.Resampling.BILINEAR)
        self.tk_img = ImageTk.PhotoImage(self.disp_img)

        # Coordinate state
        self.start_x = None
        self.start_y = None
        self.cur_x = None
        self.cur_y = None
        self.selected_rect = None  # (x1, y1, x2, y2) in original image coordinates

        self._build_ui(title_text)

    def _build_ui(self, title_text: str):
        # Header banner
        header = tk.Frame(self, bg="#21262d", padx=12, pady=8)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"📌 {title_text} ({self.cols} Kolom x {self.rows} Baris = {self.cols * self.rows} Slot)",
            font=("Segoe UI", 11, "bold"),
            bg="#21262d",
            fg="#58a6ff"
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text="Klik dan seret (drag) mouse dari pojok kiri-atas ke pojok kanan-bawah area kotak grid.",
            font=("Segoe UI", 9),
            bg="#21262d",
            fg="#8b949e"
        ).pack(side=tk.LEFT, padx=15)

        # Bottom control bar
        footer = tk.Frame(self, bg="#21262d", padx=12, pady=8)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_info = tk.Label(footer, text="Belum ada area dipilih.", font=("Consolas", 10), bg="#21262d", fg="#e1e2e6")
        self.lbl_info.pack(side=tk.LEFT)

        self.btn_save = tk.Button(
            footer,
            text="✔ Simpan Area",
            font=("Segoe UI", 10, "bold"),
            bg="#238636",
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=4,
            state=tk.DISABLED,
            command=self._save_and_close
        )
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        tk.Button(
            footer,
            text="❌ Batal",
            font=("Segoe UI", 9),
            bg="#30363d",
            fg="#c9d1d9",
            relief="flat",
            padx=10,
            pady=4,
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)

        # Canvas with scrollbars if needed
        canvas_frame = tk.Frame(self, bg="#0d1117")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, width=self.disp_w, height=self.disp_h, bg="#0d1117", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(anchor=tk.CENTER)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.cur_x = event.x
        self.cur_y = event.y
        self._redraw_selection()

    def _on_drag(self, event):
        self.cur_x = max(0, min(self.disp_w, event.x))
        self.cur_y = max(0, min(self.disp_h, event.y))
        self._redraw_selection()

    def _on_release(self, event):
        self.cur_x = max(0, min(self.disp_w, event.x))
        self.cur_y = max(0, min(self.disp_h, event.y))
        self._redraw_selection()

        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)

        # Convert back to original image coordinates
        orig_x1 = int(x1 / self.scale)
        orig_y1 = int(y1 / self.scale)
        orig_x2 = int(x2 / self.scale)
        orig_y2 = int(y2 / self.scale)

        if (orig_x2 - orig_x1) > 20 and (orig_y2 - orig_y1) > 20:
            self.selected_rect = (orig_x1, orig_y1, orig_x2, orig_y2)
            w = orig_x2 - orig_x1
            h = orig_y2 - orig_y1
            self.lbl_info.config(text=f"Area Terpilih: X=[{orig_x1}..{orig_x2}], Y=[{orig_y1}..{orig_y2}] | Ukuran: {w}x{h} px", fg="#3fb950")
            self.btn_save.config(state=tk.NORMAL)
        else:
            self.selected_rect = None
            self.btn_save.config(state=tk.DISABLED)

    def _redraw_selection(self):
        self.canvas.delete("overlay")
        if self.start_x is None or self.cur_x is None:
            return

        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)

        # Outer bounding box
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00ffcc", width=2, tags="overlay")

        # Draw grid lines for columns and rows
        if self.cols > 1 and (x2 - x1) > 10:
            col_step = (x2 - x1) / self.cols
            for c in range(1, self.cols):
                cx = x1 + (c * col_step)
                self.canvas.create_line(cx, y1, cx, y2, fill="#00ffcc", dash=(2, 2), tags="overlay")

        if self.rows > 1 and (y2 - y1) > 10:
            row_step = (y2 - y1) / self.rows
            for r in range(1, self.rows):
                ry = y1 + (r * row_step)
                self.canvas.create_line(x1, ry, x2, ry, fill="#00ffcc", dash=(2, 2), tags="overlay")

    def _save_and_close(self):
        if self.selected_rect and self.on_save_cb:
            self.on_save_cb(self.selected_rect)
        self.destroy()
