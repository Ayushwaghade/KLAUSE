import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.core.rules_manager import RulesManager
from app.core.dispatcher import Dispatcher
from app.core.context import context
from app.tools.rules_tools import modify_rules
from app.tools.session_tools import set_session_data_folder, get_session_data_folder


@pytest.fixture
def temp_rules_file(tmp_path):
    rules_file = tmp_path / "rules.md"
    content = (
        "# Last modified: 2026-06-29 17:00:00\n\n"
        "## [File] Rule 1: Session Data Folder\n"
        "- Store all files inside the session folder.\n\n"
        "## [Browser] Rule 2: Incognito Mode\n"
        "- Do not save history.\n\n"
        "## [General] Rule 3: Be Polite\n"
        "- Greet users warmly.\n"
    )
    rules_file.write_text(content, encoding="utf-8")
    return rules_file


def test_rules_manager_caching_and_tags(temp_rules_file):
    rm = RulesManager()
    rm.rules_path = temp_rules_file
    
    # First load
    rm._ensure_loaded()
    assert len(rm._cached_rules) == 3
    assert rm._last_modified > 0
    
    # Verify cached load (mtime doesn't change)
    last_mtime = rm._last_modified
    with patch("os.path.getmtime", return_value=last_mtime):
        with patch.object(rm, "_parse_rules") as mock_parse:
            rm._ensure_loaded()
            mock_parse.assert_not_called()
            
    # Verify Tag Filtering
    # 1. No filter: returns all
    all_rules = rm.get_rules()
    assert "Rule 1" in all_rules
    assert "Rule 2" in all_rules
    assert "Rule 3" in all_rules
    
    # 2. File filter: General + File
    file_rules = rm.get_rules(filter_tag="File")
    assert "Rule 1" in file_rules
    assert "Rule 3" in file_rules
    assert "Rule 2" not in file_rules  # Browser rule skipped
    
    # 3. Browser filter: General + Browser
    browser_rules = rm.get_rules(filter_tag="Browser")
    assert "Rule 2" in browser_rules
    assert "Rule 3" in browser_rules
    assert "Rule 1" not in browser_rules  # File rule skipped


def test_dispatcher_boundary_checks(tmp_path):
    # Setup context session data folder
    session_dir = tmp_path / "session_data"
    session_dir.mkdir()
    context.session_data_folder = str(session_dir)
    
    # Setup Dispatcher with confirmation callback
    confirm_results = []
    def mock_confirm(prompt):
        confirm_results.append(prompt)
        return False # Reject write exceptions by default

    dispatcher = Dispatcher(confirm_fn=mock_confirm)
    
    # Case A: Writing INSIDE session folder -> Allowed (no warning, runs mock function)
    with patch("app.core.dispatcher.tool_registry") as mock_registry:
        mock_tool = MagicMock()
        mock_tool.destructive = False
        mock_tool.func = lambda path, content: "Success"
        mock_registry.__contains__.return_value = True
        mock_registry.__getitem__.return_value = mock_tool
        
        inside_file = session_dir / "output.txt"
        obs = dispatcher.execute("write_file", {"path": str(inside_file), "content": "hello"})
        assert obs.success is True
        assert len(confirm_results) == 0

    # Case B: Writing OUTSIDE session folder -> Intercepted, confirm_fn called, rejected
    with patch("app.core.dispatcher.tool_registry") as mock_registry:
        mock_tool = MagicMock()
        mock_tool.destructive = False
        mock_tool.func = lambda path, content: "Success"
        mock_registry.__contains__.return_value = True
        mock_registry.__getitem__.return_value = mock_tool
        
        outside_file = tmp_path / "outside.txt"
        obs = dispatcher.execute("write_file", {"path": str(outside_file), "content": "hello"})
        
        assert obs.success is False
        assert "RULE_VIOLATION" in obs.error
        assert len(confirm_results) == 1
        assert "outside.txt" in confirm_results[0]

    # Reset context
    context.session_data_folder = None


def test_modify_rules_tool(temp_rules_file):
    # Setup manager path
    with patch("app.tools.rules_tools.Path") as mock_path_class:
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = temp_rules_file.read_text(encoding="utf-8")
        
        # Resolve path mock chain: Path(__file__).resolve().parent.parent.parent / "rules.md"
        mock_path_class.return_value.resolve.return_value.parent.parent.parent.__truediv__.return_value = mock_file
        
        # Test Add action
        res = modify_rules(action="add", rule_text="## [General] Rule 4: Test Rule\n- Added successfully")
        assert "Successfully modified" in res
        assert mock_file.write_text.call_count == 2  # backup file and rules file writes


def test_session_folder_tools(tmp_path):
    session_dir = tmp_path / "new_session"
    context.session_id = "test_sess_123"
    
    # Mock settings folder load/save
    with patch("app.tools.session_tools._get_settings_path") as mock_set_path:
        mock_json_file = tmp_path / "session_settings.json"
        mock_set_path.return_value = mock_json_file
        
        # Run set
        res = set_session_data_folder(str(session_dir))
        assert "successfully configured" in res
        assert context.session_data_folder == str(session_dir.resolve())
        assert session_dir.exists()
        
        # Run get
        get_res = get_session_data_folder()
        assert str(session_dir.resolve()) in get_res

    # Reset
    context.session_data_folder = None


def test_dispatcher_parameter_filtering():
    # Setup Dispatcher
    dispatcher = Dispatcher()
    
    # Mock a tool function that accepts only specific parameters
    with patch("app.core.dispatcher.tool_registry") as mock_registry:
        mock_tool = MagicMock()
        mock_tool.destructive = False
        
        # Test function accepts only 'selector' and 'limit'
        def mock_func(selector, limit=5):
            return f"Processed selector '{selector}' with limit {limit}"
            
        mock_tool.func = mock_func
        mock_registry.__contains__.return_value = True
        mock_registry.__getitem__.return_value = mock_tool
        
        # Execute with extra/hallucinated parameters (index, action, document_id)
        params = {
            "selector": "div#target",
            "limit": 10,
            "index": 0,
            "action": "none",
            "document_id": "none"
        }
        
        obs = dispatcher.execute("mock_browser_parse", params)
        assert obs.success is False
        assert obs.result == ""
        assert "Invalid parameter 'index'" in obs.error
