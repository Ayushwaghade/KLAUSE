import pygetwindow as gw
from loguru import logger
from app.tools.base import tool

# Standard imports for Windows GUI focusing
try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

@tool(
    name="list_open_windows",
    description="Lists the titles of all currently visible open application windows on the desktop (caps at 30 items).",
    destructive=False
)
def list_open_windows() -> str:
    """
    Retrieves a list of visible, titled Windows desktop applications.
    """
    logger.info("Window Tool: Querying visible application windows.")
    try:
        all_windows = gw.getAllWindows()
        # Filter: Must have titled name, be visible, and have a non-zero size
        visible = [
            w.title.strip() for w in all_windows
            if w.title and w.title.strip() and getattr(w, "visible", True) and getattr(w, "width", 0) > 0
        ]
        
        # De-duplicate while preserving order
        seen = set()
        deduped = []
        for t in visible:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
                
        if not deduped:
            return "Observation: No open, visible windows found."
            
        # Cap at 30 windows
        limit = 30
        lines = [f"Observation: Open visible window titles (showing top {min(limit, len(deduped))}):"]
        for t in deduped[:limit]:
            lines.append(f"- {t}")
            
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to query windows: {e}")
        return f"Error: Failed to list visible windows: {e}"


@tool(
    name="focus_window",
    description="Brings a visible application window to the foreground by matching its title. Argument: title (str).",
    destructive=False
)
def focus_window(title: str) -> str:
    """
    Restores and focuses a window, using pywin32 API calls to bypass OS focus-stealing protections.
    """
    logger.info(f"Window Tool: Request to focus window matching: '{title}'")
    try:
        # Search matching windows
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return f"Observation: No window found matching title substring: '{title}'"
            
        win = windows[0]
        hwnd = getattr(win, "_hWnd", None)
        
        if HAS_WIN32 and hwnd is not None:
            try:
                # Restore window if minimized
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                # Set foreground focus
                win32gui.SetForegroundWindow(hwnd)
                return f"Observation: Successfully focused window: '{win.title}'"
            except Exception as win32_err:
                logger.warning(f"win32gui focus failed: {win32_err}. Falling back to default pygetwindow activate().")
                
        # Default pygetwindow activation fallback
        try:
            win.activate()
            return f"Observation: Activated window: '{win.title}' (Note: Windows may only flash the taskbar if blocked by OS focus policies)."
        except Exception as act_err:
            return f"Error: Failed to activate window '{win.title}': {act_err}"
            
    except Exception as e:
        logger.error(f"Failed to focus window: {e}")
        return f"Error: Focus operation failed: {e}"
