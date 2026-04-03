import os
import pytesseract
import pyautogui


def _resolve_tesseract():
    """Find tesseract binary automatically."""
    # Check env variable first
    env_path = os.environ.get("TESSERACT_CMD")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Common Windows install paths
    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in windows_paths:
        if os.path.isfile(p):
            return p

    # Linux/Mac: assume it's on PATH
    return None


def read_screen() -> str:
    """Take a screenshot and return extracted text (first 500 chars)."""
    cmd = _resolve_tesseract()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

    try:
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)
        clean = " ".join(text.split())  # collapse whitespace
        return clean[:500] if clean else "No text found on screen."
    except Exception as e:
        return f"Vision error: {str(e)}"
