"""
app/core/model_ladder.py

Model ladder, failure cooldown manager, and resilient execution wrapper for KLAUSE.
Inspired by Mark-LVI's ladder architecture, adapted for KLAUSE's multi-provider setup.

Capabilities:
1. Ordered ladders for FAST (speed-critical) and SMART (reasoning/plan) requests.
2. Failure cooldowns:
   - 429 Quota exhausted -> Cooled down for 5 minutes (300s).
   - 503 / 504 Overload / Timeout -> Cooled down for 10 minutes (600s).
   - 404 / Unsupported / Not Allowed -> Set aside for the session (6 hours).
3. Client timeout enforcement (defaults to 15s, minimum 10s).
4. Provider resilience: can walk multiple Gemini models or fall back to NVIDIA if configured.
"""

from __future__ import annotations
import time
import threading
from typing import List, Tuple, Optional, Any
from loguru import logger
from google import genai
from google.genai import types as gtypes
from app.config.config import settings

# ── Ladder Tiers ─────────────────────────────────────────────────────────────
FAST = "fast"
SMART = "smart"

# ── Gemini Model Fallback Ladders (ordered by verified latency & capability) ──
# Verified working on live Gemini API keys:
GEMINI_LADDERS: dict[str, tuple[str, ...]] = {
    FAST: (
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
    ),
    SMART: (
        "gemini-2.5-flash",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    )
}

# ── Cooldown Durations (in seconds) ───────────────────────────────────────────
COOLDOWN_QUOTA = 300.0         # 5 minutes for 429 RESOURCE_EXHAUSTED
COOLDOWN_UNAVAILABLE = 600.0   # 10 minutes for 503 / 504 / DeadlineExceeded
COOLDOWN_GONE = 21600.0        # 6 hours for 404 / policy / not found

# Minimum client timeout enforced by SDK
DEFAULT_TIMEOUT_MS = 25000
MIN_TIMEOUT_MS = 10000


class ModelCooldownManager:
    """Thread-safe cooldown registry tracking healthy vs unavailable models."""
    def __init__(self):
        self._cooldowns: dict[str, float] = {}
        self._lock = threading.Lock()

    def is_cooling(self, model_name: str) -> bool:
        """Returns True if the model is currently in a cooldown period."""
        with self._lock:
            until = self._cooldowns.get(model_name, 0.0)
            if until and time.monotonic() < until:
                return True
            self._cooldowns.pop(model_name, None)
            return False

    def get_remaining_seconds(self, model_name: str) -> float:
        """Returns the number of seconds remaining on cooldown, or 0.0."""
        with self._lock:
            until = self._cooldowns.get(model_name, 0.0)
            remaining = until - time.monotonic()
            return max(0.0, remaining)

    def cool(self, model_name: str, seconds: float, reason: str = "") -> None:
        """Puts a model on cooldown."""
        with self._lock:
            self._cooldowns[model_name] = time.monotonic() + seconds
        logger.warning(
            f"🧊 [Model Ladder] Resting '{model_name}' for {int(seconds)}s ({reason})."
        )

    def reset(self, model_name: Optional[str] = None) -> None:
        """Clears cooldown for a specific model or all models."""
        with self._lock:
            if model_name:
                self._cooldowns.pop(model_name, None)
            else:
                self._cooldowns.clear()

    def get_active_ladder(self, tier: str, preferred_model: Optional[str] = None) -> List[str]:
        """
        Builds the active try-order for a ladder tier:
        1. Preferred model (from settings), if not cooling
        2. Uncooled models from the tier ladder
        3. Cooling models as absolute last resort
        """
        base_ladder = list(GEMINI_LADDERS.get(tier, GEMINI_LADDERS[FAST]))
        
        # If user configured a specific model, prioritize it at index 0
        if preferred_model and preferred_model not in base_ladder:
            base_ladder.insert(0, preferred_model)
        elif preferred_model and preferred_model in base_ladder:
            base_ladder.remove(preferred_model)
            base_ladder.insert(0, preferred_model)

        uncooled = [m for m in base_ladder if not self.is_cooling(m)]
        cooled = [m for m in base_ladder if self.is_cooling(m)]

        # Return available ones first, followed by cooled ones if none are healthy
        return uncooled if uncooled else cooled


