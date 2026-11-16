"""
Skill Controller for Tantra Online Macro.
Handles automated skill execution on configurable timers (1-0, F1-F10, E/R/F).
Thread-safe execution compatible with Auto Hunt and standalone modes.
"""

import threading
import time
from typing import Dict, Any, Callable, Optional


DEFAULT_SKILL_CONFIG = {
    "enabled": False,
    "sync_with_auto_hunt": True,
    "keys": {
        "1": {"enabled": False, "interval": 10.0},
        "2": {"enabled": False, "interval": 10.0},
        "3": {"enabled": False, "interval": 10.0},
        "4": {"enabled": False, "interval": 10.0},
        "5": {"enabled": False, "interval": 10.0},
        "6": {"enabled": False, "interval": 10.0},
        "7": {"enabled": False, "interval": 10.0},
        "8": {"enabled": False, "interval": 10.0},
        "9": {"enabled": False, "interval": 10.0},
        "0": {"enabled": False, "interval": 10.0},
        "e": {"enabled": False, "interval": 10.0},
        "r": {"enabled": False, "interval": 10.0},
        "f": {"enabled": False, "interval": 10.0},
        "f1": {"enabled": False, "interval": 10.0},
        "f2": {"enabled": False, "interval": 10.0},
        "f3": {"enabled": False, "interval": 10.0},
        "f4": {"enabled": False, "interval": 10.0},
        "f5": {"enabled": False, "interval": 10.0},
        "f6": {"enabled": False, "interval": 10.0},
        "f7": {"enabled": False, "interval": 10.0},
        "f8": {"enabled": False, "interval": 10.0},
        "f9": {"enabled": False, "interval": 10.0},
        "f10": {"enabled": False, "interval": 10.0},
    }
}


class SkillController:
    def __init__(self, input_controller, window_manager, config, logger: Optional[Callable[[str], None]] = None):
        self.input = input_controller
        self.wm = window_manager
        self.config = config
        self.log_fn = logger or print

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Runtime trackers
        self.last_press_times: Dict[str, float] = {}
        self.counts: Dict[str, int] = {}
        self._init_trackers()

    def _init_trackers(self):
        keys = self.get_keys_config()
        for k in keys.keys():
            self.last_press_times[k] = 0.0
            self.counts[k] = 0

    def log(self, text: str):
        if self.log_fn:
            self.log_fn(text)

    def get_skill_cfg(self) -> Dict[str, Any]:
        return self.config.get("auto_skill", DEFAULT_SKILL_CONFIG)

    def get_keys_config(self) -> Dict[str, Dict[str, Any]]:
        cfg = self.get_skill_cfg()
        return cfg.get("keys", DEFAULT_SKILL_CONFIG["keys"])

    def set_key_param(self, key_name: str, enabled: Optional[bool] = None, interval: Optional[float] = None):
        if "auto_skill" not in self.config.data:
            self.config.data["auto_skill"] = dict(DEFAULT_SKILL_CONFIG)
        if "keys" not in self.config.data["auto_skill"]:
            self.config.data["auto_skill"]["keys"] = dict(DEFAULT_SKILL_CONFIG["keys"])
        if key_name not in self.config.data["auto_skill"]["keys"]:
            self.config.data["auto_skill"]["keys"][key_name] = {"enabled": False, "interval": 10.0}

        if enabled is not None:
            self.config.data["auto_skill"]["keys"][key_name]["enabled"] = enabled
        if interval is not None:
            self.config.data["auto_skill"]["keys"][key_name]["interval"] = max(0.1, float(interval))

    def reset_counts(self):
        with self._lock:
            for k in self.counts:
                self.counts[k] = 0

    def reset_timers(self):
        with self._lock:
            for k in self.last_press_times:
                self.last_press_times[k] = 0.0
            for k in self.counts:
                self.counts[k] = 0
        self.log("[Auto Skill] Countdown di-reset.")

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.input.reset_abort()
            for k in self.last_press_times:
                self.last_press_times[k] = 0.0
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self.log("[Auto Skill] Berjalan...")

    def stop(self):
        with self._lock:
            self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.log("[Auto Skill] Berhenti.")

    def _loop(self):
        while self.is_running:
            keys_cfg = self.get_keys_config()
            now = time.time()

            # Find keys that are due
            for key_name, info in keys_cfg.items():
                if not self.is_running:
                    break
                if not info.get("enabled", False):
                    continue

                interval = float(info.get("interval", 10.0))
                last_t = self.last_press_times.get(key_name, 0.0)

                if now - last_t >= interval:
                    try:
                        self.input.press_key(key_name)
                        self.last_press_times[key_name] = now
                        with self._lock:
                            self.counts[key_name] = self.counts.get(key_name, 0) + 1
                        self.log(f"[Auto Skill] Menekan '{key_name.upper()}' (Total: {self.counts[key_name]})")
                        time.sleep(0.06)
                    except Exception as e:
                        self.log(f"[Auto Skill] Error menekan {key_name}: {e}")

            time.sleep(0.05)
