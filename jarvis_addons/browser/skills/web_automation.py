"""
Browser Automation Workflows
Pre-built automations for common tasks.

VOICE COMMANDS:
  Login:
    "login to github with username admin password mypass"
    "sign in to gmail"

  Download:
    "download the file on this page"
    "save this page as PDF"
    "download all images from this page"

  Forms:
    "fill and submit the contact form with name Abijith email a@b.com message hello"
    "fill the search form with python tutorial"

  YouTube:
    "play python tutorial on youtube"
    "search youtube for lofi music"
    "pause youtube"

  Gmail automation:
    "open gmail"
    "compose email to john@email.com subject hello body how are you"

  Wikipedia:
    "search wikipedia for black holes"
    "read wikipedia article on machine learning"

  Shopping:
    "search amazon for mechanical keyboard"
    "search flipkart for laptop"

  Translate:
    "translate this page to Tamil"
    "open google translate with hello world"
"""

import re
import time
from jarvis_addons.browser.core.browser_engine import (
    goto, click, type_text, press_key, get_full_page_text,
    get_page_title, screenshot, run_js, scroll_to_bottom,
    get_current_url, new_tab,
)


# ── Login automations ─────────────────────────────────────────────────────────

def login_to_site(site: str, username: str, password: str) -> str:
    """Generic login helper - tries common input selectors."""
    login_urls = {
        "github":   "https://github.com/login",
        "google":   "https://accounts.google.com",
        "facebook": "https://www.facebook.com/login",
        "twitter":  "https://twitter.com/login",
        "linkedin": "https://www.linkedin.com/login",
        "reddit":   "https://www.reddit.com/login",
    }

    url = login_urls.get(site.lower(), f"https://{site}/login")
    goto(url)
    time.sleep(2)

    # Username field
    username_selectors = [
        'input[name="login"]',
        'input[name="username"]',
        'input[name="email"]',
        'input[type="email"]',
        'input[id*="user"]',
        'input[id*="email"]',
        'input[placeholder*="email" i]',
        'input[placeholder*="username" i]',
    ]
    user_typed = False
    for sel in username_selectors:
        try:
            r = type_text(sel, username)
            if "Typed" in r:
                user_typed = True
                break
        except Exception:
            continue

    if not user_typed:
        return f"Could not find username field on {site}."

    press_key("Tab")
    time.sleep(0.5)

    # Password field
    type_text('input[type="password"]', password)
    time.sleep(0.5)
    press_key("Enter")
    time.sleep(2)

    title = get_page_title()
    return f"Login attempted on {site}. Current page: {title}"


# ── YouTube automation ────────────────────────────────────────────────────────

