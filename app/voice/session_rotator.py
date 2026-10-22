"""
app/voice/session_rotator.py

Rolling Context & Session Rotation Manager for KLAUSE Gemini Live Voice Sessions.
Monitors token accumulation against the ~65K Live API context window, generates
fast background summaries via the Model Ladder (FAST tier), and hot-swaps sessions
seamlessly with zero audible user disruption.
"""

from __future__ import annotations
import time
from collections import deque
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config.config import settings
from app.core.model_ladder import call_gemini_ladder, FAST
from app.memory.memory_manager import get_memory_manager


class LiveSessionRotator:
    """
    Manages session lifecycle, token accounting, and rolling-context rotation
    for the Gemini Live API voice interface.
    """

    def __init__(self, session_id: str = "live_voice"):
        self.session_id = session_id
        self.user_name = settings.klause.user_name or "Ayush"
        self.agent_name = settings.klause.name or "KLAUSE"
        
        # Token and turn thresholds from config
        live_cfg = getattr(settings.voice, "live", None)
        self.token_limit = getattr(live_cfg, "rotation_token_limit", 45000)
        self.turn_limit = getattr(live_cfg, "rotation_turn_limit", 40)
        
        # Live session metrics
        self.total_tokens: int = 0
        self.turn_count: int = 0
        self.last_audio_timestamp: float = time.monotonic()
        self.is_task_running: bool = False
        self.is_model_speaking: bool = False
        
        # Buffer of recent dialogue turns (role, text, timestamp)
        self.turn_buffer: deque[Dict[str, Any]] = deque(maxlen=20)
        
        # Accumulated session summary across rotations
        self.current_summary: str = ""
        self.rotation_count: int = 0

    def update_usage(self, token_count: Optional[int] = None) -> None:
        """Updates the session's token consumption counter."""
        if token_count and token_count > self.total_tokens:
            self.total_tokens = token_count
            logger.debug(f"🎙️ [Live Rotator] Token usage updated: {self.total_tokens}/{self.token_limit}")

    @property
    def active_session_id(self) -> str:
        from app.core.context import context
        return context.session_id or self.session_id or "default_session"

    def record_turn(self, role: str, text: str) -> None:
        """Records a user or assistant turn into local buffer and MongoDB."""
        if not text or not text.strip():
            return
        clean_text = text.strip()
        self.turn_buffer.append({
            "role": role,
            "text": clean_text,
            "time": time.time()
        })
        if role == "assistant":
            self.turn_count += 1
            logger.info(f"🎙️ [Live Rotator] Turn {self.turn_count} recorded. Total tokens ~{self.total_tokens}")

        # Persist to MongoDB memory manager for cross-session continuity
        try:
            get_memory_manager().save_conversation(
                session_id=self.active_session_id,
                role=role,
                content=clean_text
            )
        except Exception as e:
            logger.debug(f"[Live Rotator] Failed to save conversation turn to MongoDB: {e}")

    def record_audio_activity(self) -> None:
        """Updates the timestamp of the most recent audio activity."""
        self.last_audio_timestamp = time.monotonic()

    def set_task_running(self, running: bool) -> None:
        """Marks whether an agentic Brain task is actively running."""
        self.is_task_running = running

    def set_speaking(self, speaking: bool) -> None:
        """Marks whether the model is actively playing audio output."""
        self.is_model_speaking = speaking

    def should_rotate(self) -> bool:
        """
        Determines if session should rotate to a fresh window.
        Conditions:
        1. Token count >= limit OR turn count >= limit
        2. No active agentic task running
        3. Model is not currently speaking
        4. Silence window >= 2.0 seconds (natural conversation pause)
        """
        limit_reached = (
            self.total_tokens >= self.token_limit or
            self.turn_count >= self.turn_limit
        )
        if not limit_reached:
            return False

        if self.is_task_running or self.is_model_speaking:
            return False

        silence_duration = time.monotonic() - self.last_audio_timestamp
        if silence_duration < 2.0:
            return False

        logger.info(
            f"🔄 [Live Rotator] Rotation condition met: "
            f"Tokens={self.total_tokens}/{self.token_limit}, Turns={self.turn_count}/{self.turn_limit}, "
            f"Silence={silence_duration:.1f}s."
        )
        return True

    def generate_summary(self) -> str:
        """
        Compresses preceding conversation turns into a high-density summary
        using a fast model from the KLAUSE Model Ladder (gemini-flash-lite).
        """
        if not self.turn_buffer:
            return self.current_summary

        turns_text = "\n".join(
            f"{'Ayush' if t['role'] == 'user' else 'KLAUSE'}: {t['text']}"
            for t in self.turn_buffer
        )

        prompt = (
            f"You are the memory manager for KLAUSE, personal AI assistant to {self.user_name}.\n"
            f"Summarize the following recent voice conversation concisely in 3-5 bullet points.\n"
            f"Preserve:\n"
            f"1. Core user intents and tasks executed.\n"
            f"2. Current active project or files mentioned.\n"
            f"3. Key decisions, preferences, or unresolved questions.\n\n"
            f"Previous Summary (if any):\n{self.current_summary or 'None'}\n\n"
            f"Recent Conversation:\n{turns_text}\n\n"
            f"Return only the bullet points summary with no preamble."
        )

        try:
            logger.info("🧠 [Live Rotator] Generating session summary via Model Ladder FAST tier...")
            resp = call_gemini_ladder(contents=prompt, tier=FAST)
            summary_text = resp.text.strip()
            self.current_summary = summary_text
            self.rotation_count += 1
            logger.info(f"✅ [Live Rotator] Summary generated ({len(summary_text)} chars, rotation #{self.rotation_count}).")
            return summary_text
        except Exception as e:
            logger.warning(f"⚠️ [Live Rotator] Summary generation failed: {e}. Preserving last summary.")
            return self.current_summary

    def build_system_instruction(self, summary: Optional[str] = None) -> str:
        """
        Constructs the narrator-only system instruction for Gemini Live API.
        The Live model acts solely as KLAUSE's voice box without planning or tool execution.
        """
        return (
            f"You are {self.agent_name}'s voice, speaking to {self.user_name}. "
            "You never plan, decide, or solve tasks. You receive lines to say. "
            "Speak each one naturally and briefly, in a friendly, charismatic tone. "
            "Never add information, never claim a task succeeded or failed unless the line says so."
        )

    def reset_metrics(self) -> None:
        """Resets token counters and turn count after a successful rotation."""
        self.total_tokens = 0
        self.turn_count = 0
        self.last_audio_timestamp = time.monotonic()
        logger.info("🔄 [Live Rotator] Session counters reset for fresh Live window.")
