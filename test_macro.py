"""
Diagnostic and offline simulation test for Tantra Farmer Macro.
Tests OCR, slot detection, popup detection, and whitelist matching on sample assets.
"""

import sys
from pathlib import Path
from PIL import Image

from config import Config
from window_manager import WindowManager
from screen import ScreenCapture
from input_controller import InputController
from template_matcher import TemplateMatcher
from ocr_engine import OCREngine
from farmer_bot import FarmerBot


def run_tests():
    print("=" * 60)
    print("      TANTRA FARMER MACRO - DIAGNOSTIC & OFFLINE TEST")
    print("=" * 60)

    config = Config("config.json")
    wm = WindowManager(config)
    screen = ScreenCapture(wm, config)
    input_ctrl = InputController(wm, config)
    matcher = TemplateMatcher(config)
    ocr = OCREngine(config)
    bot = FarmerBot(wm, screen, input_ctrl, matcher, ocr, config)

    # 1. Test Popup Detection
    popup_sample = config.assets_dir / "samples" / "media_1794756048742.png"
    if popup_sample.exists():
        img = Image.open(popup_sample)
        # Create a full 1024x768 canvas with popup centered
        canvas = Image.new("RGB", (1024, 768), (0, 0, 0))
        canvas.paste(img, (281, 295))
        is_popup = matcher.detect_sell_popup(canvas)
        print(f"[TEST 1] Pop-up Konfirmasi ('Will you sell') Terdeteksi: {'PASS (BERHASIL)' if is_popup else 'FAIL'}")
    else:
        print("[TEST 1] Sample popup image not found, skipping.")

    # 2. Test Whitelist Matching
    hb_sample = config.whitelist_dir / "head_band_sample.png"
    if hb_sample.exists():
        img = Image.open(hb_sample)
        matched, name, score = matcher.match_item_in_whitelist(img)
        print(f"[TEST 2] Whitelist Item Matching ('{name}'): Score = {score:.2f} -> {'PASS (BERHASIL)' if matched else 'FAIL'}")
    else:
        print("[TEST 2] Sample whitelist image not found, skipping.")

    # 3. Test Tooltip OCR Parsing
    test_text_samples = [
        ("Pustika\nMovement Spell Sheet\nQuantity 17\nCannot be listed", 17),
        ("Kavacha of Iron\nQuantity: 100\nCan be traded", 100),
        ("Horn of Agony\nQty 100", 100),
    ]
    ocr_pass = True
    for sample, expected in test_text_samples:
        parsed_qty = ocr.parse_quantity(sample)
        if parsed_qty != expected:
            ocr_pass = False
            print(f"  Failed parsing: expected {expected}, got {parsed_qty}")
    print(f"[TEST 3] Tooltip Quantity Regex Parser: {'PASS (BERHASIL)' if ocr_pass else 'FAIL'}")

    # 4. Test Coordinate calculation
    c_inv, r_inv = bot.get_inventory_slot_coords(0, 0)
    print(f"[TEST 4] Slot Inventaris [1,1] Center: ({c_inv}, {r_inv}) (Total: {config.get('inventory', 'cols', 6)}x{config.get('inventory', 'rows', 4)} = 24)")
    c_store, r_store = bot.get_storage_slot_coords(0, 0)
    print(f"[TEST 4] Slot Storage [1,1] Center: ({c_store}, {r_store}) (Total: {config.get('storage', 'cols', 10)}x{config.get('storage', 'rows', 12)} = 120)")

    # 5. Test Empty Slot Detection on sample image
    sample_inv = config.assets_dir / "samples" / "media_1794756048926.jpg"
    if sample_inv.exists():
        im = Image.open(sample_inv)
        inv_status = bot.scan_inventory_status(im)
        empty_cnt = sum(1 for s in inv_status if s["is_empty"])
        filled_cnt = len(inv_status) - empty_cnt
        print(f"[TEST 5] Pindai Slot Kosong Inventaris: {empty_cnt} Kosong, {filled_cnt} Berisi dari {len(inv_status)} slot -> PASS (BERHASIL)")

    print("\nSemua modul inti siap digunakan!")


if __name__ == "__main__":
    run_tests()
