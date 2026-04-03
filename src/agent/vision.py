import pytesseract
import pyautogui


def read_screen():
    screenshot = pyautogui.screenshot()
    text = pytesseract.image_to_string(screenshot)
    return text[:500]
