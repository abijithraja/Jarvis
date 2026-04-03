"""
Plugin skill system — each skill is a function that returns a string response.
Skills auto-register via the @skill decorator.
"""

import os
import re
import json
import subprocess
import threading
import time
from datetime import datetime, timedelta

_SKILLS: dict = {}


def skill(name: str, keywords: list[str]):
    """Decorator to register a skill."""
    def decorator(fn):
        _SKILLS[name] = {"fn": fn, "keywords": keywords}
        return fn
    return decorator


def _keyword_match(lower_text: str, keyword: str) -> bool:
    """Boundary-aware keyword matching to reduce accidental triggers."""
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, lower_text) is not None


def dispatch(text: str, enabled_skills: set | None = None) -> str | None:
    """Try to match text to the best skill. Returns response or None."""
    lower = text.lower()
    best_name = None
    best_score = 0

    for name, info in _SKILLS.items():
        if enabled_skills is not None and name not in enabled_skills:
            continue

        score = 0
        for kw in info["keywords"]:
            if _keyword_match(lower, kw):
                score = max(score, len(kw.split()))

        if score > best_score:
            best_name = name
            best_score = score

    if best_name:
        try:
            return _SKILLS[best_name]["fn"](text)
        except Exception as e:
            return f"Skill '{best_name}' error: {e}"

    return None


# ─── Weather ─────────────────────────────────────────────────────────────────

@skill("weather", ["weather", "temperature", "forecast", "climate", "raining", "cold outside", "hot outside", "sunny outside"])
def weather_skill(text: str) -> str:
    api_key = os.environ.get("OPENWEATHER_KEY")
    if not api_key:
        return "Please set the OPENWEATHER_KEY environment variable to use weather."

    # Extract city from text
    m = re.search(r"(?:in|for|at)\s+([a-zA-Z\s]+?)(?:\?|$)", text, re.I)
    city = m.group(1).strip() if m else os.environ.get("JARVIS_CITY", "Chennai")

    import requests
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=5
        )
        d = r.json()
        if r.status_code != 200:
            return f"Couldn't get weather for {city}."
        desc   = d["weather"][0]["description"]
        temp   = round(d["main"]["temp"])
        feels  = round(d["main"]["feels_like"])
        humid  = d["main"]["humidity"]
        return (f"In {city}: {desc}, {temp}°C, feels like {feels}°C, "
                f"humidity {humid}%.")
    except Exception as e:
        return f"Weather fetch failed: {e}"


# ─── Reminders ───────────────────────────────────────────────────────────────

_reminder_thread_started = False

@skill("reminder", ["remind me", "reminder", "alarm", "alert me", "set a timer"])
def reminder_skill(text: str) -> str:
    global _reminder_thread_started

    # Parse: "remind me in 5 minutes to drink water"
    m = re.search(r"in\s+(\d+)\s+(second|minute|hour)s?\s+(?:to\s+)?(.+)", text, re.I)
    if not m:
        return "I need a time. Say: remind me in 5 minutes to drink water."

    amount = int(m.group(1))
    unit   = m.group(2).lower()
    msg    = m.group(3).strip(" .?")

    multipliers = {"second": 1, "minute": 60, "hour": 3600}
    delay = amount * multipliers[unit]

    def _fire():
        time.sleep(delay)
        from src.tts.speaker import speak
        speak(f"Reminder: {msg}")
        print(f"\n🔔 Reminder: {msg}")

    threading.Thread(target=_fire, daemon=True).start()
    return f"Got it! I'll remind you to {msg} in {amount} {unit}{'s' if amount > 1 else ''}."


# ─── News briefing ───────────────────────────────────────────────────────────

@skill("news", ["news", "headlines", "what's happening", "briefing", "top stories"])
def news_skill(text: str) -> str:
    import requests
    from bs4 import BeautifulSoup

    try:
        r = requests.get(
            "https://feeds.bbcnews.com/news/rss.xml",
            headers={"User-Agent": "Jarvis/1.0"},
            timeout=6
        )
        soup = BeautifulSoup(r.content, "xml")
        items = soup.find_all("item")[:5]
        headlines = [i.find("title").text.strip() for i in items]
        if not headlines:
            return "Couldn't fetch headlines right now."
        joined = ". ".join(headlines)
        return f"Top headlines: {joined}"
    except Exception as e:
        return f"News fetch failed: {e}"


