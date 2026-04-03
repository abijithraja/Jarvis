import os
import shutil


def resolve_tesseract_cmd():
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        return env_cmd

    from_path = shutil.which("tesseract")
    if from_path:
        return from_path

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for candidate in common_paths:
        if os.path.exists(candidate):
            return candidate

    return None