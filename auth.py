"""
Authentication and Password Protection for Tantra Online Farmer Macro.
Provides SHA-256 hashed password verification and a modal login dialog.
"""

import hashlib
import sys
from typing import Optional

try:
    import tkinter as tk
    from tkinter import messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False
    tk = object


# Default Salt and SHA-256 Hash for default password 'Mysamsung123'
SALT = "tantra_farmer_salt_2026"
DEFAULT_HASH = "1f406ec232c5a4de95539988e5f9c1a1f6c632544f08ff97f7eb26400102a1de"


def hash_password(plain_pwd: str) -> str:
    """Return SHA-256 hash of password with fixed salt."""
    salted = plain_pwd.strip() + SALT
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def verify_password(input_pwd: str, stored_hash: Optional[str] = None) -> bool:
    """Verify input password against stored hash (or default hash)."""
    target = stored_hash if stored_hash else DEFAULT_HASH
    return hash_password(input_pwd) == target


_DialogBase = tk.Toplevel if HAS_TK else object


class PasswordDialog(_DialogBase):
    """
    Modal Login Dialog for Farmer Macro.
    Blocks until valid password is provided or user cancels.
    """
    def __init__(self, parent, config, on_success):
        super().__init__(parent)
        self.config = config
        self.on_success = on_success
        self.authenticated = False

        self.title("🔐 Keamanan Akses - Tantra Farmer")
        self.geometry("400x260")
        self.resizable(False, False)
        self.configure(bg="#161b22")

        # Keep on top and modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center on screen
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self.entry_pwd.focus_set()

    def _build_ui(self):
        container = tk.Frame(self, bg="#161b22", padx=24, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Title
        tk.Label(
            container,
            text="🔒 TANTRA FARMER MACRO",
            font=("Segoe UI", 13, "bold"),
            bg="#161b22",
            fg="#58a6ff"
        ).pack(anchor=tk.CENTER, pady=(0, 4))

        tk.Label(
            container,
            text="Aplikasi ini diproteksi. Masukkan password akses:",
            font=("Segoe UI", 8),
            bg="#161b22",
            fg="#8b949e"
        ).pack(anchor=tk.CENTER, pady=(0, 16))

        # Password Input Frame
        frame_input = tk.Frame(container, bg="#161b22")
        frame_input.pack(fill=tk.X, pady=(0, 8))

        self.var_pwd = tk.StringVar()
        self.show_pwd = False

        self.entry_pwd = tk.Entry(
            frame_input,
            textvariable=self.var_pwd,
            show="●",
            font=("Segoe UI", 11),
            bg="#0d1117",
            fg="#f0f6fc",
            insertbackground="#ffffff",
            relief="solid",
            bd=1
        )
        self.entry_pwd.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        self.entry_pwd.bind("<Return>", lambda e: self._attempt_login())

        # Toggle Show / Hide Password Button
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

        # Status Error Label
        self.lbl_status = tk.Label(
            container,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg="#161b22",
            fg="#f85149"
        )
        self.lbl_status.pack(anchor=tk.CENTER, pady=(2, 10))

        # Action Buttons
        frame_btns = tk.Frame(container, bg="#161b22")
        frame_btns.pack(fill=tk.X, pady=(6, 0))

        tk.Button(
            frame_btns,
            text="🚪 Keluar",
            font=("Segoe UI", 9),
            bg="#21262d",
            fg="#8b949e",
            activebackground="#30363d",
            relief="flat",
            padx=12,
            pady=6,
            command=self._on_cancel
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

    def _toggle_show_pwd(self):
        self.show_pwd = not self.show_pwd
        if self.show_pwd:
            self.entry_pwd.config(show="")
            self.btn_eye.config(text="🙈")
        else:
            self.entry_pwd.config(show="●")
            self.btn_eye.config(text="👁")

    def _attempt_login(self):
        entered = self.var_pwd.get()
        stored_hash = None
        if self.config:
            stored_hash = self.config.get("security", "password_hash", None)

        if verify_password(entered, stored_hash):
            self.authenticated = True
            self.lbl_status.config(text="✓ Akses Diterima!", fg="#3fb950")
            self.after(200, self._proceed)
        else:
            self.lbl_status.config(text="❌ Password salah! Akses ditolak.")
            self.entry_pwd.delete(0, tk.END)
            self.entry_pwd.focus_set()

    def _proceed(self):
        self.grab_release()
        self.destroy()
        if self.on_success:
            self.on_success()

    def _on_cancel(self):
        self.grab_release()
        self.destroy()
        sys.exit(0)
