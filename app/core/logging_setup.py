import sys
from loguru import logger
from app.config.config import settings

def setup_logging(cli_mode: bool = False):
    # Remove default handler
    logger.remove()
    
    import os
    api_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
    
    def patcher(record):
        if api_key and len(str(api_key)) > 5 and str(api_key) in record["message"]:
            record["message"] = record["message"].replace(str(api_key), "[REDACTED_API_KEY]")
            
    logger.configure(patcher=patcher)
    
    # Ensure Windows console streams support UTF-8 without charmap errors
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    # If in interactive CLI mode, only log WARNING or higher to stderr
    # to avoid polluting the chat conversation.
    stdout_level = "WARNING" if cli_mode else settings.log_level
    
    # Add stdout handler with rich coloring
    logger.add(
        sys.stdout,
        level=stdout_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    # Add file handler with rotation and compression
    log_file = f"{settings.paths.logs}/klause.log"
    logger.add(
        log_file,
        level=settings.log_level,
        rotation="10 MB",
        retention="1 week",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info(f"Logging initialized. CLI Mode: {cli_mode}")
