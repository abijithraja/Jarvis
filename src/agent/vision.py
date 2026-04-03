import pytesseract
import pyautogui
from src.utils.tesseract_config import resolve_tesseract_cmd


def read_screen():
    tesseract_cmd = resolve_tesseract_cmd()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    screenshot = pyautogui.screenshot()
    text = pytesseract.image_to_string(screenshot)
    return text[:500]
