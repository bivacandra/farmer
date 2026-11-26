"""
Skill Controller for Tantra Online Macro.
Supports:
1. Smart Combo Mode (Cooldown-Aware Visual Execution):
   - Monitors skill slot graphics in real time.
   - Detects Active vs Cooldown states via visual similarity and brightness ratio.
   - Executes combos in sequence (1 -> 2 -> 3 -> 4), skips skills that are on cooldown,
     and restarts when the first skill comes off cooldown.
2. Timer Interval Mode (Legacy):
   - Triggers individual hotkeys (1-0, F1-F10, E/R/F) at configurable fixed second intervals.
Thread-safe execution compatible with Auto Hunt and standalone modes.
"""

import threading
import time
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional, Tuple
from PIL import Image, ImageChops, ImageStat


DEFAULT_SKILL_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "sync_with_auto_hunt": True,
    "mode": "smart_combo",  # "smart_combo" (visual cooldown) or "timer_interval" (legacy)
    "combo_check_interval_sec": 0.05,
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
        "f10": {"enabled": False, "interval": 10.0},
    }
}


class SkillController:
    def __init__(
        self,
        input_controller,
        screen_capture,
        window_manager,
        config,
        logger: Optional[Callable[[str], None]] = None
    ):
        self.input = input_controller
        self.screen = screen_capture
        self.wm = window_manager
        self.config = config
        self.log_fn = logger or print

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Runtime trackers for Legacy Timer Mode
        self.last_press_times: Dict[str, float] = {}
        self.counts: Dict[str, int] = {}
        self._init_trackers()

        # Runtime trackers for Smart Combo Mode
        self.combo_counts: Dict[str, int] = {}
        self.combo_status: Dict[str, Dict[str, Any]] = {}
        self.last_combo_cast_time: float = 0.0
        self.current_combo_index: int = -1
        self._template_cache: Dict[str, Image.Image] = {}

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

    def get_combo_list(self) -> List[Dict[str, Any]]:
        cfg = self.get_skill_cfg()
        return cfg.get("combo_list", [])

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

    def get_skill_slot_box(self, skill_item: Dict[str, Any]) -> Optional[Dict[str, int]]:
        """
        Resolves the slot bounding box for a combo skill item.
        First checks explicit 'slot_box' or 'box'. If not set, derives
        the box from 'slot_index' (1..10) and 'quickslot_bar' calibration.
        """
        if not skill_item:
            return None

        explicit_box = skill_item.get("slot_box") or skill_item.get("box")
        if explicit_box and explicit_box.get("w", 0) > 0 and explicit_box.get("h", 0) > 0:
            return {
                "x": int(explicit_box.get("x", 0)),
                "y": int(explicit_box.get("y", 0)),
                "w": int(explicit_box.get("w", 0)),
                "h": int(explicit_box.get("h", 0))
            }

        slot_idx = int(skill_item.get("slot_index", 1))
        quickslot_bar = self.get_skill_cfg().get("quickslot_bar", {})
        if quickslot_bar and "x" in quickslot_bar and quickslot_bar.get("w", 0) > 0:
            cols = max(1, int(quickslot_bar.get("cols", 10)))
            bar_x = int(quickslot_bar["x"])
            bar_y = int(quickslot_bar["y"])
            bar_w = int(quickslot_bar["w"])
            bar_h = int(quickslot_bar["h"])
            col_w = bar_w / cols
            col_idx = max(0, min(cols - 1, slot_idx - 1))
            return {
                "x": int(bar_x + col_idx * col_w),
                "y": bar_y,
                "w": max(1, int(col_w)),
                "h": bar_h
            }

        return None

    def get_skill_slot_crop(self, client_img: Image.Image, box_or_item: Any) -> Optional[Image.Image]:
        """
        Crops slot region from client screenshot.
        Accepts either a box dict {'x', 'y', 'w', 'h'} or a full skill_item dict.
        """
        if client_img is None or not box_or_item:
            return None

        if isinstance(box_or_item, dict) and "w" in box_or_item and "h" in box_or_item and "x" in box_or_item and "y" in box_or_item and "slot_index" not in box_or_item:
            box = box_or_item
        elif isinstance(box_or_item, dict):
            box = self.get_skill_slot_box(box_or_item)
        else:
            return None

        if not box:
            return None

        x = int(box.get("x", 0))
        y = int(box.get("y", 0))
        w = int(box.get("w", 0))
        h = int(box.get("h", 0))
        if w <= 0 or h <= 0:
            return None

        x2 = min(client_img.width, x + w)
        y2 = min(client_img.height, y + h)
        if x2 <= x or y2 <= y:
            return None
        return client_img.crop((x, y, x2, y2))

    def load_skill_template(self, tpl_path_or_filename: str) -> Optional[Image.Image]:
        """Loads and caches active skill template image."""
        if not tpl_path_or_filename:
            return None

        if tpl_path_or_filename in self._template_cache:
            return self._template_cache[tpl_path_or_filename]

        candidates = [
            Path(tpl_path_or_filename),
            Path(self.config.base_dir) / tpl_path_or_filename,
            self.config.skills_dir / tpl_path_or_filename
        ]

        for p in candidates:
            if p.is_file():
                try:
                    img = Image.open(p).convert("RGB")
                    self._template_cache[tpl_path_or_filename] = img
                    return img
                except Exception:
                    pass

        return None

    def is_skill_active(
        self,
        live_crop_or_client: Image.Image,
        template_or_item: Any,
        template_img: Optional[Image.Image] = None
    ) -> Any:
        """
        Determines whether a skill slot icon is ACTIVE (ready to cast) or on COOLDOWN.
        When on cooldown in Tantra, icons are shaded by a dark mask (brightness drops by ~70%).
        Supports two calling styles:
        1. (live_crop, template_img) -> returns (is_active, similarity_score, brightness_ratio)
        2. (client_img, skill_item, template_img=None) -> returns bool
        """
        if live_crop_or_client is None:
            return (False, 0.0, 0.0) if template_img is None and not isinstance(template_or_item, dict) else False

        # Style 2: client_img, skill_item
        if isinstance(template_or_item, dict):
            skill_item = template_or_item
            slot_crop = self.get_skill_slot_crop(live_crop_or_client, skill_item)
            if slot_crop is None:
                return False

            tpl = template_img
            if tpl is None:
                tpl_path = skill_item.get("template_path") or skill_item.get("icon_filename", "")
                tpl = self.load_skill_template(tpl_path)
            if tpl is None:
                return False

            sim_th = float(skill_item.get("similarity_threshold", 0.75))
            br_th = float(skill_item.get("brightness_ratio_threshold", 0.70))

            is_act, sim, br = self._calc_skill_active_metrics(slot_crop, tpl, sim_th, br_th)
            return is_act

        # Style 1: live_crop, template_img
        live_crop = live_crop_or_client
        tpl_img = template_or_item
        return self._calc_skill_active_metrics(live_crop, tpl_img, 0.75, 0.70)

    @staticmethod
    def _calc_skill_active_metrics(
        live_crop: Image.Image,
        template_img: Image.Image,
        similarity_threshold: float = 0.75,
        brightness_ratio_threshold: float = 0.70
    ) -> Tuple[bool, float, float]:
        if live_crop is None or template_img is None:
            return False, 0.0, 0.0

        lw, lh = live_crop.size
        tw, th = template_img.size
        if lw < 4 or lh < 4 or tw < 4 or th < 4:
            return False, 0.0, 0.0

        # Resize template to live crop size for 1:1 comparison
        t_resized = template_img.resize((lw, lh), Image.Resampling.BILINEAR)

        # 1. Structural difference
        diff = ImageChops.difference(live_crop.convert("RGB"), t_resized.convert("RGB"))
        stat_diff = ImageStat.Stat(diff)
        mae = sum(stat_diff.mean[:3]) / 3.0
        similarity = max(0.0, 1.0 - (mae / 255.0))

        # 2. Brightness comparison (focus on center 80% to avoid slot border frames)
        pad_w = max(1, int(lw * 0.1))
        pad_h = max(1, int(lh * 0.1))
        c_live = live_crop.crop((pad_w, pad_h, max(pad_w + 1, lw - pad_w), max(pad_h + 1, lh - pad_h)))
        c_tpl = t_resized.crop((pad_w, pad_h, max(pad_w + 1, lw - pad_w), max(pad_h + 1, lh - pad_h)))

        b_live = sum(ImageStat.Stat(c_live).mean[:3]) / 3.0
        b_tpl = sum(ImageStat.Stat(c_tpl).mean[:3]) / 3.0
        brightness_ratio = (b_live / b_tpl) if b_tpl > 0 else 1.0

        # Active condition: High similarity AND brightness ratio >= threshold
        is_active = (similarity >= similarity_threshold) and (brightness_ratio >= brightness_ratio_threshold)
        return is_active, similarity, brightness_ratio

    def reset_counts(self):
        with self._lock:
            for k in self.counts:
                self.counts[k] = 0
            self.combo_counts.clear()

    def reset_timers(self):
        with self._lock:
            for k in self.last_press_times:
                self.last_press_times[k] = 0.0
            for k in self.counts:
                self.counts[k] = 0
            self.combo_counts.clear()
            self.combo_status.clear()
        self.log("[Auto Skill] Status & Countdown di-reset.")

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
            cfg = self.get_skill_cfg()
            mode = cfg.get("mode", "smart_combo")
            if mode == "smart_combo":
                self.log("⚡ [Auto Skill] Berjalan dalam Mode SMART COMBO (Deteksi Visual Cooldown)...")
            else:
                self.log("⚡ [Auto Skill] Berjalan dalam Mode TIMER INTERVAL (Detik)...")

    def stop(self):
        with self._lock:
            self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.log("⚡ [Auto Skill] Berhenti.")

    def _loop(self):
        while self.is_running:
            try:
                cfg = self.get_skill_cfg()
                if not cfg.get("enabled", True):
                    time.sleep(0.3)
                    continue

                mode = cfg.get("mode", "smart_combo")

                if mode == "smart_combo":
                    self._run_smart_combo_tick(cfg)
                else:
                    self._run_timer_interval_tick()

            except Exception as e:
                time.sleep(0.1)

    def _run_smart_combo_tick(self, cfg: Dict[str, Any]):
        """
        Executes one iteration of Smart Combo:
        Iterates through combo_list in order. Triggers the first skill that is NOT on cooldown,
        applies cast delay, then finishes tick. Skips skills that are on cooldown.
        """
        combo_list = cfg.get("combo_list", [])
        if not combo_list or not self.screen:
            time.sleep(0.2)
            return

        interval = float(cfg.get("combo_check_interval_sec", 0.05))

        client_img = self.screen.capture_client()
        if client_img is None:
            time.sleep(interval)
            return

        cast_executed = False

        # Iterate through combo items in sequence
        for idx, skill_item in enumerate(combo_list):
            if not self.is_running:
                break
            if not skill_item.get("enabled", True):
                continue

            skill_id = str(skill_item.get("id", f"skill_{idx+1}"))
            hotkey = str(skill_item.get("hotkey", "1")).strip().lower()
            skill_name = skill_item.get("name", f"Skill #{idx+1} [{hotkey.upper()}]")
            tpl_path = skill_item.get("template_path") or skill_item.get("icon_filename", "")

            # If no icon configured, skip
            if not tpl_path:
                continue

            template_img = self.load_skill_template(tpl_path)
            if template_img is None:
                continue

            slot_crop = self.get_skill_slot_crop(client_img, skill_item)
            if slot_crop is None:
                continue

            sim_th = float(skill_item.get("similarity_threshold", 0.75))
            br_th = float(skill_item.get("brightness_ratio_threshold", 0.70))
            is_active, sim, b_ratio = self._calc_skill_active_metrics(slot_crop, template_img, sim_th, br_th)

            with self._lock:
                self.combo_status[skill_id] = {
                    "is_active": is_active,
                    "sim": sim,
                    "b_ratio": b_ratio,
                    "hotkey": hotkey,
                    "name": skill_name
                }

            if is_active:
                # Skill is READY to cast!
                try:
                    self.current_combo_index = idx
                    self.input.press_key(hotkey)
                    with self._lock:
                        self.combo_counts[skill_id] = self.combo_counts.get(skill_id, 0) + 1
                        total_c = self.combo_counts[skill_id]
                    cast_delay = max(0.05, float(skill_item.get("cast_delay_sec", 0.30)))
                    self.log(
                        f"⚡ [Smart Combo] Eksekusi '{skill_name}' "
                        f"(Sim: {sim:.2f}, Bright: {b_ratio:.2f}) -> Total: {total_c}x. Delay {cast_delay:.2f}s."
                    )
                    cast_executed = True
                    time.sleep(cast_delay)
                    break  # Break out to advance the combo and re-evaluate next tick
                except Exception as e:
                    self.log(f"⚡ [Smart Combo] Error eksekusi hotkey {hotkey}: {e}")
            else:
                # Skill is on COOLDOWN -> skip immediately to next skill in sequence!
                pass

        if not cast_executed:
            self.current_combo_index = -1
            # All available combo skills are on cooldown, wait a brief tick before checking combo again
            time.sleep(interval)

    def _run_timer_interval_tick(self):
        """Legacy fixed-interval skill execution."""
        keys_cfg = self.get_keys_config()
        now = time.time()

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
                    self.log(f"[Auto Skill Timer] Menekan '{key_name.upper()}' (Total: {self.counts[key_name]})")
                    time.sleep(0.06)
                except Exception as e:
                    self.log(f"[Auto Skill Timer] Error menekan {key_name}: {e}")

        time.sleep(0.05)
