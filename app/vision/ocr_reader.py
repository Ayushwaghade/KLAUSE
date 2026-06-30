import os
import shutil
import sys
from PIL import Image
from loguru import logger
import pytesseract

from app.vision.vision_engine import preprocess_for_ocr, capture_region

# ─── Self-Healing Tesseract Configuration ──────────────────────────
def _configure_tesseract_path() -> bool:
    """
    Scans common installation paths for Tesseract binary on Windows if not on PATH,
    and configures pytesseract.cmd. Returns True if available.
    """
    # 1. Check if 'tesseract' is already available in the system PATH
    if shutil.which("tesseract"):
        logger.info("Tesseract binary is active on system PATH.")
        return True

    # 2. Check standard Windows directories
    if sys.platform == "win32":
        standard_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
        ]
        for p in standard_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                logger.info(f"Tesseract binary auto-discovered and configured at: {p}")
                return True

    logger.warning("Tesseract binary could not be found on PATH or standard directories.")
    return False

# Initialize configurations
_tesseract_configured = _configure_tesseract_path()


# ─── Core OCR APIs ──────────────────────────────────────────────────

def is_tesseract_available() -> bool:
    """Public helper to verify if Tesseract is configured and available."""
    global _tesseract_configured
    if not _tesseract_configured:
        # Re-check in case user installed it recently
        _tesseract_configured = _configure_tesseract_path()
    return _tesseract_configured

def extract_text(image: Image.Image, lang: str = "eng") -> str:
    """Extracts text content from a PIL image using Tesseract OCR."""
    if not is_tesseract_available():
        return (
            "Error: Tesseract OCR is not installed or configured on this machine. "
            "Please install Tesseract OCR (https://github.com/UB-Mannheim/tesseract/wiki) "
            "and add it to your system PATH."
        )

    try:
        # Preprocess to improve readability
        processed = preprocess_for_ocr(image)
        raw_text = pytesseract.image_to_string(processed, lang=lang)
        # Strip excessive blank lines and leading/trailing whitespace
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        return "\n".join(lines).strip()
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return f"Error: OCR text extraction failed: {e}"

def extract_text_from_region(x: int, y: int, width: int, height: int, lang: str = "eng") -> str:
    """Captures a specific screen region and extracts text from it."""
    try:
        img = capture_region(x, y, width, height)
        return extract_text(img, lang=lang)
    except Exception as e:
        logger.error(f"OCR extraction from region failed: {e}")
        return f"Error: OCR extraction from region failed: {e}"
