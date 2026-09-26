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

_shared_nvidia_client = None

def get_nvidia_client() -> Optional[any]:
    """Helper to return a shared OpenAI client configured for NVIDIA integrate endpoints."""
    global _shared_nvidia_client
    if _shared_nvidia_client is None:
        api_key = settings.nvidia_api_key or os.environ.get("NVIDIA_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                _shared_nvidia_client = OpenAI(
                    base_url=settings.ai.nvidia_base_url,
                    api_key=api_key
                )
                logger.info("Shared NVIDIA OpenAI Client successfully created.")
            except Exception as e:
                logger.error(f"Failed to create shared NVIDIA client: {e}")
    return _shared_nvidia_client

