from typing import Optional
from app.tools.base import tool
from app.agents.browser_agent import get_browser_agent
from app.agents.github_client import GitHubClient


@tool(
    name="browser_open",
    description=(
        "Opens Playwright's private Chromium scraper instance to query/extract page text or take screenshots. "
        "This is NOT the user's desktop browser (like Chrome or Brave). To launch the user's actual desktop browser, "
        "use 'open_application' with 'chrome' or 'brave'. "
        "Arguments: url (str). Optional: headless (bool, default True)."
    )
)
def browser_open(url: str, headless: bool = True) -> str:
    """Open a URL in the browser."""
    agent = get_browser_agent()
    return agent.open_url(url, headless=headless)


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
    description="Locates, scrolls to, and clicks an element specified by the CSS selector. Arguments: selector (str)."
)
def browser_click(selector: str) -> str:
    """Click selector element on page."""
    agent = get_browser_agent()
    return agent.click(selector)


@tool(
    name="browser_fill",
    description="Fills an input form field matching selector with the provided value. Arguments: selector (str), value (str)."
)
def browser_fill(selector: str, value: str) -> str:
    """Fill input field on page."""
    agent = get_browser_agent()
    return agent.fill_form(selector, value)


@tool(
    name="browser_screenshot",
    description="Captures viewport screenshot and saves it. Arguments: output_name (str, default 'screenshot.png')."
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
