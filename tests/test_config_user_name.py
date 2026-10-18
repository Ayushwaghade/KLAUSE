"""
Tests for dynamic user name configuration in KLAUSE.
Verifies that user name is loaded from config and used dynamically throughout prompts.
"""

import pytest
from app.config.config import settings, AppConfig, KlauseSettings
from app.core.brain import Brain


def test_effective_user_name_default():
    assert settings.effective_user_name == "Ayush" or settings.effective_user_name == settings.klause.user_name


def test_custom_user_name_in_app_config():
    cfg = AppConfig(user_name="John Doe")
    assert cfg.effective_user_name == "John Doe"


def test_custom_user_name_in_klause_settings():
    cfg = AppConfig(klause=KlauseSettings(user_name="Alice"))
    assert cfg.effective_user_name == "Alice"


def test_brain_user_name_reflects_config(monkeypatch):
    monkeypatch.setattr(settings, "user_name", "Bob")
    brain = Brain()
    assert brain.user_name == "Bob"


from unittest.mock import MagicMock

def test_brain_generate_prompt_contains_dynamic_user_name(monkeypatch):
    monkeypatch.setattr(settings, "user_name", "Charlie")
    brain = Brain()
    monkeypatch.setattr(brain, "provider", "nvidia")
    
    captured_messages = []
    mock_client = MagicMock()
    def mock_create(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        choice = MagicMock()
        choice.message.content = '{"thought": "done", "action": "FINAL", "params": {}, "response": "done"}'
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    mock_client.chat.completions.create.side_effect = mock_create
    monkeypatch.setattr(brain, "client", mock_client)

    brain._generate_text_or_json("test task", enforce_json=True)

    assert len(captured_messages) == 1
    prompt_sent = captured_messages[0]["content"]
    assert "Your conversational response to Charlie" in prompt_sent
    assert "Charlie wants to open Wikipedia" in prompt_sent
    assert "Ayush" not in prompt_sent
