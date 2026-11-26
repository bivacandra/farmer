"""
Window manager for Tantra game client.
Handles window finding, client coordinate conversion, and window focusing on Windows
using native ctypes.windll.user32 (100% built-in, zero external dependencies).
"""

import sys
from typing import List, Optional, Tuple

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class WindowManager:
    def __init__(self, config):
        self.config = config
        self.hwnd = None
        self.window_title: str = ""
        self.window_rect: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
        self.client_rect: Optional[Tuple[int, int, int, int]] = None  # (client_left, client_top, width, height)

    def get_visible_windows(self) -> List[Tuple[int, str]]:
        """Returns list of (hwnd, title) for all visible non-empty windows."""
        if sys.platform != "win32":
            return [(1, "Kathana - The Reign of Shadow (Mock)")]

        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32

            import os
            my_pid = os.getpid()

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            windows = []

            def enum_proc(hwnd, lParam):
                if user32.IsWindowVisible(hwnd):
                    # 1. Skip windows belonging to the Python Macro process itself
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == my_pid:
                        return True

                    # 2. Get Window Title
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()

                        # 3. Exclude any macro / terminal / cmd launcher titles
                        title_lower = title.lower()
                        if "farmer macro" in title_lower or "run_macro" in title_lower:
                            return True

                        if title:
                            windows.append((hwnd, title))
                return True

            proc = WNDENUMPROC(enum_proc)
            user32.EnumWindows(proc, 0)
            return windows
        except Exception as e:
            print(f"[WindowManager] Error enumerating windows: {e}")
            return []

    def find_window(self, exact_hwnd: Optional[int] = None) -> bool:
        """Finds the Tantra window using title patterns or specific HWND."""
        if sys.platform != "win32":
            print(f"[WindowManager] Non-Windows platform ({sys.platform}). Operating in emulation/mock mode.")
            self.client_rect = (0, 0, 1024, 768)
            return True

        if exact_hwnd is not None:
            self.hwnd = exact_hwnd
            self.update_bounds()
            return True

        title_patterns = self.config.get("window", "title_patterns", ["Kathana", "Tantra"])

        windows = self.get_visible_windows()
        for hwnd, title in windows:
            title_lower = title.lower()
            for pat in title_patterns:
                if pat.lower() in title_lower:
                    self.hwnd = hwnd
                    self.window_title = title
                    print(f"[WindowManager] Found window: '{title}' (HWND: {hwnd})")
                    self.update_bounds()
                    return True

        print(f"[WindowManager] Window matching patterns {title_patterns} not found.")
        return False

    def is_foreground(self) -> bool:
        """Returns True if the Tantra window is currently the active foreground window."""
        if sys.platform != "win32":
            return True
        if not self.hwnd:
            return False
        try:
            import ctypes
            return ctypes.windll.user32.GetForegroundWindow() == self.hwnd
        except Exception:
            return False

    def is_window_active(self) -> bool:
        """Alias for is_foreground()."""
        return self.is_foreground()

    def activate_window(self) -> bool:
        """Brings the game window to foreground."""
        if sys.platform != "win32":
            return True
        if not self.hwnd:
            self.find_window()
        if not self.hwnd:
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 9 = SW_RESTORE
            user32.ShowWindow(self.hwnd, 9)
            user32.SetForegroundWindow(self.hwnd)
            self.update_bounds()
            return True
        except Exception as e:
            print(f"[WindowManager] Failed to bring window to foreground: {e}")
            return False

    def update_bounds(self) -> None:
        """Updates window and client area bounds."""
        if sys.platform != "win32":
            self.client_rect = (0, 0, 1024, 768)
            return

        if not self.hwnd:
            self.find_window()

        if not self.hwnd:
            self.client_rect = (0, 0, 1024, 768)
            return

        try:
            import ctypes
            user32 = ctypes.windll.user32

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long)
                ]

            w_rect = RECT()
            c_rect = RECT()
            user32.GetWindowRect(self.hwnd, ctypes.byref(w_rect))
            user32.GetClientRect(self.hwnd, ctypes.byref(c_rect))

            pt = POINT(0, 0)
            user32.ClientToScreen(self.hwnd, ctypes.byref(pt))

            self.window_rect = (w_rect.left, w_rect.top, w_rect.right, w_rect.bottom)
            cw = c_rect.right - c_rect.left
            ch = c_rect.bottom - c_rect.top
            self.client_rect = (pt.x, pt.y, cw, ch)
            print(f"[WindowManager] Client origin: ({pt.x}, {pt.y}), Size: {cw}x{ch}")
        except Exception as e:
            print(f"[WindowManager] Error updating bounds: {e}")

    def zero_in_window(self) -> bool:
        """
        Positions the game window at screen coordinate (0, 0).
        Restores window if minimized and moves it to top-left corner.
        """
        if sys.platform != "win32":
            print("[WindowManager] Non-Windows platform. Emulated zero_in_window to (0, 0)")
            self.client_rect = (0, 0, 1024, 768)
            self.window_rect = (0, 0, 1024, 768)
            return True

        if not self.hwnd:
            self.find_window()

        if not self.hwnd:
            print("[WindowManager] Cannot zero-in: window not found.")
            return False

        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 9 = SW_RESTORE
            user32.ShowWindow(self.hwnd, 9)
            user32.SetForegroundWindow(self.hwnd)

            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_SHOWWINDOW = 0x0040
            res = user32.SetWindowPos(self.hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_SHOWWINDOW)
            self.update_bounds()
            return bool(res)
        except Exception as e:
            print(f"[WindowManager] Failed to zero-in window: {e}")
            return False

    def to_screen_coords(self, rel_x: int, rel_y: int) -> Tuple[int, int]:
        """
        Converts coordinates relative to the client area into absolute screen coordinates.
        Always updates bounds so the game window can be located ANYWHERE on the screen
        (no need to place at zero window 0,0).
        """
        self.update_bounds()
        if self.client_rect:
            origin_x, origin_y, cw, ch = self.client_rect
            # Exact 1:1 pixel mapping from client area top-left
            abs_x = int(origin_x + rel_x)
            abs_y = int(origin_y + rel_y)
            return abs_x, abs_y
        return rel_x, rel_y
