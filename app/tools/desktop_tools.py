"""
app/tools/desktop_tools.py
OS-level GUI automation tools — mouse, keyboard, and screen interaction.
Uses pyautogui as the automation backend.
Batched macro architecture minimizes LLM round-trips and confirmation fatigue.
"""

import json
import time
from typing import Any, Dict, List, Union
import pyautogui
from loguru import logger
from app.tools.base import tool

# Safety: FAILSAFE = True means slamming mouse into top-left (0,0) aborts execution
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

KEY_ALIASES = {
    "win": "win",
    "windows": "win",
    "cmd": "win",
    "super": "win",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "esc": "escape",
    "del": "delete",
    "ret": "enter",
    "return": "enter",
}


def _normalize_key(k: str) -> str:
    k_clean = k.strip().lower()
    return KEY_ALIASES.get(k_clean, k_clean)


def is_macro_enabled() -> bool:
    """Returns True if the desktop macro system is enabled in configuration."""
    try:
        from app.config.config import settings
        if hasattr(settings, "desktop_macro"):
            return bool(settings.desktop_macro.enabled)
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────
#  BATCHED MACRO TOOL (Primary Mutating Tool)
# ──────────────────────────────────────────────

@tool(
    name="desktop_macro",
    group="desktop",
    description=(
        "Executes a batched sequence of OS-level desktop actions in a single atomic call. "
        "Minimizes round trips and requires only a single user confirmation. "
        "Argument: steps (list of dicts or JSON string). Supported action types: "
        "'click' (x, y, button='left'|'right', clicks=1|2), "
        "'move' (x, y, duration=0.2), "
        "'drag' (start_x, start_y, end_x, end_y, duration=0.5, button='left'), "
        "'scroll' (clicks: int pos=up neg=down, x=None, y=None), "
        "'type' (text: str, interval=0.02), "
        "'hotkey' (keys: str e.g. 'win+r', 'ctrl+s', 'alt+f4'), "
        "'keypress' (key: str e.g. 'enter', 'tab', 'escape', presses=1), "
        "'wait' (seconds: float e.g. 0.5)."
    ),
    destructive=True
)
def desktop_macro(steps: Union[List[Dict[str, Any]], str]) -> str:
    """Execute a list of desktop GUI automation steps sequentially."""
    if not is_macro_enabled():
        logger.info("desktop_macro called but the macro system is currently disabled.")
        return "Observation: The desktop macro system is currently turned off in configuration."

    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception as e:
            logger.error(f"Failed to parse desktop_macro steps as JSON: {e}")
            return f"Error: 'steps' must be a list of action dictionaries or valid JSON string: {e}"

    if not isinstance(steps, list):
        return f"Error: 'steps' must be a list of action dictionaries, got {type(steps).__name__}."

    if not steps:
        return "Observation: desktop_macro called with empty steps list. No actions performed."

    logger.info(f"Desktop Macro: Executing sequence of {len(steps)} steps.")
    executed = []

    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return f"Error at step {idx}: Each step must be a dict. Executed so far: {executed}"

        action = step.get("action", "").lower().strip()
        try:
            if action == "click":
                x = int(step["x"])
                y = int(step["y"])
                button = step.get("button", "left").lower()
                clicks = int(step.get("clicks", 1))
                if button not in ("left", "right", "middle"):
                    button = "left"
                pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                c_label = "double-click" if clicks == 2 else "click"
                executed.append(f"Step {idx}: {c_label} ({button}) at ({x}, {y})")

            elif action == "move":
                x = int(step["x"])
                y = int(step["y"])
                duration = float(step.get("duration", 0.2))
                pyautogui.moveTo(x=x, y=y, duration=duration)
                executed.append(f"Step {idx}: move cursor to ({x}, {y})")

            elif action == "drag":
                start_x = int(step["start_x"])
                start_y = int(step["start_y"])
                end_x = int(step["end_x"])
                end_y = int(step["end_y"])
                duration = float(step.get("duration", 0.5))
                button = step.get("button", "left").lower()
                pyautogui.moveTo(start_x, start_y, duration=0.1)
                pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
                executed.append(f"Step {idx}: drag from ({start_x}, {start_y}) to ({end_x}, {end_y})")

            elif action == "scroll":
                clicks = int(step["clicks"])
                x = step.get("x")
                y = step.get("y")
                if x is not None and y is not None:
                    pyautogui.moveTo(int(x), int(y), duration=0.1)
                pyautogui.scroll(clicks)
                direction = "up" if clicks > 0 else "down"
                executed.append(f"Step {idx}: scroll {abs(clicks)} {direction}")

            elif action == "type":
                text = str(step["text"])
                interval = float(step.get("interval", 0.02))
                try:
                    pyautogui.typewrite(text, interval=interval)
                except Exception:
                    # Non-ASCII / Unicode fallback via clipboard paste
                    import pyperclip
                    prev = pyperclip.paste()
                    pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.1)
                    pyperclip.copy(prev)
                preview = text[:40] + ("..." if len(text) > 40 else "")
                executed.append(f"Step {idx}: typed '{preview}' ({len(text)} chars)")

            elif action == "hotkey":
                keys_str = str(step["keys"])
                keys = [_normalize_key(k) for k in keys_str.split("+")]
                pyautogui.hotkey(*keys)
                executed.append(f"Step {idx}: hotkey {' + '.join(keys)}")

            elif action == "keypress":
                key = _normalize_key(str(step["key"]))
                presses = int(step.get("presses", 1))
                pyautogui.press(key, presses=presses)
                executed.append(f"Step {idx}: press '{key}' x{presses}")

            elif action in ("wait", "sleep"):
                secs = float(step.get("seconds", step.get("duration", 0.5)))
                time.sleep(secs)
                executed.append(f"Step {idx}: wait {secs}s")

            else:
                return (
                    f"Error at step {idx}: Unknown action '{action}'. "
                    f"Valid actions: click, move, drag, scroll, type, hotkey, keypress, wait. "
                    f"Executed before failure: {executed}"
                )

        except Exception as step_err:
            logger.error(f"desktop_macro failed at step {idx} ({action}): {step_err}")
            return (
                f"Error: Step {idx} ({action}) failed with exception: {step_err}. "
                f"Completed steps before failure: {executed}"
            )

    return f"Observation: Successfully executed {len(executed)} desktop macro steps:\n" + "\n".join(f"- {s}" for s in executed)


