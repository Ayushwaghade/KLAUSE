import pytest
import os
import tempfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import requests
from app.agents.browser_agent import BrowserAgent, BrowserNotReadyError
from app.agents.github_client import GitHubClient


@pytest.fixture(scope="module")
def local_html_file():
    """Create a temporary HTML file for local browser testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        html_path = Path(temp_dir) / "test_page.html"
        html_content = (
            "<html>"
            "<head><title>Test Page Title</title></head>"
            "<body>"
            "  <header><nav><a href='#'>Home</a></nav></header>"
            "  <div id='content'>"
            "    <h1>Main Content Header</h1>"
            "    <p>This is a paragraph of clean text for testing.</p>"
            "    <input id='input-field' type='text' value='' />"
            "    <a id='link-btn' href='#'>Go to target</a>"
            "  </div>"
            "  <footer><p>Footer boilerplate</p></footer>"
            "  <script>console.log('strip me');</script>"
            "  <style>body { color: red; }</style>"
            "</body>"
            "</html>"
        )
        html_path.write_text(html_content, encoding="utf-8")
        yield html_path


@pytest.fixture(scope="function")
def browser_agent():
    agent = BrowserAgent()
    yield agent
    agent.reset()


def create_mock_page():
    """Create a mock page with is_closed set to sync MagicMock returning False."""
    page = AsyncMock()
    page.is_closed = MagicMock(return_value=False)
    return page


def test_browser_agent_open_and_read(browser_agent, local_html_file):
    # Navigate to local file using file URI
    file_uri = local_html_file.as_uri()
    
    # Open page (headless mode default)
    open_res = browser_agent.open_url(file_uri, headless=True)
    assert "Successfully opened" in open_res
    assert "Test Page Title" in open_res

    # Read clean text
    clean_text = browser_agent.read_page("body")
    
    # Verify boilerplate elements are stripped
    assert "Main Content Header" in clean_text
    assert "clean text for testing" in clean_text
    assert "Home" not in clean_text  # nav stripped
    assert "Footer boilerplate" not in clean_text  # footer stripped
    assert "strip me" not in clean_text  # script stripped


def test_browser_agent_fill_and_click(browser_agent, local_html_file):
    file_uri = local_html_file.as_uri()
    browser_agent.open_url(file_uri, headless=True)
    
    # Fill form
    fill_res = browser_agent.fill_form("#input-field", "Hello KLAUSE")
    assert "Successfully filled" in fill_res
    
    # Check value filled on page using the thread run_coro
    async def get_val():
        return await browser_agent.page.locator("#input-field").input_value()
    val = browser_agent.thread.run_coro(get_val())
    assert val == "Hello KLAUSE"

    # Click link
    click_res = browser_agent.click(selector="#link-btn")
    assert "Clicked" in click_res


def test_browser_agent_screenshot(browser_agent, local_html_file):
    file_uri = local_html_file.as_uri()
    browser_agent.open_url(file_uri, headless=True)
    
    # Take screenshot
    shot_res = browser_agent.screenshot("test_screenshot.png")
    assert "Screenshot successfully saved" in shot_res
    assert "test_screenshot.png" in shot_res

    # Check file exists in data/screenshots
    expected_path = browser_agent.screenshots_dir / "test_screenshot.png"
    assert expected_path.exists()
    
    # Clean up file
    expected_path.unlink()


def test_browser_agent_error_handling(browser_agent):
    # Open non-existent selector
    browser_agent.open_url("about:blank", headless=True)
    read_err = browser_agent.read_page("#non-existent-id")
    assert "Error" in read_err

    # Click non-existent element
    click_err = browser_agent.click(selector="#non-existent-id")
    assert "Error" in click_err

    # Fill non-existent field
    fill_err = browser_agent.fill_form("#non-existent-id", "test")
    assert "Error" in fill_err


def test_browser_agent_reset(browser_agent, local_html_file):
    file_uri = local_html_file.as_uri()
    browser_agent.open_url(file_uri, headless=True)
    assert browser_agent.page is not None

    # Call reset
    browser_agent.reset()
    assert browser_agent.page is None
    assert browser_agent.browser is None


def test_browser_agent_text_truncation(browser_agent, local_html_file):
    file_uri = local_html_file.as_uri()
    browser_agent.open_url(file_uri, headless=True)

    # Mock evaluate to return a huge string (> 8000 chars)
    with patch.object(browser_agent.page, "evaluate", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = "A" * 9000
        res = browser_agent.read_page("body")
        assert len(res) < 9000
        assert "[Content truncated..." in res


# ─── New Browser Agent Upgrades Tests ──────────────────────────────

@patch("app.agents.browser_agent.BrowserAgent._find_browser_exe_and_names")
@patch("app.agents.browser_agent.BrowserAgent._is_port_open")
@patch("app.agents.browser_agent.BrowserAgent._is_browser_process_running")
def test_browser_cdp_no_force_kill(mock_process, mock_port, mock_find, browser_agent):
    """Verify that KLAUSE raises BrowserNotReadyError if browser is running but port 9222 is closed."""
    mock_port.return_value = False
    mock_process.return_value = True  # Chrome is running
    mock_find.return_value = (Path("chrome.exe"), ["chrome"])
    
    # Call _ensure_session directly to bubble up BrowserNotReadyError
    with pytest.raises(BrowserNotReadyError) as exc:
        browser_agent._ensure_session(headless=False)
        
    assert "is currently running on your system" in str(exc.value)


def test_js_first_dom_parsing(browser_agent):
    """Verify that parse_html queries the DOM directly in page context first."""
    browser_agent.page = create_mock_page()
    browser_agent.page.url = "https://example.com"
    browser_agent.page.evaluate = AsyncMock(return_value=[
        {"value": "/watch?v=123", "text": "Interesting Video"}
    ])
    
    res = browser_agent.parse_html(selector="a", limit=1)
    assert "watch?v=123" in res
    assert "Interesting Video" in res


def test_semantic_text_cleaner(browser_agent):
    """Verify get_text performs clean DOM extraction and strips noise selectors."""
    browser_agent.page = create_mock_page()
    browser_agent.page.evaluate = AsyncMock(return_value="This is a clean parsed article content.")
    
    res = browser_agent.get_text(max_chars=100, selector="div#content")
    assert res == "This is a clean parsed article content."
    assert browser_agent.page.evaluate.call_count == 2
    assert "div#content" in browser_agent.page.evaluate.call_args_list[1][0][0]


def test_password_typing_protection(browser_agent):
    """Verify KLAUSE refuses to type into password input fields."""
    browser_agent.page = create_mock_page()
    # First evaluate call returns True (is_password), second would be is_contenteditable
    browser_agent.page.evaluate = AsyncMock(return_value=True)
    
    res = browser_agent.fill_form("input#pass", "secretpassword")
    assert "restricted from typing into password fields" in res
    # Should not have called fill
    assert browser_agent.page.fill.call_count == 0


def test_contenteditable_fill_fallback(browser_agent):
    """Verify fill_form uses click + keyboard.type() on contenteditable elements."""
    browser_agent.page = create_mock_page()
    # evaluate call sequence: (1) liveness check in _ensure_session returns 1,
    # (2) is_password=False, (3) is_contenteditable=True
    browser_agent.page.evaluate = AsyncMock(side_effect=[1, False, True])
    
    res = browser_agent.fill_form("div[contenteditable='true']", "Hello from KLAUSE")
    assert "typed into contenteditable" in res
    browser_agent.page.click.assert_called_once()
    browser_agent.page.keyboard.type.assert_called_once_with("Hello from KLAUSE", delay=20)


def test_type_text_method(browser_agent):
    """Verify type_text types arbitrary text into the focused element."""
    browser_agent.page = create_mock_page()
    
    res = browser_agent.type_text("Hello world, this is a test message!")
    assert "Successfully typed" in res
    assert "36 characters" in res
    browser_agent.page.keyboard.type.assert_called_once_with("Hello world, this is a test message!", delay=30)


def test_upload_file_method(browser_agent):
    """Verify upload_file uses set_input_files for file uploads."""
    browser_agent.page = create_mock_page()
    
    # Create a temp file to upload
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake image data")
        tmp_path = f.name
    
    try:
        res = browser_agent.upload_file("input[type='file']", tmp_path)
        assert "Successfully uploaded" in res
        browser_agent.page.set_input_files.assert_called_once()
    finally:
        os.unlink(tmp_path)


def test_upload_file_not_found(browser_agent):
    """Verify upload_file returns error for non-existent files."""
    browser_agent.page = create_mock_page()
    
    res = browser_agent.upload_file("input[type='file']", "/nonexistent/fake_file.jpg")
    assert "File not found" in res


@patch("app.agents.browser_agent.get_gemini_client")
def test_screenshot_resizing_for_vision(mock_gemini, browser_agent):
    """Verify vision_read captures and resizes screenshot before calling LLM."""
    browser_agent.page = create_mock_page()
    
    # Generate valid 10x10 PNG bytes using PIL to avoid format errors
    import PIL.Image
    buf = io.BytesIO()
    PIL.Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    dummy_png = buf.getvalue()
    
    browser_agent.page.screenshot = AsyncMock(return_value=dummy_png)
    
    mock_client = mock_gemini.return_value
    
    res = browser_agent.vision_read("What is this?")
    assert "Error:" not in res
    assert browser_agent.page.screenshot.called
    assert mock_client.models.generate_content.called


def test_tab_listing_sync(browser_agent):
    """Verify list_tabs maps active playwright context pages correctly."""
    mock_page1 = create_mock_page()
    mock_page1.url = "https://google.com"
    mock_page1.title = AsyncMock(return_value="Google")
    
    mock_page2 = create_mock_page()
    mock_page2.url = "https://wikipedia.org"
    mock_page2.title = AsyncMock(return_value="Wikipedia")
    
    # Set page instance to prevent _ensure_session from overriding mock context
    browser_agent.page = mock_page1
    browser_agent.context = MagicMock()
    browser_agent.context.pages = [mock_page1, mock_page2]
    
    tabs = browser_agent.list_tabs()
    assert len(tabs) == 2
    assert tabs[0]["url"] == "https://google.com"
    assert tabs[1]["title"] == "Wikipedia"


# ─── GitHub Client Tests ─────────────────────────────────────────

@patch("requests.get")
def test_github_client_success(mock_get):
    mock_issues_response = MagicMock()
    mock_issues_response.status_code = 200
    mock_issues_response.json.return_value = [
        {"number": 1, "title": "First Issue", "state": "open", "user": {"login": "alice"}},
        {"number": 2, "title": "Second Issue", "state": "open", "user": {"login": "bob"}, "pull_request": {}}
    ]
    mock_get.return_value = mock_issues_response

    client = GitHubClient()
    issues = client.get_issues("owner/repo", limit=5)
    assert len(issues) == 1
    assert issues[0]["title"] == "First Issue"


@patch("requests.get")
def test_github_client_unauthorized(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_get.return_value = mock_resp

    client = GitHubClient()
    with pytest.raises(ValueError) as exc:
        client.get_issues("owner/repo")
    assert "Unauthorized" in str(exc.value)


@patch("requests.get")
def test_github_client_rate_limit(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"X-RateLimit-Remaining": "0"}
    mock_get.return_value = mock_resp

    client = GitHubClient()
    with pytest.raises(ValueError) as exc:
        client.get_issues("owner/repo")
    assert "Rate Limit Exceeded" in str(exc.value)


@patch("requests.get")
def test_github_client_not_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    client = GitHubClient()
    with pytest.raises(ValueError) as exc:
        client.get_issues("owner/repo")
    assert "Repository or resource not found" in str(exc.value)


@patch("webbrowser.open")
def test_desktop_open_url_success(mock_open):
    from app.tools.browser_tools import desktop_open_url
    res = desktop_open_url("youtube.com")
    assert "Opened https://youtube.com" in res
    mock_open.assert_called_once_with("https://youtube.com")


def test_tool_registrations():
    from app.tools.base import tool_registry
    assert "browser_open" in tool_registry
    assert "desktop_open_url" in tool_registry
    assert "browser_read" in tool_registry
    assert "browser_click" in tool_registry
    assert "browser_fill" in tool_registry
    assert "browser_screenshot" in tool_registry
    assert "browser_get_url_and_title" in tool_registry
    assert "browser_close" in tool_registry
    assert "browser_parse_html" in tool_registry
    assert "browser_wait_for_content" in tool_registry
    assert "browser_get_text" in tool_registry
    assert "browser_vision_read" in tool_registry
    assert "browser_scroll" in tool_registry
    assert "browser_press" in tool_registry
    assert "browser_type" in tool_registry
    assert "browser_upload_file" in tool_registry
    assert "browser_list_tabs" in tool_registry
    assert "browser_new_tab" in tool_registry
    assert "browser_close_tab" in tool_registry
    assert "browser_switch_tab" in tool_registry
    assert "github_get_issues" in tool_registry
    assert "github_get_prs" in tool_registry
    assert "github_get_commits" in tool_registry
