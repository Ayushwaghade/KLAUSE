"""
Unit tests for app.core.state_machine — Live State Machine.

All tests mock pygetwindow, pyperclip, and subprocess to avoid real system calls.
"""

import subprocess
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_window(title: str, visible: bool = True):
    win = MagicMock()
    win.title = title
    win.visible = visible
    return win


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullBlockFirstTurn:
    """First call to to_prompt_block(previous=None) returns the full state block."""

    def test_full_block_first_turn(self):
        from app.core.state_machine import SystemState, ProjectState, DesktopState

        state = SystemState(
            timestamp="14:32",
            active_project=ProjectState(
                name="klause",
                path="E:/KLAUSE",
                branch="main",
                active_file="brain.py",
                klause_spawned_processes=["npm dev (PID 3902)"],
                last_commit="abc1234 initial commit",
            ),
            desktop=DesktopState(
                active_window="Visual Studio Code",
                visible_windows=["Visual Studio Code", "Chrome"],
                clipboard_preview="hello world",
            ),
            current_task="Building state machine",
            last_tool_used="run_terminal_command",
            voice_active=False,
        )

        block = state.to_prompt_block(previous=None)

        assert "CURRENT SYSTEM STATE (14:32):" in block
        assert "Active window: Visual Studio Code" in block
        assert "Project: klause (E:/KLAUSE)" in block
        assert "Git branch: main" in block
        assert "Active file: brain.py" in block
        assert "npm dev (PID 3902)" in block
        assert "Last commit: abc1234 initial commit" in block
        assert 'Clipboard: "hello world"' in block
        assert "Current task: Building state machine" in block
        assert "Last tool: run_terminal_command" in block


class TestDiffBlockNoChanges:
    """When state hasn't changed, to_prompt_block returns empty string."""

    def test_diff_block_no_changes(self):
        from app.core.state_machine import SystemState, DesktopState

        state = SystemState(
            timestamp="14:32",
            active_project=None,
            desktop=DesktopState("Notepad", ["Notepad"], ""),
            current_task=None,
            last_tool_used=None,
            voice_active=False,
        )

        # Same state as previous → no diff
        block = state.to_prompt_block(previous=state)
        assert block == ""


class TestDiffBlockWithChanges:
    """When fields change, the diff block lists only the changed items."""

    def test_diff_detects_window_change(self):
        from app.core.state_machine import SystemState, DesktopState

        prev = SystemState(
            timestamp="14:30",
            active_project=None,
            desktop=DesktopState("Terminal", ["Terminal"], ""),
            current_task=None,
            last_tool_used=None,
            voice_active=False,
        )
        curr = SystemState(
            timestamp="14:32",
            active_project=None,
            desktop=DesktopState("Visual Studio Code", ["Visual Studio Code"], ""),
            current_task=None,
            last_tool_used=None,
            voice_active=False,
        )

        block = curr.to_prompt_block(previous=prev)
        assert "STATE CHANGES:" in block
        assert "Active window: Terminal → Visual Studio Code" in block


class TestClipboardRedaction:
    """Clipboard containing sensitive patterns is replaced with redacted text."""

    @pytest.mark.parametrize("clip_content", [
        "password=secret123",
        "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9",
        "AKIA1234567890ABCDEF",
        "ghp_abc1234567890xyz",
        "sk-proj-abcdef1234567890xyz",
    ])
    @patch("app.core.state_machine.settings")
    @patch("app.core.state_machine.pyperclip")
    def test_sensitive_clipboard_redacted(self, mock_clip, mock_settings, clip_content):
        from app.core.state_machine import StateMachine

        mock_settings.state_machine.capture_clipboard = True
        mock_clip.paste.return_value = clip_content

        sm = StateMachine()
        result = sm._safe_clipboard()
        assert result == "[redacted — possible sensitive content]"


class TestClipboardDisabled:
    """When capture_clipboard is False, clipboard is always empty."""

    @patch("app.core.state_machine.settings")
    @patch("app.core.state_machine.pyperclip")
    def test_clipboard_disabled(self, mock_clip, mock_settings):
        from app.core.state_machine import StateMachine

        mock_settings.state_machine.capture_clipboard = False
        mock_clip.paste.return_value = "some content"

        sm = StateMachine()
        result = sm._safe_clipboard()
        assert result == ""


class TestVSCodeTitleParsing:
    """VS Code window title is correctly parsed to extract the active filename."""

    @patch("app.core.state_machine.gw")
    def test_parses_vscode_title(self, mock_gw):
        from app.core.state_machine import StateMachine

        mock_win = _make_mock_window("brain.py \u2014 KLAUSE \u2014 Visual Studio Code")
        mock_gw.getActiveWindow.return_value = mock_win

        sm = StateMachine()
        result = sm._get_active_file_from_window_title()
        assert result == "brain.py"

    @patch("app.core.state_machine.gw")
    def test_non_vscode_returns_unknown(self, mock_gw):
        from app.core.state_machine import StateMachine

        mock_win = _make_mock_window("Google Chrome")
        mock_gw.getActiveWindow.return_value = mock_win

        sm = StateMachine()
        result = sm._get_active_file_from_window_title()
        assert result == "unknown"


class TestParallelTimeoutFallback:
    """When a collector times out, falls back to last-known value."""

    @patch("app.core.state_machine.gw")
    @patch("app.core.state_machine.pyperclip")
    @patch("app.core.state_machine.context")
    def test_project_collector_timeout_uses_fallback(self, mock_ctx, mock_clip, mock_gw):
        from app.core.state_machine import StateMachine, SystemState, ProjectState, DesktopState

        mock_ctx.current_project_path = "E:/KLAUSE"
        mock_ctx.current_task = None
        mock_ctx.last_tool_used = None
        mock_ctx.voice_active = False

        mock_gw.getActiveWindow.return_value = _make_mock_window("Test Window")
        mock_gw.getAllWindows.return_value = [_make_mock_window("Test Window")]
        mock_clip.paste.return_value = ""

        sm = StateMachine()

        # Seed a valid previous state
        prev_project = ProjectState(
            name="KLAUSE", path="E:/KLAUSE", branch="main",
            active_file="unknown", klause_spawned_processes=[], last_commit="none",
        )
        sm._current = SystemState(
            timestamp="14:00",
            active_project=prev_project,
            desktop=DesktopState("Test Window", ["Test Window"], ""),
            current_task=None, last_tool_used=None, voice_active=False,
        )

        # Mock the project collector to raise (simulating a timeout)
        with patch.object(sm, '_collect_project_state', side_effect=Exception("timeout")):
            state = sm.refresh()

        # Should fall back to the last-known project state
        assert state is not None
        assert state.active_project is not None
        assert state.active_project.branch == "main"
        assert state.desktop.active_window == "Test Window"


class TestProcessListFromRegistry:
    """Reads running_processes dict and formats alive processes."""

    @patch("app.core.state_machine.gw")
    def test_formats_alive_processes(self, mock_gw):
        from app.core.state_machine import StateMachine

        mock_proc_alive = MagicMock()
        mock_proc_alive.poll.return_value = None  # still running

        mock_proc_dead = MagicMock()
        mock_proc_dead.poll.return_value = 1  # exited

        fake_registry = {
            1234: {"process": mock_proc_alive, "command": "npm run dev"},
            5678: {"process": mock_proc_dead, "command": "python test.py"},
        }

        with patch("app.tools.terminal_tools.running_processes", fake_registry):
            sm = StateMachine()
            result = sm._get_klause_processes()

        assert len(result) == 1
        assert "npm run dev" in result[0]
        assert "PID 1234" in result[0]