# ──────────────────────────────────────────────
#  READ-ONLY / QUERY TOOLS (Non-Destructive)
# ──────────────────────────────────────────────

@tool(
    name="get_cursor_position",
    group="desktop",
    description="Returns the current mouse cursor position as (x, y) pixel coordinates.",
    destructive=False
)
def get_cursor_position() -> str:
    """Get current cursor position."""
    pos = pyautogui.position()
    return f"Observation: Cursor is at ({pos.x}, {pos.y})."


@tool(
    name="get_screen_size",
    group="desktop",
    description="Returns the primary monitor resolution as (width, height) in pixels.",
    destructive=False
)
def get_screen_size() -> str:
    """Get screen dimensions."""
    size = pyautogui.size()
    return f"Observation: Screen size is {size.width} x {size.height} pixels."


@tool(
    name="get_pixel_color",
    group="desktop",
    description="Returns the RGB color of the pixel at the given coordinates. Arguments: x (int), y (int).",
    destructive=False
)
def get_pixel_color(x: int, y: int) -> str:
    """Get pixel color at coordinates."""
    try:
        img = pyautogui.screenshot(region=(int(x), int(y), 1, 1))
        r, g, b = img.getpixel((0, 0))
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        return f"Observation: Pixel at ({x}, {y}) is RGB({r}, {g}, {b}) / {hex_color}."
    except Exception as e:
        logger.error(f"get_pixel_color failed: {e}")
        return f"Error: Failed to read pixel color: {e}"


@tool(
    name="locate_image_on_screen",
    group="desktop",
    description=(
        "Searches the screen for a sub-image template. "
        "Returns center (x, y) coordinates if found, or indicates not found. "
        "Arguments: image_path (str - path to template image), confidence (float - 0.0 to 1.0, default 0.8)."
    ),
    destructive=False
)
def locate_image_on_screen(image_path: str, confidence: float = 0.8) -> str:
    """Find image on screen via template matching."""
    logger.info(f"Desktop: locate_image_on_screen '{image_path}', confidence={confidence}")
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location is None:
            return f"Observation: Image '{image_path}' was NOT found on screen."
        center = pyautogui.center(location)
        return (
            f"Observation: Image found at center ({center.x}, {center.y}), "
            f"bounding box: left={location.left}, top={location.top}, "
            f"width={location.width}, height={location.height}."
        )
    except Exception as e:
        logger.error(f"locate_image_on_screen failed: {e}")
        return f"Error: Image locate failed: {e}"


@tool(
    name="wait_for_image",
    group="desktop",
    description=(
        "Waits until a template image appears on screen, polling every 0.5s. "
        "Returns center (x, y) when found, or times out. "
        "Arguments: image_path (str), timeout (float - seconds, default 10.0), "
        "confidence (float - 0.0 to 1.0, default 0.8)."
    ),
    destructive=False
)
def wait_for_image(image_path: str, timeout: float = 10.0, confidence: float = 0.8) -> str:
    """Wait for image to appear on screen."""
    logger.info(f"Desktop: wait_for_image '{image_path}', timeout={timeout}s")
    try:
        start = time.time()
        while time.time() - start < timeout:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is not None:
                center = pyautogui.center(location)
                elapsed = round(time.time() - start, 2)
                return f"Observation: Image found after {elapsed}s at center ({center.x}, {center.y})."
            time.sleep(0.5)
        return f"Observation: Image '{image_path}' did NOT appear within {timeout}s timeout."
    except Exception as e:
        logger.error(f"wait_for_image failed: {e}")
        return f"Error: Wait for image failed: {e}"
