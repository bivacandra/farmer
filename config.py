"""
Config manager for Tantra Farmer Macro.
Loads and saves configuration parameters from config.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

APP_VERSION = "v1.3.0"

DEFAULT_CONFIG: Dict[str, Any] = {
    "ui": {
        "compact_mode": False
    },
    "window": {
        "title_patterns": [
            "Kathana - The Reign of Shadow",
            "Kathana",
            "Tantra"
        ],
        "client_width": 1024,
        "client_height": 768
    },
    "security": {
        "password_hash": "1f406ec232c5a4de95539988e5f9c1a1f6c632544f08ff97f7eb26400102a1de"
    },
    "delays": {
        "speed_level": 5,
        "hover_delay_sec": 0.35,
        "drag_duration_sec": 0.25,
        "click_delay_sec": 0.1,
        "popup_wait_timeout_sec": 2.0,
        "post_action_delay_sec": 0.25,
        "hunt_loop_interval_sec": 1.5,
        "sell_wait_timeout_sec": 2.0,
        "sell_post_delay_sec": 0.35
    },
    "inventory": {
        "x1": 704,
        "y1": 412,
        "x2": 944,
        "y2": 732,
        "cols": 6,
        "rows": 4,
        "total_slots": 24
    },
    "storage": {
        "x1": 55,
        "y1": 233,
        "x2": 467,
        "y2": 691,
        "cols": 10,
        "rows": 12,
        "total_slots": 120
    },
    "merchant": {
        "x1": 360,
        "y1": 250,
        "x2": 650,
        "y2": 650,
        "drop_target_x": 505,
        "drop_target_y": 450
    },
    "storage_deposit": {
        "blacklist_enabled": True
    },
    "storage_withdraw": {
        "blacklist_enabled": True
    },
    "storage_popup": {
        "click_x": 85,
        "click_y": 55,
        "auto_dismiss": False
    },
    "rules": {
        "empty_slot_threshold": 18.0,
        "sell_whitelist_match_threshold": 0.78,
        "storage_blacklist_match_threshold": 0.50,
        "storage_withdraw_blacklist_match_threshold": 0.50,
        "auto_confirm_sell": True,
        "use_ocr_name_fallback": True
    },
    "hotkeys": {
        "start": "f11",
        "stop": "f12",
        "storage_to_inv": "f9",
        "inv_to_merchant": "f10",
        "dismiss_popup": "f8",
        "auto_loop": "f7"
    },
    "auto_nav": {
        "enabled": True,
        "walk_to_merchant_sec": 7.5,
        "walk_to_storage_sec": 7.5,
        "forward_key": "w",
        "backward_key": "s",
        "npc_click_y_offset": 50,
        "auto_align_camera": True,
        "max_align_retries": 18,
        "dialog_wait_sec": 1.2,
        "post_walk_settle_sec": 0.5,
        "low_spec_mode": False,
        "align_settle_delay": 0.20,
        "post_zoom_settle_sec": 1.0,
        "align_max_search_steps": 30,
        "align_match_threshold": 0.40
    },
    "auto_skill": {
        "enabled": False,
        "sync_with_auto_hunt": True,
        "mode": "smart_combo",
        "combo_check_interval_sec": 0.05,
        "quickslot_bar": {"x": 300, "y": 700, "w": 410, "h": 86, "cols": 10, "rows": 2},
        "combo_list": [],
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
            "f10": {"enabled": False, "interval": 10.0}
        }
    },
    "auto_pot": {
        "enabled": False,
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
}


class Config:
    def __init__(self, config_path: str = "config.json"):
        if getattr(sys, "frozen", False):
            # Running as compiled PyInstaller executable
            exe_dir = Path(sys.executable).resolve().parent
            if (exe_dir / config_path).exists():
                self.base_dir = exe_dir
            elif hasattr(sys, "_MEIPASS") and (Path(sys._MEIPASS) / config_path).exists():
                self.base_dir = Path(sys._MEIPASS)
            else:
                self.base_dir = exe_dir
        else:
            self.base_dir = Path(__file__).resolve().parent

        self.config_path = self.base_dir / config_path
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults for any missing keys
                    merged = dict(DEFAULT_CONFIG)
                    for k, v in loaded.items():
                        if isinstance(v, dict) and k in merged:
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                print(f"[Config] Error loading {self.config_path}: {e}. Using defaults.")
        return dict(DEFAULT_CONFIG)

    def save(self) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            print(f"[Config] Error saving config: {e}")
            return False

    def get(self, section: str, key: Any = None, default: Any = None) -> Any:
        if key is None:
            return self.data.get(section, {})
        if not isinstance(key, str):
            # Called like config.get("delays", {})
            return self.data.get(section, key)
        sec = self.data.get(section, {})
        if isinstance(sec, dict):
            return sec.get(key, default)
        return default

    def set(self, section: str, key: str, value: Any) -> None:
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value

    @property
    def assets_dir(self) -> Path:
        return self.base_dir / "assets"

    @property
    def merchant_blacklist_dir(self) -> Path:
        p = self.assets_dir / "merchant_blacklist"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def whitelist_dir(self) -> Path:
        return self.merchant_blacklist_dir

    @property
    def storage_blacklist_dir(self) -> Path:
        p = self.assets_dir / "storage_blacklist"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def storage_withdraw_blacklist_dir(self) -> Path:
        p = self.assets_dir / "storage_withdraw_blacklist"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def storage_qty100_dir(self) -> Path:
        p = self.assets_dir / "storage_qty100"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def skills_dir(self) -> Path:
        p = self.assets_dir / "skills"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def blacklist_dir(self) -> Path:
        p = self.assets_dir / "blacklist"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def storage_popups_dir(self) -> Path:
        p = self.assets_dir / "storage_popups"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def templates_dir(self) -> Path:
        p = self.assets_dir / "templates"
        p.mkdir(parents=True, exist_ok=True)
        return p
