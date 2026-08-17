import queue
import re
import threading
from loguru import logger
from app.config.config import settings

# Conditional imports for Windows SAPI
try:
    import win32com.client
    import pythoncom
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    pythoncom = None

def truncate_sentences(text: str, max_sentences: int) -> str:
    """
    Split text into sentences and truncate to first N sentences.
    """
    # Simple regex split on sentence endings (.!? followed by whitespace)
    cleaned = text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    if len(sentences) > max_sentences:
        return " ".join(sentences[:max_sentences]) + " ..."
    return cleaned

class TTSEngine:
    def __init__(self):
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.sapi_voice = None
        self.is_active = HAS_WIN32
        
        if not HAS_WIN32:
            logger.warning("win32com.client not found. TTS will run in offline stub mode.")
            return

        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _get_best_voice(self):
        """
        Enumerate system voices, prefer David, fallback to first available.
        """
        voices = self.sapi_voice.GetVoices()
        for idx in range(voices.Count):
            desc = voices.Item(idx).GetDescription()
            if "david" in desc.lower():
                return voices.Item(idx)
        # Fallback to Zira or first one
        for idx in range(voices.Count):
            desc = voices.Item(idx).GetDescription()
            if "zira" in desc.lower() or "hazel" in desc.lower():
                return voices.Item(idx)
        if voices.Count > 0:
            return voices.Item(0)
        raise RuntimeError("No SAPI voices registered on this Windows machine.")

    def speak(self, text: str):
        """
        Speak text non-blocking by adding it to the Queue.
        Cuts text at sentence limit cap.
        """
        if not self.is_active:
            logger.debug(f"TTS offline stub (Speaking blocked): {text}")
            return
            
        # Clean text (remove Markdown markup like asterisks, links etc. to avoid voice spelling them out)
        clean_text = re.sub(r'[\*\#\`\-\_]', '', text)
        
        # Strip "Task complete" status variations from spoken text (user wants it typed only)
        clean_text = re.sub(r'(?i)[\[\(]?\btask\s+complete[\]\)]?[\.\!\?]?\s*', '', clean_text).strip()
        
        # If the remaining text contains no words/alphanumerics, do not queue speak
        if not clean_text.strip() or not re.search(r'\w', clean_text):
            logger.debug("TTS: Suppressing speech because text contains only task status/metadata.")
            return

        # Truncate to keep speaking output concise
        max_sents = getattr(settings.voice, "max_spoken_sentences", 3)
        truncated = truncate_sentences(clean_text, max_sents)
        
        logger.debug(f"Queueing TTS output: {truncated}")
        self.stop_event.clear()
        self.queue.put(truncated)

    def stop(self):
        """
        Instantly halts any currently spoken sentences (Thread-safe speech purge).
        """
        logger.info("TTS: Purging and stopping speech output.")
        self.stop_event.set()
        
        # Clear the queue
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break

    def _worker(self):
        """
        Background worker thread pulling texts from the queue and running Speak.
        """
        if pythoncom:
            try:
                pythoncom.CoInitialize()
            except Exception as e:
                logger.error(f"Failed to CoInitialize in TTS worker thread: {e}")

        # Initialize SAPI SpVoice within the background owner thread to avoid cross-thread COM issues
        if self.is_active:
            try:
                self.sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                self.sapi_voice.Voice = self._get_best_voice()
                rate = max(-10, min(10, getattr(settings.voice, "speaking_rate", 0)))
                self.sapi_voice.Rate = rate
                logger.info(f"SAPI TTS successfully initialized in worker thread. Selected: {self.sapi_voice.Voice.GetDescription()}")
            except Exception as e:
                logger.error(f"SAPI TTS initialization failed in worker thread: {e}")
                self.is_active = False

        while True:
            try:
                text = self.queue.get()
                if not self.stop_event.is_set() and self.is_active and self.sapi_voice:
                    logger.debug(f"TTS speaking: {text}")
                    # SVSFlagsAsync = 1 speaks asynchronously so we can poll stop_event or process next
                    self.sapi_voice.Speak(text, 1)
                    # Poll while speaking to check for stop interrupt
                    while not self.sapi_voice.WaitUntilDone(50):
                        if self.stop_event.is_set():
                            # Purge speech from within the owner thread!
                            self.sapi_voice.Speak("", 2)
                            break
                self.queue.task_done()
            except Exception as e:
                logger.error(f"TTS worker exception: {e}")

# Shared global instance of TTSEngine
tts_engine = TTSEngine()

