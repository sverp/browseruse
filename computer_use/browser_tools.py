"""
Playwright Browser Tools for Autonomous Computer Use.
Exposes atomic browser automation actions as callable functions.
"""

import os
import time
import threading
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, BrowserContext, Page

DEFAULT_PROFILE = os.path.expanduser("~/.cache/playwright_ff_profile")


class PlaywrightController:
    """Manages persistent browser sessions and provides discrete tool methods."""

    def __init__(self, profile_dir: str = DEFAULT_PROFILE, headless: bool = True):
        self.profile_dir = profile_dir
        self.headless = headless
        self._playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def _load_firefox_cookies(self) -> list:
        """Reads and formats cookies from user's active Firefox profile safely via sqlite3."""
        import tempfile, shutil, sqlite3
        src = "/home/sverp/.mozilla/firefox/ldhzjtyx.default-release/cookies.sqlite"
        if not os.path.exists(src):
            return []
        cookies_list = []
        try:
            with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
                shutil.copy2(src, tmp.name)
                conn = sqlite3.connect(tmp.name)
                c = conn.cursor()
                c.execute("""
                    SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite
                    FROM moz_cookies
                """)
                for row in c.fetchall():
                    same_site_map = {0: "None", 1: "Lax", 2: "Strict"}
                    exp_val = row[4]
                    if exp_val and exp_val > 0:
                        if exp_val > 1000000000000:
                            exp_sec = int(exp_val / 1000000) if exp_val > 10000000000000 else int(exp_val / 1000)
                        else:
                            exp_sec = int(exp_val)
                    else:
                        exp_sec = -1

                    same_site = same_site_map.get(row[7], "None")
                    is_secure = bool(row[5])
                    if same_site == "None" and not is_secure:
                        same_site = "Lax"

                    host = row[2] or ""
                    if not host:
                        continue

                    cookie = {
                        "name": row[0],
                        "value": row[1],
                        "domain": host,
                        "path": row[3] or "/",
                        "expires": exp_sec,
                        "secure": is_secure,
                        "httpOnly": bool(row[6]),
                        "sameSite": same_site,
                    }
                    cookies_list.append(cookie)
                conn.close()
        except Exception as e:
            print(f"[Cookie Sync Warning] {e}")
        return cookies_list

    def start(self) -> None:
        """Starts Playwright with India locale context and auto-injects user Firefox cookies."""
        if not self._playwright:
            self._playwright = sync_playwright().start()

        if not self.context or not hasattr(self, "_browser") or not self._browser:
            self._browser = self._playwright.firefox.launch(headless=self.headless)
            self.context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                geolocation={"latitude": 28.6139, "longitude": 77.2090},
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )

            cookies = self._load_firefox_cookies()
            if cookies:
                try:
                    self.context.add_cookies(cookies)
                except Exception:
                    for ck in cookies:
                        try:
                            self.context.add_cookies([ck])
                        except Exception:
                            pass

            self.page = self.context.new_page()
        elif not self.page or self.page.is_closed():
            self.page = self.context.new_page()

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigates to a specific URL ensuring India localization and returns page title and status."""
        self.start()
        if "gl=us" in url or "gl=eu" in url:
            url = url.replace("gl=us", "gl=in").replace("gl=eu", "gl=in")
        if "hl=en-US" in url:
            url = url.replace("hl=en-US", "hl=en-IN")

        self.page.goto(url, wait_until="load")
        self.page.wait_for_timeout(3000)
        return {
            "status": "success",
            "url": self.page.url,
            "title": self.page.title(),
        }

    def click(self, selector: str) -> Dict[str, Any]:
        """Clicks an element matching a CSS or text selector."""
        self.start()
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=8000)
        locator.click()
        self.page.wait_for_timeout(1500)
        return {"status": "success", "clicked": selector}

    def double_click(self, selector: str) -> Dict[str, Any]:
        """Double clicks an element (e.g. to like an Instagram post or image)."""
        self.start()
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=8000)
        locator.dblclick()
        self.page.wait_for_timeout(1000)
        return {"status": "success", "double_clicked": selector}

    def type_text(self, selector: str, text: str, press_enter: bool = False) -> Dict[str, Any]:
        """Types text into an input element and optionally presses Enter."""
        self.start()
        locator = self.page.locator(selector).first
        locator.wait_for(state="visible", timeout=8000)
        locator.fill(text)
        if press_enter:
            locator.press("Enter")
        self.page.wait_for_timeout(1500)
        return {"status": "success", "typed": text}

    def press_key(self, key: str) -> Dict[str, Any]:
        """Presses a keyboard key (e.g. ArrowDown, PageDown, j, k, l, Space, Escape)."""
        self.start()
        self.page.keyboard.press(key)
        self.page.wait_for_timeout(1000)
        return {"status": "success", "pressed_key": key}

    def scroll(self, delta_y: int = 600) -> Dict[str, Any]:
        """Scrolls the page vertically by delta_y pixels (positive=down, negative=up)."""
        self.start()
        self.page.mouse.wheel(0, delta_y)
        self.page.wait_for_timeout(1500)
        return {"status": "success", "scrolled_by": delta_y}

    def wait(self, seconds: float = 2.0) -> Dict[str, Any]:
        """Pauses execution for a specified duration in seconds."""
        self.start()
        self.page.wait_for_timeout(int(seconds * 1000))
        return {"status": "success", "waited_seconds": seconds}

    def capture_screenshot(self, output_path: str = "current_screen.png") -> Dict[str, Any]:
        """Captures a screenshot of the current page viewport."""
        self.start()
        full_path = os.path.abspath(output_path)
        self.page.screenshot(path=full_path)
        return {"status": "success", "screenshot_path": full_path}

    def get_page_summary(self) -> Dict[str, Any]:
        """Extracts current page URL, title, and key text snippets for context."""
        self.start()
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=4000)
        except Exception:
            pass

        text = self.page.locator("body").inner_text()
        if len(text.strip()) < 50:
            self.page.wait_for_timeout(1000)
            text = self.page.locator("body").inner_text()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)
        return {
            "status": "success",
            "url": self.page.url,
            "title": self.page.title(),
            "visible_text_snippet": cleaned_text[:1200],
        }

    def send_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Composes and sends an email via Gmail using the logged-in session."""
        self.start()
        # Navigate to Gmail inbox if not already there
        if "mail.google.com" not in self.page.url:
            self.page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="load")
            self.page.wait_for_timeout(3000)

        compose_btn = self.page.locator('div[role="button"]:has-text("Compose"), div[gh="cm"]').first
        compose_btn.wait_for(state="visible", timeout=12000)
        compose_btn.click()
        self.page.wait_for_timeout(1500)

        to_field = self.page.locator('input[aria-label="To recipients"], input[peoplekit-id], textarea[name="to"]').first
        to_field.wait_for(state="visible", timeout=8000)
        to_field.fill(recipient)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(500)

        subject_field = self.page.locator('input[name="subjectbox"]').first
        subject_field.wait_for(state="visible", timeout=8000)
        subject_field.fill(subject)
        self.page.wait_for_timeout(500)

        body_field = self.page.locator('div[aria-label="Message Body"], div[role="textbox"]').first
        body_field.wait_for(state="visible", timeout=8000)
        body_field.fill(body)
        self.page.wait_for_timeout(500)

        try:
            send_btn = self.page.locator('div[role="button"]:text-is("Send"), div[role="button"][data-tooltip^="Send "]').first
            if send_btn.is_visible():
                send_btn.click()
            else:
                self.page.keyboard.press("Control+Enter")
        except Exception:
            self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(3000)

        return {
            "status": "success",
            "sent_to": recipient,
            "subject": subject,
            "message": "Email sent successfully",
        }

    def close(self) -> None:
        """Closes browser context and shuts down Playwright."""
        try:
            if self.page and not self.page.is_closed():
                self.page.close()
        except Exception:
            pass
        self.page = None

        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
        if hasattr(self, "_browser") and self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None


