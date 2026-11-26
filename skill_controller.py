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

import re
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
        "f10": {"enabled": False, "interval": 10.0},
    }
}


def parse_slot_info(slot_str: str, hotkey_hint: str = "") -> Tuple[int, int]:
    """
    Parses slot descriptor into (row, col) for 2x10 quickslot bar:
    - row 0: Baris Atas (Number keys: 1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
    - row 1: Baris Bawah (Function keys: F1, F2, F3, F4, F5, F6, F7, F8, F9, F10)
    - col: 0..9
    """
    s = str(slot_str).lower().strip()
    h = str(hotkey_hint).lower().strip()

    # Bawah / Function keys (F1 - F10)
    if "bawah" in s or "f" in s or h.startswith("f"):
        row = 1
        m = re.search(r"f(\d+)", s) or re.search(r"f(\d+)", h)
        if m:
            num = int(m.group(1))
            col = max(0, min(9, num - 1))
            return row, col
        m = re.search(r"(\d+)", s)
        if m:
            num = int(m.group(1))
            col = max(0, min(9, num - 1))
            return row, col
        return 1, 0

    # Atas / Number keys (1 - 0)
    row = 0
    m = re.search(r"(\d+)", s)
    if m:
        num = int(m.group(1))
        if num == 0 or num == 10:
            col = 9
        else:
            col = max(0, min(9, num - 1))
        return row, col

    # Fallback from hotkey hint
    if h in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        return 0, int(h) - 1
    elif h == "0":
        return 0, 9

    return 0, 0


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
        self.last_cast_times: Dict[str, float] = {}
        self.combo_step_index: int = 0
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
        the box from slot descriptor ('slot_str' / 'slot_index') and 'quickslot_bar' calibration.
        Row 0 = Baris Atas (1 - 0), Row 1 = Baris Bawah (F1 - F10).
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

        quickslot_bar = self.get_skill_cfg().get("quickslot_bar", {})
        if not quickslot_bar or "x" not in quickslot_bar or quickslot_bar.get("w", 0) <= 0:
            return None

        slot_str = str(skill_item.get("slot_str") or skill_item.get("slot_index", "") or "")
        hotkey = str(skill_item.get("hotkey", "")).strip().lower()

        row, col = parse_slot_info(slot_str, hotkey)

        cols = max(1, int(quickslot_bar.get("cols", 10)))
        rows = max(1, int(quickslot_bar.get("rows", 2)))
        bar_x = int(quickslot_bar["x"])
        bar_y = int(quickslot_bar["y"])
        bar_w = int(quickslot_bar["w"])
        bar_h = int(quickslot_bar["h"])

        col_w = bar_w / float(cols)
        row_h = bar_h / float(rows)

        col_idx = max(0, min(cols - 1, col))
        row_idx = max(0, min(rows - 1, row))

        return {
            "x": int(bar_x + col_idx * col_w),
            "y": int(bar_y + row_idx * row_h),
            "w": max(1, int(col_w)),
            "h": max(1, int(row_h))
        }

    def get_skill_slot_crop(self, client_img: Image.Image, box_or_item: Any) -> Optional[Image.Image]:
        """
        Crops slot region from client screenshot.
        Accepts either a box dict {'x', 'y', 'w', 'h'} or a full skill_item dict.
        """
        if client_img is None or not box_or_item:
            return None

        if isinstance(box_or_item, dict) and "w" in box_or_item and "h" in box_or_item and "x" in box_or_item and "y" in box_or_item and "slot_index" not in box_or_item and "slot_str" not in box_or_item and "hotkey" not in box_or_item:
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
            self.last_cast_times.clear()
            self.combo_step_index = 0
            self.current_combo_index = -1
        self.log("[Auto Skill] Status, Combo Rotasi & Countdown di-reset.")

    def start(self):
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self.input.reset_abort()
            for k in self.last_press_times:
                self.last_press_times[k] = 0.0
            self.combo_step_index = 0
            self.last_cast_times.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            cfg = self.get_skill_cfg()
            mode = cfg.get("mode", "smart_combo")
            if mode == "smart_combo":
                self.log("⚡ [Auto Skill] Berjalan dalam Mode SMART COMBO (Rotasi Sekuensial & Cooldown Awareness)...")
            else:
                self.log("⚡ [Auto Skill] Berjalan dalam Mode TIMER INTERVAL (Detik)...")

    def stop(self):
        with self._lock:
            self.is_running = False
            self.current_combo_index = -1
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
        Evaluates skills sequentially in combo order (1 -> 2 -> 3 -> 4).
        If a skill is active (not on cooldown), triggers hotkey and advances combo pointer.
        If a skill is on cooldown, skips it immediately to the next skill in sequence.
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

        n_skills = len(combo_list)
        if self.combo_step_index >= n_skills:
            self.combo_step_index = 0

        now = time.time()
        cast_executed = False

        # Evaluate skills in combo sequence starting from current combo_step_index
        for attempt in range(n_skills):
            if not self.is_running:
                break

            idx = (self.combo_step_index + attempt) % n_skills
            skill_item = combo_list[idx]

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

            cast_delay = max(0.05, float(skill_item.get("cast_delay_sec", 0.30)))
            last_cast = self.last_cast_times.get(skill_id, 0.0)

            # Per-skill debounce: cannot re-cast same skill within max(0.5s, cast_delay + 0.2s)
            min_cooldown = max(0.5, cast_delay + 0.2)
            if (now - last_cast) < min_cooldown:
                # Still in debounce window, check next skill in sequence
                continue

            if is_active:
                # Skill is READY to cast!
                try:
                    self.current_combo_index = idx

                    # Ensure game window is focused before sending key
                    if not self.wm.is_window_active():
                        self.wm.activate_window()
                        time.sleep(0.04)

                    # Hold key for 80ms to guarantee DirectX engine registers key press
                    self.input.hold_key(hotkey, 0.08)
                    self.last_cast_times[skill_id] = time.time()

                    with self._lock:
                        self.combo_counts[skill_id] = self.combo_counts.get(skill_id, 0) + 1
                        total_c = self.combo_counts[skill_id]

                    self.log(
                        f"⚡ [Smart Combo] Eksekusi '{skill_name}' "
                        f"(Sim: {sim:.2f}, Bright: {b_ratio:.2f}) -> Total: {total_c}x. Delay {cast_delay:.2f}s."
                    )

                    # Advance combo pointer to next skill in sequence!
                    self.combo_step_index = (idx + 1) % n_skills
                    cast_executed = True
                    time.sleep(cast_delay)
                    break  # Skill cast, finish tick
                except Exception as e:
                    self.log(f"⚡ [Smart Combo] Error eksekusi hotkey {hotkey}: {e}")
                    break
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
