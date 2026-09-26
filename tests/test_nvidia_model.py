import os
import pytest
from unittest.mock import patch, MagicMock
from app.config.config import settings
from app.core.brain import Brain
from app.core.client import get_nvidia_client

def test_nvidia_client_instantiation():
    # Force settings mock
    with patch.object(settings.ai, "provider", "nvidia"), \
         patch.object(settings, "nvidia_api_key", "nvapi-test-key-xyz"):
        
        # Reset client cache
        from app.core import client
        client._shared_nvidia_client = None
        
        cli = get_nvidia_client()
        assert cli is not None
        assert cli.api_key == "nvapi-test-key-xyz"
        assert str(cli.base_url) == "https://integrate.api.nvidia.com/v1/"

def test_brain_nvidia_think_json_parsing():
    # Setup Brain with nvidia provider
    with patch.object(settings.ai, "provider", "nvidia"), \
         patch.object(settings, "nvidia_api_key", "nvapi-test-key-xyz"), \
         patch.object(settings.ai, "nvidia_model", "nvidia/nemotron-3-ultra-550b-a55b"):
        
        from app.core import client
        client._shared_nvidia_client = MagicMock()
        
        brain = Brain()
        assert brain.provider == "nvidia"
        assert brain.model_name == "nvidia/nemotron-3-ultra-550b-a55b"
        
        # Mock chat completions response
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"thought": "Deciding to complete request", "action": "FINAL", "params": {}, "response": "Hello from Nemotron!"}'
        mock_completion.choices = [mock_choice]
        brain.client.chat.completions.create.return_value = mock_completion
        
        # Run thinking loop
        res = brain.think("Hello", session_id="test_nvidia_session")
        
        # Verify result and call parameters
        assert "Hello from Nemotron!" in res
        brain.client.chat.completions.create.assert_called()
        
        # Verify JSON mode format parameter
        called_args, called_kwargs = brain.client.chat.completions.create.call_args
        assert called_kwargs["response_format"] == {"type": "json_object"}
        assert called_kwargs["model"] == "nvidia/nemotron-3-ultra-550b-a55b"

def test_brain_nvidia_quick_call():
    # Setup Brain with nvidia provider
    with patch.object(settings.ai, "provider", "nvidia"), \
         patch.object(settings, "nvidia_api_key", "nvapi-test-key-xyz"):
        
        from app.core import client
        client._shared_nvidia_client = MagicMock()
        
        brain = Brain()
        
        # Mock completions return for quick call (text-only)
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "none"
        mock_completion.choices = [mock_choice]
        brain.client.chat.completions.create.return_value = mock_completion
        
        res = brain._quick_llm_call("Is this complex?")
        assert res == "none"
        
        called_args, called_kwargs = brain.client.chat.completions.create.call_args
        # Enforce json should be false for quick calls
        assert "response_format" not in called_kwargs
