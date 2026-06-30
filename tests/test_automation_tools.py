import pytest
import os
from unittest.mock import MagicMock, patch
from app.core.context import context
from app.tools.filesystem_tools import (
    _resolve_path,
    fs_list_dir,
    fs_create_dir,
    fs_copy,
    fs_move,
    fs_delete
)
from app.tools.clipboard_tools import clipboard_get_text, clipboard_set_text
from app.tools.app_tools import open_application
from app.tools.window_tools import list_open_windows, focus_window

@pytest.fixture(autouse=True)
def setup_test_context():
    """
    Setup dummy project directory context.
    """
    context.current_project_path = "E:\\dummy_workspace"
    yield
    context.current_project_path = None

# --- Filesystem Tests ---

def test_fs_traversal_blocks_escape():
    """
    Verify that resolving path traversal attempts outside the project root throws PermissionError.
    """
    # Escaping E:\dummy_workspace
    with pytest.raises(PermissionError):
        _resolve_path("../../windows/system32")

@patch("pathlib.Path.exists")
def test_fs_copy_fails_dest_exists(mock_exists):
    """
    Verify fs_copy blocks execution and returns an error when destination already exists.
    """
    # Mock destination check to return True (already exists)
    mock_exists.return_value = True
    res = fs_copy("src.txt", "dest.txt")
    assert "already exists. Overwrite blocked" in res

@patch("os.makedirs")
def test_fs_create_dir_success(mock_makedirs):
    """
    Verify fs_create_dir runs os.makedirs correctly.
    """
    res = fs_create_dir("new_folder")
    mock_makedirs.assert_called_once()
    assert "Created directory successfully" in res

# --- Clipboard Tests ---

@patch("pyperclip.paste")
def test_clipboard_get_text_non_text(mock_paste):
    """
    Verify clipboard retrieval handles non-text gracefully.
    """
    mock_paste.return_value = ""
    res = clipboard_get_text()
    assert "empty or contains non-text content" in res

@patch("pyperclip.copy")
def test_clipboard_set_text_success(mock_copy):
    """
    Verify clipboard setting calls copy helper.
    """
    res = clipboard_set_text("test content")
    mock_copy.assert_called_once_with("test content")
    assert "successfully updated" in res

# --- Application Opener Tests ---

@patch("app.tools.app_tools.settings")
def test_app_opener_blocks_unlisted(mock_settings):
    """
    Verify open_application fails if the request key is not configured on the whitelist.
    """
    # Setup allowed apps map
    mock_settings.allowed_applications = {"notepad": "notepad.exe"}
    
    # Try opening unlisted browser
    res = open_application("chrome")
    assert "not in the allowed applications list" in res

@patch("subprocess.Popen")
@patch("os.startfile", create=True)
@patch("app.tools.app_tools.settings")
def test_app_opener_launches_allowed(mock_settings, mock_startfile, mock_popen):
    """
    Verify open_application launches whitelisted apps correctly.
    """
    mock_settings.allowed_applications = {"notepad": "notepad.exe"}
    res = open_application("notepad")
    assert "Successfully launched" in res

# --- Window Manager Tests ---

@patch("pygetwindow.getAllWindows")
def test_list_open_windows_noise_filter(mock_get_all):
    """
    Verify listing open windows filters invisible, untitled windows and limits outputs.
    """
    w1 = MagicMock()
    w1.title = "Notepad - notes.txt"
    w1.visible = True
    w1.width = 800
    
    # Invisible helper window
    w2 = MagicMock()
    w2.title = "Default IME"
    w2.visible = False
    w2.width = 0
    
    mock_get_all.return_value = [w1, w2]
    
    res = list_open_windows()
    assert "Notepad - notes.txt" in res
    assert "Default IME" not in res
