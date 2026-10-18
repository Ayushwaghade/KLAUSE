"""
Unit tests for OS-level desktop automation tools (app/tools/desktop_tools.py),
tool router classification, and dispatcher macro confirmation formatting.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.tools.base import tool_registry
import app.tools.desktop_tools as dt
from app.core.tool_router import classify_request
from app.core.dispatcher import Dispatcher


class TestDesktopToolsRegistration:
    def test_tools_registered_in_registry(self):
        expected_tools = [
            "desktop_macro",
            "get_cursor_position",
            "get_screen_size",
            "get_pixel_color",
            "locate_image_on_screen",
            "wait_for_image",
        ]
        for name in expected_tools:
            assert name in tool_registry, f"Tool '{name}' should be in tool_registry"
            assert tool_registry[name].group == "desktop"

    def test_destructive_flags(self):
        assert tool_registry["desktop_macro"].destructive is True
        assert tool_registry["get_cursor_position"].destructive is False
        assert tool_registry["get_screen_size"].destructive is False
        assert tool_registry["get_pixel_color"].destructive is False
        assert tool_registry["locate_image_on_screen"].destructive is False
        assert tool_registry["wait_for_image"].destructive is False



    @patch("app.tools.desktop_tools.pyautogui")
    def test_macro_hotkey_type_keypress_wait(self, mock_pag):
        steps = [
            {"action": "hotkey", "keys": "win+r"},
            {"action": "wait", "seconds": 0.1},
            {"action": "type", "text": "notepad"},
            {"action": "keypress", "key": "enter"},
        ]
        result = dt.desktop_macro(steps)

        assert "Successfully executed 4 desktop macro steps" in result
        mock_pag.hotkey.assert_called_once_with("win", "r")
        mock_pag.typewrite.assert_called_once_with("notepad", interval=0.02)
        mock_pag.press.assert_called_once_with("enter", presses=1)

    @patch("app.tools.desktop_tools.pyautogui")
    def test_macro_mouse_click_move_drag_scroll(self, mock_pag):
        steps = [
            {"action": "move", "x": 100, "y": 200, "duration": 0.1},
            {"action": "click", "x": 100, "y": 200, "button": "left", "clicks": 2},
            {"action": "drag", "start_x": 50, "start_y": 50, "end_x": 150, "end_y": 150},
            {"action": "scroll", "clicks": -5, "x": 100, "y": 200},
        ]
        result = dt.desktop_macro(steps)

        assert "Successfully executed 4 desktop macro steps" in result
        mock_pag.click.assert_called_once_with(x=100, y=200, button="left", clicks=2)
        mock_pag.drag.assert_called_once_with(100, 100, duration=0.5, button="left")
        mock_pag.scroll.assert_called_once_with(-5)

    @patch("app.tools.desktop_tools.pyautogui")
    def test_macro_json_string_input(self, mock_pag):
        steps_json = json.dumps([
            {"action": "hotkey", "keys": "ctrl+c"}
        ])
        result = dt.desktop_macro(steps_json)
        assert "Successfully executed 1 desktop macro steps" in result
        mock_pag.hotkey.assert_called_once_with("ctrl", "c")

    def test_macro_empty_steps(self):
        result = dt.desktop_macro([])
        assert "No actions performed" in result

    def test_macro_invalid_action(self):
        result = dt.desktop_macro([{"action": "self_destruct"}])
        assert "Error at step 1: Unknown action 'self_destruct'" in result

    def test_macro_invalid_json(self):
        result = dt.desktop_macro("not valid json [")
        assert "Error: 'steps' must be a list of action dictionaries" in result


class TestReadOnlyTools:
    @patch("app.tools.desktop_tools.pyautogui")
    def test_get_cursor_position(self, mock_pag):
        mock_pag.position.return_value = MagicMock(x=350, y=420)
        res = dt.get_cursor_position()
        assert "(350, 420)" in res

    @patch("app.tools.desktop_tools.pyautogui")
    def test_get_screen_size(self, mock_pag):
        mock_pag.size.return_value = MagicMock(width=1920, height=1080)
        res = dt.get_screen_size()
        assert "1920 x 1080" in res

    @patch("app.tools.desktop_tools.pyautogui")
    def test_get_pixel_color(self, mock_pag):
        mock_img = MagicMock()
        mock_img.getpixel.return_value = (255, 0, 128)
        mock_pag.screenshot.return_value = mock_img
        res = dt.get_pixel_color(100, 100)
        assert "RGB(255, 0, 128)" in res
        assert "#ff0080" in res


class TestToolRouterDesktopClassification:
    def test_classifies_desktop_requests(self):
        groups = classify_request("click on the submit button on the screen")
        assert "desktop" in groups
        # Co-activation should inject vision and window
        assert "vision" in groups
        assert "window" in groups
        assert "core" in groups

    def test_classifies_hotkey_macro_requests(self):
        groups = classify_request("press ctrl+s to save the file")
        assert "desktop" in groups


class TestDispatcherDesktopMacroConfirmation:
    def test_dispatcher_formats_macro_steps_for_confirmation(self):
        prompts = []
        def mock_confirm(msg):
            prompts.append(msg)
            return True

        dispatcher = Dispatcher(confirm_fn=mock_confirm)
        steps = [
            {"action": "hotkey", "keys": "win+r"},
            {"action": "type", "text": "notepad"},
            {"action": "keypress", "key": "enter"},
        ]
        with patch("app.tools.desktop_tools.pyautogui"):
            obs = dispatcher.execute("desktop_macro", {"steps": steps})

        assert obs.success is True
        assert len(prompts) == 1
        assert "Execute desktop macro (3 steps):" in prompts[0]
        assert "hotkey(win+r)" in prompts[0]
        assert "type('notepad')" in prompts[0]
        assert "press(enter)" in prompts[0]

    def test_dispatcher_rejection_halts_macro(self):
        def mock_deny(msg):
            return False

        dispatcher = Dispatcher(confirm_fn=mock_deny)
        obs = dispatcher.execute("desktop_macro", {"steps": [{"action": "hotkey", "keys": "alt+f4"}]})
        assert obs.success is False
        assert "rejected by user" in obs.error
