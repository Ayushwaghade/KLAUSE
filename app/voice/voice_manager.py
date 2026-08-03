import os
import queue
import threading
from loguru import logger
from app.config.config import settings
from app.voice.stt import record_audio_clip, transcribe_audio
from app.voice.tts import TTSEngine, tts_engine

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
        self.trigger_mode = settings.voice.trigger_mode
        self.hotkey = settings.voice.hotkey
        self.temp_wav = os.path.join(settings.paths.logs, "voice_temp.wav")
        self._listening = False

    def start(self):
        """
        Starts the background voice listener/hotkey thread if enabled.
        """
        if not self.enabled:
            logger.info("Voice Manager: Voice support is disabled in config.")
            return
            
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

    def speak(self, text: str):
        """
        Proxy helper to speak text.
        """
        self.tts.speak(text)

    def stop_speaking(self):
        """
        Proxy helper to stop ongoing speech.
        """
        self.tts.stop()

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
