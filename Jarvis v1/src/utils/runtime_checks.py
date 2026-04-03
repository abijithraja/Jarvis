import importlib
import shutil
from src.utils.tesseract_config import resolve_tesseract_cmd


def _check_ollama():
    try:
        requests = importlib.import_module("requests")
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code != 200:
            return "Ollama is reachable but returned a non-200 response."
        return None
    except Exception:
        return "Ollama is not reachable at http://localhost:11434 (start with: ollama serve)."


def _check_tesseract():
    try:
        pytesseract = importlib.import_module("pytesseract")
        tesseract_cmd = resolve_tesseract_cmd()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pytesseract.get_tesseract_version()
        return None
    except Exception:
        return "Tesseract OCR binary not found. Install Tesseract, or set TESSERACT_CMD to the tesseract.exe path."


def collect_runtime_warnings():
    warnings = []

    optional_packages = {
        "selenium": "Browser automation features are unavailable (missing selenium).",
        "webdriver_manager": "Browser automation may fail (missing webdriver-manager).",
        "pyautogui": "Desktop control features are unavailable (missing pyautogui).",
        "pytesseract": "Vision OCR features are unavailable (missing pytesseract).",
        "cv2": "Computer-vision helper features are unavailable (missing opencv-python).",
        "bs4": "Web summarization features are unavailable (missing beautifulsoup4).",
    }

    for module_name, message in optional_packages.items():
        try:
            importlib.import_module(module_name)
        except Exception:
            warnings.append(message)

    ollama_warning = _check_ollama()
    if ollama_warning:
        warnings.append(ollama_warning)

    tesseract_warning = _check_tesseract()
    if tesseract_warning:
        warnings.append(tesseract_warning)

    if not shutil.which("python"):
        warnings.append("Python executable not found in PATH for subprocess-based tools.")

    return warnings