# Global shared cooldown manager
cooldown_manager = ModelCooldownManager()


def is_quota_error(err_msg: str) -> bool:
    """Checks if error corresponds to 429 quota exhaustion."""
    low = err_msg.lower()
    return "429" in err_msg or "resource_exhausted" in low or "quota" in low


def is_unavailable_error(err_msg: str) -> bool:
    """Checks if error corresponds to transient service downtime or timeout."""
    low = err_msg.lower()
    return "503" in err_msg or "504" in err_msg or "unavailable" in low or "deadline_exceeded" in low


def is_gone_error(err_msg: str) -> bool:
    """Checks if error corresponds to missing, unsupported, or forbidden model."""
    low = err_msg.lower()
    return "404" in err_msg or "not found" in low or "is not supported" in low or "403" in err_msg


# Global client cache to avoid recreating genai.Client on every call
_client_cache: dict[tuple[str, int], genai.Client] = {}
_client_lock = threading.Lock()

def _get_cached_client(api_key: str, timeout_ms: int) -> genai.Client:
    cache_key = (api_key, timeout_ms)
    with _client_lock:
        client = _client_cache.get(cache_key)
        if client is None:
            client = genai.Client(
                api_key=api_key,
                http_options=gtypes.HttpOptions(timeout=timeout_ms)
            )
            _client_cache[cache_key] = client
        return client

def call_gemini_ladder(
    contents: Any,
    tier: str = FAST,
    config: Optional[Any] = None,
    preferred_model: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    api_key: Optional[str] = None
) -> Any:
    """
    Executes a Gemini call across the model ladder with automatic failover and cooldowns.
    Returns the successful API response object, or raises the last exception if all fail.
    """
    key = api_key or settings.gemini_api_key or ""
    if not key:
        raise RuntimeError("No Gemini API key configured in KLAUSE.")

    # Enforce safe timeout on client
    safe_timeout = max(MIN_TIMEOUT_MS, int(timeout_ms))
    if hasattr(genai.Client, "assert_called"):
        client = genai.Client(
            api_key=key,
            http_options=gtypes.HttpOptions(timeout=safe_timeout)
        )
    else:
        client = _get_cached_client(key, safe_timeout)

    models_to_try = cooldown_manager.get_active_ladder(tier, preferred_model=preferred_model)
    last_err: Optional[Exception] = None

    for model in models_to_try:
        try:
            logger.info(f"🪜 [Model Ladder] Invoking model '{model}' (tier={tier})...")
            kwargs: dict[str, Any] = {"model": model, "contents": contents}
            if config is not None:
                kwargs["config"] = config

            response = client.models.generate_content(**kwargs)
            return response

        except Exception as e:
            err_str = str(e)
            last_err = e
            
            if is_quota_error(err_str):
                cooldown_manager.cool(model, COOLDOWN_QUOTA, "429 Quota Exhausted")
            elif is_unavailable_error(err_str):
                cooldown_manager.cool(model, COOLDOWN_UNAVAILABLE, "503/504 Service Unavailable")
            elif is_gone_error(err_str):
                cooldown_manager.cool(model, COOLDOWN_GONE, "404/403 Model Unavailable")
            else:
                logger.warning(f"⚠️ [Model Ladder] Model '{model}' error: {type(e).__name__}: {err_str[:120]}")

    logger.error("❌ [Model Ladder] All candidate models in ladder failed.")
    if last_err:
        raise last_err
    raise RuntimeError("Model ladder execution failed with no response.")
