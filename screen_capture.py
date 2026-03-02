# ============================================================
# screen_capture.py — Single screenshot + OCR text extraction
# ============================================================

import mss
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import logging

logger = logging.getLogger(__name__)

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _configure_tesseract():
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def capture_full_screen(monitor_index: int = 1) -> Image.Image:
    """Capture the full screen as a PIL Image."""
    _configure_tesseract()
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index >= len(monitors):
            monitor_index = 1
        monitor = monitors[monitor_index]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    logger.info(f"Screenshot captured: {img.size[0]}x{img.size[1]} px")
    return img


def preprocess_image(img: Image.Image) -> Image.Image:
    """Enhance image for better OCR accuracy."""
    w, h = img.size
    scale = min(2.0, 3000 / w)
    img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def extract_text_from_image(img: Image.Image) -> str:
    """Run Tesseract OCR on the image and return extracted text."""
    _configure_tesseract()
    processed = preprocess_image(img)
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(processed, config=config, lang="eng")
    text = text.strip()
    logger.info(f"OCR extracted {len(text)} characters from screenshot.")
    return text


def capture_and_extract(monitor_index: int = 1) -> str:
    """Capture screen → OCR → return text string."""
    img = capture_full_screen(monitor_index)
    return extract_text_from_image(img)


def is_tesseract_available() -> bool:
    _configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:
        logger.warning(f"Tesseract not available: {e}")
        return False
