"""
Desktop Reader & Analyzer
Tells Jarvis everything that is currently on the screen / desktop.

FEATURES:
  - List all open windows with their titles and state (minimized/maximized/normal)
  - Read text content of the entire screen via OCR
  - Describe what's visible in a specific region
  - Find a specific window by name
  - Get active window info
  - Read clipboard content
  - List all running processes with names
  - Get desktop icon names (Windows)
  - Summarize screen content using LLM
"""

import os
import re
import subprocess
import platform
import pyautogui
import pytesseract
from PIL import Image

# Tesseract setup
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

def _setup_tesseract():
    env = os.environ.get("TESSERACT_CMD")
    if env and os.path.isfile(env):
        pytesseract.pytesseract.tesseract_cmd = env
        return True
    for p in _TESSERACT_PATHS:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return True
    return False


# ── Window Management ─────────────────────────────────────────────────────────

def get_all_windows() -> list[dict]:
    """Return list of all open windows: {title, state, pid}"""
    system = platform.system()

    if system == "Windows":
        return _get_windows_windows()
    elif system == "Darwin":
        return _get_windows_mac()
    else:
        return _get_windows_linux()


def _get_windows_windows() -> list[dict]:
    try:
        import pygetwindow as gw
        windows = []
        for w in gw.getAllWindows():
            if w.title.strip():
                state = "minimized" if w.isMinimized else ("maximized" if w.isMaximized else "normal")
                windows.append({
                    "title": w.title,
                    "state": state,
                    "x": w.left, "y": w.top,
                    "width": w.width, "height": w.height
                })
        return windows
    except Exception as e:
        return [{"title": f"Error: {e}", "state": "unknown"}]


def _get_windows_mac() -> list[dict]:
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every process whose background only is false'],
            capture_output=True, text=True
        )
        names = [n.strip() for n in result.stdout.split(",") if n.strip()]
        return [{"title": n, "state": "unknown"} for n in names]
    except Exception as e:
        return [{"title": f"Error: {e}", "state": "unknown"}]


def _get_windows_linux() -> list[dict]:
    try:
        result = subprocess.run(
            ["wmctrl", "-l"], capture_output=True, text=True
        )
        windows = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split(None, 3)
            if len(parts) >= 4:
                windows.append({"title": parts[3], "state": "unknown"})
        return windows
    except Exception:
        return []


def list_windows_text() -> str:
    """Return human-readable list of all open windows."""
    windows = get_all_windows()
    if not windows:
        return "No windows found."
    lines = [f"  • {w['title']} ({w.get('state','?')})" for w in windows]
    return f"Open windows ({len(windows)}):\n" + "\n".join(lines)


def get_active_window() -> str:
    """Get the currently focused window title."""
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        return f"Active window: {w.title}" if w else "No active window."
    except Exception:
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True
            )
            return f"Active window: {result.stdout.strip()}"
        except Exception as e:
            return f"Could not get active window: {e}"


def find_window(name: str) -> dict | None:
    """Find a window by partial name match."""
    windows = get_all_windows()
    name_lower = name.lower()
    for w in windows:
        if name_lower in w["title"].lower():
            return w
    return None


# ── Screen Reading ────────────────────────────────────────────────────────────

def read_full_screen() -> str:
    """OCR the entire screen and return clean text."""
    if not _setup_tesseract():
        return "Tesseract not installed. Cannot read screen."

    try:
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)
        # Clean up
        clean = re.sub(r'\n{3,}', '\n\n', text)
        clean = re.sub(r'[^\x20-\x7E\n]', '', clean).strip()
        return clean[:2000] if clean else "No readable text found on screen."
    except Exception as e:
        return f"Screen read error: {e}"


def read_region(x: int, y: int, width: int, height: int) -> str:
    """OCR a specific region of the screen."""
    if not _setup_tesseract():
        return "Tesseract not installed."
    try:
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        text = pytesseract.image_to_string(screenshot).strip()
        return text if text else "No text in that region."
    except Exception as e:
        return f"Region read error: {e}"


