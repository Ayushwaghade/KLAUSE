import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import patch, MagicMock

from app.api.server import app
from app.api.security import get_or_generate_token

client = TestClient(app)

def test_api_auth_token_retrieval():
    """Verify standard endpoint fetches local verification token."""
    res = client.get("/api/auth/token")
    assert res.status_code == 200
    assert "token" in res.json()

def test_api_unauthorized_access():
    """Verify endpoints block requests without active bearer token."""
    res = client.get("/api/projects")
    assert res.status_code == 401

def test_api_authorized_access():
    """Verify endpoint allows request with active bearer token."""
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/projects", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_api_list_tasks():
    """Verify active tasks endpoint returns items."""
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/tasks", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_api_list_rules():
    """Verify registered rules endpoint returns items."""
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/rules", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_api_list_schedule():
    """Verify active schedules endpoint returns items."""
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/schedule", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@patch("app.core.brain.Brain.think")
def test_websocket_chat_streaming(mock_think):
    """Verify WebSocket /ws/chat authorization and prompt streaming."""
    token = get_or_generate_token()
    
    # 1. Refuse unauthorized ws connection
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/chat") as ws:
            pass

    # 2. Connect with token
    mock_think.return_value = "Result completed successfully."
    with client.websocket_connect(f"/ws/chat?token={token}") as ws:
        # Send json prompt
        ws.send_json({"session_id": "test_s", "prompt": "echo hello"})
        
        # Capture final response
        data = ws.receive_json()
        assert data["type"] == "final"
        assert "Result completed" in data["response"]


@patch("app.voice.stt.transcribe_audio")
def test_websocket_audio_transcription(mock_transcribe):
    """Verify WebSocket /ws/audio speech-to-text processing."""
    token = get_or_generate_token()
    mock_transcribe.return_value = "hello KLAUSE"

    # Connect with token
    with client.websocket_connect(f"/ws/audio?token={token}") as ws:
        # Send fake audio binary bytes
        ws.send_bytes(b"\x00\x00\x00\x00")
        
        # Verify returned transcript
        data = ws.receive_json()
        assert data["type"] == "transcript"
        assert data["text"] == "hello KLAUSE"