def youtube_search(query: str) -> str:
    goto(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
    time.sleep(2)
    return f"Searched YouTube for: {query}"


def youtube_play_first() -> str:
    """Click the first video result."""
    result = click("ytd-video-renderer a#thumbnail")
    time.sleep(1)
    return f"Playing first result: {get_page_title()}"


def youtube_pause() -> str:
    """Press K to toggle pause on YouTube."""
    press_key("k")
    return "Toggled YouTube playback."


def youtube_fullscreen() -> str:
    press_key("f")
    return "Toggled fullscreen."


def youtube_skip_5s() -> str:
    press_key("l")
    return "Skipped forward 5 seconds."


def youtube_mute() -> str:
    press_key("m")
    return "Toggled YouTube mute."


# ── Wikipedia ─────────────────────────────────────────────────────────────────

def wikipedia_search(query: str) -> str:
    url = f"https://en.wikipedia.org/wiki/Special:Search?search={query.replace(' ', '+')}"
    goto(url)
    time.sleep(2)

    # If it redirected to an article directly
    if "Special:Search" not in get_current_url():
        text = get_full_page_text()
        # Get just the intro (first ~500 chars of article body)
        para = _get_wikipedia_intro(text)
        return f"{get_page_title()}\n\n{para}"

    # Otherwise, click first result
    click(".mw-search-result-heading a")
    time.sleep(1)
    text = get_full_page_text()
    return f"{get_page_title()}\n\n{_get_wikipedia_intro(text)}"


def _get_wikipedia_intro(full_text: str) -> str:
    lines = [l.strip() for l in full_text.split("\n") if len(l.strip()) > 80]
    return "\n".join(lines[:3]) if lines else full_text[:400]


# ── Gmail automation ─────────────────────────────────────────────────────────

def open_gmail() -> str:
    return goto("https://mail.google.com")


def gmail_compose(to: str, subject: str, body: str) -> str:
    """Compose and send a Gmail (requires being logged into Gmail)."""
    goto("https://mail.google.com")
    time.sleep(3)

    # Click Compose
    click('[gh="cm"]')
    time.sleep(1.5)

    # Fill To
    type_text('[name="to"]', to)
    press_key("Tab")
    time.sleep(0.5)

    # Fill Subject
    type_text('[name="subjectbox"]', subject)
    press_key("Tab")
    time.sleep(0.5)

    # Fill Body
    type_text('[role="textbox"][aria-label*="Body"]', body)
    time.sleep(0.5)

    return f"Email draft ready. To: {to}, Subject: {subject}. Say 'send the email' to send."


def gmail_send() -> str:
    """Send the currently composed Gmail draft."""
    click('[data-tooltip="Send"]')
    time.sleep(1)
    return "Email sent!"


# ── Google Translate ─────────────────────────────────────────────────────────

def translate_text(text: str, target_lang: str = "ta") -> str:
    """Open Google Translate with text."""
    url = f"https://translate.google.com/?sl=auto&tl={target_lang}&text={text.replace(' ', '%20')}"
    goto(url)
    time.sleep(3)

    result = run_js("""
        const el = document.querySelector('span.ryNqvb, div[data-language-to-translate-into]');
        return el ? el.innerText : '';
    """)
    return result if result else f"Opened Google Translate for: {text}"


LANG_CODES = {
    "tamil": "ta", "hindi": "hi", "french": "fr",
    "spanish": "es", "german": "de", "japanese": "ja",
    "chinese": "zh-CN", "arabic": "ar", "russian": "ru",
    "telugu": "te", "kannada": "kn", "malayalam": "ml",
    "bengali": "bn", "marathi": "mr", "gujarati": "gu",
}


# ── Shopping search ───────────────────────────────────────────────────────────

def search_amazon(query: str) -> str:
    goto(f"https://www.amazon.in/s?k={query.replace(' ', '+')}")
    time.sleep(2)
    # Extract top results
    result = run_js("""
        return Array.from(document.querySelectorAll('h2 a.a-link-normal'))
            .slice(0, 5)
            .map(a => a.innerText.trim())
            .filter(t => t.length > 5)
            .join('\\n');
    """)
    return f"Amazon results for '{query}':\n{result}" if result else f"Searched Amazon for {query}."


def search_flipkart(query: str) -> str:
    goto(f"https://www.flipkart.com/search?q={query.replace(' ', '+')}")
    time.sleep(2)
    result = run_js("""
        return Array.from(document.querySelectorAll('._4rR01T, .s1Q9rs, .IRpwTa'))
            .slice(0, 5)
            .map(el => el.innerText.trim())
            .filter(t => t.length > 5)
            .join('\\n');
    """)
    return f"Flipkart results for '{query}':\n{result}" if result else f"Searched Flipkart for {query}."


# ── Download ─────────────────────────────────────────────────────────────────

def download_all_images() -> str:
    """Download all images from the current page."""
    result = run_js("""
        return Array.from(document.querySelectorAll('img[src]'))
            .map(i => i.src)
            .filter(s => s.startsWith('http'))
            .slice(0, 20);
    """)
    if isinstance(result, list):
        return f"Found {len(result)} images. First few:\n" + "\n".join(result[:5])
    return "No downloadable images found."


# ── Voice command router ──────────────────────────────────────────────────────

AUTOMATION_TRIGGERS = [
    "login to", "sign in to", "log into",
    "play on youtube", "search youtube", "youtube search",
    "pause youtube", "fullscreen youtube", "mute youtube",
    "wikipedia", "search wikipedia", "read wikipedia",
    "open gmail", "compose email", "send email",
    "translate", "google translate",
    "amazon", "search amazon", "flipkart",
    "download all images", "download images",
]


def handle_automation_command(text: str) -> str | None:
    lower = text.lower().strip()

    if not any(t in lower for t in AUTOMATION_TRIGGERS):
        return None

    # Login
    m = re.search(r"(?:login to|sign in to|log into)\s+(\w+)\s+with\s+username\s+(\S+)\s+password\s+(\S+)", lower)
    if m:
        return login_to_site(m.group(1), m.group(2), m.group(3))

    m = re.search(r"(?:login to|sign in to|log into)\s+(\w+)", lower)
    if m:
        return goto(f"https://{m.group(1)}.com/login")

    # YouTube
    m = re.search(r"(?:play|search youtube for|search youtube|youtube search)\s+(.+?)(?:\s+on youtube)?$", lower)
    if m:
        query = m.group(1).strip()
        youtube_search(query)
        time.sleep(1)
        return youtube_play_first()

    if "pause youtube" in lower or "pause the video" in lower:
        return youtube_pause()

    if "fullscreen" in lower and "youtube" in lower:
        return youtube_fullscreen()

    if "mute youtube" in lower:
        return youtube_mute()

    # Wikipedia
    m = re.search(r"(?:search wikipedia for|read wikipedia|wikipedia)\s+(.+)", lower)
    if m:
        return wikipedia_search(m.group(1).strip())

    # Gmail
    if "open gmail" in lower:
        return open_gmail()

    m = re.search(
        r"compose email to\s+(\S+)\s+subject\s+(.+?)\s+body\s+(.+)",
        lower
    )
    if m:
        return gmail_compose(m.group(1), m.group(2), m.group(3))

    if "send the email" in lower or "send email now" in lower:
        return gmail_send()

    # Translate
    m = re.search(r"translate\s+(.+?)\s+to\s+(\w+)", lower)
    if m:
        text_to_translate = m.group(1).strip()
        lang = m.group(2).strip().lower()
        code = LANG_CODES.get(lang, lang[:2])
        return translate_text(text_to_translate, code)

    # Shopping
    m = re.search(r"search amazon(?:\s+for)?\s+(.+)", lower)
    if m:
        return search_amazon(m.group(1).strip())

    m = re.search(r"(?:search )?flipkart(?:\s+for)?\s+(.+)", lower)
    if m:
        return search_flipkart(m.group(1).strip())

    # Images
    if "download all images" in lower or "download images" in lower:
        return download_all_images()

    return None
