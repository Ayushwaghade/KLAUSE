from typing import Optional
from app.tools.base import tool
from app.agents.browser_agent import get_browser_agent
from app.agents.github_client import GitHubClient


@tool(
    name="browser_open",
    description=(
        "Opens any URL or website in the CDP-attached real-profile browser. "
        "If a plain query/word is provided instead of a URL (e.g. 'wikipedia' or 'gmail'), "
        "it will automatically construct and navigate to that service's target URL. "
        "Arguments: url (str). Optional: headless (bool, default False)."
    )
)
def browser_open(url: str, headless: bool = False) -> str:
    """Open a URL or service in the browser."""
    agent = get_browser_agent()
    # Check if this is a plain service word rather than a URL
    if not url.startswith(("http://", "https://", "file://")) and "." not in url and "/" not in url:
        url = agent.construct_url(url, query="")
    result = agent.open_url(url, headless=headless)
    # Track referenced URL for Obsidian Canvas connections
    try:
        from app.core.context import context
        context.track_referenced_url(url)
    except Exception:
        pass
    return result


@tool(
    name="desktop_open_url",
    description="Opens any URL or website in the user's default desktop web browser (e.g. Chrome, Brave). Use this when the user wants to open/view a website or video on their own screen. Arguments: url (str)."
)
def desktop_open_url(url: str) -> str:
    """Opens a URL in the user's default web browser."""
    import webbrowser
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"Observation: Opened {url} in your default desktop browser."
    except Exception as e:
        return f"Error opening URL: {e}"


@tool(
    name="browser_read",
    description="Extracts clean inner text from a page selector in the active session. Arguments: selector (str, default 'body')."
)
def browser_read(selector: str = "body") -> str:
    """Read contents of page selector."""
    agent = get_browser_agent()
    return agent.read_page(selector)


@tool(
    name="browser_click",
    description=(
        "Clicks an element specified by the CSS selector, raw text match, or ARIA accessibility role name. "
        "Arguments: selector (str - optional), text (str - optional), description (str - optional)."
    )
)
def browser_click(selector: str = "", text: str = "", description: str = "") -> str:
    """Click element on page."""
    agent = get_browser_agent()
    return agent.click(selector=selector, text=text, description=description)


@tool(
    name="browser_fill",
    description=(
        "Fills an input form field matching selector with the provided value. "
        "KLAUSE will automatically refuse to type if it detects a password field. "
        "Arguments: selector (str), value (str)."
    )
)
def browser_fill(selector: str, value: str) -> str:
    """Fill input field on page."""
    agent = get_browser_agent()
    return agent.fill_form(selector, value)


@tool(
    name="browser_screenshot",
    description="Captures a screenshot of the active viewport. Arguments: output_name (str, default 'screenshot.png')."
)
def browser_screenshot(output_name: str = "screenshot.png") -> str:
    """Take page screenshot."""
    agent = get_browser_agent()
    return agent.screenshot(output_name)


@tool(
    name="browser_get_url_and_title",
    description="Retrieves the current URL and title of the active page session. No arguments required."
)
def browser_get_url_and_title() -> str:
    """Get url and title of page."""
    agent = get_browser_agent()
    return agent.get_url_and_title()


@tool(
    name="browser_close",
    description="Closes the active browser session and cleans up resources. No arguments required."
)
def browser_close() -> str:
    """Close browser session."""
    agent = get_browser_agent()
    agent.reset()
    return "Browser session closed successfully."


# ── New Browser Tools (Mark-LXXXV Upgrades) ──────────────────────────

@tool(
    name="browser_parse_html",
    description=(
        "Queries elements inside the live rendered DOM via JavaScript using selectors. "
        "Falls back to BeautifulSoup parser. "
        "Arguments: selector (str - optional), known_key (str - optional, e.g. 'youtube_video_link', 'google_first_result'), "
        "attribute (str - optional, 'href'|'text'|'src', default 'href'), limit (int - optional, default 5)."
    )
)
def browser_parse_html(selector: str = "", known_key: str = "", attribute: str = "href", limit: int = 5) -> str:
    """Query live DOM using selectors."""
    agent = get_browser_agent()
    return agent.parse_html(selector=selector, known_key=known_key, attribute=attribute, limit=limit)


@tool(
    name="browser_wait_for_content",
    description="Waits for the page's DOMContentLoaded state. Arguments: timeout_ms (int - optional, default 5000)."
)
def browser_wait_for_content(timeout_ms: int = 5000) -> str:
    """Wait for DOMContentLoaded state."""
    agent = get_browser_agent()
    return agent.wait_for_content(timeout_ms=timeout_ms)


@tool(
    name="browser_get_text",
    description=(
        "Strips navigation/footer/sidebar boilerplate noise and retrieves cleaned semantic text from the page. "
        "Arguments: max_chars (int - optional, default 6000), selector (str - optional, default 'body')."
    )
)
def browser_get_text(max_chars: int = 6000, selector: str = "body") -> str:
    """Extract semantic text content from page."""
    agent = get_browser_agent()
    return agent.get_text(max_chars=max_chars, selector=selector)


@tool(
    name="browser_vision_read",
    description=(
        "Screenshots the viewport and submits a natural language question about the page to Gemini Vision. "
        "Use this as a fallback when DOM extraction fails. "
        "Arguments: question (str)."
    )
)
def browser_vision_read(question: str) -> str:
    """Analyze page visually using Gemini Vision."""
    agent = get_browser_agent()
    return agent.vision_read(question)


