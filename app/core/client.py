import os
from typing import Optional
from google import genai
from loguru import logger
from app.config.config import settings

# Shared google-genai Client instance to prevent multiple client creations
_shared_client = None

def get_gemini_client() -> Optional[genai.Client]:
    """Helper to return a single shared Gemini Client instance, breaking circular imports."""
    global _shared_client
    if _shared_client is None:
        api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                _shared_client = genai.Client(api_key=api_key)
                logger.info("Shared Gemini Client successfully created.")
            except Exception as e:
                logger.error(f"Failed to create shared Gemini Client: {e}")
    return _shared_client
