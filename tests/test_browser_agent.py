import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests
from app.agents.browser_agent import BrowserAgent
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
            "    <a id='link-btn' href='https://example.com/target'>Go to target</a>"
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
    
    # Check value filled on page
    val = browser_agent.page.locator("#input-field").input_value()
    assert val == "Hello KLAUSE"

    # Click link
    # We patch navigation or ignore errors because clicking might navigate away.
    # We just click and assert click response structure
    click_res = browser_agent.click("#link-btn")
    assert "Clicked element" in click_res


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
    click_err = browser_agent.click("#non-existent-id")
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
    with patch.object(browser_agent.page, "evaluate", return_value="A" * 9000):
        res = browser_agent.read_page("body")
        assert len(res) < 9000
        assert "[Content truncated..." in res


# ─── GitHub Client Tests ─────────────────────────────────────────

@patch("requests.get")
def test_github_client_success(mock_get):
    # Mock responses for issues, prs, commits
    mock_issues_response = MagicMock()
    mock_issues_response.status_code = 200
    mock_issues_response.json.return_value = [
        {"number": 1, "title": "First Issue", "state": "open", "user": {"login": "alice"}},
        {"number": 2, "title": "Second Issue", "state": "open", "user": {"login": "bob"}, "pull_request": {}} # This is a PR, should be skipped
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
    assert "github_get_issues" in tool_registry
    assert "github_get_prs" in tool_registry
    assert "github_get_commits" in tool_registry
