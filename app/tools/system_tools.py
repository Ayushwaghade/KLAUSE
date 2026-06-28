import os
from typing import Callable, Optional
from app.tools.base import tool

@tool(
    name="read_file",
    description="Reads the contents of a file from the local workspace. Argument: path (str)."
)
def read_file(path: str) -> str:
    """Reads a file and returns its content."""
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {e}"

@tool(
    name="write_file",
    description="Writes content to a file in the local workspace. Arguments: path (str), content (str)."
)
def write_file(path: str, content: str, confirm_fn: Optional[Callable[[str], bool]] = None) -> str:
    """Writes content to a file. Prompts confirmation if overwriting."""
    try:
        # Create parent directories if they don't exist
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
            
        # Check overwrite safety
        if os.path.exists(path):
            if confirm_fn:
                approved = confirm_fn(f"File '{path}' already exists. Overwrite?")
                if not approved:
                    return f"Action cancelled. File '{path}' was not overwritten."
            else:
                return f"Error: File '{path}' exists and no confirmation callback was provided."
                
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Content written to '{path}'."
    except Exception as e:
        return f"Error writing file '{path}': {e}"

@tool(
    name="web_search",
    description="Performs a web search for the query. Argument: query (str)."
)
def web_search(query: str) -> str:
    """Mock web search for Phase 1. Real implementation in Phase 6."""
    # TODO: Phase 6 - Implement real Playwright/HTTP search
    return (
        f"Mock Search Results for '{query}':\n"
        f"1. [Documentation] FAISS Indexing Guide (https://faiss.ai)\n"
        f"2. [Tutorial] How to use Gemini structured output in Python\n"
        f"3. [Git] Advanced Git commit and branch workflows"
    )
