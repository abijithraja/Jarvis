import importlib
import shutil
import requests


def _check_ollama():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code != 200:
            return "Ollama reachable but returned non-200. Try: ollama serve"
        return None
    except Exception:
        return "Ollama not running. Start it with: ollama serve"


def _check_tesseract():
    try:
        import pytesseract
        import os
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in paths:
            if os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
        pytesseract.get_tesseract_version()
        return None
    except Exception:
        return "Tesseract OCR not found. Vision features disabled. Install from: https://github.com/UB-Mannheim/tesseract/wiki"


def collect_runtime_warnings() -> list[str]:
    warnings = []

    optional = {
        "selenium":         "Browser automation unavailable (pip install selenium)",
        "webdriver_manager":"Browser automation may fail (pip install webdriver-manager)",
        "pyautogui":        "Desktop control unavailable (pip install pyautogui)",
        "pytesseract":      "Vision OCR unavailable (pip install pytesseract)",
        "cv2":              "OpenCV unavailable (pip install opencv-python)",
        "bs4":              "Web scraping unavailable (pip install beautifulsoup4)",
        "pvporcupine":      "Wake word unavailable (pip install pvporcupine + Picovoice key)",
    }

    for module, msg in optional.items():
        try:
            importlib.import_module(module)
        except ImportError:
            warnings.append(msg)

    ollama_warn = _check_ollama()
    if ollama_warn:
        warnings.append(ollama_warn)

    tesseract_warn = _check_tesseract()
    if tesseract_warn:
        warnings.append(tesseract_warn)

    if not shutil.which("python") and not shutil.which("python3"):
        warnings.append("Python not found in PATH.")

    return warnings
