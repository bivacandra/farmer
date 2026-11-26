"""
Auto Pot Controller for Tantra Online Macro.
Monitors Character HP and TP (MP) bars periodically via screen capture and color analysis.
Triggers potion hotkeys (e.g. F9 for HP, F10 for TP) when percentages fall below user-defined thresholds.
Thread-safe execution compatible with Auto Hunt and standalone modes.
"""

import threading
import time
from typing import Dict, Any, Callable, Optional, Tuple
from PIL import Image


DEFAULT_POT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "sync_with_auto_hunt": True,
    "check_interval_sec": 0.20,
    "hp": {
        "enabled": True,
        "threshold_pct": 50,
        "key": "f9",
        "cooldown_sec": 1.0,
        "box": {"x": 4, "y": 54, "w": 214, "h": 14}
    },
    "tp": {
        "enabled": True,
        "threshold_pct": 50,
        "key": "f10",
        "cooldown_sec": 1.0,
        "box": {"x": 4, "y": 69, "w": 214, "h": 14}
    }
}


class PotController:
    def __init__(self, input_controller, screen_capture, window_manager, config, logger: Optional[Callable[[str], None]] = None):
        self.input = input_controller
        self.screen = screen_capture
        self.wm = window_manager
        self.config = config
        self.log_fn = logger or print

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Runtime trackers
        self.last_hp_pot_time: float = 0.0
        self.last_tp_pot_time: float = 0.0
        self.hp_pot_count: int = 0
        self.tp_pot_count: int = 0
        self.current_hp_pct: Optional[float] = None
        self.current_tp_pct: Optional[float] = None
        self.last_read_time: float = 0.0

    def log(self, text: str):
        if self.log_fn:
            self.log_fn(text)

    def get_pot_cfg(self) -> Dict[str, Any]:
        return self.config.get("auto_pot", DEFAULT_POT_CONFIG)

    @staticmethod
    def is_hp_pixel(r: int, g: int, b: int) -> bool:
        """
        Detects red HP bar pixels in Tantra Online HUD.
        Solid red or shaded red with strong red dominance over green and blue.
        """
        return r >= 110 and (r > g * 1.25) and (r > b * 1.25)

    @staticmethod
    def is_tp_pixel(r: int, g: int, b: int) -> bool:
        """
        Detects blue/cyan TP (Prana/Mana) bar pixels in Tantra Online HUD.
        Solid blue or cyan gradient with strong blue dominance over red.
        """
        return b >= 100 and (b > r * 1.25) and (b >= g * 0.95)

    def calc_bar_percentage(self, img: Image.Image, box: Dict[str, int], is_filled_fn: Callable[[int, int, int], bool]) -> float:
        """
        Calculates fill percentage (0.0% to 100.0%) of a health or mana bar.
        Samples multiple vertical positions (top 15%, 25%, 35%, 80%) to be completely
        immune to font/text overlay (e.g. '56/56' or '34/34' centered on the bar).
        """
        x = int(box.get("x", 0))
        y = int(box.get("y", 0))
        w = int(box.get("w", 0))
        h = int(box.get("h", 0))

        if w <= 0 or h <= 0 or img is None:
            return 0.0

        sample_ratios = [0.15, 0.25, 0.35, 0.80]
        sample_ys = list(dict.fromkeys([y + max(0, min(h - 1, int(h * r))) for r in sample_ratios]))

        filled_cols = 0
        consecutive_empty = 0

        for col in range(w):
            cx = x + col
            col_filled = False
            for sy in sample_ys:
                if 0 <= cx < img.width and 0 <= sy < img.height:
                    r, g, b = img.getpixel((cx, sy))[:3]
                    if is_filled_fn(r, g, b):
                        col_filled = True
                        break
            if col_filled:
                filled_cols = col + 1
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                # If 5 consecutive columns are empty, the filled portion has ended
                if consecutive_empty >= 5:
                    break

        pct = max(0.0, min(100.0, (filled_cols / float(w)) * 100.0))
        return pct

    def read_hp_percentage(self, client_img: Optional[Image.Image] = None) -> Optional[float]:
        if client_img is None:
            client_img = self.screen.capture_client()
        cfg = self.get_pot_cfg()
        box = cfg.get("hp", {}).get("box", DEFAULT_POT_CONFIG["hp"]["box"])
        return self.calc_bar_percentage(client_img, box, self.is_hp_pixel)

    def read_tp_percentage(self, client_img: Optional[Image.Image] = None) -> Optional[float]:
        if client_img is None:
            client_img = self.screen.capture_client()
        cfg = self.get_pot_cfg()
        box = cfg.get("tp", {}).get("box", DEFAULT_POT_CONFIG["tp"]["box"])
        return self.calc_bar_percentage(client_img, box, self.is_tp_pixel)

    def get_current_readings(self, client_img: Optional[Image.Image] = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Captures client screen and returns (hp_percent, tp_percent).
        Updates runtime trackers for GUI consumption.
        """
        try:
            if client_img is None:
                client_img = self.screen.capture_client()
            hp = self.read_hp_percentage(client_img)
            tp = self.read_tp_percentage(client_img)
            with self._lock:
                self.current_hp_pct = hp
                self.current_tp_pct = tp
                self.last_read_time = time.time()
            return hp, tp
        except Exception as e:
            self.log(f"[Auto Pot] Gagal membaca HP/TP: {e}")
            return None, None

    @staticmethod
    def auto_detect_hud_bars(img: Image.Image) -> Tuple[Optional[Dict[str, int]], Optional[Dict[str, int]]]:
        """
        Attempts to automatically locate the HP and TP bar boxes from a screenshot.
        Constrains search to the player HUD region (top-left 320x130).
        """
        if img is None:
            return None, None

        max_w = min(img.width, 320)
        max_h = min(img.height, 130)

        # 1. Detect red horizontal segment for HP
        best_red_row = None
        best_red_span = (0, 0)
        for y in range(25, max_h - 20):
            red_cols = [
                x for x in range(3, max_w)
                if img.getpixel((x, y))[0] >= 120 and
                img.getpixel((x, y))[0] > img.getpixel((x, y))[1] * 1.3 and
                img.getpixel((x, y))[0] > img.getpixel((x, y))[2] * 1.3
            ]
            if len(red_cols) > 40:
                span_len = red_cols[-1] - red_cols[0] + 1
                if span_len > (best_red_span[1] - best_red_span[0]):
                    best_red_span = (red_cols[0], red_cols[-1])
                    best_red_row = y

        # 2. Detect blue horizontal segment for TP right below HP
        best_blue_row = None
        best_blue_span = (0, 0)
        start_y = (best_red_row + 8) if best_red_row else 40
        for y in range(start_y, min(max_h, start_y + 35)):
            blue_cols = [
                x for x in range(3, max_w)
                if img.getpixel((x, y))[2] >= 100 and
                img.getpixel((x, y))[2] > img.getpixel((x, y))[0] * 1.25 and
                img.getpixel((x, y))[2] >= img.getpixel((x, y))[1] * 0.95
            ]
            if len(blue_cols) > 40:
                span_len = blue_cols[-1] - blue_cols[0] + 1
                if span_len > (best_blue_span[1] - best_blue_span[0]):
                    best_blue_span = (blue_cols[0], blue_cols[-1])
                    best_blue_row = y

        hp_box = None
        if best_red_row and best_red_span[1] > best_red_span[0]:
            hp_w = best_red_span[1] - best_red_span[0] + 1
            hp_box = {"x": best_red_span[0], "y": max(0, best_red_row - 2), "w": hp_w, "h": 14}

        tp_box = None
        if best_blue_row and best_blue_span[1] > best_blue_span[0]:
            tp_w = best_blue_span[1] - best_blue_span[0] + 1
            tp_box = {"x": best_blue_span[0], "y": max(0, best_blue_row - 2), "w": tp_w, "h": 14}

        return hp_box, tp_box

    def reset_counts(self):
        with self._lock:
            self.hp_pot_count = 0
            self.tp_pot_count = 0

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.last_hp_pot_time = 0.0
            self.last_tp_pot_time = 0.0
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self.log("🧪 [Auto Pot] Pemantau HP & TP aktif dan berjalan...")

    def stop(self):
        with self._lock:
            self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.log("🧪 [Auto Pot] Berhenti.")

    def _loop(self):
        while self.is_running:
            try:
                cfg = self.get_pot_cfg()
                if not cfg.get("enabled", True):
                    time.sleep(0.5)
                    continue

                interval = float(cfg.get("check_interval_sec", 0.20))
                hp_cfg = cfg.get("hp", {})
                tp_cfg = cfg.get("tp", {})

                client_img = self.screen.capture_client()
                if client_img is None:
                    time.sleep(interval)
                    continue

                now = time.time()
                hp_pct = self.read_hp_percentage(client_img)
                tp_pct = self.read_tp_percentage(client_img)

                with self._lock:
                    self.current_hp_pct = hp_pct
                    self.current_tp_pct = tp_pct
                    self.last_read_time = now

                # 1. HP Auto Pot Check
                if hp_cfg.get("enabled", True) and hp_pct is not None:
                    hp_thresh = float(hp_cfg.get("threshold_pct", 50))
                    hp_cooldown = float(hp_cfg.get("cooldown_sec", 1.0))
                    hp_key = str(hp_cfg.get("key", "f9")).strip().lower()

                    # Safety: If HP is 0.0%, character might be dead or window minimized; do not spam
                    if 0.5 <= hp_pct <= hp_thresh:
                        if now - self.last_hp_pot_time >= hp_cooldown:
                            try:
                                self.input.press_key(hp_key)
                                self.last_hp_pot_time = now
                                with self._lock:
                                    self.hp_pot_count += 1
                                self.log(
                                    f"🧪 [Auto Pot] HP di bawah {hp_thresh:.0f}% ({hp_pct:.1f}%). "
                                    f"Menekan Pot HP '{hp_key.upper()}' (Total: {self.hp_pot_count})."
                                )
                            except Exception as e:
                                self.log(f"🧪 [Auto Pot] Error menekan Pot HP '{hp_key}': {e}")

                # 2. TP/MP Auto Pot Check
                if tp_cfg.get("enabled", True) and tp_pct is not None:
                    tp_thresh = float(tp_cfg.get("threshold_pct", 50))
                    tp_cooldown = float(tp_cfg.get("cooldown_sec", 1.0))
                    tp_key = str(tp_cfg.get("key", "f10")).strip().lower()

                    # Safety: If TP is 0.0%, character might be dead or window minimized; do not spam
                    if 0.5 <= tp_pct <= tp_thresh:
                        if now - self.last_tp_pot_time >= tp_cooldown:
                            try:
                                self.input.press_key(tp_key)
                                self.last_tp_pot_time = now
                                with self._lock:
                                    self.tp_pot_count += 1
                                self.log(
                                    f"🧪 [Auto Pot] TP di bawah {tp_thresh:.0f}% ({tp_pct:.1f}%). "
                                    f"Menekan Pot TP '{tp_key.upper()}' (Total: {self.tp_pot_count})."
                                )
                            except Exception as e:
                                self.log(f"🧪 [Auto Pot] Error menekan Pot TP '{tp_key}': {e}")

            except Exception as e:
                # Log non-fatal error and retry
                time.sleep(0.3)

            time.sleep(interval)
