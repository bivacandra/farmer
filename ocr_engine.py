"""
OCR Engine module for Tantra tooltip reading.
Reads item names and 'Quantity XX' from tooltips using Tesseract OCR or EasyOCR.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False


class OCREngine:
    def __init__(self, config):
        self.config = config
        self._easyocr_reader = None
        self._init_ocr()

    def _init_ocr(self) -> None:
        """Configures Tesseract binary path on Windows if needed."""
        if HAS_PYTESSERACT and sys.platform == "win32":
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            for p in common_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def _preprocess_tooltip(self, img: Image.Image) -> Image.Image:
        """
        Preprocesses game tooltip image:
        - Grayscale conversion
        - 2x upscale with bicubic interpolation
        - Thresholding white text on dark background
        - Invert to crisp black text on white background
        """
        w, h = img.size
        # 2x upscale for clearer OCR on small bitmap fonts
        upscaled = img.resize((w * 2, h * 2), Image.Resampling.BICUBIC)
        gray = upscaled.convert("L")

        # White text in Tantra tooltips has brightness >= 135 (antialiased font edges)
        threshold = 135
        table = [0 if i < threshold else 255 for i in range(256)]
        bw = gray.point(table, "1")

        # Invert to black text on white background
        inverted = ImageOps.invert(bw.convert("L"))
        return inverted

    def read_tooltip_text(self, tooltip_img: Image.Image) -> str:
        """Performs OCR on a tooltip crop."""
        prep_img = self._preprocess_tooltip(tooltip_img)

        # 1. Try pytesseract with multi-PSM fallback (psm 6 uniform block, psm 11 sparse text)
        if HAS_PYTESSERACT:
            best_text = ""
            for psm in [6, 11]:
                try:
                    text = pytesseract.image_to_string(prep_img, config=f"--psm {psm}")
                    if text.strip():
                        if re.search(r"(?:[Qq0O]uant|Qty)", text, re.IGNORECASE):
                            return text.strip()
                        if not best_text:
                            best_text = text.strip()
                except Exception:
                    pass

            if best_text:
                return best_text

        # 2. Try EasyOCR fallback
        if HAS_EASYOCR:
            try:
                if self._easyocr_reader is None:
                    self._easyocr_reader = easyocr.Reader(["en"], gpu=False)
                import numpy as np
                results = self._easyocr_reader.readtext(np.array(prep_img))
                lines = [res[1] for res in results]
                return "\n".join(lines)
            except Exception:
                pass

        return ""

    def parse_quantity(self, text: str) -> Optional[int]:
        """
        Extracts quantity integer from text like:
        'Quantity 100', 'Quantity: 100', 'Qty 100', 'Ouantity 100', 'Quantity IOO'.
        """
        # Primary match: handles Quantity, Quantlty, Ouantity, Qty followed by numbers/letter digits
        match = re.search(r'(?:[Qq0O]uant[a-z1lI]{1,5}|Qty)[^\d\n\w]*\s*([0-9OlI]+)', text, re.IGNORECASE)
        if match:
            raw_num = match.group(1).upper().replace('O', '0').replace('I', '1').replace('L', '1')
            try:
                return int(raw_num)
            except ValueError:
                pass

        # Secondary match: handles line breaks or extra spaces between Quantity and number
        match_nl = re.search(r'(?:[Qq0O]uant[a-z1lI]{1,5}|Qty)[\s\S]{1,20}?([0-9OlI]{1,3})', text, re.IGNORECASE)
        if match_nl:
            raw_num = match_nl.group(1).upper().replace('O', '0').replace('I', '1').replace('L', '1')
            try:
                return int(raw_num)
            except ValueError:
                pass

        return None

    def parse_item_name(self, text: str) -> Optional[str]:
        """
        Extracts the first non-empty line as the item name.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[0]
        return None

    def read_slot_info(self, tooltip_img: Image.Image) -> Tuple[Optional[str], Optional[int]]:
        """
        Reads tooltip and returns (item_name, quantity).
        """
        raw_text = self.read_tooltip_text(tooltip_img)
        item_name = self.parse_item_name(raw_text)
        quantity = self.parse_quantity(raw_text)
        return item_name, quantity
