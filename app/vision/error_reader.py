import re
from loguru import logger
import pygetwindow as gw

from app.vision.vision_engine import capture_window, capture_region, capture_fullscreen
from app.vision.ocr_reader import extract_text

# Regex patterns for identifying terminal errors
ERROR_PATTERNS = [
    re.compile(r"(error|exception|traceback|warning|failed|failed_tests|denied|unauthorized)", re.IGNORECASE),
    re.compile(r"(exit code|exit status)", re.IGNORECASE),
    re.compile(r"fatal:", re.IGNORECASE),
    re.compile(r"line \d+ in", re.IGNORECASE)  # Stack traces
]

def read_terminal_errors(window_title: str = "terminal") -> str:
    """
    Locates a terminal window, captures it, runs OCR,
    and returns lines matching standard error patterns.
    """
    logger.info(f"Looking for terminal window: '{window_title}' to extract errors.")
    img = capture_window(window_title)
    ocr_text = extract_text(img)
    
    if "Error:" in ocr_text and "Tesseract OCR is not installed" in ocr_text:
        return ocr_text

    if not ocr_text.strip():
        return "Observation: No text could be extracted from the terminal window."

    # Filter lines by error patterns
    error_lines = []
    lines = ocr_text.splitlines()
    for line in lines:
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                error_lines.append(line)
                break
                
    if not error_lines:
        return "Observation: No obvious error patterns found in terminal text."
        
    return "Observation: Visible terminal errors found:\n" + "\n".join(error_lines)

def read_vscode_problems(window_title: str = "Visual Studio Code") -> str:
    """Captures VS Code, runs OCR, and extracts visible warning/problem lines."""
    logger.info(f"Capturing VS Code window: '{window_title}' to read problems.")
    img = capture_window(window_title)
    ocr_text = extract_text(img)
    
    if "Error:" in ocr_text and "Tesseract OCR is not installed" in ocr_text:
        return ocr_text

    if not ocr_text.strip():
        return "Observation: No text could be extracted from VS Code."

    # Filter lines indicating warnings or syntax issues
    problem_lines = []
    lines = ocr_text.splitlines()
    for line in lines:
        if any(w in line.lower() for w in ("problem", "error", "warning", "syntax", "undefined", "typeerror")):
            problem_lines.append(line)

    if not problem_lines:
        return "Observation: No obvious code errors/problems visible in VS Code window."

    return "Observation: VS Code problem lines extracted:\n" + "\n".join(problem_lines)

def get_active_window_text() -> str:
    """Captures the currently active focused window and runs full OCR on it."""
    logger.info("Capturing active focused window for OCR.")
    try:
        win = gw.getActiveWindow()
        if win and win.title and win.width > 0 and win.height > 0:
            logger.info(f"Active window: '{win.title}' at x={win.left}, y={win.top}, w={win.width}, h={win.height}")
            img = capture_region(win.left, win.top, win.width, win.height)
            return extract_text(img)
        else:
            logger.warning("No active window geometry resolved. Capturing fullscreen instead.")
            img = capture_fullscreen()
            return extract_text(img)
    except Exception as e:
        logger.error(f"Active window capture failed: {e}. Falling back to fullscreen.")
        img = capture_fullscreen()
        return extract_text(img)
