import os
import subprocess
import platform
import time
import re
from urllib.parse import quote_plus

import requests


def run_external_agent(command: str) -> str:
    """
    Handle external commands: open apps, search web, type text.
    """
    cmd = command.lower().strip()

    try:
        # --- SEARCH ---
        if "search" in cmd:
            query = (cmd
                     .replace("search google for", "")
                     .replace("search for", "")
                     .replace("search", "")
                     .replace("google", "")
                     .strip())
            if query:
                _open_url(f"https://www.google.com/search?q={query.replace(' ', '+')}")
                return f"Searching Google for: {query}"

        # --- OPEN URLS ---
        if "youtube" in cmd:
            if any(w in cmd for w in ["play", "watch"]):
                query = _extract_youtube_query(cmd)
                if query:
                    _play_youtube_query(query)
                    return f"Playing on YouTube: {query}"
            _open_url("https://www.youtube.com")
            return "Opening YouTube."

        if "open website" in cmd or "go to" in cmd:
            url = cmd.replace("open website", "").replace("go to", "").strip()
            if not url.startswith("http"):
                url = "https://" + url
            _open_url(url)
            return f"Opening {url}"

        # --- APPS ---
        if "notepad" in cmd:
            subprocess.Popen(["notepad.exe"] if platform.system() == "Windows" else ["gedit"])
            return "Opening Notepad."

        if "chrome" in cmd or "browser" in cmd:
            _open_url("https://www.google.com")
            return "Opening Chrome."

        if "calculator" in cmd:
            subprocess.Popen("calc.exe" if platform.system() == "Windows" else ["gnome-calculator"], shell=True)
            return "Opening Calculator."

        # --- TYPE ---
        if cmd.startswith("type"):
            import pyautogui
            text = cmd.replace("type", "", 1).strip(" ,.\t\n")
            if text:
                time.sleep(0.5)
                pyautogui.write(text, interval=0.04)
                return f"Typed: {text}"

        return "I'm not sure how to do that yet."

    except Exception as e:
        return f"Error: {str(e)}"


def _open_url(url: str):
    """Open a URL in the default browser cross-platform."""
    import webbrowser
    webbrowser.open(url)


def _extract_youtube_query(cmd: str) -> str:
    """Extract the media query from phrases like 'open youtube and play rain music'."""
    cleaned = cmd.lower().strip()
    cleaned = cleaned.replace("jarvis", "").replace("javis", "")

    m = re.search(r"(?:play|watch)\s+(.+?)(?:\s+on\s+youtube)?$", cleaned)
    if m:
        query = m.group(1)
    else:
        m = re.search(r"youtube.*(?:play|watch)\s+(.+)$", cleaned)
        query = m.group(1) if m else ""

    query = re.sub(r"\b(song|video)\b", "", query)
    query = re.sub(r"^(a|an|the)\s+", "", query.strip())
    return query.strip(" .?!,")


def _play_youtube_query(query: str):
    """Try to open first matching YouTube video; fallback to search results."""
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        r = requests.get(
            search_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        if matches:
            _open_url(f"https://www.youtube.com/watch?v={matches[0]}&autoplay=1")
            return
    except Exception:
        pass

    _open_url(search_url)
