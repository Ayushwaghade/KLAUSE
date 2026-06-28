import os
import shutil
from pathlib import Path
from loguru import logger
from send2trash import send2trash
from app.tools.base import tool
from app.core.context import context

def _resolve_path(relative: str) -> Path:
    """
    Safely resolves a relative path against the active project context path.
    Raises ValueError if context is missing, or PermissionError if path traversal is detected.
    """
    cwd = context.current_project_path
    if not cwd:
        raise ValueError("No active project context. Please open a project first.")
        
    root = Path(cwd).resolve()
    # Resolve absolute destination
    resolved = (root / relative).resolve()
    
    # Path containment check (resolved path must start with root directory path)
    if not str(resolved).startswith(str(root)):
        raise PermissionError(f"Security Warning: Path traversal blocked. '{relative}' resolves outside of project root '{root}'")
        
    return resolved

@tool(
    name="fs_list_dir",
    description="Lists contents of a folder inside the active project. Argument: dir_path (str, optional - defaults to current project root '.').",
    destructive=False
)
def fs_list_dir(dir_path: str = ".") -> str:
    """
    Lists directory contents safely with containment checks.
    """
    logger.info(f"Filesystem Tool: Listing directory '{dir_path}'")
    try:
        target = _resolve_path(dir_path)
        if not target.exists():
            return f"Error: Directory '{dir_path}' does not exist."
        if not target.is_dir():
            return f"Error: '{dir_path}' is a file, not a directory."
            
        items = os.listdir(target)
        if not items:
            return f"Observation: Directory '{dir_path}' is empty."
            
        lines = [f"Observation: Contents of '{dir_path}':"]
        for item in items:
            item_path = target / item
            is_folder = item_path.is_dir()
            type_lbl = "[DIR] " if is_folder else "[FILE]"
            size_lbl = "" if is_folder else f" ({item_path.stat().st_size} bytes)"
            lines.append(f"- {type_lbl} {item}{size_lbl}")
            
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to list directory: {e}")
        return f"Error: {e}"


@tool(
    name="fs_create_dir",
    description="Creates a directory inside the active project workspace. Argument: path (str).",
    destructive=False
)
def fs_create_dir(path: str) -> str:
    """
    Creates a folder safely.
    """
    logger.info(f"Filesystem Tool: Creating directory '{path}'")
    try:
        target = _resolve_path(path)
        os.makedirs(target, exist_ok=True)
        return f"Observation: Created directory successfully at: {path}"
    except Exception as e:
        logger.error(f"Failed to create directory: {e}")
        return f"Error: {e}"


@tool(
    name="fs_copy",
    description="Copies a file or folder inside the active project workspace. Arguments: src (str), dest (str).",
    destructive=False
)
def fs_copy(src: str, dest: str) -> str:
    """
    Copies files or folders with destination overwrite verification.
    """
    logger.info(f"Filesystem Tool: Copying from '{src}' to '{dest}'")
    try:
        src_path = _resolve_path(src)
        dest_path = _resolve_path(dest)
        
        if not src_path.exists():
            return f"Error: Source path '{src}' does not exist."
            
        if dest_path.exists():
            return f"Error: Destination path '{dest}' already exists. Overwrite blocked. Please specify a different destination name."
            
        if src_path.is_dir():
            shutil.copytree(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
            
        return f"Observation: Successfully copied '{src}' to '{dest}'."
    except Exception as e:
        logger.error(f"Failed to copy file: {e}")
        return f"Error: {e}"


@tool(
    name="fs_move",
    description="Moves or renames a file or folder inside the active project workspace. Arguments: src (str), dest (str).",
    destructive=False
)
def fs_move(src: str, dest: str) -> str:
    """
    Moves files or folders with destination overwrite verification.
    """
    logger.info(f"Filesystem Tool: Moving from '{src}' to '{dest}'")
    try:
        src_path = _resolve_path(src)
        dest_path = _resolve_path(dest)
        
        if not src_path.exists():
            return f"Error: Source path '{src}' does not exist."
            
        if dest_path.exists():
            return f"Error: Destination path '{dest}' already exists. Move blocked. Please specify a different destination name."
            
        shutil.move(src_path, dest_path)
        return f"Observation: Successfully moved/renamed '{src}' to '{dest}'."
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        return f"Error: {e}"


@tool(
    name="fs_delete",
    description="Deletes a file or folder safely by moving it to the system Recycle Bin. Argument: path (str).",
    destructive=True
)
def fs_delete(path: str) -> str:
    """
    Moves file or folder to Windows Recycle Bin using send2trash.
    """
    logger.info(f"Filesystem Tool: Requesting deletion of '{path}'")
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Error: File or directory '{path}' does not exist."
            
        # Send to Recycle Bin
        send2trash(str(target))
        logger.info(f"Moved to Recycle Bin: {target}")
        return f"Observation: File/directory '{path}' successfully moved to Recycle Bin (recoverable)."
    except Exception as e:
        logger.error(f"Failed to delete '{path}': {e}")
        return f"Error: {e}"
