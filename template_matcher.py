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

    def detect_death_popup(self, client_img: Image.Image, threshold: float = 0.65) -> Optional[Tuple[int, int, float]]:
        """
        Detects character death respawn dialog:
        'If you click OK, you will respawn at the last saved location'.
        Checks popup_respawn_death.png and death_text_needle.png in templates_dir across full screen.
        Compatible with 800x600, 1024x768, and any dragged popup positions.
        Returns (center_x, center_y, confidence) or None.
        """
        # Full client image search to ensure detection in all resolutions (800x600, 1024x768)
        search_region = client_img

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
                        return (rx, ry, conf)
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

    # =========================================================================
    # NPC & Navigation Detection Methods
    # =========================================================================
    @staticmethod
    def _is_yellow_pixel(r: int, g: int, b: int) -> bool:
        """
        Detects yellow text pixels regardless of terrain blending, anti-aliasing, or lighting.
        Yellow color requires high Red & Green, and significantly lower Blue relative to both.
        """
        return bool(r > 160 and g > 160 and (r - b) > 40 and (g - b) > 40)

    def find_yellow_tag_clusters(self, client_img: Image.Image, min_pixels: int = 25) -> List[Dict]:
        """
        Fast C-accelerated scan for yellow text pixels (NPC names like Tradesman Abahan & Jeweler Ashuri).
        Uses PIL channel operations for ~10x speedup and line-based bounding box clustering.
        Returns a list of cluster dicts: {'x_mid', 'y_mid', 'x_min', 'x_max', 'y_min', 'y_max', 'count'}.
        """
        from PIL import ImageChops
        offset_x, offset_y = 50, 40
        w_img, h_img = client_img.size
        crop_w = max(10, w_img - 100)
        crop_h = max(10, h_img - 120)

        crop = client_img.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h)).convert("RGB")
        r, g, b = crop.split()

        # C-accelerated thresholding & difference mask:
        # (r > 160) & (g > 160) & ((r - b) > 40) & ((g - b) > 40)
        r_th = r.point(lambda p: 255 if p > 160 else 0)
        g_th = g.point(lambda p: 255 if p > 160 else 0)
        rg_mask = ImageChops.multiply(r_th, g_th)

        r_sub_b = ImageChops.subtract(r, b).point(lambda p: 255 if p > 40 else 0)
        g_sub_b = ImageChops.subtract(g, b).point(lambda p: 255 if p > 40 else 0)
        diff_mask = ImageChops.multiply(r_sub_b, g_sub_b)

        yellow_mask = ImageChops.multiply(rg_mask, diff_mask)
        raw_bytes = yellow_mask.tobytes()
        mw, mh = yellow_mask.size

        clusters = []
        for idx in range(len(raw_bytes)):
            if raw_bytes[idx]:
                x = (idx % mw) + offset_x
                y = (idx // mw) + offset_y
                matched = False
                for c in clusters:
                    # Text line clustering: vertical within 8px, horizontal within 24px of word bounding box
                    if abs(c["y_mid"] - y) <= 8 and (c["x_min"] - 24) <= x <= (c["x_max"] + 24):
                        c["pts"].append((x, y))
                        c["x_min"] = min(c["x_min"], x)
                        c["x_max"] = max(c["x_max"], x)
                        c["y_min"] = min(c["y_min"], y)
                        c["y_max"] = max(c["y_max"], y)
                        c["x_mid"] = (c["x_min"] + c["x_max"]) // 2
                        c["y_mid"] = (c["y_min"] + c["y_max"]) // 2
                        matched = True
                        break
                if not matched:
                    clusters.append({
                        "x_min": x, "x_max": x,
                        "y_min": y, "y_max": y,
                        "x_mid": x, "y_mid": y,
                        "pts": [(x, y)]
                    })

        valid_clusters = []
        for c in clusters:
            count = len(c["pts"])
            if count >= min_pixels:
                valid_clusters.append({
                    "x_mid": c["x_mid"],
                    "y_mid": c["y_mid"],
                    "x_min": c["x_min"],
                    "x_max": c["x_max"],
                    "y_min": c["y_min"],
                    "y_max": c["y_max"],
                    "count": count
                })

        # Sort clusters from top to bottom (ascending y)
        valid_clusters.sort(key=lambda item: item["y_mid"])
        return valid_clusters

    def _extract_yellow_points(self, img_crop: Image.Image) -> set:
        """Extracts relative (x, y) coordinates of yellow text pixels."""
        rgb = img_crop.convert("RGB")
        w, h = rgb.size
        pts = set()
        for y in range(h):
            for x in range(w):
                r, g, b = rgb.getpixel((x, y))
                if self._is_yellow_pixel(r, g, b):
                    pts.add((x, y))
        return pts

    def _match_pattern_iou(self, cand_pts: set, tmpl_pts: set) -> float:
        """Calculates IoU match score between candidate yellow points and template yellow points."""
        if not cand_pts or not tmpl_pts:
            return 0.0
        min_cx = min(p[0] for p in cand_pts)
        min_cy = min(p[1] for p in cand_pts)
        min_tx = min(p[0] for p in tmpl_pts)
        min_ty = min(p[1] for p in tmpl_pts)

        cand_norm = set((p[0] - min_cx, p[1] - min_cy) for p in cand_pts)
        tmpl_norm = set((p[0] - min_tx, p[1] - min_ty) for p in tmpl_pts)

        best_iou = 0.0
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                shifted_tmpl = set((p[0] + dx, p[1] + dy) for p in tmpl_norm)
                intersection = len(cand_norm.intersection(shifted_tmpl))
                union = len(cand_norm.union(shifted_tmpl))
                iou = intersection / union if union > 0 else 0.0
                if iou > best_iou:
                    best_iou = iou
        return best_iou

    def detect_npc_tag(self, client_img: Image.Image, target_npc: str = "ashuri", threshold: float = 0.50) -> Optional[Tuple[int, int, float]]:
        """
        Detects NPC yellow text tag ('ashuri' or 'abahan') using shape-accurate binary IoU matching.
        Strictly rejects unrelated NPCs like Craftsman Kirika (score ~0.18 < 0.50).
        Returns (center_x, center_y, confidence) or None if target is not visible.
        """
        target_lower = target_npc.lower()
        tpl_name = "npc_ashuri_exact.png" if "ashuri" in target_lower else "npc_abahan_exact.png"
        tpl_path = self.templates_dir / tpl_name

        if not tpl_path.exists():
            tpl_path = self.templates_dir / ("npc_ashuri_tag.png" if "ashuri" in target_lower else "npc_abahan_tag.png")

        if not tpl_path.exists():
            return None

        try:
            tmpl_img = Image.open(tpl_path)
            tmpl_pts = self._extract_yellow_points(tmpl_img)
            if not tmpl_pts:
                return None
        except Exception:
            return None

        clusters = self.find_yellow_tag_clusters(client_img, min_pixels=25)
        if not clusters:
            return None

        best_match = None
        best_score = 0.0

        w_img, h_img = client_img.size

        for c in clusters:
            pad = 3
            cx1 = max(0, c["x_min"] - pad)
            cy1 = max(0, c["y_min"] - pad)
            cx2 = min(w_img, c["x_max"] + pad)
            cy2 = min(h_img, c["y_max"] + pad)

            crop = client_img.crop((cx1, cy1, cx2, cy2))
            cand_pts = self._extract_yellow_points(crop)
            score = self._match_pattern_iou(cand_pts, tmpl_pts)

            if score > best_score:
                best_score = score
                best_match = (c["x_mid"], c["y_mid"], float(score))

        # Only accept if match score meets threshold (eliminates Kirika, other players/NPCs)
        if best_match and best_score >= threshold:
            return best_match

        return None

    def detect_conversation_dialog(self, client_img: Image.Image, threshold: float = 0.65) -> bool:
        """
        Checks if the NPC Conversation window is currently open.
        Looks for the 'Conversation' header at top-left (x: 10-200, y: 80-140).
        """
        conv_tpl = self.templates_dir / "dialog_conversation_title.png"
        if conv_tpl.exists():
            needle = Image.open(conv_tpl)
            search_region = client_img.crop((10, 70, 220, 150))
            res = self.match_template_in_image(search_region, needle, threshold=threshold)
            if res is not None:
                return True

        # Fallback: check for dark conversation box with orange options
        rgb_img = client_img.crop((10, 80, 350, 450)).convert("RGB")
        orange_count = 0
        w, h = rgb_img.size
        for y in range(h):
            for x in range(w):
                r, g, b = rgb_img.getpixel((x, y))
                if r > 180 and 80 < g < 180 and b < 60:
                    orange_count += 1
                    if orange_count > 60:
                        return True
        return False

    def detect_dialog_menu_option(self, client_img: Image.Image, option_type: str = "storage", threshold: float = 0.65) -> Optional[Tuple[int, int]]:
        """
        Finds the clickable coordinate for the dialog option:
        - option_type == 'storage': 'Store/Remove Items'
        - option_type == 'merchant': 'Buy/Sell Items'
        Returns (x, y) coordinates relative to client canvas, or None.
        """
        tpl_name = "dialog_store_menu.png" if option_type == "storage" else "dialog_merchant_menu.png"
        tpl_path = self.templates_dir / tpl_name

        search_crop = client_img.crop((50, 200, 300, 320))
        if tpl_path.exists():
            needle = Image.open(tpl_path)
            res = self.match_template_in_image(search_crop, needle, threshold=threshold)
            if res is not None:
                rx, ry, _ = res
                return rx + 50, ry + 200

        # Fallback: calculate based on orange text line 2 in conversation dialog
        rgb_crop = search_crop.convert("RGB")
        w, h = rgb_crop.size
        orange_pts = []
        for y in range(h):
            for x in range(w):
                r, g, b = rgb_crop.getpixel((x, y))
                if r > 180 and 80 < g < 180 and b < 60:
                    orange_pts.append((x + 50, y + 200))

        if not orange_pts:
            # Default fallback coordinates based on UI layout
            return (167, 270) if option_type == "storage" else (167, 242)

        # The action option is always in the lower group of orange text
        y_split = 255 if option_type == "storage" else 235
        line2_pts = [p for p in orange_pts if p[1] >= y_split]
        if line2_pts:
            avg_x = sum(p[0] for p in line2_pts) // len(line2_pts)
            avg_y = sum(p[1] for p in line2_pts) // len(line2_pts)
            return avg_x, avg_y

        return (167, 270) if option_type == "storage" else (167, 242)
