"""
Screen capture module.
Supports high-performance capture with mss, PIL.ImageGrab, and offline mock screenshots.
"""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


class ScreenCapture:
    def __init__(self, window_manager, config):
        self.wm = window_manager
        self.config = config
        self._sct = mss.mss() if HAS_MSS else None
        self._mock_image: Optional[Image.Image] = None

    def set_mock_image(self, image_or_path) -> None:
        """Sets a static image for testing and calibration without the game running."""
        if isinstance(image_or_path, (str, Path)):
            self._mock_image = Image.open(image_or_path).convert("RGB")
        elif isinstance(image_or_path, Image.Image):
            self._mock_image = image_or_path.convert("RGB")
        else:
            self._mock_image = None

    def clear_mock_image(self) -> None:
        self._mock_image = None

    def capture_client(self) -> Image.Image:
        """
        Captures the game client area (1024x768).
        Returns a PIL Image.
        """
        if self._mock_image is not None:
            return self._mock_image

        self.wm.update_bounds()
        if not self.wm.client_rect:
            # Fallback to primary screen
            return self._capture_region(0, 0, 1024, 768)

        left, top, width, height = self.wm.client_rect
        return self._capture_region(left, top, width, height)

    def _capture_region(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """Captures a specific screen region."""
        if self._sct is not None:
            monitor = {"top": top, "left": left, "width": width, "height": height}
            sct_img = self._sct.grab(monitor)
            # Convert mss BGRA image to PIL RGB Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
        else:
            from PIL import ImageGrab
            bbox = (left, top, left + width, top + height)
            return ImageGrab.grab(bbox=bbox)

    def crop_region(self, full_img: Image.Image, rel_rect: Tuple[int, int, int, int]) -> Image.Image:
        """
        Crops a region from the 1024x768 client image.
        rel_rect = (x, y, width, height)
        """
        x, y, w, h = rel_rect
        return full_img.crop((x, y, x + w, y + h))
