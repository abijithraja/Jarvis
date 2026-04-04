"""
Smart Web Scraper
Navigates to any URL, extracts structured content, summarizes with LLM.

VOICE COMMANDS:
  "summarize this page"
  "summarize bbc.com/news"
  "what is on techcrunch.com"
  "read and summarize the article"
  "extract all prices from this page"
  "get the table from this page"
  "scrape product name and price"
  "get the top 5 results from google"
  "monitor this page for changes"
"""

import re
import time
import json
from jarvis_addons.browser.core.browser_engine import (
    goto, get_full_page_text, get_current_url,
    get_page_title, run_js, screenshot,
)


# ── Summarizer ────────────────────────────────────────────────────────────────

def summarize_url(url: str) -> str:
    """Navigate to a URL and return an AI summary of the content."""
    if not url.startswith("http"):
        url = "https://" + url
    goto(url)
    return summarize_current_page()


def summarize_current_page() -> str:
    """Summarize the content of the current page using LLM."""
    title = get_page_title()
    text  = get_full_page_text()
    url   = get_current_url()

    if not text or len(text) < 50:
        return f"Could not read content from {url}"

    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "jarvis_fixed"))
        from src.llm.ollama_client import generate_response

        prompt = (
            f"Summarize this webpage in 3-4 sentences. "
            f"Title: {title}\nURL: {url}\n\nContent:\n{text[:2000]}"
        )
        return generate_response(prompt)
    except Exception:
        # Fallback: return first 300 chars of text
        return f"{title}\n{text[:300]}..."


# ── Content extractor ─────────────────────────────────────────────────────────

def extract_tables() -> str:
    """Extract all HTML tables from the current page as text."""
    script = """
        const tables = document.querySelectorAll('table');
        return Array.from(tables).map(t => {
            const rows = Array.from(t.querySelectorAll('tr'));
            return rows.map(r =>
                Array.from(r.querySelectorAll('td,th'))
                    .map(c => c.innerText.trim())
                    .join(' | ')
            ).join('\\n');
        }).join('\\n\\n');
    """
    result = run_js(script)
    return result[:2000] if result else "No tables found on this page."


def extract_prices() -> str:
    """Find all price-like patterns on the current page."""
    text = get_full_page_text()
    prices = re.findall(r'(?:₹|Rs\.?|INR|USD|\$|€|£)\s*[\d,]+(?:\.\d{1,2})?', text)
    if prices:
        unique = list(dict.fromkeys(prices))[:20]
        return "Prices found: " + ", ".join(unique)
    return "No prices found on this page."


def extract_emails() -> str:
    """Find all email addresses on the current page."""
    text = get_full_page_text()
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    unique = list(dict.fromkeys(emails))[:15]
    return "Emails found: " + ", ".join(unique) if unique else "No emails found."


def extract_phone_numbers() -> str:
    """Find phone numbers on the current page."""
    text = get_full_page_text()
    phones = re.findall(r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{3,5}\)?[\s\-]?\d{3,5}[\s\-]?\d{4,6}', text)
    unique = [p.strip() for p in list(dict.fromkeys(phones))[:10] if len(p.strip()) >= 7]
    return "Phone numbers: " + ", ".join(unique) if unique else "No phone numbers found."


def extract_headings() -> str:
    """Extract all headings (H1–H3) from the current page."""
    script = """
        return Array.from(document.querySelectorAll('h1,h2,h3'))
            .map(h => h.tagName + ': ' + h.innerText.trim())
            .filter(h => h.length > 5)
            .slice(0, 20)
            .join('\\n');
    """
    result = run_js(script)
    return result if result else "No headings found."


def extract_images() -> str:
    """List all images with alt text on the current page."""
    script = """
        return Array.from(document.querySelectorAll('img[src]'))
            .map(i => ({src: i.src, alt: i.alt || '(no alt)'}))
            .slice(0, 15)
            .map(i => i.alt + ' — ' + i.src.slice(0,60))
            .join('\\n');
    """
    result = run_js(script)
    return result if result else "No images found."


# ── Page monitor ─────────────────────────────────────────────────────────────

