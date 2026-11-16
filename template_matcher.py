"""
Template matcher module.
Handles empty vs occupied slot detection, whitelist/blacklist icon matching,
and confirmation dialog detection using OpenCV and PIL fallbacks.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class TemplateMatcher:
    def __init__(self, config):
        self.config = config
        self.templates_dir = self.config.templates_dir
        self.whitelist_dir = self.config.whitelist_dir
        self.blacklist_dir = self.config.blacklist_dir

        # Cache of loaded templates
        self._cached_templates: Dict[str, Image.Image] = {}

    def _pil_to_cv2(self, pil_img: Image.Image):
        """Converts PIL RGB Image to OpenCV BGR numpy array."""
        if not HAS_CV2:
            return None
        arr = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    def is_slot_empty(self, slot_crop: Image.Image, threshold: float = None) -> bool:
        """
        FR-2: Deteksi Status Slot (Berisi vs Kosong)
        Determines whether an inventory or storage slot is empty or has an item.
        Uses texture variance and color standard deviation.
        """
        if threshold is None:
            threshold = float(self.config.get("rules", "empty_slot_threshold", 18.0))

        w, h = slot_crop.size
        margin_x = max(2, int(w * 0.20))
        margin_y = max(2, int(h * 0.20))
        inner = slot_crop.crop((margin_x, margin_y, w - margin_x, h - margin_y)).convert("RGB")

        if HAS_CV2:
            arr = np.array(inner)
            std_dev = float(np.std(arr))
            return bool(std_dev < threshold)
        else:
            from PIL import ImageStat
            stat = ImageStat.Stat(inner)
            avg_std = sum(stat.stddev) / 3.0
            return bool(avg_std < threshold)

    def match_template_in_image(
        self,
        haystack: Image.Image,
        needle: Image.Image,
        threshold: float = 0.8
    ) -> Optional[Tuple[int, int, float]]:
        """
        Finds needle inside haystack.
        Returns (center_x, center_y, confidence) or None if below threshold.
        """
        if HAS_CV2:
            hay_cv = self._pil_to_cv2(haystack)
            need_cv = self._pil_to_cv2(needle)

            if hay_cv is None or need_cv is None:
                return None

            if need_cv.shape[0] > hay_cv.shape[0] or need_cv.shape[1] > hay_cv.shape[1]:
                return None

            res = cv2.matchTemplate(hay_cv, need_cv, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if max_val >= threshold:
                h, w = need_cv.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return center_x, center_y, float(max_val)
            return None
        else:
            # PIL sliding difference fallback
            from PIL import ImageChops, ImageStat
            hw, hh = haystack.size
            nw, nh = needle.size
            if nw > hw or nh > hh:
                return None

            needle_rgb = needle.convert("RGB")
            step = 4
            best_score = 0.0
            best_pos = None

            for y in range(0, hh - nh + 1, step):
                for x in range(0, hw - nw + 1, step):
                    patch = haystack.crop((x, y, x + nw, y + nh)).convert("RGB")
                    diff = ImageChops.difference(patch, needle_rgb)
                    stat = ImageStat.Stat(diff)
                    mae = sum(stat.mean) / 3.0
                    score = max(0.0, 1.0 - (mae / 255.0))
                    if score > best_score:
                        best_score = score
                        best_pos = (x + nw // 2, y + nh // 2)

            if best_score >= threshold and best_pos:
                return best_pos[0], best_pos[1], best_score
            return None

    def detect_sell_popup(self, client_img: Image.Image) -> bool:
        """
        FR-6: Detects if the sell confirmation dialog ('Message' / 'Will you sell') is visible.
        Checks for the OK button or the popup message title.
        """
        ok_btn_path = self.templates_dir / "btn_ok.png"
        msg_title_path = self.templates_dir / "popup_message_title.png"

        # Search in center region of the client window
        search_region = client_img.crop((200, 150, 824, 600))

        if ok_btn_path.exists():
            needle = Image.open(ok_btn_path)
            res = self.match_template_in_image(search_region, needle, threshold=0.72)
            if res is not None:
                return True

        if msg_title_path.exists():
            needle = Image.open(msg_title_path)
            res = self.match_template_in_image(search_region, needle, threshold=0.70)
            if res is not None:
                return True

        return False

    def match_item_in_whitelist(self, slot_crop: Image.Image, whitelist_dir: Optional[Path] = None, threshold: Optional[float] = None) -> Tuple[bool, Optional[str], float]:
        """
        Compares slot image against all icons in whitelist_dir (defaults to assets/merchant_blacklist/).
        Uses sliding window matching to tolerate 1-4px calibration shifts and jitter.
        Returns (is_whitelisted, item_name, confidence).
        """
        target_dir = whitelist_dir if whitelist_dir is not None else self.whitelist_dir
        if threshold is None:
            threshold = float(self.config.get("rules", "sell_whitelist_match_threshold", 0.50))

        whitelist_files = list(target_dir.glob("*.png")) + list(target_dir.glob("*.jpg"))
        if not whitelist_files:
            return False, None, 0.0

        best_score = 0.0
        best_name = None

        w, h = slot_crop.size
        inner_slot = slot_crop.crop((2, 2, max(3, w - 2), max(3, h - 2))).convert("RGB")
        sw_in, sh_in = inner_slot.size

        for icon_path in whitelist_files:
            icon_name = icon_path.stem
            try:
                icon_img = Image.open(icon_path).convert("RGB")
                iw, ih = icon_img.size
                if iw < 4 or ih < 4:
                    continue

                if HAS_CV2:
                    slot_cv = self._pil_to_cv2(inner_slot)
                    scores = []

                    # Scale A: Sliding window (needle smaller by 6px to allow sliding search across jitter)
                    target_w = max(10, sw_in - 6)
                    target_h = max(10, sh_in - 6)
                    icon_small = icon_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
                    icon_cv_small = self._pil_to_cv2(icon_small)

                    if slot_cv.shape[0] >= icon_cv_small.shape[0] and slot_cv.shape[1] >= icon_cv_small.shape[1]:
                        res_slide = cv2.matchTemplate(slot_cv, icon_cv_small, cv2.TM_CCOEFF_NORMED)
                        _, max_v, _, _ = cv2.minMaxLoc(res_slide)
                        scores.append(float(max_v))

                    # Scale B: Exact size overlay
                    icon_exact = icon_img.resize((sw_in, sh_in), Image.Resampling.BILINEAR)
                    icon_cv_exact = self._pil_to_cv2(icon_exact)
                    res_exact = cv2.matchTemplate(slot_cv, icon_cv_exact, cv2.TM_CCOEFF_NORMED)
                    scores.append(float(res_exact[0][0]))

                    score = max(scores) if scores else 0.0
                else:
                    from PIL import ImageChops, ImageStat
                    icon_exact = icon_img.resize(inner_slot.size, Image.Resampling.BILINEAR)
                    diff = ImageChops.difference(inner_slot, icon_exact)
                    stat = ImageStat.Stat(diff)
                    mae = sum(stat.mean) / 3.0
                    score = max(0.0, 1.0 - (mae / 255.0))

                if score > best_score:
                    best_score = score
                    best_name = icon_name
            except Exception as e:
                print(f"[TemplateMatcher] Error matching {icon_path}: {e}")

        is_match = bool(best_score >= threshold)
        return is_match, best_name, float(best_score)
