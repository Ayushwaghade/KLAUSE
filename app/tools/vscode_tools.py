import subprocess
import os
from loguru import logger
from app.tools.base import tool

def check_vscode_available() -> bool:
    """
    Utility check to see if the 'code' command is available in the environment's PATH.
    """
    try:
        # Run code --version with shell=True to handle PATH lookup correctly on Windows
        result = subprocess.run("code --version", shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

@tool(
    name="vscode_open_project",
    group="terminal",
    description="Opens VS Code in the specified directory. Argument: path (str).",
    destructive=False
)
def vscode_open_project(path: str) -> str:
    """
    Opens VS Code in the specified directory.
    """
    logger.info(f"VSCode Tool: Opening project at path: {path}")
    
    # Resolve to absolute path
    abs_path = os.path.abspath(path)
    
    if not check_vscode_available():
        logger.warning("VS Code 'code' binary is not found in PATH.")
        return "Warning: The VS Code 'code' binary was not found in your PATH. Please ensure VS Code is installed and in your environment variables."
        
    try:
        # Run code CLI command
        subprocess.Popen(f'code "{abs_path}"', shell=True)
        return f"Observation: VS Code has been launched for folder: {abs_path}"
    except Exception as e:
        logger.error(f"Failed to launch VS Code: {e}")
        return f"Observation: Failed to launch VS Code: {e}"


@tool(
    name="vscode_open_file",
    group="terminal",
    description="Opens a file in the active VS Code editor. Argument: file_path (str). Uses 'code -g' format.",
    destructive=False
)
def vscode_open_file(file_path: str) -> str:
    """
    Opens a file in VS Code using the 'code -g' command.
    """
    logger.info(f"VSCode Tool: Opening file: {file_path}")
    
    # Resolve to absolute path
    abs_path = os.path.abspath(file_path)
    
    if not check_vscode_available():
        logger.warning("VS Code 'code' binary is not found in PATH.")
        return "Warning: The VS Code 'code' binary was not found in your PATH. Please ensure VS Code is installed and in your environment variables."

    try:
        # code -g opens file at path (with optional line/column numbers)
        subprocess.Popen(f'code -g "{abs_path}"', shell=True)
        return f"Observation: File opened in VS Code: {abs_path}"
    except Exception as e:
        logger.error(f"Failed to open file in VS Code: {e}")
        return f"Observation: Failed to open file in VS Code: {e}"
