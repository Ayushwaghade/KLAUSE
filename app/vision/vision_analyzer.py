import io
from PIL import Image
from loguru import logger
from google.genai import types

from app.config.config import settings
from app.core.client import get_gemini_client
from app.vision.vision_engine import capture_fullscreen

def analyze_image(image: Image.Image, prompt: str) -> str:
    """
    Sends a PIL image and a textual prompt to Gemini's multimodal API.
    Reuses the shared GenAI client to send the image as transient bytes.
    """
    client = get_gemini_client()
    if not client:
        return "Error: Gemini API client is offline. Please configure GEMINI_API_KEY."

    try:
        # Convert image to PNG bytes
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Create multimodal part
        image_part = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/png"
        )
        
        # Query model
        model = settings.ai.gemini_model or "gemini-2.5-flash"
        logger.info(f"Sending vision request to Gemini ({model}) with prompt: '{prompt[:50]}...'")
        
        response = client.models.generate_content(
            model=model,
            contents=[image_part, prompt]
        )
        
        if response and response.text:
            return response.text
        return "Error: Empty text response received from Gemini Vision."
        
    except Exception as e:
        logger.error(f"Gemini Vision API request failed: {e}")
        return f"Error: Gemini Vision query failed: {e}"

def describe_screen() -> str:
    """Captures fullscreen and sends to Gemini to describe visible contents."""
    try:
        img = capture_fullscreen()
        prompt = (
            "Describe what is currently visible on this desktop screen screenshot in detail. "
            "Identify the open applications, files, and general layout."
        )
        return analyze_image(img, prompt)
    except Exception as e:
        logger.error(f"describe_screen failed: {e}")
        return f"Error: Screen description failed: {e}"

def detect_errors(image: Image.Image) -> str:
    """Queries Gemini Vision to identify application error messages or warnings."""
    prompt = (
        "Analyze this screenshot of an engineering workspace. Identify any error messages, "
        "exceptions, stack traces, warning logs, or failing test reports. "
        "Summarize the error and provide suggestions on how to resolve it."
    )
    return analyze_image(image, prompt)

def analyze_layout(image: Image.Image) -> str:
    """Queries Gemini Vision to perform a visual UI/UX layout inspection."""
    prompt = (
        "Perform a visual design review on this layout. Analyze the structural organization, "
        "spacing, color combinations, styling details, element positions, and alignment. "
        "Provide specific feedback to make it look highly professional and polished."
    )
    return analyze_image(image, prompt)
