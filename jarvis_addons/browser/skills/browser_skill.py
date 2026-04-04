"""
Browser Voice Skill
Parses natural voice commands and maps them to browser_engine actions.

ALL SUPPORTED COMMANDS:

Navigation:
  "open google.com"
  "go to youtube"
  "go back"
  "go forward"
  "refresh the page"
  "what page am I on"
  "what is the title"

Interaction:
  "click the login button"
  "click sign in"
  "type hello world in the search box"
  "press enter"
  "press escape"
  "scroll down"
  "scroll to the bottom"
  "hover over the menu"
  "select option English from the dropdown"
  "upload file report.pdf"

Reading:
  "read the page"
  "read the main content"
  "find Python on this page"
  "get all links"
  "what does it say about pricing"

Search:
  "search for python tutorials on google"
  "google machine learning basics"
  "search youtube for lofi music"

Tabs:
  "open new tab"
  "open new tab at github.com"
  "show all tabs"
  "switch to tab 2"
  "close this tab"

Screenshot:
  "take a screenshot"
  "save full page screenshot"
  "save page as PDF"

JavaScript:
  "run javascript document.title"
  "highlight the submit button"

Forms:
  "fill in the username field with admin"
  "fill the password field with mypassword"
  "submit the form"

Network:
  "start network monitor"
  "show network log"

Browser:
  "close the browser"
  "save session"
  "show cookies"
"""

import re
from jarvis_addons.browser.core.browser_engine import (
    goto, go_back, go_forward, refresh,
    get_current_url, get_page_title,
    click, type_text, press_key, scroll, scroll_to_bottom,
    hover, select_option, upload_file,
    get_text, get_full_page_text, get_all_links, find_text_on_page,
    google_search, new_tab, list_tabs, switch_tab, close_tab,
    screenshot, full_page_screenshot, save_as_pdf,
    run_js, highlight_element, fill_form,
    get_cookies, save_session,
    start_network_monitor, get_network_log,
    close_browser,
)

# ── Trigger detection ─────────────────────────────────────────────────────────

BROWSER_TRIGGERS = [
    "open", "go to", "navigate to", "visit", "browse",
    "click", "type", "press", "scroll", "hover",
    "read the page", "read page", "read this", "what does it say",
    "find on page", "find on this page", "search on page",
    "get all links", "list links",
    "google", "search for", "search youtube",
    "new tab", "open tab", "switch to tab", "close tab", "show tabs", "show all tabs",
    "take a screenshot", "screenshot", "save pdf", "save page",
    "run javascript", "highlight",
    "fill", "submit the form",
    "network log", "network monitor",
    "close the browser", "close browser",
    "go back", "go forward", "refresh",
    "current url", "what page", "page title",
    "upload file", "select option",
    "save session", "show cookies",
]


def is_browser_command(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in BROWSER_TRIGGERS)


