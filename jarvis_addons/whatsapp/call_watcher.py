"""
WhatsApp Call Watcher
Runs as a background thread, watches the screen for incoming WhatsApp call
notification, then accepts or declines based on Jarvis command.

HOW IT WORKS:
  - Takes a screenshot every 2 seconds
  - Uses OCR (pytesseract) to detect "Incoming call", "Voice call", "Video call"
    text anywhere on screen
  - If detected: speaks an alert via Jarvis TTS
  - If commanded to accept: clicks the green Accept button using image matching
  - If commanded to decline/busy: clicks Red Decline, then auto-sends
    "Sorry, I'm busy right now. Will call you back soon." via WhatsApp

REQUIREMENTS:
  - pip install pytesseract pyautogui opencv-python pillow
  - Tesseract installed (https://github.com/UB-Mannheim/tesseract/wiki)
  - WhatsApp Desktop app OR WhatsApp Web open in Chrome

LIMITATION:
  - Button detection uses image templates in assets/whatsapp_templates/
    You must screenshot your own accept/decline buttons once and save them there.
    See README in assets/ for instructions.
"""

import time
import threading
import os
import re
import pyautogui
import pytesseract
from PIL import Image

# --- Config ------------------------------------------------------------------

CHECK_INTERVAL   = 2.0       # seconds between screen checks
CALL_KEYWORDS    = ["incoming", "voice call", "video call", "whatsapp call", "calling"]
BUSY_MESSAGE     = "Sorry, I'm busy right now. Will call you back soon! 🙏"
ASSETS_DIR       = os.path.join(os.path.dirname(__file__), "..", "assets", "whatsapp_templates")

# Tesseract path (Windows default)
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# --- State -------------------------------------------------------------------

_watcher_thread: threading.Thread | None = None
_stop_event = threading.Event()
_call_detected = False
_call_contact  = "Unknown"
_on_call_detected_callback = None   # set by Jarvis to trigger voice alert


# --- Setup -------------------------------------------------------------------

def _setup_tesseract():
    env = os.environ.get("TESSERACT_CMD")
    if env and os.path.isfile(env):
        pytesseract.pytesseract.tesseract_cmd = env
        return
    for p in _TESSERACT_PATHS:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return


# --- Core watcher loop -------------------------------------------------------

def _watch_loop():
    global _call_detected, _call_contact
    _setup_tesseract()

    while not _stop_event.is_set():
        try:
            screenshot = pyautogui.screenshot()
            text = pytesseract.image_to_string(screenshot).lower()

            if any(kw in text for kw in CALL_KEYWORDS):
                if not _call_detected:
                    _call_detected = True
                    _call_contact = _extract_contact_name(text)
                    print(f"\n📞  Incoming call detected from: {_call_contact}")
                    if _on_call_detected_callback:
                        _on_call_detected_callback(_call_contact)
            else:
                _call_detected = False

        except Exception as e:
            pass  # Don't crash the watcher on screenshot errors

        time.sleep(CHECK_INTERVAL)


def _extract_contact_name(ocr_text: str) -> str:
    """Try to extract caller name from OCR text near call keywords."""
    lines = ocr_text.split("\n")
    for i, line in enumerate(lines):
        if any(kw in line for kw in CALL_KEYWORDS):
            # Try line above (usually has contact name)
            if i > 0 and lines[i-1].strip():
                name = lines[i-1].strip().title()
                # Filter out garbage OCR
                if len(name) > 2 and re.match(r"^[A-Za-z\s]+$", name):
                    return name
    return "Unknown"


# --- Public API --------------------------------------------------------------

def start_call_watcher(on_detected=None):
    """
    Start watching for incoming WhatsApp calls in background.
    on_detected(contact_name) is called when a call is detected.
    """
    global _watcher_thread, _on_call_detected_callback
    _on_call_detected_callback = on_detected
    _stop_event.clear()
    _watcher_thread = threading.Thread(target=_watch_loop, daemon=True)
    _watcher_thread.start()
    return "Call watcher started."


def stop_call_watcher():
    _stop_event.set()
    return "Call watcher stopped."


def is_call_active() -> bool:
    return _call_detected


def get_caller() -> str:
    return _call_contact


def accept_call() -> str:
    """Click the Accept (green) button."""
    template = os.path.join(ASSETS_DIR, "accept_call.png")
    return _click_button(template, "Accept")


def decline_call() -> str:
    """Click the Decline (red) button."""
    template = os.path.join(ASSETS_DIR, "decline_call.png")
    return _click_button(template, "Decline")


def decline_and_send_busy(contact: str = None) -> str:
    """
    Decline the call, then send a 'busy' message to the caller.
    """
    result = decline_call()

    # Send busy message via WhatsApp Web
    try:
        target = contact or _call_contact
        if target and target != "Unknown":
            from jarvis_addons.whatsapp.whatsapp_web import send_whatsapp_message
            time.sleep(1.5)
            send_whatsapp_message(target, BUSY_MESSAGE)
            return f"Declined call from {target} and sent busy message."
        return f"{result} (Could not identify caller to send message.)"
    except Exception as e:
        return f"Declined call. Failed to send message: {e}"


def _click_button(template_path: str, label: str) -> str:
    """
    Find a button on screen using image template matching and click it.
    Requires a screenshot of the button saved in assets/whatsapp_templates/
    """
    if not os.path.exists(template_path):
        return (
            f"Template '{os.path.basename(template_path)}' not found. "
            f"Please screenshot your {label} button and save it to: {template_path}"
        )

    try:
        location = pyautogui.locateCenterOnScreen(
            template_path,
            confidence=0.8,
            grayscale=True
        )
        if location:
            pyautogui.click(location.x, location.y)
            return f"Clicked {label} button."
        else:
            return f"{label} button not found on screen."
    except pyautogui.ImageNotFoundException:
        return f"{label} button not visible on screen right now."
    except Exception as e:
        return f"Error clicking {label}: {e}"
