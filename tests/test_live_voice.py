"""
tests/test_live_voice.py

Unit tests for Gemini 3.8 Live Voice Integration, Rolling Context Session Rotation,
and the Dual-Model Voice Frontend <-> Agentic Backend Bridge in KLAUSE.
"""

import time
import pytest
from app.config.config import settings, AppConfig, LiveVoiceSettings
from app.voice.session_rotator import LiveSessionRotator
from app.voice.live_session import LiveVoiceSessionManager
from app.voice.voice_manager import VoiceManager


def test_live_voice_settings_configuration():
    """Verify LiveVoiceSettings and VoiceSettings contain proper defaults and config values."""
    assert hasattr(settings.voice, "mode")
    assert settings.voice.mode == "live"
    assert hasattr(settings.voice, "live")
    assert isinstance(settings.voice.live, LiveVoiceSettings)
    assert settings.voice.live.model == "gemini-3.8-live"
    assert settings.voice.live.voice_name == "Puck"
    assert settings.voice.live.rotation_token_limit == 45000
    assert settings.voice.live.sample_rate_in == 16000
    assert settings.voice.live.sample_rate_out == 24000
    assert settings.voice.live.barge_in is True


def test_session_rotator_metrics_and_turns():
    """Verify LiveSessionRotator correctly tracks token consumption and turns."""
    rotator = LiveSessionRotator(session_id="test_rotator_session")
    assert rotator.total_tokens == 0
    assert rotator.turn_count == 0

    rotator.update_usage(1500)
    assert rotator.total_tokens == 1500

    # Monotonic update only
    rotator.update_usage(1200)
    assert rotator.total_tokens == 1500

    rotator.record_turn("user", "Hello KLAUSE")
    rotator.record_turn("assistant", "Hello Ayush, ready to work.")
    assert rotator.turn_count == 1
    assert len(rotator.turn_buffer) == 2


def test_session_rotator_rotation_triggers():
    """Verify should_rotate() respects token limits, active tasks, speaking, and silence."""
    rotator = LiveSessionRotator(session_id="test_rotation_triggers")
    rotator.token_limit = 1000
    rotator.turn_limit = 10

    # 1. Under limits -> False
    rotator.total_tokens = 500
    assert not rotator.should_rotate()

    # 2. Exceeds tokens, but just had audio activity (< 2s) -> False
    rotator.total_tokens = 1200
    rotator.last_audio_timestamp = time.monotonic()
    assert not rotator.should_rotate()

    # 3. Exceeds tokens, silence > 2s -> True
    rotator.last_audio_timestamp = time.monotonic() - 2.5
    assert rotator.should_rotate()

    # 4. Exceeds tokens, silence > 2s, but agent task is running -> False
    rotator.set_task_running(True)
    assert not rotator.should_rotate()
    rotator.set_task_running(False)

    # 5. Exceeds tokens, silence > 2s, but model is speaking -> False
    rotator.set_speaking(True)
    assert not rotator.should_rotate()
    rotator.set_speaking(False)

    # 6. Cleared speaking & task -> True again
    assert rotator.should_rotate()


def test_session_rotator_system_instruction_building():
    """Verify system instruction contains persona, user name, and narrator directives."""
    rotator = LiveSessionRotator(session_id="test_sys_inst")
    instruction = rotator.build_system_instruction()
    
    assert "Ayush" in instruction
    assert "KLAUSE" in instruction
    assert "voice" in instruction
    assert "never plan" in instruction


def test_live_session_narrator_speech_queue():
    """Verify LiveVoiceSessionManager routes speech and falls back to SAPI when offline."""
    manager = LiveVoiceSessionManager()
    assert manager.is_connected is False
    # Test say() falls back gracefully to SAPI without throwing
    manager.say("Hello Ayush", event_type="done")


def test_live_session_barge_in_purge():
    """Verify _purge_audio_playback() flushes the output buffer cleanly."""
    manager = LiveVoiceSessionManager()
    with manager._audio_out_lock:
        manager._audio_out_buffer.extend(b"\x01\x02\x03\x04" * 100)
    assert len(manager._audio_out_buffer) == 400

    manager._purge_audio_playback()
    with manager._audio_out_lock:
        assert len(manager._audio_out_buffer) == 0
    assert manager.rotator.is_model_speaking is False


def test_voice_manager_live_mode_delegation():
    """Verify VoiceManager initializes in live mode and delegates controls."""
    vm = VoiceManager()
    assert vm.mode == "live"
    assert vm.live_session is not None

    # Test stop_speaking does not throw
    vm.stop_speaking()
