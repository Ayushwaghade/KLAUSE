import os
import wave
import numpy as np
from loguru import logger
from app.config.config import settings

# Conditional imports for sounddevice
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False

# Global cache for the Whisper model
_whisper_model_cached = None

def get_whisper_model():
    """
    Cached Whisper model initialisation to prevent disk-loading latency.
    """
    global _whisper_model_cached
    if _whisper_model_cached is None:
        logger.info("Loading offline Whisper STT model ('base.en') on CPU.")
        from faster_whisper import WhisperModel
        # base.en is small (~140MB), runs on CPU using int8 quantization
        _whisper_model_cached = WhisperModel("base.en", device="cpu", compute_type="int8")
    return _whisper_model_cached

def record_audio_clip(filepath: str, duration: int = 8, sample_rate: int = 16000) -> bool:
    """
    Records mono audio from the system microphone using sounddevice.
    Converts float32 audio to int16 PCM and writes to WAV file.
    """
    if not HAS_SD:
        logger.error("sounddevice is not installed. Audio capture aborted.")
        return False
        
    logger.info(f"STT: Recording microphone for {duration} seconds...")
    try:
        # Record audio
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait() # Block until recording finishes
        logger.info("STT: Recording finished.")
        
        # Convert float32 range (-1.0, 1.0) to int16 range (-32768, 32767)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Write to WAV file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 2 bytes (16-bit)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())
            
        logger.debug(f"Wav file saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        return False

def transcribe_audio(wav_path: str) -> str:
    """
    Transcribes a WAV file using the configured STT engine (whisper or google).
    """
    if not os.path.exists(wav_path):
        return ""
        
    engine = getattr(settings.voice, "stt_engine", "whisper")
    logger.info(f"STT: Transcribing audio using engine '{engine}'")
    
    if engine == "google":
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)
            logger.info(f"Google STT Transcription: {text}")
            return text.strip()
        except Exception as e:
            logger.error(f"Google STT failed: {e}")
            return ""
            
    # Default: offline faster-whisper
    try:
        model = get_whisper_model()
        segments, info = model.transcribe(wav_path, beam_size=5)
        text = " ".join(seg.text for seg in segments)
        logger.info(f"Whisper STT Transcription: {text}")
        return text.strip()
    except Exception as e:
        logger.error(f"Whisper offline STT failed: {e}")
        return ""
