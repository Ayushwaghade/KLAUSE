import pytest
from unittest.mock import MagicMock, patch
from app.voice.tts import truncate_sentences, TTSEngine
from app.voice.voice_manager import VoiceManager

def test_truncate_sentences():
    """
    Verify sentence split and truncation helper works correctly.
    """
    text = "Hello world. This is KLAUSE. How are you? Nice day."
    res = truncate_sentences(text, max_sentences=2)
    assert "Hello world. This is KLAUSE." in res
    assert "Nice day" not in res
    
    # Check limit boundaries
    assert truncate_sentences("Hello.", 3) == "Hello."

@patch("win32com.client.Dispatch")
@patch("threading.Thread")
def test_get_best_voice_fallback(mock_thread, mock_dispatch):
    """
    Verify voice enumeration falls back correctly.
    """
    mock_sapi = MagicMock()
    mock_voices = MagicMock()
    
    v1 = MagicMock()
    v1.GetDescription.return_value = "Microsoft Zira Desktop"
    v2 = MagicMock()
    v2.GetDescription.return_value = "Microsoft David Desktop"
    
    mock_voices.Count = 2
    mock_voices.Item.side_effect = lambda idx: v1 if idx == 0 else v2
    mock_sapi.GetVoices.return_value = mock_voices
    mock_dispatch.return_value = mock_sapi
    
    engine = TTSEngine()
    engine.sapi_voice = mock_sapi
    
    best_voice = engine._get_best_voice()
    assert best_voice == v2

@patch("win32com.client.Dispatch")
@patch("threading.Thread")
def test_speak_queue_clean_text(mock_thread, mock_dispatch):
    """
    Verify speak cleans markdown characters before queueing.
    """
    mock_sapi = MagicMock()
    mock_dispatch.return_value = mock_sapi
    
    # Mock GetVoices Count to avoid comparison exceptions
    mock_voices = MagicMock()
    mock_voices.Count = 0
    mock_sapi.GetVoices.return_value = mock_voices
    
    engine = TTSEngine()
    engine.is_active = True # Force active to ensure speak queues the cleaned text
    
    engine.speak("**Hello** `KLAUSE`!")
    
    txt = engine.queue.get_nowait()
    assert txt == "Hello KLAUSE!"

@patch("win32com.client.Dispatch")
@patch("threading.Thread")
def test_speak_strips_task_complete(mock_thread, mock_dispatch):
    """
    Verify speak strips 'Task complete' variations and avoids speaking empty strings.
    """
    mock_sapi = MagicMock()
    mock_dispatch.return_value = mock_sapi
    mock_voices = MagicMock()
    mock_voices.Count = 0
    mock_sapi.GetVoices.return_value = mock_voices
    
    engine = TTSEngine()
    engine.is_active = True
    
    # 1. Spoken string containing dialog + status
    engine.speak("All operations complete. [Task complete]")
    txt = engine.queue.get_nowait()
    assert txt == "All operations complete."
    
    # 2. String containing only status variations (should not queue speaking)
    engine.speak("Task complete.")
    assert engine.queue.empty()
    
    engine.speak("[Task complete]")
    assert engine.queue.empty()

@patch("app.voice.voice_manager.settings")
def test_voice_manager_init(mock_settings):
    """
    Verify voice manager settings are loaded.
    """
    mock_settings.voice.enabled = False
    mock_settings.voice.trigger_mode = "push_to_talk"
    mock_settings.voice.hotkey = "ctrl+space"
    
    with patch("app.voice.tts.HAS_WIN32", False):
        manager = VoiceManager()
        assert manager.enabled is False
        assert manager.trigger_mode == "push_to_talk"
        assert manager.hotkey == "ctrl+space"
