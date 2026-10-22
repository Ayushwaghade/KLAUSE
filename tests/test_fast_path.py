import pytest
from unittest.mock import MagicMock, patch
from app.core.brain import Brain, SHORTCUT_SAFE
from app.core.dispatcher import Dispatcher
from app.models.agent import ToolObservation

def test_fast_path_matching():
    brain = Brain()
    
    # 1. Websites
    match = brain._check_fast_path("open youtube")
    assert match is not None
    assert match[0] == "browser_open"
    assert match[1] == {"url": "https://youtube.com"}

    match = brain._check_fast_path("please launch google for me")
    assert match is not None
    assert match[0] == "browser_open"
    assert match[1] == {"url": "https://google.com"}

    match = brain._check_fast_path("go to https://example.com/docs")
    assert match is not None
    assert match[0] == "browser_open"
    assert match[1] == {"url": "https://example.com/docs"}

    # 2. Applications
    match = brain._check_fast_path("open notepad")
    assert match is not None
    assert match[0] == "open_application"
    assert match[1] == {"app_key": "notepad"}

    match = brain._check_fast_path("launch calculator")
    assert match is not None
    assert match[0] == "open_application"
    assert match[1] == {"app_key": "calc"}

    match = brain._check_fast_path("open cmd")
    assert match is not None
    assert match[0] == "open_application"
    assert match[1] == {"app_key": "cmd"}

    # 3. Window & System Controls
    match = brain._check_fast_path("minimize window")
    assert match is not None
    assert match[0] == "window_minimize"

    match = brain._check_fast_path("what is git status?")
    assert match is not None
    assert match[0] == "git_status"

    # 4. Non-matching complex tasks should return None
    assert brain._check_fast_path("write a python script to parse CSV files") is None
    assert brain._check_fast_path("search for latest news about AI") is None


def test_fast_path_execution_zero_llm_calls():
    mock_dispatcher = MagicMock(spec=Dispatcher)
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="browser_open",
        success=True,
        result="Opened browser at https://youtube.com"
    )

    mock_gemini_client = MagicMock()
    brain = Brain(dispatcher=mock_dispatcher)
    brain.is_connected = True
    brain.client = mock_gemini_client

    # Execute fast-path command
    resp = brain.think("open youtube")

    # Assert tool was dispatched with zero LLM calls
    mock_dispatcher.execute.assert_called_once_with("browser_open", {"url": "https://youtube.com"})
    assert mock_gemini_client.models.generate_content.call_count == 0
    assert "Opened YouTube" in resp
    assert "[Task complete]" in resp


def test_fast_path_failure_falls_back_to_react():
    mock_dispatcher = MagicMock(spec=Dispatcher)
    # Fast path attempt fails
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="browser_open",
        success=False,
        result="",
        error="Browser crashed"
    )

    mock_gemini_client = MagicMock()
    res1 = MagicMock()
    res1.text = '{"thought": "Browser failed, I will notify the user.", "action": "FINAL", "params": {}, "response": "Could not open browser"}'
    mock_gemini_client.models.generate_content.return_value = res1

    from app.config.config import settings
    with patch.object(settings.ai, "provider", "gemini"), \
         patch("app.core.brain.genai.Client", return_value=mock_gemini_client):
        brain = Brain(dispatcher=mock_dispatcher)
        brain.is_connected = True
        brain.client = mock_gemini_client

        with patch.object(brain, '_maybe_load_relevant_skill', return_value=""):
            resp = brain.think("open youtube")

        # LLM was invoked as fallback when fast path failed
        assert mock_gemini_client.models.generate_content.call_count >= 1
        assert "Could not open browser" in resp


def test_complexity_router_behavior():
    brain = Brain()
    # Simple single-verb commands must NOT be classified as complex
    assert brain._detect_complexity("open youtube") is False
    assert brain._detect_complexity("open notepad") is False
    assert brain._detect_complexity("what's on my screen") is False
    assert brain._detect_complexity("git status") is False

    # Genuinely complex / multi-step tasks must be classified as complex
    assert brain._detect_complexity("research security vulnerabilities and write a detailed report") is True
    assert brain._detect_complexity("refactor the authentication module and implement architecture fixes") is True
    assert brain._detect_complexity("open browser and then download the file and finally analyze the data") is True


def test_shortcut_safe_single_call():
    mock_dispatcher = MagicMock(spec=Dispatcher)
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="browser_open",
        success=True,
        result="Opened browser"
    )

    mock_gemini_client = MagicMock()
    # Step 1 sets final_on_success=True for a SHORTCUT_SAFE tool
    res1 = MagicMock()
    res1.text = '{"thought": "Opening site", "action": "browser_open", "params": {"url": "https://example.com/custom"}, "response": "Site opened successfully.", "final_on_success": true}'
    mock_gemini_client.models.generate_content.return_value = res1

    from app.config.config import settings
    with patch.object(settings.ai, "provider", "gemini"), \
         patch("app.core.brain.genai.Client", return_value=mock_gemini_client):
        brain = Brain(dispatcher=mock_dispatcher)
        brain.is_connected = True
        brain.client = mock_gemini_client

        with patch.object(brain, '_maybe_load_relevant_skill', return_value=""):
            resp = brain.think("browse to https://example.com/custom")

        # Shortcut triggered: Call #2 was skipped! Exactly 1 LLM call made!
        assert mock_gemini_client.models.generate_content.call_count == 1
        assert "Site opened successfully." in resp
        assert "[Task complete]" in resp
