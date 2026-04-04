"""
Screen Reader & Describer Skill
Reads and describes everything visible on the desktop.

VOICE COMMANDS:
  "what's on my screen"
  "read the screen"
  "what windows are open"
  "what am I working on"
  "read the active window"
  "describe the desktop"
  "what apps are running"
  "find [text] on screen"
  "read the clipboard"
  "copy [text] to clipboard"
  "kill chrome" / "close chrome process"
"""

import re
from jarvis_addons.desktop.desktop_reader import (
    list_windows_text,
    get_active_window,
    read_full_screen,
    describe_screen,
    list_running_processes,
    kill_process,
    read_clipboard,
    write_clipboard,
    summarize_screen_with_ai,
)


SCREEN_TRIGGERS = [
    "what's on", "what is on", "read the screen", "read screen",
    "what windows", "open windows", "active window",
    "describe the desktop", "describe the screen",
    "what am i working on", "what apps", "running apps",
    "find on screen", "clipboard", "copy to clipboard",
    "kill process", "close process", "running processes",
    "summarize screen", "what can you see",
]


def handle_screen_command(text: str) -> str | None:
    lower = text.lower().strip()

    if not any(t in lower for t in SCREEN_TRIGGERS):
        return None

    # ── Windows list ─────────────────────────────────────────────────────────

    if any(p in lower for p in ["what windows", "open windows", "list windows"]):
        return list_windows_text()

    if "active window" in lower or "current window" in lower:
        return get_active_window()

    # ── Screen reading ────────────────────────────────────────────────────────

    if any(p in lower for p in ["read the screen", "read screen", "read it"]):
        text_on_screen = read_full_screen()
        if len(text_on_screen) > 500:
            return text_on_screen[:500] + "... (truncated)"
        return text_on_screen

    if any(p in lower for p in ["what's on", "what is on", "what can you see", "describe the"]):
        return describe_screen()

    if "what am i working on" in lower or "what am i doing" in lower:
        return summarize_screen_with_ai()

    # ── Find text ────────────────────────────────────────────────────────────

    m = re.search(r"find\s+['\"]?(.+?)['\"]?\s+on\s+screen", lower)
    if m:
        query = m.group(1).strip()
        screen_text = read_full_screen()
        if query.lower() in screen_text.lower():
            idx = screen_text.lower().find(query.lower())
            context = screen_text[max(0, idx-50):idx+100]
            return f"Found '{query}' on screen. Context: ...{context}..."
        return f"'{query}' not found on screen."

    # ── Processes ─────────────────────────────────────────────────────────────

    if any(p in lower for p in ["what apps", "running apps", "running processes", "list processes"]):
        return list_running_processes()

    m = re.search(r"(?:kill|force close|close process)\s+(.+)", lower)
    if m:
        proc_name = m.group(1).strip()
        return kill_process(proc_name)

    # ── Clipboard ─────────────────────────────────────────────────────────────

    if "read the clipboard" in lower or "what's in clipboard" in lower or "clipboard content" in lower:
        return read_clipboard()

    m = re.search(r"copy\s+['\"]?(.+?)['\"]?\s+to\s+clipboard", lower)
    if m:
        content = m.group(1).strip()
        return write_clipboard(content)

    # ── Summarize ─────────────────────────────────────────────────────────────

    if "summarize screen" in lower or "summarise screen" in lower:
        return summarize_screen_with_ai()

    return None
