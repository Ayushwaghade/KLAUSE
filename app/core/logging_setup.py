import sys
from loguru import logger
from app.config.config import settings

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Add stdout handler with rich coloring
    logger.add(
        sys.stdout,
        level=settings.log_level,
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
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info("Logging initialized.")
