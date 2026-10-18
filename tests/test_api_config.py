"""
Unit tests for configuration endpoints in app/api/server.py.
"""

from fastapi.testclient import TestClient
from app.api.server import app
from app.api.security import get_or_generate_token

client = TestClient(app)


def test_get_config_unauthorized():
    res = client.get("/api/config")
    assert res.status_code == 401


def test_get_config_authorized():
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/config", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "config" in data
    assert "raw_yaml" in data
    assert "effective_user_name" in data
    assert isinstance(data["config"], dict)


def test_update_config_valid_dict(monkeypatch, tmp_path):
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Mock save_yaml_config so we don't overwrite user's actual config.yaml in test
    fake_saved = {
        "raw_yaml": "klause:\n  name: KLAUSE\n  user_name: TestUser\n",
        "config": {"klause": {"name": "KLAUSE", "user_name": "TestUser"}},
        "effective_user_name": "TestUser"
    }
    monkeypatch.setattr("app.config.config.save_yaml_config", lambda *args, **kwargs: fake_saved)

    payload = {
        "config": {"klause": {"name": "KLAUSE", "user_name": "TestUser"}}
    }
    res = client.post("/api/config", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["effective_user_name"] == "TestUser"


def test_update_config_valid_raw_yaml(monkeypatch):
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}

    fake_saved = {
        "raw_yaml": "klause:\n  user_name: YamlUser\n",
        "config": {"klause": {"user_name": "YamlUser"}},
        "effective_user_name": "YamlUser"
    }
    monkeypatch.setattr("app.config.config.save_yaml_config", lambda *args, **kwargs: fake_saved)

    payload = {
        "raw_yaml": "klause:\n  user_name: YamlUser\n"
    }
    res = client.put("/api/config", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["effective_user_name"] == "YamlUser"


def test_update_config_empty_payload():
    token = get_or_generate_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/config", json={}, headers=headers)
    assert res.status_code == 400
