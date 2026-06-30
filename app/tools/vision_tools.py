import os
from app.tools.base import tool
from app.vision import vision_engine
from app.vision import ocr_reader
from app.vision import vision_analyzer
from app.vision import error_reader

@tool(
    name="vision_capture_screen",
    description="Captures a fullscreen screenshot of the primary monitor and saves it to data/screenshots/. Arguments: monitor (int - default 1)."
)
def vision_capture_screen(monitor: int = 1) -> str:
    """Capture screen."""
    img = vision_engine.capture_fullscreen(monitor=monitor)
    filepath = vision_engine.save_screenshot(img, f"fullscreen_mon{monitor}.png")
    if filepath:
        return f"Observation: Fullscreen screenshot successfully captured and saved at: '{filepath}'"
    return "Error: Failed to save fullscreen screenshot."

@tool(
    name="vision_capture_window",
    description="Locates an active window matching a title substring (e.g., 'chrome', 'vscode') and captures a screenshot of it. Arguments: window_title (str)."
)
def vision_capture_window(window_title: str) -> str:
    """Capture window."""
    img = vision_engine.capture_window(window_title)
    safe_title = "".join([c if c.isalnum() else "_" for c in window_title])
    filepath = vision_engine.save_screenshot(img, f"window_{safe_title}.png")
    if filepath:
        return f"Observation: Window '{window_title}' successfully captured and saved at: '{filepath}'"
    return f"Error: Failed to capture window '{window_title}'."

@tool(
    name="vision_capture_region",
    description="Captures a specific bounding area of the screen. Arguments: x (int), y (int), width (int), height (int)."
)
def vision_capture_region(x: int, y: int, width: int, height: int) -> str:
    """Capture region."""
    img = vision_engine.capture_region(x, y, width, height)
    filepath = vision_engine.save_screenshot(img, f"region_{x}_{y}.png")
    if filepath:
        return f"Observation: Screen region x={x}, y={y} successfully captured and saved at: '{filepath}'"
    return "Error: Failed to capture screen region."

@tool(
    name="vision_ocr_screen",
    description="Captures the full screen and extracts all visible text content using Tesseract OCR. Argument: none."
)
def vision_ocr_screen() -> str:
    """OCR screen."""
    img = vision_engine.capture_fullscreen()
    text = ocr_reader.extract_text(img)
    return f"Observation: Extracted text from screen:\n\n{text}"

@tool(
    name="vision_ocr_region",
    description="Extracts visible text from a specific screen region using Tesseract OCR. Arguments: x (int), y (int), width (int), height (int)."
)
def vision_ocr_region(x: int, y: int, width: int, height: int) -> str:
    """OCR region."""
    text = ocr_reader.extract_text_from_region(x, y, width, height)
    return f"Observation: Extracted text from region x={x}, y={y}:\n\n{text}"

@tool(
    name="vision_analyze",
    description="Captures the fullscreen and sends it to Gemini multimodal vision API along with a custom prompt query. Arguments: prompt (str)."
)
def vision_analyze(prompt: str) -> str:
    """Analyze screen via Gemini."""
    img = vision_engine.capture_fullscreen()
    res = vision_analyzer.analyze_image(img, prompt)
    return f"Observation: Gemini Vision analysis output:\n\n{res}"

@tool(
    name="vision_describe_screen",
    description="Captures the fullscreen and uses Gemini Vision to provide a detailed description of all visible content. Argument: none."
)
def vision_describe_screen() -> str:
    """Describe screen."""
    res = vision_analyzer.describe_screen()
    return f"Observation: Screen description:\n\n{res}"

@tool(
    name="vision_detect_errors",
    description="Captures the screen and uses Gemini Vision to detect and diagnose visible warnings, logs, terminal exceptions, or compiler errors. Argument: none."
)
def vision_detect_errors() -> str:
    """Detect errors via Gemini."""
    img = vision_engine.capture_fullscreen()
    res = vision_analyzer.detect_errors(img)
    return f"Observation: Error detection observations:\n\n{res}"

@tool(
    name="vision_read_terminal",
    description="Captures a terminal window matching the title, extracts text via OCR, and filters for lines containing error tags. Arguments: window_title (str - default 'terminal')."
)
def vision_read_terminal(window_title: str = "terminal") -> str:
    """Read terminal errors."""
    return error_reader.read_terminal_errors(window_title)

@tool(
    name="vision_read_vscode_problems",
    description="Captures the VS Code editor window, runs OCR, and extracts any visible code problems or compiler issues. Argument: none."
)
def vision_read_vscode_problems() -> str:
    """Read VS Code compiler issues."""
    return error_reader.read_vscode_problems()