def describe_screen() -> str:
    """
    Give a smart summary of what's on screen.
    Uses OCR + window list + heuristics.
    """
    windows = get_all_windows()
    active = get_active_window()
    screen_text = read_full_screen()

    # Detect what kind of app is in focus
    app_type = _classify_screen_content(screen_text, windows)

    summary_parts = [active]
    if windows:
        top5 = [w["title"] for w in windows[:5]]
        summary_parts.append(f"Open apps: {', '.join(top5)}")
    summary_parts.append(f"Screen type: {app_type}")

    if screen_text and len(screen_text) > 10:
        preview = screen_text[:300].replace("\n", " ")
        summary_parts.append(f"Visible text preview: {preview}")

    return "\n".join(summary_parts)


def _classify_screen_content(text: str, windows: list) -> str:
    text_lower = text.lower()
    all_titles = " ".join(w["title"].lower() for w in windows)

    if any(w in text_lower for w in ["inbox", "compose", "reply", "forward"]):
        return "email client"
    if any(w in text_lower for w in ["whatsapp", "telegram", "discord", "messenger"]):
        return "messaging app"
    if any(w in text_lower for w in ["def ", "import ", "class ", "function", "print("]):
        return "code editor"
    if any(w in text_lower for w in ["spreadsheet", "cell", "formula", "=sum"]):
        return "spreadsheet"
    if any(w in text_lower for w in ["browser", "http", "www", "google"]):
        return "web browser"
    if "youtube" in all_titles or "netflix" in all_titles:
        return "video streaming"
    return "general desktop"


# ── Clipboard ────────────────────────────────────────────────────────────────

def read_clipboard() -> str:
    """Read text from clipboard."""
    try:
        import pyperclip
        content = pyperclip.paste()
        return f"Clipboard content: {content[:500]}" if content else "Clipboard is empty."
    except ImportError:
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            content = root.clipboard_get()
            root.destroy()
            return f"Clipboard: {content[:500]}"
        except Exception as e:
            return f"Could not read clipboard: {e}"


def write_clipboard(text: str) -> str:
    """Write text to clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Copied to clipboard."
    except Exception as e:
        return f"Clipboard write failed: {e}"


# ── Running Processes ─────────────────────────────────────────────────────────

def list_running_processes(filter_str: str = "") -> str:
    """List running processes, optionally filtered by name."""
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split("\n")
            procs = []
            for line in lines:
                parts = line.strip('"').split('","')
                if parts:
                    name = parts[0]
                    if not filter_str or filter_str.lower() in name.lower():
                        procs.append(name)
        else:
            result = subprocess.run(["ps", "-eo", "comm"], capture_output=True, text=True)
            procs = [
                p.strip() for p in result.stdout.split("\n")
                if p.strip() and (not filter_str or filter_str.lower() in p.lower())
            ]

        if not procs:
            return f"No processes found matching '{filter_str}'."

        unique = sorted(set(procs))[:30]
        return f"Running processes ({len(unique)}):\n" + "\n".join(f"  • {p}" for p in unique)

    except Exception as e:
        return f"Process list error: {e}"


def kill_process(name: str) -> str:
    """Kill a process by name."""
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(
                ["taskkill", "/f", "/im", name],
                capture_output=True, text=True
            )
            return f"Killed {name}." if result.returncode == 0 else f"Could not kill {name}: {result.stderr}"
        else:
            result = subprocess.run(["pkill", "-f", name], capture_output=True)
            return f"Killed processes matching {name}." if result.returncode == 0 else f"No process named {name}."
    except Exception as e:
        return f"Kill error: {e}"


# ── Screen Summarize with LLM ────────────────────────────────────────────────

def summarize_screen_with_ai() -> str:
    """
    Take a screenshot, OCR it, then ask the LLM to summarize what's on screen.
    """
    screen_text = read_full_screen()
    if not screen_text or len(screen_text) < 10:
        return "Could not read enough text from screen to summarize."

    try:
        # Import from jarvis_fixed
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "jarvis_fixed"))
        from src.llm.ollama_client import generate_response

        prompt = (
            f"The following text was extracted from a user's computer screen via OCR. "
            f"In 2-3 sentences, describe what the user is currently looking at or working on:\n\n"
            f"{screen_text[:1500]}"
        )
        return generate_response(prompt)
    except Exception as e:
        # Fallback: just return the raw description
        return describe_screen()
