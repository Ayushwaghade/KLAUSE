import pytest
import time
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.voice.voice_typer import LiveVoiceTyper, SAMPLE_RATE, OVERLAP_SAMPLES


@pytest.fixture
def voice_typer_mocked():
    """Returns a LiveVoiceTyper instance with WhisperModel mocked out to prevent actual downloads during tests."""
    with patch("app.voice.voice_typer.WhisperModel") as mock_model_class:
        # Mock class instantiation
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], None)
        mock_model_class.return_value = mock_model
        
        # Instantiate
        typer = LiveVoiceTyper()
        return typer


def test_toggle_starts_and_stops_threads(voice_typer_mocked):
    typer = voice_typer_mocked
    typer.chunk_seconds = 0.05
    
    with patch("sounddevice.InputStream") as mock_input_stream:
        # Mock InputStream instance and enter block
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        
        # E.g. mock read to return silent float array
        mock_stream.read.return_value = (np.zeros(1024, dtype=np.float32), False)
        
        # Setup run-time checks
        assert typer.is_recording is False
        
        # Start dictation
        typer._toggle()
        assert typer.is_recording is True
        
        # Verify capture and transcribe loops started
        assert typer._capture_thread.is_alive()
        assert typer._transcribe_thread.is_alive()
        
        # Stop dictation
        typer._toggle()
        assert typer.is_recording is False
        
        # Wait a brief moment for threads to join/terminate
        time.sleep(0.5)
        assert not typer._capture_thread.is_alive()
        assert not typer._transcribe_thread.is_alive()


def test_overlap_data_preservation(voice_typer_mocked):
    typer = voice_typer_mocked
    
    # Check that previous tail is correctly concatenated
    typer._previous_tail = np.ones(OVERLAP_SAMPLES, dtype=np.float32) * 0.5
    
    # Buffer contains two 1000-sample chunks of 1.0
    typer._buffer = [np.ones(1000, dtype=np.float32), np.ones(1000, dtype=np.float32)]
    
    # We mock _transcribe to verify prepended audio length
    with patch.object(typer, "_transcribe", return_value="test text") as mock_transcribe:
        with patch.object(typer, "_paste") as mock_paste:
            typer._drain_and_transcribe()
            
            # The concatenated audio should have length: OVERLAP_SAMPLES (4800) + 2000 = 6800 samples
            assert mock_transcribe.call_count == 1
            passed_audio = mock_transcribe.call_args[0][0]
            assert len(passed_audio) == OVERLAP_SAMPLES + 2000
            
            # Verifies that first 4800 values are 0.5 (from previous tail) and last 2000 are 1.0
            assert np.all(passed_audio[:OVERLAP_SAMPLES] == 0.5)
            assert np.all(passed_audio[OVERLAP_SAMPLES:] == 1.0)
            
            # Verifies new previous tail contains the last 4800 values of passed_audio (which are 0.5 and 1.0 values)
            assert len(typer._previous_tail) == OVERLAP_SAMPLES


def test_temp_file_unlinking_on_transcription(voice_typer_mocked):
    typer = voice_typer_mocked
    
    # Mock whisper transcribe to raise exception
    typer.model.transcribe.side_effect = Exception("Whisper error")
    
    # Create test input float array
    audio = np.zeros(1000, dtype=np.float32)
    
    with patch("tempfile.NamedTemporaryFile") as mock_temp_file:
        mock_file_obj = MagicMock()
        mock_file_obj.name = "fake_temp_audio.wav"
        mock_temp_file.return_value.__enter__.return_value = mock_file_obj
        
        with patch("wave.open") as mock_wave_open:
            with patch("pathlib.Path.unlink") as mock_unlink:
                res = typer._transcribe(audio)
                
                # Check that even with exception, unlink is called inside finally block
                assert res == ""
                mock_unlink.assert_called_once_with(missing_ok=True)


def test_paste_lock_and_clipboard_restoration(voice_typer_mocked):
    typer = voice_typer_mocked
    
    with patch("pyperclip.paste", return_value="original text") as mock_paste:
        with patch("pyperclip.copy") as mock_copy:
            with patch("pyautogui.hotkey") as mock_hotkey:
                typer._paste("dictation text")
                
                # Check call sequences
                mock_paste.assert_called_once()
                # 1. Copies "dictation text", 2. Restores "original text"
                assert mock_copy.call_count == 2
                mock_copy.assert_any_call("dictation text")
                mock_copy.assert_any_call("original text")
                # Emulated paste key trigger
                mock_hotkey.assert_called_once_with("ctrl", "v")