_monitors: dict = {}   # url → last_hash

def start_page_monitor(url: str, interval_seconds: int = 60) -> str:
    """
    Monitor a page for content changes.
    Alerts via TTS when the page changes.
    """
    import threading
    import hashlib

    def _watch():
        last_hash = ""
        while url in _monitors:
            try:
                goto(url)
                text = get_full_page_text()
                current_hash = hashlib.md5(text.encode()).hexdigest()
                if last_hash and current_hash != last_hash:
                    try:
                        from src.tts.speaker import speak
                        speak(f"Page changed: {get_page_title()}")
                    except Exception:
                        print(f"\n🔔 Page changed: {url}")
                last_hash = current_hash
            except Exception:
                pass
            time.sleep(interval_seconds)

    _monitors[url] = True
    thread = threading.Thread(target=_watch, daemon=True)
    thread.start()
    return f"Monitoring {url} every {interval_seconds} seconds."


def stop_page_monitor(url: str) -> str:
    if url in _monitors:
        del _monitors[url]
        return f"Stopped monitoring {url}."
    return f"Not monitoring {url}."


# ── Google search + read results ─────────────────────────────────────────────

def search_and_read(query: str, open_first: bool = False) -> str:
    """Search Google, optionally open the first result and summarize it."""
    from jarvis_addons.browser.core.browser_engine import google_search, click

    results = google_search(query)

    if open_first:
        # Click the first result
        click("h3")
        time.sleep(2)
        return summarize_current_page()

    return results


# ── Voice command router ──────────────────────────────────────────────────────

SCRAPER_TRIGGERS = [
    "summarize", "what is on", "read and summarize",
    "extract", "scrape", "get the table", "get all prices",
    "get emails", "find emails", "get phone numbers",
    "list headings", "list images",
    "monitor this page", "watch this page", "stop monitoring",
    "search and read", "open first result",
]


def handle_scraper_command(text: str) -> str | None:
    lower = text.lower().strip()

    if not any(t in lower for t in SCRAPER_TRIGGERS):
        return None

    # Summarize a URL
    m = re.search(r"summarize\s+(https?://\S+|[\w\-]+\.\w{2,}(?:/\S*)?)", lower)
    if m:
        return summarize_url(m.group(1).strip())

    # Summarize current page
    if any(p in lower for p in ["summarize this page", "summarize the page", "summarize current page"]):
        return summarize_current_page()

    if "what is on" in lower:
        m = re.search(r"what is on\s+(.+)", lower)
        if m:
            return summarize_url(m.group(1).strip())

    # Extract
    if "extract" in lower or "get the table" in lower:
        if "table" in lower:
            return extract_tables()
        if "price" in lower:
            return extract_prices()
        if "email" in lower:
            return extract_emails()
        if "phone" in lower:
            return extract_phone_numbers()
        if "heading" in lower:
            return extract_headings()
        if "image" in lower:
            return extract_images()

    if "get all prices" in lower or "find prices" in lower:
        return extract_prices()

    if "get emails" in lower or "find emails" in lower:
        return extract_emails()

    if "get phone numbers" in lower or "find phone numbers" in lower:
        return extract_phone_numbers()

    if "list headings" in lower or "show headings" in lower:
        return extract_headings()

    if "list images" in lower or "show images" in lower:
        return extract_images()

    # Monitor
    m = re.search(r"monitor\s+(?:this\s+page|page\s+at\s+)?(.+?)(?:\s+every\s+(\d+)\s+(?:second|minute)s?)?$", lower)
    if m and any(t in lower for t in ["monitor", "watch"]):
        url = m.group(1).strip() if "http" in m.group(1) else get_current_url()
        interval = int(m.group(2) or 60)
        if "minute" in lower:
            interval *= 60
        return start_page_monitor(url, interval)

    if "stop monitoring" in lower:
        return stop_page_monitor(get_current_url())

    # Search and read
    m = re.search(r"search\s+(?:for\s+)?(.+?)\s+and\s+(?:read|open|summarize)", lower)
    if m:
        return search_and_read(m.group(1).strip(), open_first=True)

    return None
