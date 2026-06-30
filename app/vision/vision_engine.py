import os
import base64
from io import BytesIO
from pathlib import Path
from loguru import logger
from PIL import Image, ImageEnhance
import mss
import pygetwindow as gw

def _get_screenshots_dir() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    screenshots_dir = project_root / "data" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir

def capture_fullscreen(monitor: int = 1) -> Image.Image:
    """Captures the full screen of the specified monitor using mss."""
    logger.info(f"Capturing fullscreen (monitor: {monitor})")
    with mss.mss() as sct:
        # Check monitor count
        monitors = sct.monitors
        if monitor >= len(monitors):
            # Fall back to primary screen (index 1)
            logger.warning(f"Monitor {monitor} not found. Falling back to primary monitor.")
            monitor = 1
        
        sct_img = sct.grab(monitors[monitor])
        # Convert raw mss image to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """Captures a specific bounding region of the screen."""
    logger.info(f"Capturing screen region (x={x}, y={y}, w={width}, h={height})")
    with mss.mss() as sct:
        region = {"top": y, "left": x, "width": width, "height": height}
        sct_img = sct.grab(region)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

def capture_window(window_title: str) -> Image.Image:
    """
    Locates a window by title substring match using pygetwindow and captures it.
    Falls back to fullscreen capture if window title matching is unsupported or fails.
    """
    logger.info(f"Attempting to capture window title matching: '{window_title}'")
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            # Let's search case-insensitively
            all_windows = gw.getAllWindows()
            windows = [w for w in all_windows if window_title.lower() in w.title.lower()]
            
        if windows:
            win = windows[0]
            # Ensure window is not minimized or offscreen
            if win.isMinimized:
                logger.info(f"Window '{win.title}' is minimized. Attempting to restore...")
                win.restore()
            
            # Get geometry coordinates
            x, y, w, h = win.left, win.top, win.width, win.height
            if w <= 0 or h <= 0:
                logger.warning(f"Invalid window dimensions: {w}x{h}. Falling back to fullscreen.")
                return capture_fullscreen()
            
            logger.info(f"Found window '{win.title}' at x={x}, y={y}, w={w}, h={h}")
            return capture_region(x, y, w, h)
        else:
            logger.warning(f"Window matching '{window_title}' not found. Falling back to fullscreen capture.")
            return capture_fullscreen()
    except Exception as e:
        logger.error(f"Window capture exception: {e}. Falling back to fullscreen capture.")
        return capture_fullscreen()

def save_screenshot(image: Image.Image, filename: str = "vision_capture.png") -> str:
    """Saves PIL Image to data/screenshots/ and returns the absolute path."""
    dest_dir = _get_screenshots_dir()
    filepath = dest_dir / filename
    try:
        image.save(filepath, format="PNG")
        logger.info(f"Saved screenshot: {filepath}")
        return str(filepath.resolve())
    except Exception as e:
        logger.error(f"Failed to save screenshot to {filepath}: {e}")
        return ""

def image_to_base64(image: Image.Image) -> str:
    """Converts a PIL Image to a base64 encoded PNG string."""
    buffered = BytesIO()
    # Save as PNG
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    Converts image to grayscale, enhances contrast, and downscales
    to max 1920x1080 to improve processing speed and quality.
    """
    # 1. Downscale to max 1920x1080 if larger, preserving aspect ratio
    image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
    
    # 2. Convert to grayscale
    gray_image = image.convert("L")
    
    # 3. Enhance contrast
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(2.0)
    
    return enhanced_image
