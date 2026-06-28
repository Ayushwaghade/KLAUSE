import pyperclip
from loguru import logger
from app.tools.base import tool

@tool(
    name="clipboard_get_text",
    description="Retrieves the current text content from the system clipboard.",
    destructive=False
)
def clipboard_get_text() -> str:
    """
    Reads the system clipboard, handling empty/non-text content gracefully.
    """
    logger.info("Clipboard Tool: Reading text content.")
    try:
        content = pyperclip.paste()
        if not content:
            return "Observation: Clipboard is empty or contains non-text content."
        return f"Observation: Clipboard Content:\n{content}"
    except Exception as e:
        logger.error(f"Failed to read clipboard: {e}")
        return "Observation: Failed to read clipboard (clipboard may contain non-text content)."


@tool(
    name="clipboard_set_text",
    description="Writes text content to the system clipboard, overwriting existing clipboard content. Argument: text (str).",
    destructive=True
)
def clipboard_set_text(text: str) -> str:
    """
    Writes text to the system clipboard.
    """
    logger.info(f"Clipboard Tool: Writing text content of length: {len(text)}")
    try:
        pyperclip.copy(text)
        return "Observation: Clipboard content successfully updated."
    except Exception as e:
        logger.error(f"Failed to write to clipboard: {e}")
        return f"Error: Failed to write to clipboard: {e}"
