import os
import time
import socket
import subprocess
import re
import io
import threading
import asyncio
from pathlib import Path
from urllib.parse import quote_plus, urljoin
from loguru import logger
from playwright.async_api import async_playwright
from app.config.config import settings
from app.core.client import get_gemini_client

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

# Constants
CDP_PORT = 9222
_OS = "Windows" if os.name == "nt" else "Darwin" if os.uname().sysname == "Darwin" else "Linux"

# Selector mappings
KNOWN_SELECTORS = {
    "youtube_video_link": [
        "ytd-video-renderer a#video-title",
        "#video-title-link",
        "ytd-grid-video-renderer a#video-title",
        "a#video-title"
    ],
    "google_first_result": [
        ".yuRUbf > a",
        "#search a",
        "a h3"
    ]
}

# Browser paths database
_BROWSERS = {
    "brave": {
        "display": "Brave",
        "exe": {
            "Windows": [
                Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe",
                Path("C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe"),
            ],
            "Darwin": [Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")],
            "Linux":  [Path("/usr/bin/brave-browser"), Path("/usr/bin/brave")],
        },
        "proc_names": ["brave.exe", "Brave Browser", "brave-browser", "brave"]
    },
    "chrome": {
        "display": "Google Chrome",
        "exe": {
            "Windows": [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            ],
            "Darwin": [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")],
            "Linux":  [Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium-browser")],
        },
        "proc_names": ["chrome.exe", "Google Chrome", "google-chrome", "chromium-browser"]
    },
    "edge": {
        "display": "Microsoft Edge",
        "exe": {
            "Windows": [
                Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
            ],
            "Darwin": [Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")],
            "Linux":  [Path("/usr/bin/microsoft-edge")],
        },
        "proc_names": ["msedge.exe", "Microsoft Edge", "microsoft-edge"]
    },
    "firefox": {
        "display": "Firefox",
        "exe": {
            "Windows": [
                Path("C:/Program Files/Mozilla Firefox/firefox.exe"),
                Path("C:/Program Files (x86)/Mozilla Firefox/firefox.exe"),
            ],
            "Darwin": [Path("/Applications/Firefox.app/Contents/MacOS/firefox")],
            "Linux":  [Path("/usr/bin/firefox")],
        },
        "proc_names": ["firefox.exe", "firefox"]
    }
}


class BrowserNotReadyError(Exception):
    """Exception raised when browser debugging connection fails or process profile locks exist."""
    pass


class BrowserThread(threading.Thread):
    """Dedicated background daemon thread managing the asyncio loop for async Playwright."""
    def __init__(self):
        super().__init__(daemon=True, name="KLAUSE_BrowserThread")
        self.loop = None
        self.ready = threading.Event()
        self.pw = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._init_playwright())
        self.ready.set()
        self.loop.run_forever()

    async def _init_playwright(self):
        self.pw = await async_playwright().start()

    def run_coro(self, coro, timeout=60):
        self.ready.wait(timeout=10)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            logger.error(f"Error executing coroutine on browser thread: {e}")
            raise

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


class BrowserAgent:
    """
    Thread-safe Playwright-based browser session manager.
    Runs async Playwright commands inside a background BrowserThread event loop.
    Supports CDP-attached user profiles and isolated fallback configurations.
    """

    def __init__(self):
        self.thread = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = False
        self._listener_registered = False
        
        project_root = Path(__file__).resolve().parent.parent.parent
        self.screenshots_dir = project_root / "data" / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def reset(self):
        """Close browser context and clean up resources."""
        logger.info("Resetting BrowserAgent session...")
        if self.thread and self.thread.is_alive():
            try:
                self.thread.run_coro(self._async_reset(), timeout=5)
            except Exception:
                pass
            try:
                self.thread.run_coro(self.thread.pw.stop(), timeout=5)
            except Exception:
                pass
            self.thread.stop()
            self.thread = None
        
        self.page = None
        self.context = None
        self.browser = None
        self._listener_registered = False

    async def _async_reset(self):
        try:
            if self.page:
                await self.page.close()
        except Exception:
            pass
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass

    # ---- helper status checks ----

    def _is_port_open(self, port: int) -> bool:
        try:
            # Bind to 127.0.0.1 to avoid localhost IPv6/IPv4 lookup translation delays on Windows
            s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            s.close()
            return True
        except Exception:
            return False

    def _find_browser_exe_and_names(self, name: str) -> tuple[Path | None, list[str]]:
        info = _BROWSERS.get(name, {})
        exes = info.get("exe", {}).get(_OS, [])
        for p in exes:
            if p.exists():
                return p, info.get("proc_names", [])
        return None, info.get("proc_names", [])

    def _is_browser_process_running(self, proc_names: list[str]) -> bool:
        """Check if any of the target browser process names are active in the OS."""
        if not proc_names:
            return False
        try:
            if _OS == "Windows":
                # Check using tasklist filtered by image name for speed (prevents timeout slowness)
                for name in proc_names:
                    res = subprocess.run(
                        ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"],
                        capture_output=True, text=True, timeout=2
                    )
                    if name.lower() in res.stdout.lower():
                        return True
            else:
                # Check using ps
                res = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
                for name in proc_names:
                    if name.lower() in res.stdout.lower():
                        return True
        except Exception as e:
            logger.warning(f"Error checking running browser processes: {e}")
        return False

    def _auto_launch_browser_process(self, exe: Path):
        logger.info(f"Auto-launching preferred browser: {exe.name} with debugging port {CDP_PORT}")
        args = [
            str(exe),
            f"--remote-debugging-port={CDP_PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble"
        ]
        # Append profile directory to bypass Chrome profile picker screen
        profile_dir = getattr(getattr(settings, "browser", None), "profile_directory", None)
        if profile_dir:
            args.append(f"--profile-directory={profile_dir}")
        else:
            args.append("--profile-directory=Default")
            
        # Run process
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Poll port until open
        deadline = time.time() + 10
        while time.time() < deadline:
            if self._is_port_open(CDP_PORT):
                logger.info("Auto-launched browser is now listening on debugging port.")
                return
            time.sleep(0.4)
            
        logger.warning("Browser took too long to open the debugging port. Terminating spawned process.")
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # ---- session setup ----

    async def _async_find_active_page(self):
        if not self.context or not self.context.pages:
            return None
        pages = self.context.pages
        # Try to find the page with visibilityState == 'visible'
        for p in reversed(pages):
            try:
                state = await p.evaluate("document.visibilityState")
                if state == "visible":
                    return p
            except Exception:
                pass
        # Fallback to the last page if none are visible or on error
        return pages[-1] if pages else None

    def _on_page_created(self, page):
        logger.info(f"New tab created/opened: {page.url}. Auto-switching active page focus.")
        self.page = page

    async def _async_setup_context_and_page(self, context, page):
        self.context = context
        self.page = page
        if self.context and not getattr(self, "_listener_registered", False):
            try:
                self.context.on("page", self._on_page_created)
                self._listener_registered = True
                logger.info("Registered auto-page-created listener on browser context.")
            except Exception as e:
                logger.warning(f"Could not register page listener: {e}")

    def _ensure_session(self, headless: bool = False):
        # Start browser thread if not running
        if self.thread is None or not self.thread.is_alive():
            self.thread = BrowserThread()
            self.thread.start()
            self.thread.ready.wait(timeout=10)

        # Execute loop connection safely inside thread
        self.thread.run_coro(self._async_ensure_session(headless))

    async def _async_ensure_session(self, headless: bool = False):
        if self.page is not None:
            try:
                # Real async liveness check: verify browser connection is active and page is not closed
                if self.page.is_closed():
                    raise RuntimeError("Page is closed")
                await self.page.evaluate("1")
                
                if not headless:
                    active = await self._async_find_active_page()
                    if active and active != self.page:
                        logger.info(f"Switching active page to user's visible tab: {active.url}")
                        self.page = active
                return
            except Exception:
                logger.warning("Browser page was closed unexpectedly. Restarting session.")
                await self._async_reset()

        logger.info(f"Setting up Browser session...")
        pw = self.thread.pw

        # If headless, we do NOT use the real profile CDP connection
        if headless:
            logger.info("Launching isolated headless Chromium context...")
            self.headless = True
            self.browser = await pw.chromium.launch(headless=True)
            context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()
            await self._async_setup_context_and_page(context, page)
            return

        # Headful mode -> attempt real-profile connection
        self.headless = False
        prefer_browser = getattr(getattr(settings, "browser", None), "prefer", "chrome").lower()
        if prefer_browser == "firefox":
            logger.warning("Firefox does not support CDP debugging. Falling back to isolated local context.")
            self.browser = await pw.firefox.launch(headless=False)
            context = await self.browser.new_context()
            page = await context.new_page()
            await self._async_setup_context_and_page(context, page)
            return

        # Handle CDP Connection for Chromium-based browsers (Chrome, Brave, Edge)
        port = CDP_PORT
        if self._is_port_open(port):
            try:
                logger.info(f"Attaching directly to existing browser context on port {port}")
                self.browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
                # Always open a new blank tab to avoid hijacking the user's active tab or triggering system page locks
                page = await context.new_page()
                await self._async_setup_context_and_page(context, page)
                return
            except Exception as e:
                logger.warning(f"CDP connection to active port failed: {e}")

        # Port is closed — check if it is running
        exe_path, proc_names = self._find_browser_exe_and_names(prefer_browser)
        if exe_path:
            if self._is_browser_process_running(proc_names):
                # Process is running but port is closed. DO NOT force-kill. Inform user.
                logger.error(f"{prefer_browser.capitalize()} is running without debugging port open.")
                raise BrowserNotReadyError(
                    f"{prefer_browser.capitalize()} is currently running on your system without debugging enabled.\n"
                    f"To let KLAUSE connect to your real profile, please either:\n"
                    f"1. Close all open {prefer_browser.capitalize()} windows and ask KLAUSE to open the page again.\n"
                    f"2. Restart your browser manually from the terminal with debugging enabled:\n"
                    f"   \"{exe_path}\" --remote-debugging-port={port}"
                )
            else:
                # Browser is not running at all. Safe to auto-launch.
                self._auto_launch_browser_process(exe_path)
                if self._is_port_open(port):
                    try:
                        self.browser = await pw.chromium.connect_over_cdp(f"http://localhost:{port}")
                        context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
                        page = context.pages[0] if context.pages else await context.new_page()
                        await self._async_setup_context_and_page(context, page)
                        active = await self._async_find_active_page()
                        if active:
                            self.page = active
                        return
                    except Exception as e:
                        logger.warning(f"Failed to connect to newly launched browser: {e}")
        
        # Fallback: Launch a built-in isolated Chromium instance if no real browser can be launched
        logger.warning("No real browser connection could be established. Falling back to default Playwright browser.")
        self.browser = await pw.chromium.launch(headless=False)
        context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        await self._async_setup_context_and_page(context, page)

    # ---- construct url helper ----

    def construct_url(self, service: str, **kwargs) -> str:
        service = service.lower().strip()
        q = kwargs.get("query", "")
        q_enc = quote_plus(q)
        patterns = {
            "google":           f"https://www.google.com/search?q={q_enc}",
            "google_search":    f"https://www.google.com/search?q={q_enc}",
            "bing":             f"https://www.bing.com/search?q={q_enc}",
            "duckduckgo":       f"https://duckduckgo.com/?q={q_enc}",
            "youtube":          f"https://www.youtube.com/results?search_query={q_enc}",
            "youtube_search":   f"https://www.youtube.com/results?search_query={q_enc}",
            "soundcloud":       f"https://soundcloud.com/search?q={q_enc}",
            "soundcloud_search":f"https://soundcloud.com/search?q={q_enc}",
            "spotify":          f"https://open.spotify.com/search/{q_enc}",
            "gmail":            "https://mail.google.com/",
            "google_drive":     "https://drive.google.com/",
            "google_classroom": "https://classroom.google.com/",
            "google_calendar":  "https://calendar.google.com/",
            "google_docs":      "https://docs.google.com/",
            "whatsapp":         "https://web.whatsapp.com/",
            "twitter":          f"https://twitter.com/search?q={q_enc}",
            "x":                f"https://x.com/search?q={q_enc}",
            "instagram":        f"https://www.instagram.com/explore/tags/{q_enc}/",
            "reddit":           f"https://www.reddit.com/search/?q={q_enc}",
            "amazon":           f"https://www.amazon.com/s?k={q_enc}",
            "ebay":             f"https://www.ebay.com/sch/i.html?_nkw={q_enc}",
            "wikipedia":        f"https://en.wikipedia.org/wiki/{q_enc}",
            "github":           f"https://github.com/search?q={q_enc}",
            "weather":          f"https://www.google.com/search?q=weather+{q_enc}",
        }
        return patterns.get(service, f"https://www.google.com/search?q={q_enc}")

    # ---- browser operations ----

    def open_url(self, url: str, headless: bool = False) -> str:
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        try:
            self._ensure_session(headless=headless)
            return self.thread.run_coro(self._async_open_url(url, headless))
        except BrowserNotReadyError as bne:
            return f"Error: Browser configuration error.\n{str(bne)}"
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return f"Error: Navigation failed to {url}: {e}"

    async def _async_open_url(self, url: str, headless: bool) -> str:
        logger.info(f"Navigating to URL: {url}")
        try:
            await self.page.goto(url, wait_until="load", timeout=15000)
        except Exception:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
        # Settle wait for SPA hydration
        await self.page.wait_for_timeout(1500)
        return f"Successfully opened {self.page.url} | Title: '{await self.page.title()}'"

    def parse_html(self, selector: str = "", known_key: str = "", attribute: str = "href", limit: int = 5) -> str:
        """JS-first live DOM query. Returns matching elements, falling back to static BS4 parser."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_parse_html(selector, known_key, attribute, limit))

    async def _async_parse_html(self, selector: str, known_key: str, attribute: str, limit: int) -> str:
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        selectors = []
        if known_key and known_key in KNOWN_SELECTORS:
            selectors.extend(KNOWN_SELECTORS[known_key])
        if selector:
            selectors.insert(0, selector)
        if not selectors:
            return '{"error": "No selector specified."}'

        base_url = self.page.url
        for sel in selectors:
            try:
                await self.page.wait_for_selector(sel, timeout=4000)
                raw = await self.page.evaluate("""
                    ([sel, attr]) => {
                        const elements = Array.from(document.querySelectorAll(sel));
                        return elements.map(el => {
                            let val = '';
                            if (attr === 'href') {
                                val = el.href || el.getAttribute('href') || '';
                            } else if (attr === 'text') {
                                val = el.textContent.trim();
                            } else if (attr === 'src') {
                                val = el.src || el.getAttribute('src') || '';
                            } else {
                                val = el.getAttribute(attr) || el.textContent.trim();
                            }
                            return {
                                value: val,
                                text: el.textContent.trim().replace(/\\s+/g, ' ').substring(0, 120)
                            };
                        }).filter(r => r.value && r.value.length > 0);
                    }
                """, [sel, attribute])

                if raw:
                    results = []
                    seen = set()
                    for r in raw:
                        v = r.get("value", "")
                        if v and not v.startswith("http") and not v.startswith("//"):
                            v = urljoin(base_url, v)
                            r["value"] = v
                        if v in seen or v.startswith("javascript:") or v.startswith("data:"):
                            continue
                        seen.add(v)
                        results.append(r)
                        if len(results) >= limit:
                            break
                    if results:
                        import json
                        return json.dumps({"found": results, "count": len(results)}, ensure_ascii=False)
            except Exception as e:
                logger.debug(f"JS evaluate failed for selector '{sel}': {e}")
                continue

        # Fallback to BeautifulSoup if JS eval yielded nothing
        try:
            from bs4 import BeautifulSoup
            html = await self.page.content()
            soup = BeautifulSoup(html, "html.parser")
            results = []
            for sel in selectors:
                for el in soup.select(sel, limit=limit * 2)[:limit]:
                    if attribute == "text":
                        val = el.get_text(strip=True)
                    elif attribute == "href":
                        val = el.get("href", "")
                        if val and not val.startswith("http"):
                            val = urljoin(base_url, val)
                    else:
                        val = el.get(attribute, el.get_text(strip=True))
                    if val:
                        results.append({"value": val, "text": el.get_text(strip=True)[:100]})
                if results:
                    break
            if results:
                import json
                return json.dumps({"found": results, "count": len(results)}, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"BeautifulSoup fallback parser failed: {e}")

        import json
        return json.dumps({"found": [], "count": 0, "note": f"No elements matched: {selectors}"})

    def wait_for_content(self, timeout_ms: int = 5000) -> str:
        """Wait for page domcontentloaded state."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_wait_for_content(timeout_ms))

    async def _async_wait_for_content(self, timeout_ms: int) -> str:
        if not self.page:
            return "Error: No active browser session."
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            return "Page loaded (domcontentloaded)."
        except Exception:
            return "Wait timeout reached (page may be partially loaded)."

    def read_page(self, selector: str = "body") -> str:
        """Extract clean text content from target selector."""
        self._ensure_session(headless=self.headless)
        return self.get_text(max_chars=8000, selector=selector)

    def get_text(self, max_chars: int = 6000, selector: str = "body") -> str:
        """Smart text extraction. Clones DOM, strips noise elements, returns text."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_get_text(max_chars, selector))

    async def _async_get_text(self, max_chars: int, selector: str) -> str:
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        try:
            await self.page.wait_for_selector(selector, timeout=4000)
            text = await self.page.evaluate(f"""
                () => {{
                    const root = document.querySelector('{selector}');
                    if (!root) return '';
                    const clone = root.cloneNode(true);
                    const noiseSelectors = [
                        'nav', 'header', 'footer', 'aside',
                        '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                        '[role="complementary"]', '.sidebar', '.nav', '.navbar', '.menu',
                        '.footer', '.header', '.cookie-banner', '.cookie-consent',
                        '.ad', '.ads', '.advertisement', '.social-share', '.share-buttons',
                        '.related-posts', '.comments', '#comments', '.popup', '.modal',
                        'script', 'style', 'noscript', 'iframe'
                    ];
                    for (const sel of noiseSelectors) {{
                        clone.querySelectorAll(sel).forEach(el => el.remove());
                    }}
                    
                    const mainSelectors = [
                        'main', 'article', '[role="main"]', '#mw-content-text',
                        '#content', '#main-content', '.post-content', '.article-content',
                        '.article-body', '.entry-content', '.page-content'
                    ];
                    for (const sel of mainSelectors) {{
                        const el = clone.querySelector(sel);
                        if (el) {{
                            const t = el.innerText.trim();
                            if (t.length > 200) return t;
                        }}
                    }}
                    return clone.innerText.trim();
                }}
            """)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            if len(text) > max_chars:
                truncated = text[:max_chars]
                return f"{truncated}\n\n[Content truncated... Total length was {len(text)} characters]"
            return text
        except Exception as e:
            return f"Error extracting page text: {e}"

    def click(self, selector: str = "", text: str = "", description: str = "") -> str:
        """Emulate click with ARIA role support."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_click(selector, text, description))

    async def _async_click(self, selector: str, text: str, description: str) -> str:
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        for attempt in range(2):
            try:
                url_before = self.page.url
                if selector:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector, timeout=5000)
                elif text:
                    await self.page.get_by_text(text, exact=False).first.click(timeout=5000)
                elif description:
                    clicked = False
                    for role in ["button", "link", "menuitem"]:
                        try:
                            await self.page.get_by_role(role, name=description, exact=False).first.click(timeout=2000)
                            clicked = True
                            break
                        except Exception:
                            pass
                    if not clicked:
                        await self.page.get_by_text(description, exact=False).first.click(timeout=4000)
                else:
                    return "Error: No click target provided."
                
                # Smart post-click waiting: try networkidle for SPA transitions, fallback to static wait
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    await self.page.wait_for_timeout(1500)

                # If URL changed (navigation), re-validate page reference
                if self.page.url != url_before:
                    active = await self._async_find_active_page()
                    if active and active != self.page:
                        self.page = active
                        logger.info(f"Page reference updated after navigation to: {self.page.url}")

                return f"Clicked. Current URL: {self.page.url} | Title: '{await self.page.title()}'"
            except Exception as e:
                err_str = str(e).lower()
                if attempt < 1 and ("detached" in err_str or "stale" in err_str or "disposed" in err_str or "target closed" in err_str):
                    logger.warning(f"Stale/detached element on click attempt {attempt+1}, retrying after settle...")
                    await self.page.wait_for_timeout(1000)
                    continue
                return f"Error: Click failed: {e}"
        return "Error: Click failed after retries."

    def fill_form(self, selector: str, value: str) -> str:
        """Types into input selector. Blocks if target element is a password field."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_fill_form(selector, value))

    async def _async_fill_form(self, selector: str, value: str) -> str:
        if not self.page:
            return "Error: No active browser session."

        for attempt in range(2):
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                
                # Security check: verify if element is password field (safe arg passing)
                is_password = await self.page.evaluate("""
                    (sel) => {
                        const el = document.querySelector(sel);
                        if (!el) return false;
                        return el.type === 'password' || 
                               el.getAttribute('type') === 'password' ||
                               (el.id && el.id.toLowerCase().includes('password')) ||
                               (el.name && el.name.toLowerCase().includes('password'));
                    }
                """, selector)
                if is_password:
                    logger.warning(f"Security Alert: Typing blocked on password field matching selector: {selector}")
                    return f"Error: Write operation blocked. KLAUSE is restricted from typing into password fields."

                # Check if element is a contenteditable div (not a standard input/textarea)
                is_contenteditable = await self.page.evaluate("""
                    (sel) => {
                        const el = document.querySelector(sel);
                        if (!el) return false;
                        return el.getAttribute('contenteditable') === 'true' || 
                               el.isContentEditable;
                    }
                """, selector)

                if is_contenteditable:
                    # Contenteditable elements don't work with page.fill() — use click + keyboard.type()
                    logger.info(f"Detected contenteditable element for '{selector}'. Using click + keyboard.type() fallback.")
                    await self.page.click(selector, timeout=3000)
                    await self.page.wait_for_timeout(300)
                    # Select all existing content and replace it
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.type(value, delay=20)
                    return f"Successfully typed into contenteditable '{selector}'."
                else:
                    await self.page.fill(selector, value, timeout=5000)
                    return f"Successfully filled selector '{selector}'."
            except Exception as e:
                err_str = str(e).lower()
                if attempt < 1 and ("detached" in err_str or "stale" in err_str or "disposed" in err_str):
                    logger.warning(f"Stale element on fill attempt {attempt+1}, retrying...")
                    await self.page.wait_for_timeout(500)
                    continue
                return f"Error: Fill failed: {e}"
        return "Error: Fill failed after retries."

    def scroll(self, direction: str = "down", amount: int = 500) -> str:
        """Emulate mouse wheel scroll."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_scroll(direction, amount))

    async def _async_scroll(self, direction: str, amount: int) -> str:
        if not self.page:
            return "Error: No active browser session."
        try:
            scroll_val = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, scroll_val)
            await self.page.wait_for_timeout(300)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Error: Scroll failed: {e}"

    def press(self, key: str) -> str:
        """Press keyboard key."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_press(key))

    async def _async_press(self, key: str) -> str:
        if not self.page:
            return "Error: No active browser session."
        try:
            await self.page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Error: Key press failed: {e}"

    def get_url_and_title(self) -> str:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_get_url_and_title())

    async def _async_get_url_and_title(self) -> str:
        if not self.page:
            return "No active browser session."
        try:
            return f"Current URL: {self.page.url} | Title: '{await self.page.title()}'"
        except Exception as e:
            return f"Error getting metadata: {e}"

    # ---- text typing ----

    def type_text(self, text: str, delay: int = 30) -> str:
        """Type arbitrary text into the currently focused element using keyboard simulation."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_type_text(text, delay))

    async def _async_type_text(self, text: str, delay: int) -> str:
        if not self.page:
            return "Error: No active browser session."
        try:
            await self.page.keyboard.type(text, delay=delay)
            return f"Successfully typed {len(text)} characters."
        except Exception as e:
            return f"Error: Type failed: {e}"

    # ---- file upload ----

    def upload_file(self, selector: str, file_path: str) -> str:
        """Upload a file to an <input type='file'> element using Playwright's set_input_files API."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_upload_file(selector, file_path))

    async def _async_upload_file(self, selector: str, file_path: str) -> str:
        if not self.page:
            return "Error: No active browser session."
        try:
            import os
            if not os.path.exists(file_path):
                return f"Error: File not found: {file_path}"
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.set_input_files(selector, file_path)
            await self.page.wait_for_timeout(1000)
            return f"Successfully uploaded file '{os.path.basename(file_path)}' to '{selector}'."
        except Exception as e:
            return f"Error: File upload failed: {e}"

    # ---- tab management ----

    def list_tabs(self) -> list[dict]:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_list_tabs())

    async def _async_list_tabs(self) -> list[dict]:
        if not self.context:
            return []
        tabs = []
        for idx, p in enumerate(self.context.pages):
            try:
                title = await p.title()
                tabs.append({"index": idx, "url": p.url, "title": title})
            except Exception:
                tabs.append({"index": idx, "url": p.url, "title": ""})
        return tabs

    def new_tab(self, url: str = "") -> str:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_new_tab(url))

    async def _async_new_tab(self, url: str = "") -> str:
        if not self.context:
            return "Error: No active browser context."
        try:
            page = await self.context.new_page()
            self.page = page
            if url:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return f"Successfully opened new tab. Active URL: {self.page.url}"
        except Exception as e:
            return f"Error: Failed to open new tab: {e}"

    def close_tab(self, index: int = -1) -> str:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_close_tab(index))

    async def _async_close_tab(self, index: int = -1) -> str:
        if not self.context or not self.context.pages:
            return "Error: No active browser pages."
        try:
            pages = self.context.pages
            if index >= len(pages) or index < -len(pages):
                return f"Error: Invalid tab index {index}. Total tabs: {len(pages)}"
            
            target_page = pages[index]
            await target_page.close()
            
            # Update active page reference
            remaining = self.context.pages
            self.page = remaining[-1] if remaining else None
            return f"Tab closed. Active URL: {self.page.url if self.page else 'none'}"
        except Exception as e:
            return f"Error: Close tab failed: {e}"

    def switch_tab(self, index: int) -> str:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_switch_tab(index))

    async def _async_switch_tab(self, index: int) -> str:
        if not self.context or not self.context.pages:
            return "Error: No active browser context."
        pages = self.context.pages
        if index >= len(pages) or index < 0:
            return f"Error: Index out of bounds. Open tabs count: {len(pages)}"
        self.page = pages[index]
        return f"Switched to tab {index} | URL: {self.page.url} | Title: '{await self.page.title()}'"

    # ---- screenshot and vision read ----

    def screenshot(self, output_name: str = "screenshot.png") -> str:
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_screenshot(output_name))

    async def _async_screenshot(self, output_name: str = "screenshot.png") -> str:
        if not self.page:
            return "Error: No active browser session. Open a URL first."

        if not output_name.lower().endswith((".png", ".jpg", ".jpeg")):
            output_name += ".png"

        filepath = self.screenshots_dir / output_name
        try:
            await self.page.screenshot(path=str(filepath))
            file_size_kb = os.path.getsize(filepath) / 1024
            viewport = self.page.viewport_size or {"width": "unknown", "height": "unknown"}
            return (
                f"Screenshot successfully saved to '{filepath.name}' "
                f"({viewport['width']}x{viewport['height']}, size: {file_size_kb:.1f} KB). "
                f"File path: {filepath.as_uri()}"
            )
        except Exception as e:
            return f"Error: Screenshot capture failed: {e}"

    def vision_read(self, question: str) -> str:
        """Visual page query: screenshots viewport, scales to 1280x720, queries Gemini Multimodal."""
        self._ensure_session(headless=self.headless)
        return self.thread.run_coro(self._async_vision_read(question))

    async def _async_vision_read(self, question: str) -> str:
        if not self.page:
            return "Error: No active browser session."

        try:
            png_bytes = await self.page.screenshot(full_page=False)
            
            # Scale down image using PIL to save tokens & latency
            if _PIL:
                img = PIL.Image.open(io.BytesIO(png_bytes)).convert("RGB")
                img.thumbnail([1280, 720], PIL.Image.Resampling.BILINEAR)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=60)
                image_bytes = buf.getvalue()
                mime_type = "image/jpeg"
            else:
                image_bytes = png_bytes
                mime_type = "image/png"

            client = get_gemini_client()
            if not client:
                return "Error: Gemini client not initialized. Cannot run vision query."

            from google.genai import types
            response = client.models.generate_content(
                model=settings.ai.gemini_model,
                contents=types.Content(role="user", parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    types.Part.from_text(text=question)
                ])
            )
            return response.text.strip() if response.text else "Observation: Gemini returned empty vision response."
        except Exception as e:
            return f"Error: Vision reading failed: {e}"


# Singleton instance getter
_browser_agent_inst = None

def get_browser_agent() -> BrowserAgent:
    global _browser_agent_inst
    if _browser_agent_inst is None:
        _browser_agent_inst = BrowserAgent()
    return _browser_agent_inst
