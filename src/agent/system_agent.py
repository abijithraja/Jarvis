import subprocess
import time
import sys
import os
import re
from src.memory import state


def handle_system_command(text: str):
    """
    Handle desktop/OS commands. Returns response string or None
    if this is not a system command.
    """
    if not text:
        return None

    t = text.lower().strip()

    # Fix common speech-to-text mishearing
    t = t.replace("one pad", "notepad").replace("note pad", "notepad")
    t = t.replace("sptoify", "spotify").replace("spotifiy", "spotify")

    # Handle chained commands: "open notepad and type hello"
    if " and " in t:
        parts = [p.strip() for p in t.split(" and ") if p.strip()]
        responses = []
        for part in parts:
            res = handle_system_command(part)
            if res:
                responses.append(res)
        return ", ".join(responses) if responses else None

    # --- CLOSE ---
    if "close notepad" in t:
        subprocess.call("taskkill /f /im notepad.exe", shell=True)
        state.current_app = None
        return "Closing Notepad."

    if "close chrome" in t:
        subprocess.call("taskkill /f /im chrome.exe", shell=True)
        state.current_app = None
        return "Closing Chrome."

    if "close calculator" in t:
        subprocess.call("taskkill /f /im calc.exe", shell=True)
        return "Closing Calculator."

    if "close spotify" in t or "quit spotify" in t or "exit spotify" in t:
        subprocess.call("taskkill /f /im Spotify.exe", shell=True)
        if state.current_app == "spotify":
            state.current_app = None
        return "Closing Spotify."

    # --- TYPE ---
    if t.startswith("type"):
        import pyautogui
        content = t[4:].strip(" ,.\t\n")
        if not content:
            return None
        # If Chrome is open, type into address bar
        if state.current_app == "chrome":
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.3)
            pyautogui.write(content, interval=0.04)
            pyautogui.press("enter")
            return f"Searching '{content}' in Chrome."
        time.sleep(0.5)
        pyautogui.write(content, interval=0.04)
        return f"Typed: {content}"

    # --- CREATE FILE ---
    if any(p in t for p in ["create file", "make file", "new file"]):
        filename = _extract_filename_from_command(t) or "new_file.txt"
        base_dir = _desktop_path() if "desktop" in t else os.getcwd()
        full_path = os.path.join(base_dir, filename)
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "a", encoding="utf-8"):
                pass
            return f"Created file at {full_path}."
        except Exception as e:
            return f"Couldn't create file: {e}"

    # --- OPEN APPS ---
    if any(w in t for w in ["open notepad", "launch notepad", "start notepad", "notepad"]):
        subprocess.Popen(["notepad.exe"])
        state.current_app = "notepad"
        return "Opening Notepad."

    if any(w in t for w in ["open chrome", "launch chrome", "start chrome", "open browser"]):
        _open_chrome()
        return "Opening Chrome."

    if any(w in t for w in ["open calculator", "launch calculator", "calculator"]):
        subprocess.Popen("calc.exe", shell=True)
        return "Opening Calculator."

    if "screenshot" in t or "take a screenshot" in t:
        import pyautogui
        path = "screenshot.png"
        pyautogui.screenshot(path)
        return f"Screenshot saved to {path}."

    if "volume up" in t:
        import pyautogui
        pyautogui.press("volumeup", presses=5)
        return "Volume up."

    if "volume down" in t:
        import pyautogui
        pyautogui.press("volumedown", presses=5)
        return "Volume down."

    if "mute" in t:
        import pyautogui
        pyautogui.press("volumemute")
        return "Muted."

    return None  # Not a system command


def _open_chrome():
    import platform
    state.current_app = "chrome"
    if platform.system() == "Windows":
        subprocess.Popen("start chrome", shell=True)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", "-a", "Google Chrome"])
    else:
        subprocess.Popen(["google-chrome"])
    time.sleep(2)


def _extract_filename_from_command(text: str) -> str | None:
    m = re.search(r"(?:named|called)\s+([a-zA-Z0-9_.-]+)", text)
    if not m:
        m = re.search(r"(?:create|make)(?:\s+(?:a|new))?\s+file\s+([a-zA-Z0-9_.-]+)", text)
    if not m:
        return None

    name = m.group(1).strip(" .?!,")
    if "." not in name:
        name += ".txt"
    return name


def _desktop_path() -> str:
    return os.path.join(os.path.expanduser("~"), "Desktop")
