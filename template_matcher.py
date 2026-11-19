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

    def detect_death_popup(self, client_img: Image.Image, threshold: float = 0.70) -> Optional[Tuple[int, int, float]]:
        """
        Detects character death respawn dialog:
        'If you click OK, you will respawn at the last saved location'.
        Checks popup_respawn_death.png and death_text_needle.png in templates_dir.
        Returns (center_x, center_y, confidence) or None.
        """
        w, h = client_img.size
        # Search in central area of the client window
        off_x = max(0, (w - 600) // 2)
        off_y = max(0, (h - 450) // 2)
        search_w = min(w - off_x, 600)
        search_h = min(h - off_y, 450)
        search_region = client_img.crop((off_x, off_y, off_x + search_w, off_y + search_h))

        candidates = [
            self.templates_dir / "popup_respawn_death.png",
            self.templates_dir / "death_text_needle.png"
        ]

        for cand_path in candidates:
            if cand_path.exists():
                try:
                    needle = Image.open(cand_path)
                    res = self.match_template_in_image(search_region, needle, threshold=threshold)
                    if res is not None:
                        rx, ry, conf = res
                        return (off_x + rx, off_y + ry, conf)
                except Exception as e:
                    print(f"[TemplateMatcher] Error matching death popup: {e}")

        return None

    def detect_storage_popup(self, client_img: Image.Image, threshold: float = 0.70) -> Optional[Tuple[str, int, int, float]]:
        """
        Detects modal popups (Notice, Quiz, Lucky Number, Raffle) blocking the storage window.
        Scans against all popup templates in config.storage_popups_dir.
        Returns (popup_name, center_x, center_y, confidence) or None.
        """
        popups_dir = getattr(self.config, "storage_popups_dir", self.config.assets_dir / "storage_popups")
        popup_files = list(popups_dir.glob("*.png")) + list(popups_dir.glob("*.jpg"))
        if not popup_files:
            return None

        # Search region: seluruh layar game Tantra agar popup tetap terdeteksi meski digeser ke mana saja
        search_region = client_img

        best_match = None
        best_conf = 0.0

        for p_file in popup_files:
            try:
                needle = Image.open(p_file)
                res = self.match_template_in_image(search_region, needle, threshold=threshold)
                if res is not None:
                    rx, ry, conf = res
                    if conf > best_conf:
                        best_conf = conf
                        best_match = (p_file.stem, rx, ry, conf)
            except Exception as e:
                print(f"[TemplateMatcher] Error checking popup template {p_file}: {e}")

        return best_match

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

                    # Scale C: Unresized center needle (preserves 100% original texture & edge sharpness)
                    if iw >= 10 and ih >= 10:
                        pad = 3
                        icon_needle = icon_img.crop((pad, pad, max(pad + 4, iw - pad), max(pad + 4, ih - pad)))
                        icon_cv_needle = self._pil_to_cv2(icon_needle)
                        if slot_cv.shape[0] >= icon_cv_needle.shape[0] and slot_cv.shape[1] >= icon_cv_needle.shape[1]:
                            res_needle = cv2.matchTemplate(slot_cv, icon_cv_needle, cv2.TM_CCOEFF_NORMED)
                            _, max_v_needle, _, _ = cv2.minMaxLoc(res_needle)
                            scores.append(float(max_v_needle))

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

        # Toleransi: jika skor sama dengan threshold (misal 0.70 == 0.70) atau lebih -> Cocok (JANGAN dieksekusi)
        # Hanya dieksekusi jika skor benar-benar kurang dari threshold
        is_match = bool(round(best_score, 2) >= round(threshold, 2) or best_score >= (threshold - 1e-4))
        return is_match, best_name, float(best_score)
