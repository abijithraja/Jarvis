"""
Jarvis Browser Engine — powered by Playwright
The single browser instance Jarvis reuses across all tasks.

FEATURES:
  - Persistent login sessions (saved to disk, survives restarts)
  - Stealth mode (looks like a real human browser)
  - Auto-waiting (no sleep() needed)
  - Multi-tab support
  - Screenshot & PDF capture
  - Network interception
  - Console log capture
  - File download handling
  - Cookie management
  - JavaScript execution

INSTALL:
  pip install playwright
  playwright install chromium
"""

import asyncio
import os
import json
import time
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
SESSION_DIR   = BASE_DIR / "sessions"
DOWNLOAD_DIR  = BASE_DIR / "downloads"
SCREENSHOT_DIR= BASE_DIR / "screenshots"

for d in [SESSION_DIR, DOWNLOAD_DIR, SCREENSHOT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_SESSION = str(SESSION_DIR / "default")

# ── Browser singleton ─────────────────────────────────────────────────────────

_browser      = None
_context      = None
_page         = None
_playwright   = None
_loop         = None


def _get_or_create_loop():
    global _loop
    try:
        _loop = asyncio.get_event_loop()
        if _loop.is_closed():
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
    except RuntimeError:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = _get_or_create_loop()
    return loop.run_until_complete(coro)


async def _launch_browser(headless: bool = False, session: str = DEFAULT_SESSION):
    """Launch Playwright browser with persistent context (saved login state)."""
    global _browser, _context, _page, _playwright
    from playwright.async_api import async_playwright

    _playwright = await async_playwright().start()

    # Persistent context = saved cookies/localStorage between runs
    _context = await _playwright.chromium.launch_persistent_context(
        user_data_dir=session,
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",  # stealth
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--start-maximized",
        ],
        ignore_https_errors=True,
        downloads_path=str(DOWNLOAD_DIR),
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )

    # Inject stealth JS to bypass bot detection
    await _context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
        window.chrome = {runtime: {}};
    """)

    pages = _context.pages
    _page = pages[0] if pages else await _context.new_page()
    return _page


def get_page(headless: bool = False):
    """Get the current browser page, launching if needed."""
    global _page
    if _page is None:
        _run(_launch_browser(headless=headless))
    return _page


async def _ensure_page(headless: bool = False):
    global _page
    if _page is None:
        await _launch_browser(headless=headless)
    return _page


# ── Navigation ────────────────────────────────────────────────────────────────

def goto(url: str, wait_until: str = "domcontentloaded") -> str:
    """Navigate to a URL."""
    async def _go():
        page = await _ensure_page()
        if not url.startswith("http"):
            full_url = "https://" + url
        else:
            full_url = url
        await page.goto(full_url, wait_until=wait_until, timeout=30000)
        return f"Navigated to {page.url}"
    return _run(_go())


def go_back() -> str:
    async def _back():
        page = await _ensure_page()
        await page.go_back()
        return f"Went back to {page.url}"
    return _run(_back())


def go_forward() -> str:
    async def _fwd():
        page = await _ensure_page()
        await page.go_forward()
        return f"Went forward to {page.url}"
    return _run(_fwd())


def refresh() -> str:
    async def _reload():
        page = await _ensure_page()
        await page.reload()
        return "Page refreshed."
    return _run(_reload())


def get_current_url() -> str:
    async def _url():
        page = await _ensure_page()
        return page.url
    return _run(_url())


def get_page_title() -> str:
    async def _title():
        page = await _ensure_page()
        return await page.title()
    return _run(_title())


# ── Interaction ───────────────────────────────────────────────────────────────

def click(selector: str) -> str:
    """Click an element by CSS selector, text, or role."""
    async def _click():
        page = await _ensure_page()
        try:
            await page.click(selector, timeout=8000)
            return f"Clicked: {selector}"
        except Exception:
            # Try by text
            try:
                await page.get_by_text(selector).first.click(timeout=5000)
                return f"Clicked text: {selector}"
            except Exception as e:
                return f"Could not click '{selector}': {e}"
    return _run(_click())


def type_text(selector: str, text: str, clear_first: bool = True) -> str:
    """Type text into an input field."""
    async def _type():
        page = await _ensure_page()
        try:
            if clear_first:
                await page.fill(selector, text, timeout=8000)
            else:
                await page.type(selector, text, delay=50)
            return f"Typed '{text}' into {selector}"
        except Exception as e:
            return f"Type failed: {e}"
    return _run(_type())


def press_key(key: str) -> str:
    """Press a keyboard key (Enter, Tab, Escape, ArrowDown, etc.)."""
    async def _press():
        page = await _ensure_page()
        await page.keyboard.press(key)
        return f"Pressed {key}."
    return _run(_press())


def scroll(direction: str = "down", amount: int = 500) -> str:
    """Scroll the page."""
    async def _scroll():
        page = await _ensure_page()
        y = amount if direction == "down" else -amount
        x = amount if direction == "right" else (-amount if direction == "left" else 0)
        await page.mouse.wheel(x if direction in ("left","right") else 0, y)
        return f"Scrolled {direction}."
    return _run(_scroll())


def scroll_to_bottom() -> str:
    async def _s():
        page = await _ensure_page()
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        return "Scrolled to bottom."
    return _run(_s())


def hover(selector: str) -> str:
    async def _hover():
        page = await _ensure_page()
        await page.hover(selector, timeout=5000)
        return f"Hovered over {selector}."
    return _run(_hover())


def select_option(selector: str, value: str) -> str:
    """Select a dropdown option by value or label."""
    async def _select():
        page = await _ensure_page()
        try:
            await page.select_option(selector, value=value, timeout=5000)
            return f"Selected '{value}' in {selector}."
        except Exception:
            try:
                await page.select_option(selector, label=value, timeout=5000)
                return f"Selected '{value}' in {selector}."
            except Exception as e:
                return f"Select failed: {e}"
    return _run(_select())


def upload_file(selector: str, file_path: str) -> str:
    async def _upload():
        page = await _ensure_page()
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        await page.set_input_files(selector, file_path)
        return f"Uploaded {file_path}."
    return _run(_upload())


# ── Reading ───────────────────────────────────────────────────────────────────

def get_text(selector: str = "body") -> str:
    """Get visible text from an element."""
    async def _text():
        page = await _ensure_page()
        try:
            el = page.locator(selector).first
            text = await el.inner_text(timeout=5000)
            return text.strip()[:2000]
        except Exception as e:
            return f"Could not read text: {e}"
    return _run(_text())


def get_full_page_text() -> str:
    """Get all visible text on the page."""
    async def _text():
        page = await _ensure_page()
        text = await page.inner_text("body")
        # Clean up excessive whitespace
        import re
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text[:3000]
    return _run(_text())


def get_all_links() -> list[str]:
    """Get all hyperlinks on the current page."""
    async def _links():
        page = await _ensure_page()
        hrefs = await page.evaluate("""
            Array.from(document.querySelectorAll('a[href]'))
                 .map(a => ({text: a.innerText.trim(), href: a.href}))
                 .filter(a => a.href.startswith('http'))
                 .slice(0, 30)
        """)
        return hrefs
    return _run(_links())


def find_text_on_page(query: str) -> str:
    """Search for text on the current page."""
    text = get_full_page_text()
    import re
    lower_text = text.lower()
    lower_q = query.lower()
    if lower_q in lower_text:
        idx = lower_text.find(lower_q)
        context = text[max(0, idx-100):idx+200]
        return f"Found '{query}': ...{context}..."
    return f"'{query}' not found on this page."


def get_element_attribute(selector: str, attr: str) -> str:
    async def _attr():
        page = await _ensure_page()
        try:
            val = await page.get_attribute(selector, attr, timeout=5000)
            return val or f"Attribute '{attr}' not found."
        except Exception as e:
            return f"Error: {e}"
    return _run(_attr())


# ── Search ────────────────────────────────────────────────────────────────────

def google_search(query: str) -> str:
    """Search Google and return top results."""
    async def _search():
        page = await _ensure_page()
        await page.goto(f"https://www.google.com/search?q={query.replace(' ', '+')}", timeout=20000)
        await page.wait_for_load_state("domcontentloaded")

        # Extract result titles + snippets
        results = await page.evaluate("""
            Array.from(document.querySelectorAll('h3')).slice(0,5).map(h => ({
                title: h.innerText,
                href: h.closest('a')?.href || ''
            })).filter(r => r.title)
        """)

        if not results:
            return "No results found."

        lines = [f"{i+1}. {r['title']}" for i, r in enumerate(results)]
        return "Google results:\n" + "\n".join(lines)
    return _run(_search())


# ── Tabs ──────────────────────────────────────────────────────────────────────

def new_tab(url: str = "") -> str:
    async def _tab():
        page = await _ensure_page()
        new = await _context.new_page()
        global _page
        _page = new
        if url:
            await new.goto(url if url.startswith("http") else "https://" + url)
        return f"Opened new tab{' at ' + url if url else ''}."
    return _run(_tab())


def list_tabs() -> str:
    async def _tabs():
        await _ensure_page()
        pages = _context.pages
        lines = [f"  {i+1}. {await p.title()} — {p.url}" for i, p in enumerate(pages)]
        return f"Open tabs ({len(pages)}):\n" + "\n".join(lines)
    return _run(_tabs())


def switch_tab(index: int) -> str:
    async def _switch():
        global _page
        pages = _context.pages
        if 0 <= index - 1 < len(pages):
            _page = pages[index - 1]
            await _page.bring_to_front()
            return f"Switched to tab {index}: {await _page.title()}"
        return f"Tab {index} does not exist."
    return _run(_switch())


def close_tab() -> str:
    async def _close():
        global _page
        page = await _ensure_page()
        await page.close()
        pages = _context.pages
        if pages:
            _page = pages[-1]
            return f"Closed tab. Now on: {await _page.title()}"
        _page = None
        return "Closed last tab."
    return _run(_close())


# ── Screenshot & PDF ─────────────────────────────────────────────────────────

def screenshot(filename: str = "") -> str:
    async def _shot():
        page = await _ensure_page()
        if not filename:
            name = f"screenshot_{int(time.time())}.png"
        else:
            name = filename if filename.endswith(".png") else filename + ".png"
        path = str(SCREENSHOT_DIR / name)
        await page.screenshot(path=path, full_page=False)
        return f"Screenshot saved: {path}"
    return _run(_shot())


def full_page_screenshot(filename: str = "") -> str:
    async def _shot():
        page = await _ensure_page()
        name = filename or f"fullpage_{int(time.time())}.png"
        path = str(SCREENSHOT_DIR / name)
        await page.screenshot(path=path, full_page=True)
        return f"Full-page screenshot saved: {path}"
    return _run(_shot())


def save_as_pdf(filename: str = "") -> str:
    async def _pdf():
        page = await _ensure_page()
        name = filename or f"page_{int(time.time())}.pdf"
        path = str(DOWNLOAD_DIR / name)
        await page.pdf(path=path)
        return f"PDF saved: {path}"
    return _run(_pdf())


# ── JavaScript ────────────────────────────────────────────────────────────────

def run_js(script: str) -> str:
    async def _js():
        page = await _ensure_page()
        result = await page.evaluate(script)
        return str(result)
    return _run(_js())


def highlight_element(selector: str) -> str:
    """Visually highlight an element on the page."""
    script = f"""
        const el = document.querySelector('{selector}');
        if(el) {{
            el.style.outline = '3px solid red';
            el.style.backgroundColor = 'rgba(255,0,0,0.1)';
        }}
    """
    return run_js(script)


# ── Forms ─────────────────────────────────────────────────────────────────────

def fill_form(fields: dict[str, str]) -> str:
    """Fill multiple form fields. fields = {selector: value}"""
    results = []
    for selector, value in fields.items():
        result = type_text(selector, value)
        results.append(result)
    return "\n".join(results)


# ── Cookies & Storage ────────────────────────────────────────────────────────

def get_cookies() -> str:
    async def _cookies():
        page = await _ensure_page()
        cookies = await _context.cookies()
        lines = [f"  {c['name']}={c['value'][:20]}..." for c in cookies[:10]]
        return f"Cookies ({len(cookies)}):\n" + "\n".join(lines)
    return _run(_cookies())


def save_session(name: str = "default") -> str:
    async def _save():
        path = str(SESSION_DIR / f"{name}_state.json")
        await _context.storage_state(path=path)
        return f"Session saved to {path}"
    return _run(_save())


def load_session(name: str = "default") -> str:
    path = SESSION_DIR / f"{name}_state.json"
    if not path.exists():
        return f"No saved session named '{name}'."
    # Session is auto-loaded via persistent context
    return f"Session '{name}' will be loaded on next browser launch."


# ── Network monitoring ────────────────────────────────────────────────────────

_network_log = []

def start_network_monitor() -> str:
    async def _monitor():
        page = await _ensure_page()
        page.on("request", lambda req: _network_log.append({
            "type": "request",
            "method": req.method,
            "url": req.url
        }))
        page.on("response", lambda res: _network_log.append({
            "type": "response",
            "status": res.status,
            "url": res.url
        }))
        return "Network monitor started."
    return _run(_monitor())


def get_network_log(last_n: int = 10) -> str:
    recent = _network_log[-last_n:]
    if not recent:
        return "No network activity recorded."
    lines = [f"  [{e['type'].upper()}] {e.get('method','')} {e['url'][:80]}" for e in recent]
    return "Network log:\n" + "\n".join(lines)


# ── Close ─────────────────────────────────────────────────────────────────────

def close_browser() -> str:
    global _browser, _context, _page, _playwright
    async def _close():
        if _context:
            await _context.close()
        if _playwright:
            await _playwright.stop()
    _run(_close())
    _browser = _context = _page = _playwright = None
    return "Browser closed."
