import pyautogui
import time


def open_app(name):
    pyautogui.press("win")
    time.sleep(1)
    pyautogui.write(name)
    time.sleep(1)
    pyautogui.press("enter")
    return f"Opening {name}"


def type_text(text):
    pyautogui.write(text, interval=0.05)
    return f"Typing {text}"


def press_key(key):
    pyautogui.press(key)
    return f"Pressed {key}"
