"""
app/voice/live_session.py

Gemini Live Voice Narration Engine for KLAUSE.

Architecture:
1. Stripped of all tools and planning logic: The Live model acts solely as KLAUSE's voice narrator.
2. No mic audio is sent to Live: User vocal input is transcribed cleanly via Whisper/PTT into text commands for the Brain.
3. Brain emits events (started, step, done, error) into a unified priority speech queue.
4. Preemption: 'done' or 'error' events immediately preempt stale steps and purge the audio buffer.
5. Fallback: If Live WebSocket is offline, speech automatically routes to SAPI/local TTS without dropping.
"""

from __future__ import annotations
import asyncio
import os
import re
import time
import threading
from typing import Optional, Tuple
from loguru import logger
import sounddevice as sd
from google import genai
from google.genai import types

from app.config.config import settings
from app.core.context import context
from app.core.orb_state_broadcaster import orb_broadcaster
from app.voice.session_rotator import LiveSessionRotator


class LiveVoiceSessionManager:
    """
    Manages the persistent Gemini Live WebSocket session strictly as a Voice Narrator.
    Does not accept microphone audio and does not perform tool dispatching.
    Receives text lines from KLAUSE Brain events and speaks them via Puck's voice.
    """

    def __init__(self):
        self.model_name: str = getattr(settings.voice.live, "model", "gemini-3.8-live")
        self.voice_name: str = getattr(settings.voice.live, "voice_name", "Puck")
        self.sample_rate_out: int = getattr(settings.voice.live, "sample_rate_out", 24000)
        self.barge_in: bool = getattr(settings.voice.live, "barge_in", True)

        # Thread-safe speech queue for narrator events: (event_type, text)
        self._speech_queue: Optional[asyncio.Queue[Tuple[str, str]]] = None

        # Hardware audio output buffer & lock (24kHz PCM int16)
        self._audio_out_buffer = bytearray()
        self._audio_out_lock = threading.Lock()
        self._speaker_stream: Optional[sd.RawOutputStream] = None

        # Background asyncio worker thread
        self._worker_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        self._current_session = None

        # Session metrics and persona manager
        self.rotator = LiveSessionRotator()
        self._last_spoke_timestamp: float = 0.0

    @property
    def is_connected(self) -> bool:
        """Returns True if the Live WebSocket session is active and ready to vocalize."""
        return self._current_session is not None and not self._stop_event.is_set()

    def start(self) -> None:
        """Starts the Live Voice narrator background thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning("Live Voice Narrator is already running.")
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="KlauseLiveVoiceNarratorThread"
        )
        self._worker_thread.start()
        logger.info("🎙️ [Live Voice] Narrator worker thread started.")

    def stop(self) -> None:
        """Stops the Live Voice narrator session and releases audio hardware."""
        self._stop_event.set()
        self._purge_audio_playback()
        self._purge_speech_queue_steps()

        if self._speaker_stream:
            try:
                self._speaker_stream.stop()
                self._speaker_stream.close()
            except Exception as e:
                logger.debug(f"Live Voice: Error stopping speaker stream: {e}")
            self._speaker_stream = None

        logger.info("🎙️ [Live Voice] Narrator stopped.")

    def _purge_audio_playback(self) -> None:
        """Flushes the hardware output buffer immediately."""
        with self._audio_out_lock:
            self._audio_out_buffer.clear()
        self.rotator.set_speaking(False)
        self._last_spoke_timestamp = time.monotonic()

    def _purge_speech_queue_steps(self) -> None:
        """Drains any pending intermediate 'step' updates from the speech queue."""
        if not self._speech_queue:
            return
        temp_items = []
        while not self._speech_queue.empty():
            try:
                item = self._speech_queue.get_nowait()
                # Keep 'done' and 'error' items, drop 'step' items
                if item[0] in ("done", "error"):
                    temp_items.append(item)
            except Exception:
                break
        for item in temp_items:
            try:
                self._speech_queue.put_nowait(item)
            except Exception:
                pass

    def say(self, text: str, event_type: str = "done") -> None:
        """
        Enqueue a line to be spoken by Gemini Live.
        event_type can be 'started', 'step', 'done', or 'error'.
        Preempts stale step updates when 'done' or 'error' is passed.
        Falls back to local SAPI TTS if Live session is not connected.
        """
        if not text or not text.strip():
            return

        # Strip markdown syntax and task metadata
        clean = re.sub(r'[\*\#\`\-\_]', '', text)
        clean = re.sub(r'(?i)[\[\(]?\btask\s+complete[\]\)]?[\.\!\?]?\s*', '', clean).strip()
        if not clean or not re.search(r'\w', clean):
            return

        # Fallback to local SAPI TTS if the Live session is not connected
        if not self.is_connected or not self._loop or self._stop_event.is_set():
            logger.debug(f"[Live Voice Offline] Routing speech to SAPI fallback: '{clean[:60]}...'")
            from app.voice.tts import tts_engine
            tts_engine.speak(clean)
            return

        # If 'done' or 'error', preempt any pending step narrations
        if event_type in ("done", "error"):
            self._purge_speech_queue_steps()

        try:
            self._loop.call_soon_threadsafe(
                self._speech_queue.put_nowait,
                (event_type, clean)
            )
        except Exception as e:
            logger.warning(f"[Live Voice] Failed to enqueue speech: {e}. Falling back to SAPI.")
            from app.voice.tts import tts_engine
            tts_engine.speak(clean)

    def _init_audio_hardware(self) -> bool:
        """Initializes the sounddevice output speaker stream (24kHz int16)."""
        try:
            def _speaker_callback(outdata, frames, time_info, status):
                if status:
                    logger.debug(f"[Live Voice] Speaker output status: {status}")
                needed_bytes = frames * 2  # 2 bytes per int16 sample
                with self._audio_out_lock:
                    available = len(self._audio_out_buffer)
                    if available >= needed_bytes:
                        outdata[:] = bytes(self._audio_out_buffer[:needed_bytes])
                        del self._audio_out_buffer[:needed_bytes]
                        self.rotator.set_speaking(True)
                    elif available > 0:
                        outdata[:available] = bytes(self._audio_out_buffer[:available])
                        outdata[available:] = b"\x00" * (needed_bytes - available)
                        self._audio_out_buffer.clear()
                        self.rotator.set_speaking(True)
                    else:
                        outdata[:] = b"\x00" * needed_bytes
                        if self.rotator.is_model_speaking:
                            self._last_spoke_timestamp = time.monotonic()
                        self.rotator.set_speaking(False)

            self._speaker_stream = sd.RawOutputStream(
                samplerate=self.sample_rate_out,
                channels=1,
                dtype="int16",
                blocksize=1024,
                callback=_speaker_callback
            )
            self._speaker_stream.start()
            logger.info("🎙️ [Live Voice] Speaker output stream initialized (24kHz).")
            return True
        except Exception as e:
            logger.error(f"[Live Voice] Speaker hardware init error: {e}")
            return False

    def _run_loop(self) -> None:
        """Entry point for the background worker thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_session_loop())
        except Exception as e:
            logger.error(f"[Live Voice] Worker loop encountered unexpected error: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for t in pending:
                    t.cancel()
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception:
                pass

    async def _main_session_loop(self) -> None:
        """Main connection and reconnection lifecycle loop."""
        api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("Live Voice: GEMINI_API_KEY not found. Live Voice disabled.")
            return

        if not self._init_audio_hardware():
            return

        client = genai.Client(api_key=api_key)
        self._speech_queue = asyncio.Queue(maxsize=50)

        logger.info("🎙️ [Live Voice] Connecting to Gemini Live API as Narrator...")
        orb_broadcaster.set_state("idle")

        while not self._stop_event.is_set():
            try:
                system_instruction = self.rotator.build_system_instruction()

                # Narrator-only config: No tools, no mic stream
                config = types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name
                            )
                        )
                    ),
                    system_instruction=types.Content(
                        parts=[types.Part.from_text(text=system_instruction)]
                    ),
                    tools=None
                )

                logger.info(f"🎙️ [Live Voice] Establishing session with model '{self.model_name}'...")

                async with client.aio.live.connect(model=self.model_name, config=config) as session:
                    logger.info("✅ [Live Voice] Narrator session connected.")
                    self._current_session = session
                    self.rotator.reset_metrics()

                    # Run speech consumer and server message receiver concurrently
                    consumer_task = asyncio.create_task(self._speech_consumer_loop(session))
                    receive_task = asyncio.create_task(self._receive_messages_loop(session))

                    done, pending = await asyncio.wait(
                        [consumer_task, receive_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                self._current_session = None

                if self._stop_event.is_set():
                    break

                logger.info("🎙️ [Live Voice] Connection ended. Reconnecting in 2 seconds...")
                await asyncio.sleep(2.0)

            except Exception as e:
                self._current_session = None
                logger.error(f"[Live Voice] Session disconnected: {e}")
                orb_broadcaster.set_state("error")
                if self._stop_event.is_set():
                    break
                logger.info("🎙️ [Live Voice] Reconnecting in 3 seconds...")
                await asyncio.sleep(3.0)

        self.stop()

    async def _speech_consumer_loop(self, session) -> None:
        """Pulls lines from the speech queue and sends them to Gemini Live to be spoken."""
        try:
            while not self._stop_event.is_set():
                try:
                    event_type, text = await asyncio.wait_for(self._speech_queue.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue

                # If this is a step update and newer items exist, discard stale step
                if event_type == "step" and not self._speech_queue.empty():
                    continue

                if event_type in ("done", "error"):
                    self._purge_audio_playback()

                prompt = f"Say this in a natural, friendly tone: {text}"
                try:
                    await session.send(input=prompt, end_of_turn=True)
                except Exception as e:
                    logger.warning(f"[Live Voice] Failed to send line to Live: {e}. Falling back to SAPI.")
                    from app.voice.tts import tts_engine
                    tts_engine.speak(text)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[Live Voice] Speech consumer error: {e}")

    async def _receive_messages_loop(self, session) -> None:
        """Receives streaming audio chunks from Gemini Live and buffers them for playback."""
        try:
            while not self._stop_event.is_set():
                ws = getattr(session, "_ws", None)
                if ws and getattr(ws, "closed", False):
                    logger.warning("🎙️ [Live Voice] Underlying WebSocket closed by server.")
                    break

                async for message in session.receive():
                    if self._stop_event.is_set():
                        break

                    # Update token usage metrics
                    if message.usage_metadata:
                        token_count = getattr(message.usage_metadata, "total_token_count", None)
                        if token_count:
                            self.rotator.update_usage(token_count)

                    if message.server_content:
                        sc = message.server_content
                        # Extract incoming model audio parts
                        if sc.model_turn and sc.model_turn.parts:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    orb_broadcaster.set_state("speaking")
                                    with self._audio_out_lock:
                                        self._audio_out_buffer.extend(part.inline_data.data)

                        # Turn complete
                        if getattr(sc, "turn_complete", False):
                            active_sid = context.session_id or "default_session"
                            orb_broadcaster.set_state("listening")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[Live Voice] Audio receive error: {e}")


# Global shared instance
live_voice_session = LiveVoiceSessionManager()
