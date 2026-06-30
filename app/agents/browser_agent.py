import os
from pathlib import Path
from loguru import logger
from playwright.sync_api import sync_playwright
from app.config.config import settings

class BrowserAgent:
    """
    Playwright-based interactive browser automation session manager.
    Maintains a single persistent Chromium browser page context across tools actions.
    """

    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = True
        
        # Resolve screenshots dir
        project_root = Path(__file__).resolve().parent.parent.parent
        self.screenshots_dir = project_root / "data" / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_session(self, headless: bool = True):
        """Lazy-initialize the Playwright browser session if not running."""
        if self.page is not None:
            if self.headless != headless:
                logger.info(f"Toggling browser headless mode from {self.headless} to {headless}. Resetting session.")
                self.reset()
            else:
                # Check if page is closed
                try:
                    self.page.url
                    return
                except Exception:
                    logger.warning("Browser page was closed unexpectedly. Restarting session.")
                    self.reset()

        try:
            logger.info(f"Initializing Playwright session (requested headless={headless})...")
            self.pw = sync_playwright().start()

            # 1. Attempt to connect to an existing Chrome instance on port 9222
            try:
                logger.info("Attempting to connect to existing Chrome instance over CDP on http://localhost:9222...")
                self.browser = self.pw.chromium.connect_over_cdp("http://localhost:9222")
                if self.browser.contexts:
                    self.context = self.browser.contexts[0]
                else:
                    self.context = self.browser.new_context()
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = self.context.new_page()
                logger.info("Successfully connected to existing Chrome instance over CDP.")
                return
            except Exception as cdp_err:
                logger.warning(f"Could not connect to existing Chrome instance: {cdp_err}. Launching a new instance.")

            # 2. Fallback: Launch a new instance (using local Chrome if configured)
            self.headless = headless
            launch_kwargs = {"headless": self.headless}
            chrome_path = settings.allowed_applications.get("chrome")
            if chrome_path and os.path.exists(chrome_path):
                launch_kwargs["executable_path"] = chrome_path
                logger.info(f"Using local Chrome executable: {chrome_path}")
            else:
                logger.info("Using Playwright default Chromium executable.")

            self.browser = self.pw.chromium.launch(**launch_kwargs)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # Default timeout for actions
            self.context.set_default_timeout(10000)
            self.page = self.context.new_page()
        except Exception as e:
            logger.error(f"Failed to start Playwright session: {e}")
            self.reset()
            raise RuntimeError(f"Playwright initialization failed: {e}")

    def reset(self):
        """Close browser context and clean up resources for a clean session reconnect."""
        logger.info("Resetting BrowserAgent session...")
        try:
            if self.page:
                self.page.close()
        except Exception:
            pass
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except Exception:
            pass
        
        self.page = None
        self.context = None
        self.browser = None
        self.pw = None

    def open_url(self, url: str, headless: bool = True) -> str:
        """Navigates the persistent session to the specified URL."""
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        try:
            self._ensure_session(headless=headless)
            logger.info(f"Navigating browser to: {url}")
            
            # Navigate with 10s timeout, wait for domcontentloaded
            self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
            
            title = self.page.title()
            return f"Successfully opened {self.page.url} | Title: '{title}'"
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return f"Error: Navigation failed to {url}: {e}"

    def read_page(self, selector: str = "body") -> str:
        """
        Extracts clean, readable text from the specified selector.
        Strips navigation/footer/boilerplate scripts, styles, and caps response.
        """
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        try:
            # Verify selector exists with 5s timeout
            self.page.wait_for_selector(selector, timeout=5000)
            
            # Clean boilerplate scripts, styling, navs, footers, headers
            cleaned_text = self.page.evaluate("""(sel) => {
                const root = document.querySelector(sel);
                if (!root) return '';
                
                // Clone the node to avoid mutating the actual page
                const clone = root.cloneNode(true);
                const stripSelectors = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe'];
                stripSelectors.forEach(s => {
                    clone.querySelectorAll(s).forEach(el => el.remove());
                });
                
                return clone.innerText || clone.textContent || '';
            }""", selector)

            # Clean whitespace
            cleaned_text = re.sub(r'\n+', '\n', cleaned_text).strip()
            cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)

            if not cleaned_text:
                return f"No readable text content found under selector '{selector}'."

            # Truncate text to 8,000 characters to prevent blowing LLM context
            if len(cleaned_text) > 8000:
                truncated = cleaned_text[:8000]
                return f"{truncated}\n\n[Content truncated... Total length was {len(cleaned_text)} characters]"
            
            return cleaned_text
        except Exception as e:
            return f"Error: Failed to read selector '{selector}': {e}"

    def click(self, selector: str) -> str:
        """Locates, scrolls to, and clicks the element specified by the selector."""
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        try:
            self.page.wait_for_selector(selector, timeout=5000)
            self.page.click(selector, timeout=5000)
            # Wait briefly for transition or load
            self.page.wait_for_timeout(500)
            
            new_url = self.page.url
            new_title = self.page.title()
            return f"Clicked element '{selector}' | Current URL: {new_url} | Title: '{new_title}'"
        except Exception as e:
            return f"Error: Click failed on selector '{selector}': {e}"

    def fill_form(self, selector: str, value: str) -> str:
        """Fills the input field specified by the selector with value."""
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        try:
            self.page.wait_for_selector(selector, timeout=5000)
            self.page.fill(selector, value, timeout=5000)
            return f"Successfully filled selector '{selector}' with value."
        except Exception as e:
            return f"Error: Failed to fill selector '{selector}': {e}"

    def screenshot(self, output_name: str = "screenshot.png") -> str:
        """Takes a screenshot of the current page viewport and saves it to disk."""
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        # Force valid file name extension
        if not output_name.lower().endswith((".png", ".jpg", ".jpeg")):
            output_name += ".png"

        filepath = self.screenshots_dir / output_name
        
        try:
            self.page.screenshot(path=str(filepath))
            file_size_kb = os.path.getsize(filepath) / 1024
            
            # Get viewport size
            viewport = self.page.viewport_size or {"width": "unknown", "height": "unknown"}
            return (
                f"Screenshot successfully saved to '{filepath.name}' "
                f"({viewport['width']}x{viewport['height']}, size: {file_size_kb:.1f} KB). "
                f"File path: {filepath.as_uri()}"
            )
        except Exception as e:
            return f"Error: Screenshot capture failed: {e}"

    def get_url_and_title(self) -> str:
        """Returns the current URL and page title."""
        if not self.page:
            return "No active browser session."
        try:
            return f"Current URL: {self.page.url} | Title: '{self.page.title()}'"
        except Exception as e:
            return f"Error getting page metadata: {e}"


# Regular expression helper
import re

# Singleton BrowserAgent instance
_browser_agent_inst = None

def get_browser_agent() -> BrowserAgent:
    global _browser_agent_inst
    if _browser_agent_inst is None:
        _browser_agent_inst = BrowserAgent()
    return _browser_agent_inst