@tool(
    name="browser_scroll",
    description="Scrolls page viewport mouse wheel. Arguments: direction (str, 'up'|'down', default 'down'), amount (int - optional, default 500)."
)
def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """Scroll page view."""
    agent = get_browser_agent()
    return agent.scroll(direction=direction, amount=amount)


@tool(
    name="browser_press",
    description="Presses a keyboard key on the active window. Arguments: key (str, e.g. 'Enter', 'Tab', 'Escape')."
)
def browser_press(key: str) -> str:
    """Press keyboard key."""
    agent = get_browser_agent()
    return agent.press(key)


@tool(
    name="browser_type",
    description=(
        "Types arbitrary text into the currently focused element using keyboard simulation. "
        "Use this after clicking/focusing a contenteditable div or input field. "
        "Unlike browser_fill, this works on contenteditable divs (Instagram DMs, WhatsApp Web, Gmail compose). "
        "Arguments: text (str). Optional: delay (int, ms between keystrokes, default 30)."
    )
)
def browser_type(text: str, delay: int = 30) -> str:
    """Type text into focused element."""
    agent = get_browser_agent()
    return agent.type_text(text, delay=delay)


@tool(
    name="browser_upload_file",
    description=(
        "Uploads a local file to an <input type='file'> element on the page. "
        "This bypasses the OS file picker dialog entirely — no clipboard or manual interaction needed. "
        "Arguments: selector (str - CSS selector for the file input element), file_path (str - absolute path to the file)."
    )
)
def browser_upload_file(selector: str, file_path: str) -> str:
    """Upload file to input element."""
    agent = get_browser_agent()
    return agent.upload_file(selector, file_path)


@tool(
    name="browser_list_tabs",
    description="Lists all currently open tabs (index, URL, title) in the active browser context. No arguments required."
)
def browser_list_tabs() -> str:
    """List open tabs."""
    agent = get_browser_agent()
    tabs = agent.list_tabs()
    if not tabs:
        return "No active tabs found."
    lines = ["Open browser tabs:"]
    for t in tabs:
        lines.append(f"  - [{t['index']}] Title: '{t['title']}' | URL: {t['url']}")
    return "\n".join(lines)


@tool(
    name="browser_new_tab",
    description="Opens a new page tab in the active context. Arguments: url (str - optional)."
)
def browser_new_tab(url: str = "") -> str:
    """Open new browser tab."""
    agent = get_browser_agent()
    return agent.new_tab(url=url)


@tool(
    name="browser_close_tab",
    description="Closes the page tab matching the given index. Arguments: index (int - optional, default -1 closes active tab)."
)
def browser_close_tab(index: int = -1) -> str:
    """Close tab by index."""
    agent = get_browser_agent()
    return agent.close_tab(index=index)


@tool(
    name="browser_switch_tab",
    description="Switches the active tab view focus to the given tab index. Arguments: index (int)."
)
def browser_switch_tab(index: int) -> str:
    """Switch active tab focus."""
    agent = get_browser_agent()
    return agent.switch_tab(index)


# ── GitHub Tools ─────────────────────────────────────────────────────

@tool(
    name="github_get_issues",
    description="Retrieves issues for a public GitHub repository. Arguments: repo (str, format 'owner/repo'). Optional: state (str, 'open' or 'closed', default 'open'), limit (int, default 30)."
)
def github_get_issues(repo: str, state: str = "open", limit: int = 30) -> str:
    """Fetch repo issues."""
    try:
        client = GitHubClient()
        issues = client.get_issues(repo, state=state, limit=limit)
        if not issues:
            return f"No {state} issues found for repository '{repo}'."
            
        lines = [f"Issues for {repo} ({len(issues)} total):"]
        for item in issues:
            lines.append(f"  - #{item['number']}: {item['title']} (by {item['user']})")
        return "\n".join(lines)
    except Exception as e:
        return str(e)


@tool(
    name="github_get_prs",
    description="Retrieves Pull Requests for a public GitHub repository. Arguments: repo (str, format 'owner/repo'). Optional: state (str, 'open' or 'closed', default 'open'), limit (int, default 30)."
)
def github_get_prs(repo: str, state: str = "open", limit: int = 30) -> str:
    """Fetch repo PRs."""
    try:
        client = GitHubClient()
        prs = client.get_prs(repo, state=state, limit=limit)
        if not prs:
            return f"No {state} Pull Requests found for repository '{repo}'."
            
        lines = [f"Pull Requests for {repo} ({len(prs)} total):"]
        for item in prs:
            lines.append(f"  - #{item['number']}: {item['title']} (by {item['user']})")
        return "\n".join(lines)
    except Exception as e:
        return str(e)


@tool(
    name="github_get_commits",
    description="Retrieves commits for a public GitHub repository. Arguments: repo (str, format 'owner/repo'). Optional: limit (int, default 30)."
)
def github_get_commits(repo: str, limit: int = 30) -> str:
    """Fetch repo commits."""
    try:
        client = GitHubClient()
        commits = client.get_commits(repo, limit=limit)
        if not commits:
            return f"No commits found for repository '{repo}'."
            
        lines = [f"Commits for {repo} ({len(commits)} total):"]
        for item in commits:
            lines.append(f"  - {item['sha']}: {item['message']} (by {item['author']} on {item['date']})")
        return "\n".join(lines)
    except Exception as e:
        return str(e)
