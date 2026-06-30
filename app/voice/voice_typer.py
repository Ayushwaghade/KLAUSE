import os
import threading
import tempfile
import wave
import time
from pathlib import Path
import numpy as np
import sounddevice as sd
import pyperclip
import pyautogui
import keyboard
from faster_whisper import WhisperModel
from loguru import logger

from app.config.config import settings

SAMPLE_RATE = 16000
OVERLAP_SECONDS = 0.3
OVERLAP_SAMPLES = int(SAMPLE_RATE * OVERLAP_SECONDS)  # 300ms overlap

class LiveVoiceTyper:
    def __init__(self):
        # Fetch configurations from settings
        voice_cfg = getattr(settings, "voice", None)
        typer_cfg = getattr(voice_cfg, "live_typer", None) if voice_cfg else None

        self.hotkey = getattr(typer_cfg, "hotkey", "ctrl+shift+v") if typer_cfg else "ctrl+shift+v"
        self.chunk_seconds = getattr(typer_cfg, "chunk_seconds", 2) if typer_cfg else 2
        self.max_duration = getattr(typer_cfg, "max_duration_seconds", 300) if typer_cfg else 300

        self.is_recording = False
        self._buffer = []
        self._previous_tail = np.array([], dtype=np.float32)
        self._last_transcribed_text = ""
        self._lock = threading.Lock()
        self._paste_lock = threading.Lock()
        self._timer_thread = None

        # Eager model loading at boot
        self.model = None
        try:
            logger.info("LiveVoiceTyper: Eagerly loading Whisper model 'base.en'...")
            self.model = WhisperModel("base.en", device="cpu", compute_type="int8")
            logger.info("LiveVoiceTyper: Whisper model 'base.en' loaded successfully.")
        except Exception as e:
            logger.warning(f"LiveVoiceTyper: Failed to load model 'base.en': {e}. Attempting fallback to 'tiny.en'...")
            try:
                self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
                logger.info("LiveVoiceTyper: Whisper model 'tiny.en' loaded successfully.")
            except Exception as fe:
                logger.error(f"LiveVoiceTyper: Failed to load fallback Whisper model: {fe}. Live dictation is offline.")

    def start(self):
        """Registers global hotkey binding."""
        if not self.model:
            logger.warning("LiveVoiceTyper: Cannot start voice dictation because Whisper model is offline.")
            return
        try:
            keyboard.add_hotkey(self.hotkey, self._toggle)
            logger.info(f"LiveVoiceTyper: Global dictation hotkey bound to: '{self.hotkey}'")
        except Exception as e:
            logger.error(f"LiveVoiceTyper: Failed to bind hotkey '{self.hotkey}': {e}")

    def stop(self):
        """Unregisters hotkey bindings and stops recording if active."""
        self._stop_recording()
        try:
            keyboard.remove_hotkey(self.hotkey)
        except Exception:
            pass

    def _toggle(self):
        """Toggles recording start/stop."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Starts mic capture and transcription loops."""
        self.is_recording = True
        self._buffer = []
        self._previous_tail = np.array([], dtype=np.float32)
        self._last_transcribed_text = ""
        
        # Audio cue: Beep start
        print("\a", end="", flush=True)
        logger.info("Live dictation started...")

        # Start timer for auto-stop safety guard
        self._timer_thread = threading.Timer(self.max_duration, self._stop_recording)
        self._timer_thread.daemon = True
        self._timer_thread.start()

        # Thread 1: continuous mic capture
        self._capture_thread = threading.Thread(target=self._capture, daemon=True)
        self._capture_thread.start()

        # Thread 2: chunk transcription loop
        self._transcribe_thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._transcribe_thread.start()

    def _stop_recording(self):
        """Stops active recording loops."""
        if not self.is_recording:
            return
        self.is_recording = False
        
        # Cancel safety timer
        if self._timer_thread:
            self._timer_thread.cancel()
            self._timer_thread = None
            
        # Audio cue: Beep stop
        print("\a", end="", flush=True)
        logger.info("Live dictation stopped.")

    def _capture(self):
        """Continuously reads mic streams into the audio list buffer."""
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
                while self.is_recording:
                    # Read chunks of size 1024
                    chunk, overflow = stream.read(1024)
                    if overflow:
                        logger.debug("InputStream overflowed.")
                    with self._lock:
                        self._buffer.append(chunk)
        except Exception as e:
            logger.error(f"InputStream capture failure: {e}")
            self._stop_recording()

    def _transcribe_loop(self):
        """Periodically drains audio samples from buffer and transcribes them."""
        while self.is_recording:
            time.sleep(self.chunk_seconds)
            self._drain_and_transcribe()

        # Final drain after stop to capture remaining words
        time.sleep(0.3)
        self._drain_and_transcribe()

    def _drain_and_transcribe(self):
        """Extracts buffered chunks, prepends tail overlaps, and triggers Whisper."""
        with self._lock:
            if not self._buffer:
                return
            audio_chunks = self._buffer.copy()
            self._buffer.clear()

        # Concatenate buffered audio float arrays
        audio = np.concatenate(audio_chunks)
        # Flatten structure if multidimensional
        if len(audio.shape) > 1:
            audio = audio.flatten()

        # Prepend tail overlap of previous chunk
        if len(self._previous_tail) > 0:
            audio = np.concatenate([self._previous_tail, audio])

        # Save tail of current chunk for the next iteration
        if len(audio) >= OVERLAP_SAMPLES:
            self._previous_tail = audio[-OVERLAP_SAMPLES:]
        else:
            self._previous_tail = audio.copy()

        # Skip if chunk is too silent (volume filter)
        if len(audio) == 0 or np.abs(audio).mean() < 0.005:
            return

        # Transcribe audio chunk
        text = self._transcribe(audio).strip()
        if text:
            # Strip duplicate words overlapping with the tail of the previous text
            cleaned_text = self._strip_duplicate_prefix(self._last_transcribed_text, text)
            if cleaned_text:
                logger.info(f"Live dictation chunk: {cleaned_text}")
                self._last_transcribed_text = text
                self._paste(cleaned_text + " ")

    def _strip_duplicate_prefix(self, prev_text: str, new_text: str) -> str:
        """Compares word lists at chunk boundaries to eliminate duplicates."""
        if not prev_text or not new_text:
            return new_text
            
        prev_words = prev_text.lower().split()
        new_words = new_text.lower().split()
        actual_new_words = new_text.split()
        
        # Check overlapping word sequences up to 4 words
        max_overlap = min(len(prev_words), len(new_words), 4)
        for overlap in range(max_overlap, 0, -1):
            if prev_words[-overlap:] == new_words[:overlap]:
                return " ".join(actual_new_words[overlap:])
        return new_text

    def _transcribe(self, audio: np.ndarray) -> str:
        """Saves float array to temp WAV, transcribes with VAD filter, and cleans up."""
        tmp = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name

            # Write WAV file format
            with wave.open(tmp, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                # Convert float32 [-1.0, 1.0] to int16
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())

            # Perform Whisper transcription with VAD filter to avoid silent hallucinations
            segments, _ = self.model.transcribe(tmp, vad_filter=True)
            return " ".join(s.text for s in segments)
        except Exception as e:
            logger.error(f"Whisper transcription chunk error: {e}")
            return ""
        finally:
            if tmp:
                try:
                    Path(tmp).unlink(missing_ok=True)
                except Exception:
                    pass

    def _paste(self, text: str):
        """Simulates system paste operation in focused fields, synchronized with a lock."""
        with self._paste_lock:
            try:
                prev = pyperclip.paste()
                pyperclip.copy(text)
                # Emulate pasting via OS shortcut
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)
                # Restore clipboard
                pyperclip.copy(prev)
            except Exception as e:
                logger.error(f"Clipboard paste emulation failed: {e}")
