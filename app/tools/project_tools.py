import os
from loguru import logger
from app.tools.base import tool
from app.core.context import context
from app.memory.memory_manager import get_memory_manager

@tool(
    name="open_project",
    group="core",
    description="Opens and activates a project workspace. Argument: name_or_path (str) - can be an absolute path or a registered project name in memory.",
    destructive=False
)
def open_project(name_or_path: str) -> str:
    """
    Sets KLAUSE's active project path, auto-registering disk paths in MongoDB.
    """
    logger.info(f"Project Tool: Request to open project '{name_or_path}'")
    
    # Try resolving name_or_path as a direct disk path
    if os.path.isdir(name_or_path):
        abs_path = os.path.abspath(name_or_path)
        context.current_project_path = abs_path
        
        # Save project in database for future name queries
        try:
            mgr = get_memory_manager()
            proj_name = os.path.basename(abs_path) or "workspace"
            mgr.save_project(name=proj_name, path=abs_path, description="Auto-registered directory workspace")
            logger.info(f"Registered project '{proj_name}' with path '{abs_path}' in MongoDB.")
        except Exception as e:
            logger.warning(f"Could not auto-register project path in database: {e}")
            
        return f"Observation: Active project workspace set to path: {abs_path}"
        
    # Try matching against registered projects in database
    try:
        mgr = get_memory_manager()
        proj_doc = mgr.db.projects.find_one({"name": name_or_path})
        if proj_doc:
            path = proj_doc.get("path")
            if os.path.isdir(path):
                context.current_project_path = path
                return f"Observation: Active project workspace set to path: {path} (retrieved from project '{name_or_path}')"
            else:
                return f"Error: Project '{name_or_path}' is registered in database with path '{path}', but that directory does not exist on disk."
    except Exception as e:
        logger.error(f"Failed to query project database: {e}")
        
    return f"Error: '{name_or_path}' is not a valid directory and does not match any registered project names in database."
