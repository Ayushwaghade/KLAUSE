import os
import subprocess
from loguru import logger
from app.tools.base import tool
from app.config.config import settings

@tool(
    name="open_application",
    description="Launches a registered desktop application from the allowed list. Argument: app_key (str).",
    destructive=False
)
def open_application(app_key: str) -> str:
    """
    Launches an application if it is configured on the whitelist inside config.yaml.
    """
    logger.info(f"App Tool: Request to launch application key '{app_key}'")
    
    # Retrieve allowlist mapping from configuration
    allowed_apps = settings.allowed_applications or {}
    
    if app_key not in allowed_apps:
        logger.warning(f"Blocked attempt to launch unlisted application: {app_key}")
        allowed_list = ", ".join(allowed_apps.keys()) if allowed_apps else "none"
        return f"Error: Application '{app_key}' is not in the allowed applications list. Registered apps: [{allowed_list}]."
        
    target = allowed_apps[app_key]
    logger.info(f"Launching application key '{app_key}' targeting: {target}")
    
    try:
        # Use os.startfile on Windows for standard document/app launch
        if hasattr(os, "startfile"):
            try:
                os.startfile(target)
                return f"Observation: Successfully launched '{app_key}'."
            except Exception as start_err:
                logger.debug(f"os.startfile failed: {start_err}. Falling back to subprocess.Popen.")
                
        # Subprocess fallback (crucial for console CLI apps or custom PATH lookups)
        subprocess.Popen(target, shell=True)
        return f"Observation: Successfully launched '{app_key}' via subprocess shell."
    except Exception as e:
        logger.error(f"Failed to launch application '{app_key}': {e}")
        return f"Error: Failed to launch application '{app_key}': {e}"
