"""
Farmer Bot core automation module for Tantra Online.
Supports customizable bounding box areas for:
- Inventory (48 slots default, 6 cols x 8 rows)
- Storage (128 slots default, 16 cols x 8 rows)
- Merchant (drop target area)
Strictly enforces dropping ONLY on empty slots (never stacks).
"""

import time
from typing import Callable, Dict, List, Optional, Tuple
from PIL import Image

from skill_controller import SkillController


class FarmerBot:
    def __init__(self, window_manager, screen_capture, input_controller, template_matcher, ocr_engine, config):
        self.wm = window_manager
        self.screen = screen_capture
        self.input = input_controller
        self.matcher = template_matcher
        self.ocr = ocr_engine
        self.config = config
        self.skills = SkillController(self.input, self.wm, self.config, logger=self.log)

        self.is_running = False
        self.log_callback: Optional[Callable[[str], None]] = None
        self.on_death_callback: Optional[Callable[[], None]] = None

    def log(self, message: str) -> None:
        formatted = f"[FarmerBot] {message}"
        print(formatted)
        if self.log_callback:
            self.log_callback(formatted)

    def stop(self) -> None:
        """Stops the current running macro execution."""
        self.is_running = False
        self.input.abort()
        self.skills.stop()
        self.log("Macro stopped by user.")

    # =========================================================================
    # Coordinate & Crop Helpers (Dynamic Bounding Boxes)
    # =========================================================================
    def get_inventory_slot_coords(self, col: int, row: int) -> Tuple[int, int]:
        """Returns (cx, cy) relative center for an inventory slot."""
        inv = self.config.get("inventory")
        x1 = inv.get("x1", 537)
        y1 = inv.get("y1", 280)
        x2 = inv.get("x2", 758)
        y2 = inv.get("y2", 430)
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)

        cell_w = (x2 - x1) / max(1, cols)
        cell_h = (y2 - y1) / max(1, rows)

        cx = int(x1 + (col * cell_w) + (cell_w / 2))
        cy = int(y1 + (row * cell_h) + (cell_h / 2))
        return cx, cy

    def get_inventory_slot_crop(self, client_img: Image.Image, col: int, row: int) -> Image.Image:
        """Crops a specific inventory slot."""
        inv = self.config.get("inventory")
        x1 = inv.get("x1", 537)
        y1 = inv.get("y1", 280)
        x2 = inv.get("x2", 758)
        y2 = inv.get("y2", 430)
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)

        cell_w = (x2 - x1) / max(1, cols)
        cell_h = (y2 - y1) / max(1, rows)

        sl = max(0, int(x1 + (col * cell_w)))
        st = max(0, int(y1 + (row * cell_h)))
        sr = min(client_img.width, int(sl + cell_w))
        sb = min(client_img.height, int(st + cell_h))
        return client_img.crop((sl, st, sr, sb))

    def get_storage_slot_coords(self, col: int, row: int) -> Tuple[int, int]:
        """Returns (cx, cy) relative center for a storage slot."""
        store = self.config.get("storage")
        x1 = store.get("x1", 55)
        y1 = store.get("y1", 233)
        x2 = store.get("x2", 467)
        y2 = store.get("y2", 691)
        cols = store.get("cols", 10)
        rows = store.get("rows", 12)

        cell_w = (x2 - x1) / max(1, cols)
        cell_h = (y2 - y1) / max(1, rows)

        cx = int(x1 + (col * cell_w) + (cell_w / 2))
        cy = int(y1 + (row * cell_h) + (cell_h / 2))
        return cx, cy

    def get_storage_slot_crop(self, client_img: Image.Image, col: int, row: int) -> Image.Image:
        """Crops a specific storage slot."""
        store = self.config.get("storage")
        x1 = store.get("x1", 55)
        y1 = store.get("y1", 233)
        x2 = store.get("x2", 467)
        y2 = store.get("y2", 691)
        cols = store.get("cols", 10)
        rows = store.get("rows", 12)

        cell_w = (x2 - x1) / max(1, cols)
        cell_h = (y2 - y1) / max(1, rows)

        sl = max(0, int(x1 + (col * cell_w)))
        st = max(0, int(y1 + (row * cell_h)))
        sr = min(client_img.width, int(sl + cell_w))
        sb = min(client_img.height, int(st + cell_h))
        return client_img.crop((sl, st, sr, sb))

    def get_merchant_drop_coords(self) -> Tuple[int, int]:
        """Returns center coordinates of the merchant drop area."""
        merch = self.config.get("merchant")
        if "x1" in merch and "x2" in merch:
            cx = int((merch["x1"] + merch["x2"]) / 2)
            cy = int((merch["y1"] + merch["y2"]) / 2)
            return cx, cy
        return merch.get("drop_target_x", 505), merch.get("drop_target_y", 450)

    # =========================================================================
    # Empty Slot Scanners (Strict No-Stacking)
    # =========================================================================
    def find_empty_inventory_slot(self, client_img: Image.Image) -> Optional[Tuple[int, int]]:
        """
        Scans all 48 inventory slots to find the first strictly empty slot.
        Returns (col, row) or None if inventory is full.
        """
        inv = self.config.get("inventory")
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)

        for r in range(rows):
            for c in range(cols):
                slot_crop = self.get_inventory_slot_crop(client_img, c, r)
                if self.matcher.is_slot_empty(slot_crop):
                    return c, r
        return None

    def find_empty_storage_slot(self, client_img: Image.Image) -> Optional[Tuple[int, int]]:
        """
        Scans all 120 storage slots to find the first strictly empty slot.
        Returns (col, row) or None if storage is full.
        """
        store = self.config.get("storage")
        cols = store.get("cols", 10)
        rows = store.get("rows", 12)

        for r in range(rows):
            for c in range(cols):
                slot_crop = self.get_storage_slot_crop(client_img, c, r)
                if self.matcher.is_slot_empty(slot_crop):
                    return c, r
        return None

    def scan_inventory_status(self, client_img: Image.Image) -> List[Dict]:
        """Scans and returns the status of every inventory slot."""
        inv = self.config.get("inventory")
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)
        results = []

        for r in range(rows):
            for c in range(cols):
                idx = (r * cols) + c + 1
                crop = self.get_inventory_slot_crop(client_img, c, r)
                is_empty = self.matcher.is_slot_empty(crop)
                results.append({
                    "col": c,
                    "row": r,
                    "index": idx,
                    "is_empty": is_empty,
                    "crop": crop
                })
        return results

    def scan_storage_status(self, client_img: Image.Image) -> List[Dict]:
        """Scans and returns the status of every storage slot."""
        store = self.config.get("storage")
        cols = store.get("cols", 10)
        rows = store.get("rows", 12)
        results = []

        for r in range(rows):
            for c in range(cols):
                idx = (r * cols) + c + 1
                crop = self.get_storage_slot_crop(client_img, c, r)
                is_empty = self.matcher.is_slot_empty(crop)
                results.append({
                    "col": c,
                    "row": r,
                    "index": idx,
                    "is_empty": is_empty,
                    "crop": crop
                })
        return results

    def capture_tooltip_for_slot(self, slot_x: int, slot_y: int) -> Image.Image:
        """Hover over slot and capture the appearing tooltip."""
        self.input.hover(slot_x, slot_y)
        client_img = self.screen.capture_client()

        x_min = max(0, slot_x - 300)
        y_min = max(0, slot_y - 250)
        x_max = min(client_img.width, slot_x + 300)
        y_max = min(client_img.height, slot_y + 250)
        return client_img.crop((x_min, y_min, x_max, y_max))

    # =========================================================================
    # HELPER: Tutup Objek / Popup yang Menutupi Storage (Notice, Quiz, Raffle)
    # =========================================================================
    def dismiss_storage_popup(self, manual: bool = False) -> bool:
        """
        Menutup objek / popup modal (Notice, Lucky Number, Raffle, Quiz) yang menutupi Storage.
        Hanya bertindak jika terdeteksi popup dari template yang cocok (score >= threshold).
        Jika TIDAK ada popup yang cocok atau TIDAK ada template popup terdaftar,
        makro TIDAK AKAN mengklik atau menekan Esc agar jendela Storage tidak ikut tertutup!
        """
        self.wm.activate_window()
        time.sleep(0.12)

        client_img = self.screen.capture_client()
        th = float(self.config.get("storage_popup", "match_threshold", 0.70))
        match = self.matcher.detect_storage_popup(client_img, threshold=th)

        if match:
            p_name, cx, cy, conf = match
            self.log(f"🛡️ [Popup Guard] Terdeteksi popup '{p_name}' di ({cx}, {cy}) [Score: {conf:.2f} >= Min:{th:.2f}].")
            self.log(f"🛡️ [Popup Guard] Mengklik judul popup ({cx}, {cy}) lalu menekan Esc 1x untuk menutup modal...")
            self.input.click(cx, cy)
            time.sleep(0.15)
            self.input.press_key("esc")
            time.sleep(0.25)
            self.log(f"🛡️ [Popup Guard] Popup '{p_name}' berhasil ditutup.")
            return True
        else:
            if manual:
                self.log(f"ℹ️ [Popup Guard] Tidak ada popup yang cocok terdeteksi di layar (Threshold: {th:.2f}). Esc tidak ditekan agar Storage tidak tertutup.")
            return False

    # =========================================================================
    # TASK 1: Inventory ke Storage (Simpan ke Gudang dengan Filter Blacklist)
    # =========================================================================
    def run_inventory_to_storage(self) -> None:
        self.is_running = True
        self.input.reset_abort()
        self.log("Memulai tugas: Inventory ke Storage...")

        self.wm.activate_window()
        time.sleep(0.3)

        if self.config.get("storage_popup", "auto_dismiss", False):
            self.dismiss_storage_popup()

        inv = self.config.get("inventory")
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)

        storage_cfg = self.config.get("storage_deposit", {})
        blacklist_enabled = storage_cfg.get("blacklist_enabled", True)
        blacklist_icons = list(self.config.storage_blacklist_dir.glob("*.png")) + list(self.config.storage_blacklist_dir.glob("*.jpg"))

        transferred_count = 0

        try:
            for r in range(rows):
                for c in range(cols):
                    if not self.is_running:
                        self.log("Proses dihentikan.")
                        return

                    slot_idx = (r * cols) + c + 1
                    client_img = self.screen.capture_client()
                    slot_crop = self.get_inventory_slot_crop(client_img, c, r)

                    # 1. Lewati slot kosong
                    if self.matcher.is_slot_empty(slot_crop):
                        continue

                    slot_cx, slot_cy = self.get_inventory_slot_coords(c, r)

                    # 2. Cek BLACKLIST GUDANG (Item yang TIDAK dipindahkan dari inventory ke gudang)
                    is_blacklisted = False
                    bl_name = None
                    score = 0.0
                    th_store = float(self.config.get("rules", "storage_blacklist_match_threshold",
                                     self.config.get("rules", "sell_whitelist_match_threshold", 0.50)))
                    if blacklist_enabled and blacklist_icons:
                        is_blacklisted, bl_name, score = self.matcher.match_item_in_whitelist(
                            slot_crop, whitelist_dir=self.config.storage_blacklist_dir, threshold=th_store
                        )
                        if round(score, 2) >= round(th_store, 2) or score >= (th_store - 1e-4):
                            is_blacklisted = True

                        status_str = "🛑 BLACKLIST GUDANG (TINGGAL DI TAS)" if is_blacklisted else "📦 PINDAH KE GUDANG"
                        self.log(f"Slot #{slot_idx} [B:{r+1}, K:{c+1}]: Match '{bl_name}'={score:.2f} (Min:{th_store:.2f}) -> {status_str}")

                    if is_blacklisted:
                        continue

                    # 3. Item bukan Blacklist: Pindahkan langsung ke slot kosong di gudang
                    fresh_screen = self.screen.capture_client()
                    empty_storage = self.find_empty_storage_slot(fresh_screen)
                    if not empty_storage:
                        self.log("Gudang (Storage 120 slot) PENUH! Tidak ada slot kosong tersisa.")
                        return

                    target_store_c, target_store_r = empty_storage
                    dest_cx, dest_cy = self.get_storage_slot_coords(target_store_c, target_store_r)
                    dest_idx = (target_store_r * self.config.get("storage", "cols", 10)) + target_store_c + 1

                    self.log(f"Memindahkan Slot #{slot_idx} ke Storage Kosong #{dest_idx} [{target_store_r+1},{target_store_c+1}]...")
                    self.input.drag_and_drop(slot_cx, slot_cy, dest_cx, dest_cy)
                    transferred_count += 1
                    time.sleep(self.config.get("delays", "post_action_delay_sec", 0.25))

            self.log(f"Selesai! Berhasil memindahkan {transferred_count} item ke Storage.")

        except InterruptedError:
            self.log("Tugas dibatalkan oleh user.")
        except Exception as e:
            self.log(f"Error pada Inventory ke Storage: {e}")
        finally:
            self.is_running = False

    # =========================================================================
    # TASK 2: Storage ke Inventory (Tarik ke Slot Kosong Tas - Ga Bisa Ditumpuk)
    # =========================================================================
    def run_storage_to_inventory(self) -> None:
        self.is_running = True
        self.input.reset_abort()
        self.log("Memulai tugas: Storage ke Inventory (Wajib Drop di Slot Kosong)...")

        self.wm.activate_window()
        time.sleep(0.3)

        if self.config.get("storage_popup", "auto_dismiss", False):
            self.dismiss_storage_popup()

        store = self.config.get("storage")
        cols = store.get("cols", 10)
        rows = store.get("rows", 12)

        withdrawn_count = 0

        try:
            for r in range(rows):
                for c in range(cols):
                    if not self.is_running:
                        self.log("Proses dihentikan.")
                        return

                    slot_idx = (r * cols) + c + 1
                    client_img = self.screen.capture_client()
                    slot_crop = self.get_storage_slot_crop(client_img, c, r)

                    # If storage slot is empty, continue
                    if self.matcher.is_slot_empty(slot_crop):
                        continue

                    # Find a STRICTLY EMPTY slot in inventory
                    empty_inv = self.find_empty_inventory_slot(client_img)
                    if not empty_inv:
                        self.log("Inventaris Tas PENUH! Tidak ada slot kosong tersisa. Penarikan dihentikan.")
                        return

                    target_inv_c, target_inv_r = empty_inv
                    dest_cx, dest_cy = self.get_inventory_slot_coords(target_inv_c, target_inv_r)
                    dest_idx = (target_inv_r * self.config.get("inventory", "cols", 6)) + target_inv_c + 1

                    src_cx, src_cy = self.get_storage_slot_coords(c, r)

                    self.log(f"Menarik item Storage #{slot_idx} ke Tas Kosong #{dest_idx} [{target_inv_r+1},{target_inv_c+1}]...")
                    self.input.drag_and_drop(src_cx, src_cy, dest_cx, dest_cy)
                    withdrawn_count += 1
                    time.sleep(0.3)

            self.log(f"Selesai! Berhasil menarik {withdrawn_count} item ke Inventaris.")

        except InterruptedError:
            self.log("Tugas dibatalkan oleh user.")
        except Exception as e:
            self.log(f"Error pada Storage ke Inventory: {e}")
        finally:
            self.is_running = False

    # =========================================================================
    # =========================================================================
    # TASK 3: Inventory ke NPC Merchant (Jual Item kecuali Blacklist)
    # =========================================================================
    def run_inventory_to_npc(self) -> None:
        self.is_running = True
        self.input.reset_abort()
        self.log("Memulai tugas: Penjualan Item ke NPC Merchant (Filter Blacklist Toko)...")

        self.wm.activate_window()
        time.sleep(0.3)

        drop_x, drop_y = self.get_merchant_drop_coords()

        inv = self.config.get("inventory")
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)

        bl_icons = list(self.config.merchant_blacklist_dir.glob("*.png")) + list(self.config.merchant_blacklist_dir.glob("*.jpg"))
        threshold = float(self.config.get("rules", "sell_whitelist_match_threshold", 0.50))
        self.log(f"[Blacklist Jual NPC] Memuat {len(bl_icons)} item blacklist: {[p.stem for p in bl_icons]} (Threshold: {threshold})")
        sold_count = 0

        try:
            for r in range(rows):
                for c in range(cols):
                    if not self.is_running:
                        self.log("Proses dihentikan.")
                        return

                    slot_idx = (r * cols) + c + 1
                    client_img = self.screen.capture_client()
                    slot_crop = self.get_inventory_slot_crop(client_img, c, r)

                    # 1. Lewati slot kosong
                    if self.matcher.is_slot_empty(slot_crop):
                        continue

                    slot_cx, slot_cy = self.get_inventory_slot_coords(c, r)

                    # 2. Cek apakah item masuk BLACKLIST JUAL NPC (Item yang TIDAK dijual)
                    is_blacklisted = False
                    bl_name = None
                    if bl_icons:
                        is_blacklisted, bl_name, score = self.matcher.match_item_in_whitelist(
                            slot_crop, whitelist_dir=self.config.merchant_blacklist_dir, threshold=threshold
                        )
                        # Toleransi: jika skor sama dengan threshold (misal 0.70 == 0.70) atau lebih -> JANGAN DIJUAL
                        if round(score, 2) >= round(threshold, 2) or score >= (threshold - 1e-4):
                            is_blacklisted = True

                        status_str = "🛑 BLACKLIST (TIDAK DIJUAL)" if is_blacklisted else "💰 AKAN DIJUAL"
                        self.log(f"Slot #{slot_idx} [B:{r+1}, K:{c+1}]: Match '{bl_name}'={score:.2f} (Min:{threshold:.2f}) -> {status_str}")

                    if is_blacklisted:
                        continue

                    # 3. Item bukan Blacklist: Jual ke Merchant
                    self.log(f"Menjual Slot #{slot_idx} ke Toko Merchant...")
                    self.input.drag_and_drop(slot_cx, slot_cy, drop_x, drop_y)

                    # Langsung tekan Enter untuk konfirmasi penjualan
                    time.sleep(0.2)
                    self.log(f"Menekan Enter untuk konfirmasi penjualan Slot #{slot_idx}...")
                    self.input.press_key("enter")
                    sold_count += 1
                    time.sleep(0.25)

            self.log(f"Selesai! Total item berhasil dijual: {sold_count}.")

        except InterruptedError:
            self.log("Tugas dibatalkan oleh user.")
        except Exception as e:
            self.log(f"Error pada Penjualan ke NPC: {e}")
        finally:
            self.is_running = False

    # =========================================================================
    # TASK 4: Auto Hunt Loop (Continuous Inventory Monitor & Auto Deposit)
    # =========================================================================
    def run_hunt_auto_deposit(self) -> None:
        self.is_running = True
        self.input.reset_abort()
        interval = self.config.get("delays", "hunt_loop_interval_sec", 1.5)
        self.log(f"Memulai Mode AUTO HUNT: Monitoring tas aktif (Interval cek: {interval}s).")
        self.log("Macro akan otomatis memindahkan item drop selain Blacklist ke Gudang saat hunt.")
        self.log("Tekan F12 atau Esc kapan saja untuk menghentikan.")

        self.wm.activate_window()
        time.sleep(0.3)

        inv = self.config.get("inventory")
        cols = inv.get("cols", 6)
        rows = inv.get("rows", 4)
        storage_cfg = self.config.get("storage_deposit", {})
        blacklist_enabled = storage_cfg.get("blacklist_enabled", True)

        skill_cfg = self.config.get("auto_skill", {})
        if skill_cfg.get("enabled", True) and skill_cfg.get("sync_with_auto_hunt", True):
            self.skills.start()

        last_logged_slot_status = {}  # slot_idx -> (status_str, bl_name, rounded_score)

        try:
            while self.is_running:
                # Pastikan game Tantra berada di foreground sebelum capture agar tidak tertutup GUI atau window lain
                if not self.wm.is_foreground():
                    self.wm.activate_window()
                    time.sleep(0.15)

                # 1. Pindai tas secara pasif (screen capture tanpa gerak mouse)
                client_img = self.screen.capture_client()

                # 0. Safety Guard: Cek apakah karakter mati (muncul popup respawn)
                death_match = self.matcher.detect_death_popup(client_img)
                if death_match:
                    cx, cy, conf = death_match
                    self.log(f"🚨 [SAFETY STOP] KARAKTER MATI! Terdeteksi popup respawn di ({cx}, {cy}) [Match: {conf:.2f}].")
                    self.log("🛑 Karakter telah mati. Menghentikan seluruh proses makro untuk keamanan akun.")
                    self.is_running = False
                    if hasattr(self, 'on_death_callback') and self.on_death_callback:
                        self.on_death_callback()
                    return

                blacklist_icons = list(self.config.storage_blacklist_dir.glob("*.png")) + list(self.config.storage_blacklist_dir.glob("*.jpg"))

                items_to_transfer = []

                for r in range(rows):
                    for c in range(cols):
                        slot_crop = self.get_inventory_slot_crop(client_img, c, r)
                        slot_idx = (r * cols) + c + 1

                        if self.matcher.is_slot_empty(slot_crop):
                            # Slot kosong: bersihkan tracker agar jika nanti ada item baru masuk slot ini, langsung di-log
                            last_logged_slot_status.pop(slot_idx, None)
                            continue

                        # Cek apakah item masuk Blacklist Gudang
                        is_blacklisted = False
                        bl_name = None
                        sc = 0.0
                        th_hunt = float(self.config.get("rules", "storage_blacklist_match_threshold",
                                         self.config.get("rules", "sell_whitelist_match_threshold", 0.50)))
                        if blacklist_enabled and blacklist_icons:
                            is_blacklisted, bl_name, sc = self.matcher.match_item_in_whitelist(
                                slot_crop, whitelist_dir=self.config.storage_blacklist_dir, threshold=th_hunt
                            )
                            if round(sc, 2) >= round(th_hunt, 2) or sc >= (th_hunt - 1e-4):
                                is_blacklisted = True

                            status_str = "🛑 BLACKLIST GUDANG (TINGGAL DI TAS)" if is_blacklisted else "📦 AKAN DIPINDAH"
                            cur_signature = (status_str, bl_name, round(sc, 2))

                            # Hanya log jika ada perubahan status/skor pada slot ini agar tidak spam loop setiap 1.5 detik
                            if last_logged_slot_status.get(slot_idx) != cur_signature:
                                last_logged_slot_status[slot_idx] = cur_signature
                                self.log(f"[Auto Hunt] Slot #{slot_idx} [B:{r+1}, K:{c+1}]: Match '{bl_name}'={sc:.2f} (Min:{th_hunt:.2f}) -> {status_str}")

                        if not is_blacklisted:
                            items_to_transfer.append((c, r, slot_idx, bl_name, sc, th_hunt))

                # 2. Jika ada item yang perlu dipindahkan ke storage
                if items_to_transfer:
                    if self.config.get("storage_popup", "auto_dismiss", False):
                        self.dismiss_storage_popup()

                    self.log(f"[Auto Hunt] Terdeteksi {len(items_to_transfer)} item untuk dipindahkan ke Gudang...")
                    self.wm.activate_window()
                    time.sleep(0.05)

                    for c, r, slot_idx, bl_name, sc, th_hunt in items_to_transfer:
                        if not self.is_running:
                            return

                        fresh_screen = self.screen.capture_client()
                        empty_storage = self.find_empty_storage_slot(fresh_screen)
                        if not empty_storage:
                            self.log("[Auto Hunt] Peringatan: Gudang (Storage 120 slot) PENUH!")
                            time.sleep(3.0)
                            break

                        target_store_c, target_store_r = empty_storage
                        dest_cx, dest_cy = self.get_storage_slot_coords(target_store_c, target_store_r)
                        slot_cx, slot_cy = self.get_inventory_slot_coords(c, r)
                        dest_idx = (target_store_r * self.config.get("storage", "cols", 10)) + target_store_c + 1

                        match_info = f" (Match '{bl_name}'={sc:.2f} < Min:{th_hunt:.2f})" if bl_name else ""
                        self.log(f"[Auto Hunt] Pindah Slot #{slot_idx}{match_info} -> Storage Kosong #{dest_idx} [{target_store_r+1},{target_store_c+1}]...")
                        self.input.drag_and_drop(slot_cx, slot_cy, dest_cx, dest_cy)
                        time.sleep(self.config.get("delays", "post_action_delay_sec", 0.15))

                # 3. Jeda interval sebelum pemindaian berikutnya
                sleep_start = time.time()
                while time.time() - sleep_start < interval:
                    if not self.is_running:
                        return
                    time.sleep(0.1)

        except InterruptedError:
            self.log("Auto Hunt dibatalkan oleh user.")
        except Exception as e:
            self.log(f"Error pada Auto Hunt: {e}")
        finally:
            self.skills.stop()
            self.is_running = False
            self.log("Mode Auto Hunt berhenti.")
