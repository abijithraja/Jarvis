import pyautogui
import subprocess
import time
from src.memory import state


def handle_system_command(text):
    text = text.lower()

    if "one pad" in text:
        text = text.replace("one pad", "notepad")

    if "and" in text:
        parts = text.split("and")
        responses = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            res = handle_system_command(part)
            if res:
                responses.append(res)

        return ", ".join(responses) if responses else None

    if "close notepad" in text:
        subprocess.call("taskkill /f /im notepad.exe", shell=True)
        if state.current_app == "notepad":
            state.current_app = None
        return "Closing Notepad"

    if text.startswith("type") and "chrome" in text:
        content = text.split("type", 1)[-1].strip()
        content = content.replace("in chrome", "").strip()
        content = content.strip(",. ")

        if content:
            time.sleep(2)
            pyautogui.hotkey("ctrl", "l")
            pyautogui.write(content)
            pyautogui.press("enter")
            return f"Searching: {content}"

    if text.startswith("type"):
        content = text.split("type", 1)[-1].strip()
        content = content.strip(",. ")

        if content:
            time.sleep(1)
            pyautogui.write(content)
            return f"Typing: {content}"

    if "notepad" in text and any(word in text for word in ["open", "launch", "start"]):
        subprocess.Popen(["notepad.exe"])
        state.current_app = "notepad"
        return "Opening Notepad"

    if text.strip() == "notepad":
        subprocess.Popen(["notepad.exe"])
        state.current_app = "notepad"
        return "Opening Notepad"

    elif "chrome" in text:
        subprocess.Popen("start chrome", shell=True)
        time.sleep(3)
        pyautogui.click(500, 500)
        state.current_app = "chrome"
        return "Opening Chrome"

    return None