# ─── Spotify control ─────────────────────────────────────────────────────────

@skill("spotify", [
    "spotify", "open spotify", "pause spotify", "play spotify", "resume spotify",
    "skip spotify", "next song", "previous song", "shuffle spotify", "play on spotify",
    "resume playback spotify", "stop spotify", "pause music", "stop music",
    "pause the music", "stop the music", "stop playback"
])
def spotify_skill(text: str) -> str:
    lower = text.lower()
    try:
        import subprocess, platform
        if platform.system() != "Windows":
            return "Spotify control is currently supported on Windows only."

        if any(p in lower for p in ["open spotify", "launch spotify", "start spotify"]):
            subprocess.Popen("start spotify", shell=True)
            return "Opening Spotify."

        # Use Spotify web API if token set, else use keyboard shortcuts
        token = os.environ.get("SPOTIFY_TOKEN")
        if token:
            return _spotify_api(lower, token)
        return _spotify_keys(lower)
    except Exception as e:
        return f"Spotify error: {e}"


def _spotify_keys(lower: str) -> str:
    import pyautogui
    if "pause" in lower or "stop" in lower:
        pyautogui.press("playpause")
        return "Paused Spotify."
    elif "next" in lower or "skip" in lower:
        pyautogui.press("nexttrack")
        return "Skipped to next track."
    elif "previous" in lower or "back" in lower:
        pyautogui.press("prevtrack")
        return "Went back a track."
    elif "play" in lower or "resume" in lower:
        pyautogui.press("playpause")
        return "Resumed playback."
    return "Spotify command not recognised. Try play, pause, next, or previous."


def _spotify_api(lower: str, token: str) -> str:
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    base = "https://api.spotify.com/v1/me/player"
    if "pause" in lower or "stop" in lower:
        requests.put(f"{base}/pause", headers=headers)
        return "Paused Spotify."
    elif "play" in lower or "resume" in lower:
        requests.put(f"{base}/play", headers=headers)
        return "Playing Spotify."
    elif "next" in lower or "skip" in lower:
        requests.post(f"{base}/next", headers=headers)
        return "Skipped to next track."
    elif "previous" in lower:
        requests.post(f"{base}/previous", headers=headers)
        return "Went back a track."
    return "Spotify command not recognised."


# ─── File operations ─────────────────────────────────────────────────────────

@skill("file_ops", ["read file", "open file", "show file", "list files", "delete file", "rename file"])
def file_ops_skill(text: str) -> str:
    lower = text.lower()

    m = re.search(r"read (?:file\s+)?[\"']?([^\s\"']+\.\w+)[\"']?", lower)
    if m:
        path = m.group(1)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(800)
            return f"Contents of {path}:\n{content}"
        except FileNotFoundError:
            return f"File not found: {path}"

    if "list files" in lower:
        import os
        cwd = os.getcwd()
        files = os.listdir(cwd)[:20]
        return "Files here: " + ", ".join(files)

    return "Tell me what file operation to perform."


# ─── Sandboxed code runner ───────────────────────────────────────────────────

@skill("code_runner", ["run code", "execute code", "run this", "run output.py", "run the code"])
def code_runner_skill(text: str) -> str:
    # Find filename in text, default to output.py
    m = re.search(r"run\s+([a-zA-Z0-9_]+\.py)", text, re.I)
    filename = m.group(1) if m else "output.py"

    if not os.path.exists(filename):
        return f"{filename} not found. Generate code first."

    try:
        result = subprocess.run(
            ["python", filename],
            capture_output=True,
            text=True,
            timeout=10,         # 10 second sandbox limit
        )
        output = (result.stdout + result.stderr).strip()
        return output[:400] if output else "Code ran with no output."
    except subprocess.TimeoutExpired:
        return "Code timed out after 10 seconds."
    except Exception as e:
        return f"Run error: {e}"