_thread_local = threading.local()


def get_browser_controller() -> PlaywrightController:
    """Returns the PlaywrightController dedicated to the current thread."""
    if not hasattr(_thread_local, "controller") or _thread_local.controller is None:
        _thread_local.controller = PlaywrightController()
    return _thread_local.controller


class _BrowserToolProxy:
    """Dynamic proxy directing attribute access to current thread's PlaywrightController."""

    def __getattr__(self, name: str):
        return getattr(get_browser_controller(), name)

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            setattr(get_browser_controller(), name, value)


browser_tool = _BrowserToolProxy()


def navigate(url: str) -> Dict[str, Any]:
    return get_browser_controller().navigate(url)


def click(selector: str) -> Dict[str, Any]:
    return get_browser_controller().click(selector)


def double_click(selector: str) -> Dict[str, Any]:
    return get_browser_controller().double_click(selector)


def type_text(selector: str, text: str, press_enter: bool = False) -> Dict[str, Any]:
    return get_browser_controller().type_text(selector, text, press_enter)


def press_key(key: str) -> Dict[str, Any]:
    return get_browser_controller().press_key(key)


def scroll(delta_y: int = 600) -> Dict[str, Any]:
    return get_browser_controller().scroll(delta_y)


def wait(seconds: float = 2.0) -> Dict[str, Any]:
    return get_browser_controller().wait(seconds)


def capture_screenshot(output_path: str = "current_screen.png") -> Dict[str, Any]:
    return get_browser_controller().capture_screenshot(output_path)


def get_page_summary() -> Dict[str, Any]:
    return get_browser_controller().get_page_summary()


def send_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    return get_browser_controller().send_email(recipient, subject, body)


def close() -> None:
    """Closes and releases the browser session for the current thread."""
    ctrl = getattr(_thread_local, "controller", None)
    if ctrl:
        ctrl.close()
        _thread_local.controller = None
