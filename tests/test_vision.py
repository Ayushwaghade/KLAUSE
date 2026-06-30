import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
from app.vision import vision_engine
from app.vision import ocr_reader
from app.vision import vision_analyzer
from app.vision import error_reader
from app.tools.vision_tools import vision_capture_screen, vision_capture_window, vision_read_terminal


@pytest.fixture
def mock_pil_image():
    """Returns a simple synthetic PIL image for testing."""
    return Image.new("RGB", (100, 100), color="white")


@patch("mss.mss")
def test_screen_capture(mock_mss_class, mock_pil_image):
    # Mock mss screen grab
    mock_sct = MagicMock()
    mock_sct.monitors = [{}, {"top": 0, "left": 0, "width": 800, "height": 600}]
    
    mock_grab = MagicMock()
    mock_grab.size = (800, 600)
    mock_grab.bgra = b"\x00" * (800 * 600 * 4) # 4 bytes per pixel
    mock_sct.grab.return_value = mock_grab
    mock_mss_class.return_value.__enter__.return_value = mock_sct

    img = vision_engine.capture_fullscreen(monitor=1)
    assert img is not None
    assert img.size == (800, 600)
    
    reg_img = vision_engine.capture_region(0, 0, 100, 100)
    assert reg_img is not None
    assert reg_img.size == (800, 600) # mss grab mock size


@patch("app.vision.ocr_reader.is_tesseract_available")
@patch("pytesseract.image_to_string")
def test_ocr_extraction(mock_to_string, mock_available, mock_pil_image):
    # Case A: Tesseract not available
    mock_available.return_value = False
    res = ocr_reader.extract_text(mock_pil_image)
    assert "Tesseract OCR is not installed" in res

    # Case B: Tesseract available, returning text
    mock_available.return_value = True
    mock_to_string.return_value = "Line 1\n\nLine 2\n"
    res2 = ocr_reader.extract_text(mock_pil_image)
    assert res2 == "Line 1\nLine 2"


@patch("app.vision.ocr_reader.shutil.which")
@patch("app.vision.ocr_reader.sys")
def test_tesseract_availability_checks(mock_sys, mock_which):
    mock_sys.platform = "win32"
    mock_which.return_value = None # Not on PATH
    
    # Verify falls back to search Windows paths (should return True/False based on existence, but doesn't crash)
    res = ocr_reader._configure_tesseract_path()
    assert isinstance(res, bool)


@patch("pygetwindow.getWindowsWithTitle")
@patch("app.vision.vision_engine.capture_fullscreen")
def test_capture_window_fallback(mock_capture_full, mock_get_win, mock_pil_image):
    # Window not found case -> should fall back to capture_fullscreen
    mock_get_win.return_value = []
    mock_capture_full.return_value = mock_pil_image

    img = vision_engine.capture_window("nonexistent_app")
    assert img == mock_pil_image
    mock_capture_full.assert_called_once()


@patch("app.vision.error_reader.capture_window")
@patch("app.vision.error_reader.extract_text")
def test_error_pattern_filtering(mock_ocr, mock_capture, mock_pil_image):
    mock_capture.return_value = mock_pil_image
    
    # Synthetic OCR output containing error triggers and normal text
    mock_ocr.return_value = (
        "Starting test runner...\n"
        "ValueError: invalid literal for int() with base 10: 'abc'\n"
        "Tests completed successfully.\n"
        "exit status 1\n"
    )
    
    res = error_reader.read_terminal_errors("terminal")
    assert "ValueError" in res
    assert "exit status 1" in res
    assert "Starting test runner" not in res # Should filter out non-errors


@patch("app.vision.vision_analyzer.get_gemini_client")
def test_gemini_vision_analyzer(mock_get_client, mock_pil_image):
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.text = "This screen shows VS Code open with a python test file."
    mock_client.models.generate_content.return_value = mock_res
    mock_get_client.return_value = mock_client

    with patch("app.config.config.settings.ai.gemini_model", "gemini-3.1-flash-lite-preview"):
        res = vision_analyzer.analyze_image(mock_pil_image, "Describe the screen")
        assert res == "This screen shows VS Code open with a python test file."
        mock_client.models.generate_content.assert_called_once()
