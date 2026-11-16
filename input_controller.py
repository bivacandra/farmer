"""
Input controller for Tantra macro.
Handles mouse movement, drag-and-drop, and keyboard input.
Uses pydirectinput / pyautogui / ctypes for DirectInput compatibility.
"""

import sys
import time
from typing import Tuple

try:
    import pydirectinput
    # DirectInput settings
    pydirectinput.PAUSE = 0.02
    HAS_DIRECT_INPUT = True
except ImportError:
    HAS_DIRECT_INPUT = False

try:
    import pyautogui
    pyautogui.PAUSE = 0.02
    pyautogui.FAILSAFE = True
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class InputController:
    def __init__(self, window_manager, config):
        self.wm = window_manager
        self.config = config
        self.delays = self.config.get("delays", {})
        self.is_aborted = False

    def abort(self) -> None:
        self.is_aborted = True

    def reset_abort(self) -> None:
        self.is_aborted = False

    def _sleep(self, duration: float) -> None:
        """Sleep with cancellation check."""
        end_time = time.time() + duration
        while time.time() < end_time:
            if self.is_aborted:
                raise InterruptedError("Operation aborted by user.")
            time.sleep(min(0.02, end_time - time.time()))

    def move_to(self, rel_x: int, rel_y: int, smooth: bool = True) -> Tuple[int, int]:
        """Moves cursor to relative game canvas coordinates."""
        if self.is_aborted:
            raise InterruptedError("Operation aborted.")

        abs_x, abs_y = self.wm.to_screen_coords(rel_x, rel_y)

        if sys.platform != "win32":
            # Simulation mode
            return abs_x, abs_y

        import ctypes
        ctypes.windll.user32.SetCursorPos(abs_x, abs_y)

        if HAS_DIRECT_INPUT:
            pydirectinput.moveTo(abs_x, abs_y)
        elif HAS_PYAUTOGUI:
            pyautogui.moveTo(abs_x, abs_y, duration=0.02 if smooth else 0.0)

        return abs_x, abs_y

    def hover(self, rel_x: int, rel_y: int, duration: float = None) -> None:
        """Hovers cursor at coordinate to trigger tooltip."""
        if duration is None:
            duration = self.delays.get("hover_delay_sec", 0.35)
        self.move_to(rel_x, rel_y)
        self._sleep(duration)

    def click(self, rel_x: int, rel_y: int) -> None:
        """Performs left click at coordinate."""
        self.move_to(rel_x, rel_y)
        self._sleep(0.05)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            self._sleep(0.05)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        elif HAS_DIRECT_INPUT:
            pydirectinput.mouseDown()
            self._sleep(0.05)
            pydirectinput.mouseUp()
        elif HAS_PYAUTOGUI:
            pyautogui.click()
        self._sleep(self.delays.get("click_delay_sec", 0.1))

    def drag_and_drop(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = None) -> None:
        """
        FR-1: Mekanisme Pemindahan Barang (Drag-and-Drop)
        Simulates mouse down at start, smooth move to end, and mouse up at target.
        """
        if self.is_aborted:
            raise InterruptedError("Operation aborted.")

        if duration is None:
            duration = self.delays.get("drag_duration_sec", 0.25)

        start_abs_x, start_abs_y = self.wm.to_screen_coords(start_x, start_y)
        end_abs_x, end_abs_y = self.wm.to_screen_coords(end_x, end_y)

        # 1. Move to start position
        self.move_to(start_x, start_y)
        self._sleep(0.08)

        # 2. Mouse Down (FR-1)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.SetCursorPos(start_abs_x, start_abs_y)
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        if HAS_DIRECT_INPUT:
            pydirectinput.mouseDown()
        elif HAS_PYAUTOGUI:
            pyautogui.mouseDown()
        self._sleep(0.08)

        # 3. Smooth Mouse Move while holding down
        steps = max(8, int(duration * 60))
        dt = duration / steps
        for i in range(1, steps + 1):
            if self.is_aborted:
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                if HAS_DIRECT_INPUT:
                    pydirectinput.mouseUp()
                elif HAS_PYAUTOGUI:
                    pyautogui.mouseUp()
                raise InterruptedError("Operation aborted during drag.")
            cur_x = int(start_abs_x + (end_abs_x - start_abs_x) * (i / steps))
            cur_y = int(start_abs_y + (end_abs_y - start_abs_y) * (i / steps))
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.SetCursorPos(cur_x, cur_y)
            if HAS_DIRECT_INPUT:
                pydirectinput.moveTo(cur_x, cur_y)
            elif HAS_PYAUTOGUI:
                pyautogui.moveTo(cur_x, cur_y)
            time.sleep(dt)

        self._sleep(0.08)

        # 4. Mouse Up at destination (FR-1)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.SetCursorPos(end_abs_x, end_abs_y)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        if HAS_DIRECT_INPUT:
            pydirectinput.mouseUp()
        elif HAS_PYAUTOGUI:
            pyautogui.mouseUp()

        self._sleep(self.delays.get("post_action_delay_sec", 0.25))

    def press_key(self, key_name: str) -> None:
        """Sends key press (e.g. 'enter', 'esc', 'f1', '1')."""
        key_lower = key_name.lower().strip()
        try:
            if HAS_DIRECT_INPUT:
                pydirectinput.press(key_lower)
            elif HAS_PYAUTOGUI:
                pyautogui.press(key_lower)
        except Exception:
            if HAS_PYAUTOGUI:
                try:
                    pyautogui.press(key_lower)
                except Exception:
                    pass
        time.sleep(0.04)
