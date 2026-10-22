import os
import queue
import threading
from loguru import logger
from app.config.config import settings
from app.voice.stt import record_audio_clip, transcribe_audio
from app.voice.tts import TTSEngine, tts_engine
from app.voice.live_session import live_voice_session

# Global thread-safe queue for routing transcribed vocal inputs to main loop
voice_input_queue = queue.Queue()

# Global keyboard conditional import
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

class VoiceManager:
    def __init__(self):
        self.tts = tts_engine
        self.enabled = settings.voice.enabled
        self.mode = getattr(settings.voice, "mode", "live")
        self.trigger_mode = settings.voice.trigger_mode
        self.hotkey = settings.voice.hotkey
        self.temp_wav = os.path.join(settings.paths.logs, "voice_temp.wav")
        self._listening = False
        self.live_session = live_voice_session

    def start(self):
        """
        Starts the background voice listener or Gemini Live session if enabled.
        """
        if not self.enabled:
            logger.info("Voice Manager: Voice support is disabled in config.")
            return

        if self.mode == "live":
            logger.info("Voice Manager: Starting Gemini 3.8 Live API voice engine...")
            try:
                self.live_session.start()
                return
            except Exception as e:
                logger.error(f"Voice Manager: Failed to start Live API voice engine ({e}). Falling back to legacy STT/TTS mode.")
                self.mode = "legacy"
            
        if self.trigger_mode == "push_to_talk":
            if not HAS_KEYBOARD:
                logger.error("Voice Manager: 'keyboard' library not found. PTT cannot start.")
                return
            
            # Start hotkey listener thread
            logger.info(f"Voice Manager: Registering PTT hotkey: '{self.hotkey}'")
            try:
                keyboard.add_hotkey(self.hotkey, self._on_ptt_triggered)
            except Exception as e:
                logger.error(f"Failed to register keyboard hotkey: {e}")

    def speak(self, text: str, event_type: str = "done"):
        """
        Proxy helper to speak text out loud.
        In Live mode, delegates to Live Voice narrator (with automatic SAPI fallback).
        In legacy mode, uses SAPI directly.
        """
        if self.mode == "live" and self.live_session:
            self.live_session.say(text, event_type=event_type)
        else:
            self.tts.speak(text)

    def stop_speaking(self):
        """
        Proxy helper to stop ongoing speech across both Live and legacy engines.
        """
        if self.mode == "live" and self.live_session:
            try:
                self.live_session._purge_audio_playback()
                self.live_session._purge_speech_queue_steps()
            except Exception as e:
                logger.debug(f"Live voice stop error: {e}")
        self.tts.stop()

    def stop(self):
        """
        Terminates active voice sessions and unregisters hotkeys.
        """
        if self.mode == "live":
            try:
                self.live_session.stop()
            except Exception as e:
                logger.debug(f"Live session stop error: {e}")
        self.stop_speaking()

    def _on_ptt_triggered(self):
        """
        Callback fired on hotkey press.
        Prevents overlapping recordings.
        """
        if self._listening:
            logger.warning("PTT: Already recording audio.")
            return
            
        self._listening = True
        # Stop any ongoing speaking before starting recording
        self.stop_speaking()
        
        # Spawn recording and transcription in a separate thread so keyboard thread is not blocked
        threading.Thread(target=self._recording_worker, daemon=True).start()

    def _recording_worker(self):
        print(f"\n[LISTENING... Speak now for 7 seconds]")
        success = record_audio_clip(self.temp_wav, duration=7)
        print("[PROCESSING...]")
        
        if success:
            text = transcribe_audio(self.temp_wav)
            if text and text.strip():
                logger.info(f"PTT: Captured voice command: {text}")
                voice_input_queue.put(text)
            else:
                print("[No voice command detected]")
        else:
            print("[Audio capture failed]")
            
        self._listening = False
