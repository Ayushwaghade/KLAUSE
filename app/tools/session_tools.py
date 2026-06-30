import os
import json
from pathlib import Path
from loguru import logger
from app.tools.base import tool
from app.core.context import context

# Helper to load/save data/session_settings.json
def _get_settings_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    settings_dir = project_root / "data"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "session_settings.json"

def _load_session_settings() -> dict:
    path = _get_settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session settings: {e}")
    return {"sessions": {}, "last_used_data_folder": None}

def _save_session_settings(settings: dict):
    path = _get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save session settings: {e}")


# ─── Tools ────────────────────────────────────────────────────────

@tool(
    name="get_session_data_folder",
    description="Returns the currently active session data folder path. Argument: none."
)
def get_session_data_folder() -> str:
    """Get active session folder."""
    folder = context.session_data_folder
    if folder:
        return f"Observation: Active session data folder is set to: '{folder}'"
    return "Observation: No active session data folder has been set for this session yet."


@tool(
    name="set_session_data_folder",
    description="Configures and creates a dedicated data folder for the current session. All downloads and output files will be stored here. Arguments: path (str)."
)
def set_session_data_folder(path: str) -> str:
    """Set active session folder."""
    # Resolve path
    abs_path = os.path.abspath(path)
    try:
        # Create folder if it doesn't exist
        os.makedirs(abs_path, exist_ok=True)
        
        # Update context
        context.session_data_folder = abs_path
        
        # Save to JSON settings
        settings = _load_session_settings()
        session_id = context.session_id
        
        settings["sessions"][session_id] = abs_path
        settings["last_used_data_folder"] = abs_path
        _save_session_settings(settings)
        
        return f"Observation: Active session data folder successfully configured and created at: '{abs_path}'."
    except Exception as e:
        logger.error(f"Failed to set session data folder: {e}")
        return f"Error: Failed to configure session data folder: {e}"


@tool(
    name="list_last_used_data_folder",
    description="Retrieves the path of the last used session data folder. Useful for prompting the user to reuse it. Argument: none."
)
def list_last_used_data_folder() -> str:
    """Get last used session folder."""
    settings = _load_session_settings()
    last_folder = settings.get("last_used_data_folder")
    if last_folder:
        return f"Observation: Last used session data folder was: '{last_folder}'."
    return "Observation: No prior session data folder found."
