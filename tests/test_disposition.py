import os
import time
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.config.disposition import DispositionConfig
from app.tools.system_tools import show_disposition
from app.core.context import context

@pytest.fixture
def mock_workspace(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    agents_dir = ws / ".agents"
    agents_dir.mkdir()
    return ws

def test_default_disposition_loading():
    # Make sure cache is clean
    DispositionConfig._cache.clear()
    
    # Load default settings (no workspace)
    disp = DispositionConfig.load_from_workspace(None)
    
    assert disp.proactivity.flag_code_smells is True
    assert disp.proactivity.suggest_unit_tests is True
    assert disp.proactivity.explain_architectural_decisions is True
    assert disp.style.code_philosophy == "explicit_over_clever"
    assert disp.style.formatting_strictness == "balanced"
    assert disp.personality.tone == "hacker"
    assert disp.personality.brevity == "concise"

def test_workspace_partial_deep_merge(mock_workspace):
    DispositionConfig._cache.clear()
    
    # Create a partial workspace configuration overriding only the tone and code philosophy
    ws_file = mock_workspace / ".agents" / "disposition.yaml"
    ws_data = {
        "style": {
            "code_philosophy": "clever_hacks"
        },
        "personality": {
            "tone": "minimalist"
        }
    }
    with open(ws_file, "w", encoding="utf-8") as f:
        yaml.dump(ws_data, f)
        
    disp = DispositionConfig.load_from_workspace(str(mock_workspace))
    
    # Assert overriden values
    assert disp.style.code_philosophy == "clever_hacks"
    assert disp.personality.tone == "minimalist"
    
    # Assert inherited default values (deep merge verified)
    assert disp.proactivity.flag_code_smells is True
    assert disp.proactivity.suggest_unit_tests is True
    assert disp.style.formatting_strictness == "balanced"
    assert disp.personality.brevity == "concise"

def test_validation_errors_fallback(mock_workspace):
    DispositionConfig._cache.clear()
    
    # Create invalid configuration in workspace (invalid tone)
    ws_file = mock_workspace / ".agents" / "disposition.yaml"
    ws_data = {
        "personality": {
            "tone": "invalid_tone_xyz"  # Should trigger pydantic literal validation failure
        }
    }
    with open(ws_file, "w", encoding="utf-8") as f:
        yaml.dump(ws_data, f)
        
    with patch("loguru.logger.warning") as mock_warn:
        disp = DispositionConfig.load_from_workspace(str(mock_workspace))
        
        # Verify that warning was logged
        mock_warn.assert_called()
        # Verify that it gracefully fell back to default config due to validation error
        assert disp.personality.tone == "hacker"

def test_mtime_caching_and_invalidation(mock_workspace):
    DispositionConfig._cache.clear()
    
    ws_file = mock_workspace / ".agents" / "disposition.yaml"
    
    # Write first configuration
    with open(ws_file, "w", encoding="utf-8") as f:
        yaml.dump({"personality": {"tone": "architect"}}, f)
        
    disp1 = DispositionConfig.load_from_workspace(str(mock_workspace))
    assert disp1.personality.tone == "architect"
    
    # Simulate caching: read again immediately (mtimes match)
    disp2 = DispositionConfig.load_from_workspace(str(mock_workspace))
    assert disp2 is disp1  # Same object reference returned from cache
    
    # Update modification time (sleep to ensure st_mtime changes)
    time.sleep(0.05)
    
    # Write updated configuration (override to hacker)
    with open(ws_file, "w", encoding="utf-8") as f:
        yaml.dump({"personality": {"tone": "hacker"}}, f)
        
    disp3 = DispositionConfig.load_from_workspace(str(mock_workspace))
    assert disp3.personality.tone == "hacker"
    assert disp3 is not disp1  # New object created

def test_show_disposition_tool(mock_workspace):
    DispositionConfig._cache.clear()
    context.current_project_path = str(mock_workspace)
    
    # Setup specific workspace config
    ws_file = mock_workspace / ".agents" / "disposition.yaml"
    with open(ws_file, "w", encoding="utf-8") as f:
        yaml.dump({"personality": {"tone": "minimalist"}}, f)
        
    import json
    res = show_disposition()
    data = json.loads(res)
    
    assert data["personality"]["tone"] == "minimalist"
    assert data["style"]["code_philosophy"] == "explicit_over_clever"
    
    context.current_project_path = None