def handle_browser_command(text: str) -> str | None:
    if not is_browser_command(text):
        return None
    return _parse(text)


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse(text: str) -> str:
    lower = text.lower().strip()

    # ── Tabs (must run before generic "open <target>") ─────────────────────

    m = re.search(r"open\s+(?:a\s+)?new\s+tab\s*(?:at|on|with)?\s*(.+)?", lower)
    if m:
        url = (m.group(1) or "").strip()
        return new_tab(url)

    if any(p in lower for p in ["show all tabs", "list tabs", "show tabs", "what tabs"]):
        return list_tabs()

    m = re.search(r"switch\s+to\s+tab\s+(\d+)", lower)
    if m:
        return switch_tab(int(m.group(1)))

    if any(p in lower for p in ["close this tab", "close tab", "close current tab"]):
        return close_tab()

    # ── Navigation ────────────────────────────────────────────────────────────

    # "go to / open / navigate to / visit <url>"
    m = re.search(
        r"(?:open|go to|navigate to|visit|browse to|take me to)\s+(.+)",
        lower
    )
    if m:
        target = m.group(1).strip().rstrip(".")

        # Delegate to tab logic if utterance is phrased like "open new tab ...".
        if target.startswith("new tab"):
            tab_target = re.sub(r"^new\s+tab\s*(?:at|on|with)?\s*", "", target).strip()
            return new_tab(tab_target)

        # Map common spoken names to URLs
        url_map = {
            "google":    "https://www.google.com",
            "youtube":   "https://www.youtube.com",
            "github":    "https://www.github.com",
            "facebook":  "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "twitter":   "https://www.twitter.com",
            "reddit":    "https://www.reddit.com",
            "wikipedia": "https://www.wikipedia.org",
            "amazon":    "https://www.amazon.in",
            "netflix":   "https://www.netflix.com",
            "gmail":     "https://mail.google.com",
            "maps":      "https://maps.google.com",
            "news":      "https://news.google.com",
        }
        url = url_map.get(target, target)
        if not url.startswith("http"):
            url = "https://" + url
        try:
            return goto(url)
        except Exception as e:
            return f"Could not open browser target '{target}': {e}"

    if any(p in lower for p in ["go back", "previous page", "back"]):
        return go_back()

    if any(p in lower for p in ["go forward", "next page", "forward"]):
        return go_forward()

    if any(p in lower for p in ["refresh", "reload", "reload the page", "refresh the page"]):
        return refresh()

    if any(p in lower for p in ["current url", "what url", "what page am i on", "what site"]):
        return f"Current URL: {get_current_url()}"

    if any(p in lower for p in ["page title", "what is the title", "what's the title"]):
        return f"Page title: {get_page_title()}"

    # ── Search ────────────────────────────────────────────────────────────────

    # "search for X on google" / "google X"
    m = re.search(r"(?:search(?:\s+for)?|google)\s+(.+?)(?:\s+on\s+google)?$", lower)
    if m and "on page" not in lower and "on this page" not in lower:
        query = m.group(1).strip()
        # YouTube search
        if "youtube" in lower:
            return goto(f"https://www.youtube.com/results?search_query={query.replace(' ','+')}")
        return google_search(query)

    # ── Click ─────────────────────────────────────────────────────────────────

    m = re.search(r"click\s+(?:on\s+)?(?:the\s+)?(.+)", lower)
    if m:
        target = m.group(1).strip().rstrip(".")
        # Try common element names → CSS selectors
        selector_map = {
            "search box":     'input[type="search"], input[name="q"], input[placeholder*="search" i]',
            "search bar":     'input[type="search"], input[name="q"]',
            "login button":   'button:has-text("Login"), button:has-text("Sign in"), a:has-text("Login")',
            "sign in":        'button:has-text("Sign in"), a:has-text("Sign in")',
            "sign up":        'button:has-text("Sign up"), a:has-text("Sign up")',
            "submit button":  'button[type="submit"], input[type="submit"]',
            "next button":    'button:has-text("Next"), a:has-text("Next")',
            "close button":   'button:has-text("Close"), button[aria-label="Close"]',
            "accept":         'button:has-text("Accept"), button:has-text("OK")',
        }
        selector = selector_map.get(target, target)
        return click(selector)

    # ── Type ─────────────────────────────────────────────────────────────────

    # "type <text> in the <field>"
    m = re.search(r"type\s+(.+?)\s+in(?:to)?\s+(?:the\s+)?(.+)", lower)
    if m:
        text_to_type = m.group(1).strip()
        field = m.group(2).strip()
        selector_map = {
            "search box":  'input[type="search"], input[name="q"]',
            "username":    'input[name="username"], input[name="email"], input[id*="user"]',
            "password":    'input[type="password"]',
            "email field": 'input[type="email"]',
            "address bar": 'input[type="url"]',
        }
        selector = selector_map.get(field, f'input[placeholder*="{field}" i], input[name*="{field}" i]')
        return type_text(selector, text_to_type)

    # "fill in the <field> with <value>"
    m = re.search(r"fill\s+(?:in\s+)?(?:the\s+)?(.+?)\s+(?:field\s+)?with\s+(.+)", lower)
    if m:
        field = m.group(1).strip()
        value = m.group(2).strip()
        selector = f'input[name*="{field}" i], input[placeholder*="{field}" i], input[id*="{field}" i]'
        return type_text(selector, value)

    # ── Press ─────────────────────────────────────────────────────────────────

    m = re.search(r"press\s+(.+)", lower)
    if m:
        key_name = m.group(1).strip()
        key_map = {
            "enter": "Enter", "escape": "Escape", "esc": "Escape",
            "tab": "Tab", "space": "Space", "backspace": "Backspace",
            "delete": "Delete", "up": "ArrowUp", "down": "ArrowDown",
            "left": "ArrowLeft", "right": "ArrowRight",
            "home": "Home", "end": "End", "f5": "F5",
        }
        key = key_map.get(key_name.lower(), key_name.capitalize())
        return press_key(key)

    # ── Scroll ────────────────────────────────────────────────────────────────

    if "scroll to the bottom" in lower or "scroll all the way down" in lower:
        return scroll_to_bottom()

    m = re.search(r"scroll\s+(down|up|left|right)(?:\s+(\d+))?", lower)
    if m:
        direction = m.group(1)
        amount = int(m.group(2)) * 100 if m.group(2) else 500
        return scroll(direction, amount)

    # ── Hover ─────────────────────────────────────────────────────────────────

    m = re.search(r"hover\s+(?:over\s+)?(?:the\s+)?(.+)", lower)
    if m:
        target = m.group(1).strip()
        return hover(target)

    # ── Select ────────────────────────────────────────────────────────────────

    m = re.search(r"select\s+(?:option\s+)?(.+?)\s+from\s+(?:the\s+)?(.+?)(?:\s+dropdown)?$", lower)
    if m:
        value = m.group(1).strip()
        field = m.group(2).strip()
        selector = f'select[name*="{field}" i], select[id*="{field}" i]'
        return select_option(selector, value)

    # ── Upload ────────────────────────────────────────────────────────────────

    m = re.search(r"upload\s+(?:file\s+)?(.+)", lower)
    if m:
        file_path = m.group(1).strip()
        return upload_file('input[type="file"]', file_path)

    # ── Read ──────────────────────────────────────────────────────────────────

    if any(p in lower for p in ["read the page", "read page", "read this page", "read the content"]):
        text = get_full_page_text()
        return text[:800] if len(text) > 800 else text

    if any(p in lower for p in ["read the main", "read main content", "what does it say"]):
        text = get_text("main, article, .content, .main, body")
        return text[:600] if len(text) > 600 else text

    m = re.search(r"find\s+(.+?)\s+on\s+(?:this\s+)?page", lower)
    if m:
        return find_text_on_page(m.group(1).strip())

    if any(p in lower for p in ["get all links", "list all links", "show links", "all links on page"]):
        links = get_all_links()
        if isinstance(links, list):
            lines = [f"  {l['text']}: {l['href']}" for l in links[:15] if l.get('text')]
            return "Links on page:\n" + "\n".join(lines)
        return str(links)

    # ── Screenshot ────────────────────────────────────────────────────────────

    if any(p in lower for p in ["take a screenshot", "take screenshot", "screenshot"]):
        m = re.search(r"(?:save|name it|called)\s+(.+?)(?:\s|$)", lower)
        name = m.group(1).strip() if m else ""
        if "full" in lower:
            return full_page_screenshot(name)
        return screenshot(name)

    if any(p in lower for p in ["save as pdf", "save page as pdf", "export pdf"]):
        return save_as_pdf()

    # ── JavaScript ────────────────────────────────────────────────────────────

    m = re.search(r"run\s+javascript\s+(.+)", lower)
    if m:
        return run_js(m.group(1).strip())

    m = re.search(r"highlight\s+(?:the\s+)?(.+)", lower)
    if m:
        return highlight_element(m.group(1).strip())

    # ── Form submit ───────────────────────────────────────────────────────────

    if "submit the form" in lower or "submit form" in lower:
        return press_key("Enter")

    # ── Network ───────────────────────────────────────────────────────────────

    if "start network monitor" in lower:
        return start_network_monitor()

    if any(p in lower for p in ["show network log", "network log", "network activity"]):
        return get_network_log()

    # ── Session ───────────────────────────────────────────────────────────────

    m = re.search(r"save session(?:\s+as\s+)?(.+)?", lower)
    if m:
        name = (m.group(1) or "default").strip()
        return save_session(name)

    if "show cookies" in lower or "list cookies" in lower:
        return get_cookies()

    # ── Close ─────────────────────────────────────────────────────────────────

    if any(p in lower for p in ["close the browser", "close browser", "quit browser"]):
        return close_browser()

    return None
