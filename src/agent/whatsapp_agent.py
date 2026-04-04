"""
WhatsApp Web automation for Jarvis.

Features:
- Open WhatsApp Web with a persistent profile
- Send messages to a contact with emoji aliases
- Start voice calls
- Detect incoming calls and announce them
- Accept or decline incoming calls
- Convey a message to the caller
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import threading
import time
from difflib import SequenceMatcher
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from src.memory import state
from src.tts.speaker import speak


# Alias words are mapped to emoji codepoints so this file stays ASCII-safe.
_EMOJI_ALIASES = {
    "smile": "\U0001F60A",
    "happy": "\U0001F60A",
    "laugh": "\U0001F602",
    "lol": "\U0001F602",
    "heart": "\u2764\ufe0f",
    "love": "\u2764\ufe0f",
    "thumbs up": "\U0001F44D",
    "ok": "\U0001F44C",
    "fire": "\U0001F525",
    "party": "\U0001F973",
    "sad": "\U0001F622",
    "cry": "\U0001F622",
    "wink": "\U0001F609",
    "cool": "\U0001F60E",
    "pray": "\U0001F64F",
    "clap": "\U0001F44F",
}

_WHATSAPP_MISHEAR_PATTERNS = [
    (r"\bwahts?\s*app\b", "whatsapp"),
    (r"\bwatts?\s*app\b", "whatsapp"),
    (r"\bwhats?ap\b", "whatsapp"),
    (r"\bwhats?appening\b", "whatsapp"),
    (r"\bwaterpan\b", "whatsapp"),
    (r"\bmessgae\b", "message"),
    (r"\bmesage\b", "message"),
    (r"\bmssage\b", "message"),
]


class WhatsAppAgent:
    WEB_URL = "https://web.whatsapp.com/"
    VALID_MODES = {"desktop", "web", "auto"}
    STORE_APPSFOLDER_IDS = [
        r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
        r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!WhatsAppDesktop",
    ]

    def __init__(self):
        self._driver: Optional[webdriver.Chrome] = None
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()

        self._last_contact: Optional[str] = None
        self._pending_message_contact: Optional[str] = None
        self._last_incoming_caller: Optional[str] = None
        self._pending_call: Optional[dict] = None
        self._last_call_notice_sig: Optional[str] = None

        requested_mode = os.environ.get("JARVIS_WHATSAPP_MODE", "desktop").strip().lower()
        self._mode = requested_mode if requested_mode in self.VALID_MODES else "desktop"

        self._profile_dir = os.path.join(os.getcwd(), ".jarvis_whatsapp_profile")
        os.makedirs(self._profile_dir, exist_ok=True)

    def set_mode(self, mode: str) -> str:
        mode = (mode or "").strip().lower()
        if mode not in self.VALID_MODES:
            return "Mode must be desktop, web, or auto."

        with self._lock:
            self._mode = mode

        if mode == "desktop":
            return "Okay, I'll use WhatsApp Desktop by default."
        if mode == "web":
            return "Okay, I'll use WhatsApp Web by default."
        return "Okay, I'll auto-pick Desktop first and Web as fallback."

    # ------------------------------
    # Public actions
    # ------------------------------

    def open_whatsapp(self) -> str:
        with self._lock:
            if self._should_use_desktop_locked():
                if self._open_desktop_locked():
                    state.current_app = "whatsapp"
                    return "WhatsApp Desktop is open and ready."
                if self._mode == "desktop":
                    return (
                        "I couldn't open WhatsApp Desktop. Make sure the app is installed, "
                        "or say use whatsapp web mode."
                    )

            return self._open_web_locked()

    def send_message(self, contact: str, message: str) -> str:
        contact = _clean_contact_name(contact)
        if not contact:
            return "Tell me who to message."

        message = _apply_emoji_aliases(message)
        if not message:
            return "Tell me what message to send."

        with self._lock:
            if self._should_use_desktop_locked():
                return self._send_message_desktop_locked(contact, message)

            if not self._open_chat_locked(contact):
                return f"I could not find a matching WhatsApp chat for {contact}."

            box = self._find_first_locked(self._message_box_selectors(), timeout=8, clickable=True)
            if not box:
                return "I opened WhatsApp, but I could not find the message box."

            box.click()
            box.send_keys(message)
            box.send_keys(Keys.ENTER)
            self._last_contact = contact
            self._pending_message_contact = None
            state.current_app = "whatsapp"

        return f"Sent WhatsApp message to {contact}: {message}"

    def start_voice_call(self, contact: str) -> str:
        contact = _clean_contact_name(contact)
        if not contact:
            return "Tell me who to call on WhatsApp."

        with self._lock:
            if self._should_use_desktop_locked():
                return self._start_voice_call_desktop_locked(contact)

            if not self._open_chat_locked(contact):
                return f"I could not find a matching WhatsApp chat for {contact}."

            call_btn = self._find_first_locked(self._voice_call_button_selectors(), timeout=8, clickable=True)
            if not call_btn:
                return "I found the chat, but couldn't find the voice call button."

            call_btn.click()
            self._last_contact = contact
            state.current_app = "whatsapp"

        return f"Starting WhatsApp voice call to {contact}."

    def accept_call(self) -> str:
        with self._lock:
            if self._should_use_desktop_locked() and not self._driver:
                return (
                    "Accept/decline automation is available in WhatsApp Web mode. "
                    "Say use whatsapp web mode if you want automatic incoming-call controls."
                )

            self._ensure_driver_locked()
            btn = self._find_first_locked(self._accept_call_selectors(), timeout=4, clickable=True)
            if not btn:
                return "I could not find an incoming call to accept right now."

            btn.click()
            caller = self._pending_caller_locked()
            self._pending_call = None

        return f"Accepted call from {caller}."

    def decline_call(self) -> str:
        with self._lock:
            if self._should_use_desktop_locked() and not self._driver:
                return (
                    "Accept/decline automation is available in WhatsApp Web mode. "
                    "Say use whatsapp web mode if you want automatic incoming-call controls."
                )

            self._ensure_driver_locked()
            btn = self._find_first_locked(self._decline_call_selectors(), timeout=4, clickable=True)
            if not btn:
                return "I could not find an incoming call to decline right now."

            btn.click()
            caller = self._pending_caller_locked()
            self._pending_call = None

        return f"Declined call from {caller}."

    def convey_message_to_caller(self, message: str) -> str:
        message = _apply_emoji_aliases(message)
        if not message:
            return "Tell me what to convey."

        with self._lock:
            caller = self._pending_caller_locked()

        if not caller or caller == "the caller":
            return "I don't know who the current caller is yet. Ask me to accept or decline first, or say their contact name."

        send_result = self.send_message(caller, message)

        with self._lock:
            decline_btn = self._find_first_locked(self._decline_call_selectors(), timeout=2, clickable=True)
            if decline_btn:
                try:
                    decline_btn.click()
                    self._pending_call = None
                    return f"Declined the call and {send_result.lower()}"
                except Exception:
                    pass

        return send_result

    def start_monitor(self) -> str:
        with self._lock:
            if self._should_use_desktop_locked() and not self._driver:
                return (
                    "Incoming-call monitor works in WhatsApp Web mode. "
                    "Say use whatsapp web mode to enable it."
                )

            self._ensure_driver_locked()
            self._start_monitor_locked()
        return "WhatsApp call monitor is active."

    def stop_monitor(self) -> str:
        with self._lock:
            if not self._monitor_thread or not self._monitor_thread.is_alive():
                return "WhatsApp call monitor is already stopped."
            self._monitor_stop.set()
            thread = self._monitor_thread

        thread.join(timeout=2)
        return "WhatsApp call monitor stopped."

    def check_incoming_call(self) -> str:
        with self._lock:
            if self._should_use_desktop_locked() and not self._driver:
                return (
                    "Incoming-call detection works in WhatsApp Web mode. "
                    "Say use whatsapp web mode to check incoming calls automatically."
                )

            self._ensure_driver_locked()
            info = self._detect_incoming_call_locked()
            if not info:
                return "No incoming WhatsApp call detected right now."
            self._pending_call = info
            caller = info.get("caller") or "unknown caller"
        return f"Incoming WhatsApp call from {caller}. Say attend call, decline call, or convey message."

    def _open_web_locked(self) -> str:
        driver = self._ensure_driver_locked()
        if not driver:
            return "I could not start Chrome for WhatsApp."

        if "web.whatsapp.com" not in (driver.current_url or ""):
            driver.get(self.WEB_URL)

        state.current_app = "whatsapp"

        ready = self._find_first_locked(self._search_box_selectors(), timeout=10, clickable=False)
        self._start_monitor_locked()

        if ready:
            return "WhatsApp Web is open and ready."
        return (
            "WhatsApp Web opened. If this is your first time, scan the QR code once. "
            "I will keep watching for incoming calls."
        )

    def _should_use_desktop_locked(self) -> bool:
        if self._mode == "web":
            return False
        if platform.system() != "Windows":
            return False
        if self._mode == "desktop":
            return True

        # auto mode
        return self._has_whatsapp_window_locked() or bool(self._find_whatsapp_desktop_exe())

    def _has_whatsapp_window_locked(self) -> bool:
        try:
            import pygetwindow as gw

            for title in gw.getAllTitles():
                if _is_likely_whatsapp_window_title(title):
                    return True
            return False
        except Exception:
            return False

    def _open_desktop_locked(self) -> bool:
        if platform.system() != "Windows":
            return False

        if self._focus_whatsapp_window_locked():
            state.current_app = "whatsapp"
            return True

        exe = self._find_whatsapp_desktop_exe()
        launch_attempts = []
        if exe:
            launch_attempts.append(("exe", exe))
        launch_attempts.extend(("appsfolder", app_id) for app_id in self.STORE_APPSFOLDER_IDS)
        launch_attempts.append(("uri", "whatsapp://"))
        launch_attempts.append(("uri", "whatsapp://send"))

        for kind, value in launch_attempts:
            try:
                if kind == "exe":
                    subprocess.Popen([value])
                elif kind == "appsfolder":
                    subprocess.Popen(["explorer.exe", value])
                elif kind == "uri":
                    if hasattr(os, "startfile"):
                        os.startfile(value)  # type: ignore[attr-defined]
                    else:
                        subprocess.Popen(["cmd", "/c", "start", "", value])
                else:
                    subprocess.Popen(value, shell=True)

                for _ in range(10):
                    if self._focus_whatsapp_window_locked() or self._has_whatsapp_window_locked():
                        state.current_app = "whatsapp"
                        return True
                    time.sleep(0.2)
            except Exception:
                continue

        for _ in range(30):
            if self._focus_whatsapp_window_locked():
                state.current_app = "whatsapp"
                return True
            time.sleep(0.2)

        return False

    def _focus_whatsapp_window_locked(self) -> bool:
        try:
            import pygetwindow as gw
        except Exception:
            return False

        windows = []
        try:
            for candidate in gw.getAllWindows():
                title = getattr(candidate, "title", "")
                if _is_likely_whatsapp_window_title(title):
                    windows.append(candidate)
        except Exception:
            windows = []

        # Backward-compatible fallback if getAllWindows is unavailable.
        if not windows:
            for title in ["WhatsApp", "whatsapp"]:
                try:
                    for candidate in gw.getWindowsWithTitle(title):
                        if _is_likely_whatsapp_window_title(getattr(candidate, "title", "")):
                            windows.append(candidate)
                except Exception:
                    continue

        for w in windows:
            try:
                if not (w.title or "").strip():
                    continue
                if getattr(w, "isMinimized", False):
                    w.restore()
                w.activate()
                for _ in range(6):
                    if self._is_whatsapp_foreground_locked():
                        return True
                    time.sleep(0.15)
            except Exception:
                continue

        return self._is_whatsapp_foreground_locked()

    def _is_whatsapp_foreground_locked(self) -> bool:
        try:
            import pygetwindow as gw

            active = gw.getActiveWindow()
            title = ((active.title if active else "") or "")
            return _is_likely_whatsapp_window_title(title)
        except Exception:
            return False

    def _find_whatsapp_desktop_exe(self) -> Optional[str]:
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "WhatsApp", "WhatsApp.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "WhatsApp", "WhatsApp.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "WhatsApp", "WhatsApp.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "WhatsApp", "WhatsApp.exe"),
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def _open_chat_desktop_locked(self, contact: str) -> bool:
        if not self._open_desktop_locked():
            return False

        if not self._is_whatsapp_foreground_locked():
            return False

        try:
            import pyautogui
        except Exception:
            return False

        # WhatsApp Desktop search picks the best/first matching contact, so exact title is not required.
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.25)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        pyautogui.write(contact, interval=0.03)
        time.sleep(0.45)
        pyautogui.press("down")
        time.sleep(0.08)
        pyautogui.press("enter")
        time.sleep(0.4)
        pyautogui.press("esc")
        time.sleep(0.1)

        if not self._focus_message_box_desktop_locked():
            return False

        self._last_contact = contact
        state.current_app = "whatsapp"
        return True

    def _send_message_desktop_locked(self, contact: str, message: str) -> str:
        if not self._open_chat_desktop_locked(contact):
            return "I couldn't safely focus WhatsApp Desktop chat. I did not type anything."

        try:
            import pyautogui
        except Exception:
            return "Desktop message automation needs pyautogui installed."

        if not self._focus_message_box_desktop_locked():
            return "I found the chat, but could not focus the message box. Please click inside chat once and try again."

        if _contains_non_ascii(message) and _set_clipboard_text(message):
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.write(message, interval=0.02)
        pyautogui.press("enter")
        self._pending_message_contact = None
        state.current_app = "whatsapp"
        return f"Sent WhatsApp Desktop message to {contact}: {message}"

    def _focus_message_box_desktop_locked(self) -> bool:
        if platform.system() != "Windows":
            return False

        if not self._focus_whatsapp_window_locked():
            return False

        try:
            import pyautogui
        except Exception:
            return False

        try:
            pyautogui.press("esc")
            time.sleep(0.07)

            win = self._get_whatsapp_window_locked()
            if not win:
                return self._is_whatsapp_foreground_locked()

            left = int(getattr(win, "left", 0))
            top = int(getattr(win, "top", 0))
            width = max(240, int(getattr(win, "width", 0)))
            height = max(240, int(getattr(win, "height", 0)))

            # Composer is usually in the lower-right conversation pane.
            input_x = left + int(width * 0.73)
            input_y = top + int(height * 0.93)

            pyautogui.click(input_x, input_y)
            time.sleep(0.08)
            pyautogui.click(input_x, input_y)
            time.sleep(0.08)
            return self._is_whatsapp_foreground_locked()
        except Exception:
            return False

    def _get_whatsapp_window_locked(self):
        try:
            import pygetwindow as gw
        except Exception:
            return None

        try:
            active = gw.getActiveWindow()
            if active and _is_likely_whatsapp_window_title(getattr(active, "title", "")):
                return active
        except Exception:
            pass

        best = None
        best_area = -1
        try:
            for candidate in gw.getAllWindows():
                title = getattr(candidate, "title", "")
                if not _is_likely_whatsapp_window_title(title):
                    continue
                area = int(getattr(candidate, "width", 0)) * int(getattr(candidate, "height", 0))
                if area > best_area:
                    best = candidate
                    best_area = area
        except Exception:
            return None

        return best

    def _start_voice_call_desktop_locked(self, contact: str) -> str:
        if not self._open_chat_desktop_locked(contact):
            return "I couldn't open WhatsApp Desktop chat for that contact."

        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "shift", "c")
            return (
                f"Opened {contact} in WhatsApp Desktop and triggered voice-call shortcut. "
                "If call did not start, click the call icon once."
            )
        except Exception:
            return (
                f"Opened {contact} in WhatsApp Desktop. "
                "Please click the voice-call icon once."
            )

    # ------------------------------
    # Internal browser helpers
    # ------------------------------

    def _ensure_driver_locked(self) -> Optional[webdriver.Chrome]:
        if self._driver:
            try:
                _ = self._driver.title
                return self._driver
            except Exception:
                try:
                    self._driver.quit()
                except Exception:
                    pass
                self._driver = None

        try:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument(f"--user-data-dir={self._profile_dir}")
            options.add_argument("--profile-directory=Default")
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            return self._driver
        except WebDriverException:
            return None

    def _open_chat_locked(self, contact: str) -> bool:
        driver = self._ensure_driver_locked()
        if not driver:
            return False

        self._start_monitor_locked()

        if "web.whatsapp.com" not in (driver.current_url or ""):
            driver.get(self.WEB_URL)

        search = self._find_first_locked(self._search_box_selectors(), timeout=12, clickable=True)
        if not search:
            return False

        search.click()
        search.send_keys(Keys.CONTROL, "a")
        search.send_keys(Keys.BACKSPACE)
        search.send_keys(contact)
        time.sleep(1.0)

        contact_lit = _xpath_literal(contact)
        selectors = [
            (By.XPATH, f"//span[@title={contact_lit}]"),
            (By.XPATH, f"//span[contains(@title, {contact_lit})]"),
            (By.XPATH, f"//div[@role='grid']//span[contains(@title, {contact_lit})]"),
        ]
        chat_row = self._find_first_locked(selectors, timeout=5, clickable=True)

        if not chat_row:
            chat_row = self._pick_best_chat_match_locked(contact)

        if chat_row:
            try:
                chat_row.click()
                return True
            except Exception:
                pass

        # Fallback: press Enter on first search result.
        try:
            search.send_keys(Keys.ENTER)
            active = self._wait_for_active_chat_locked(timeout=2.5)
            return bool(active)
        except Exception:
            return False

    def _pick_best_chat_match_locked(self, contact: str):
        if not self._driver:
            return None

        contact_l = (contact or "").strip().lower()
        best_el = None
        best_score = 0.0

        try:
            candidates = self._driver.find_elements(By.XPATH, "//div[@role='grid']//span[@title]")
        except Exception:
            candidates = []

        for el in candidates:
            try:
                if not el.is_displayed() or not el.is_enabled():
                    continue
                title = (el.get_attribute("title") or el.text or "").strip()
                if not title:
                    continue

                score = _name_match_score(contact_l, title.lower())
                if score > best_score:
                    best_score = score
                    best_el = el
            except Exception:
                continue

        if best_el and best_score >= 0.33:
            return best_el

        # Final fallback to first visible row, if present.
        return best_el

    def _wait_for_active_chat_locked(self, timeout: float = 2.5) -> Optional[str]:
        deadline = time.time() + max(0.2, timeout)
        while time.time() < deadline:
            active = self._active_chat_name_locked()
            if active:
                return active
            time.sleep(0.2)
        return None

    def _active_chat_name_locked(self) -> Optional[str]:
        el = self._find_first_locked(
            [
                (By.XPATH, "//header//span[@dir='auto' and @title]"),
                (By.XPATH, "//header//h1//span[@dir='auto']"),
            ],
            timeout=2,
            clickable=False,
        )
        if not el:
            return None
        try:
            name = (el.get_attribute("title") or el.text or "").strip()
            return name or None
        except Exception:
            return None

    def _find_first_locked(self, selectors: list[tuple], timeout: float, clickable: bool) -> Optional[object]:
        if not self._driver:
            return None

        deadline = time.time() + max(timeout, 0.2)
        while True:
            for by, value in selectors:
                try:
                    elements = self._driver.find_elements(by, value)
                except Exception:
                    elements = []

                for el in elements:
                    try:
                        if not el.is_displayed():
                            continue
                        if clickable and not el.is_enabled():
                            continue
                        return el
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue

            if time.time() >= deadline:
                break
            time.sleep(0.2)

        return None

    def _start_monitor_locked(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        while not self._monitor_stop.is_set():
            notify = None
            wait_for_driver = False
            try:
                with self._lock:
                    if not self._driver:
                        wait_for_driver = True
                    else:
                        info = self._detect_incoming_call_locked()
                        if info:
                            self._pending_call = info
                            caller = info.get("caller") or "unknown caller"
                            sig = f"{caller}:{int(info.get('time', 0) // 12)}"
                            if sig != self._last_call_notice_sig:
                                self._last_call_notice_sig = sig
                                notify = (
                                    f"Incoming WhatsApp call from {caller}. "
                                    "Say attend call, decline call, or convey message."
                                )
            except Exception:
                notify = None

            if wait_for_driver:
                time.sleep(1.0)
                continue

            if notify:
                print(f"\n\U0001F4DE  {notify}")
                try:
                    speak(notify)
                except Exception:
                    pass

            time.sleep(2.0)

    def _detect_incoming_call_locked(self) -> Optional[dict]:
        if not self._driver:
            return None

        has_incoming_text = self._find_first_locked(self._incoming_text_selectors(), timeout=0.6, clickable=False)
        has_accept_button = self._find_first_locked(self._accept_call_selectors(), timeout=0.6, clickable=True)

        if not has_incoming_text and not has_accept_button:
            return None

        caller = self._extract_caller_locked()
        self._last_incoming_caller = caller
        return {"caller": caller, "time": time.time()}

    def _extract_caller_locked(self) -> str:
        name_el = self._find_first_locked(
            [
                (By.XPATH, "//span[@title and @dir='auto']"),
                (By.XPATH, "//header//span[@title]"),
            ],
            timeout=0.8,
            clickable=False,
        )
        if name_el:
            try:
                name = (name_el.get_attribute("title") or name_el.text or "").strip()
                if name:
                    return name
            except Exception:
                pass

        if self._last_contact:
            return self._last_contact

        return "the caller"

    def _pending_caller_locked(self) -> str:
        if self._pending_call and self._pending_call.get("caller"):
            return self._pending_call["caller"]
        if self._last_incoming_caller:
            return self._last_incoming_caller
        return "the caller"

    @staticmethod
    def _search_box_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//div[@role='textbox' and contains(@aria-label, 'Search')]"),
            (By.XPATH, "//div[@contenteditable='true' and (@data-tab='3' or @data-tab='10')]"),
            (By.XPATH, "//div[@title='Search input textbox']"),
        ]

    @staticmethod
    def _message_box_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//footer//div[@role='textbox' and @contenteditable='true']"),
            (By.XPATH, "//div[@title='Type a message']"),
            (By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"),
        ]

    @staticmethod
    def _voice_call_button_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//header//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'voice') and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'call')]"),
            (By.XPATH, "//header//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'call')]"),
            (By.XPATH, "//header//*[name()='button']//*[contains(@data-icon,'call')]/ancestor::button"),
        ]

    @staticmethod
    def _incoming_text_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'incoming') and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'call')]"),
            (By.XPATH, "//*[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'incoming') and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'call')]"),
        ]

    @staticmethod
    def _accept_call_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept') and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'call')]"),
            (By.XPATH, "//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'answer') and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'call')]"),
            (By.XPATH, "//*[contains(@data-icon,'accept')]/ancestor::button"),
        ]

    @staticmethod
    def _decline_call_selectors() -> list[tuple]:
        return [
            (By.XPATH, "//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'decline') and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'call')]"),
            (By.XPATH, "//button[contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'reject') and contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'call')]"),
            (By.XPATH, "//*[contains(@data-icon,'decline')]/ancestor::button"),
            (By.XPATH, "//*[contains(@data-icon,'x')]/ancestor::button"),
        ]


_agent = WhatsAppAgent()


def is_whatsapp_intent(text: str) -> bool:
    lower = _normalize_whatsapp_text(text).lower()
    direct = bool(re.search(r"\bwhatsapp\b|\bwhats app\b", lower))
    send_phrase = bool(re.search(r"\b(send|text|message)\b", lower))
    call_phrase = bool(re.search(r"\b(call|voice call)\b", lower))
    target_phrase = bool(re.search(r"\b(send|text|message)\b.*\bto\b", lower))
    compact_send_phrase = bool(re.search(r"\b(send|text)\b\s+[a-z0-9_.-]+\s+\S+", lower))
    open_then_send = bool(re.search(r"\bopen\b.*\bwhatsapp\b.*\b(send|text|message|call)\b", lower))
    active_context = state.current_app == "whatsapp"
    pending_context = bool(_agent._pending_message_contact)
    call_flow = any(
        phrase in lower
        for phrase in [
            "attend call",
            "answer call",
            "accept call",
            "decline call",
            "reject call",
            "incoming call",
            "convey message",
            "send message to caller",
        ]
    )
    return (
        direct
        or call_flow
        or target_phrase
        or open_then_send
        or pending_context
        or (active_context and (send_phrase or call_phrase or compact_send_phrase))
    )


def handle_whatsapp_command(text: str) -> Optional[str]:
    if not text:
        return None

    normalized_text = _normalize_whatsapp_text(text)
    lower = normalized_text.lower().strip()
    if _is_likely_jarvis_whatsapp_echo(normalized_text):
        return None

    if not is_whatsapp_intent(normalized_text):
        return None

    # Handle chained phrases like: "open whatsapp and send message to Alex saying hi".
    if " and " in lower and "whatsapp" in lower:
        parts = [p.strip(" ,.!?") for p in re.split(r"\band\b", normalized_text, flags=re.I) if p.strip()]
        responses = []
        for part in parts:
            normalized = part
            if "whatsapp" not in part.lower():
                normalized = f"whatsapp {part}"
            result = _handle_whatsapp_single(normalized)
            if result:
                responses.append(result)
        if responses:
            return ", ".join(responses)
        return None

    return _handle_whatsapp_single(normalized_text)


def _handle_whatsapp_single(text: str) -> Optional[str]:
    normalized_text = _normalize_whatsapp_text(text)
    lower = normalized_text.lower().strip()

    if _is_likely_jarvis_whatsapp_echo(normalized_text):
        return None

    parse_inputs = [text]
    if normalized_text != text:
        parse_inputs.append(normalized_text)

    if re.search(r"\b(use|switch|set)\b.*\bwhatsapp\b.*\bdesktop\b", lower):
        return _agent.set_mode("desktop")
    if re.search(r"\b(use|switch|set)\b.*\bwhatsapp\b.*\bweb\b", lower):
        return _agent.set_mode("web")
    if re.search(r"\b(use|switch|set)\b.*\bwhatsapp\b.*\bauto\b", lower):
        return _agent.set_mode("auto")

    # Monitor controls
    if re.search(r"\b(start|enable)\b.*\b(call )?monitor\b", lower):
        return _agent.start_monitor()
    if re.search(r"\b(stop|disable)\b.*\b(call )?monitor\b", lower):
        return _agent.stop_monitor()
    if re.search(r"\b(check|status)\b.*\b(incoming )?call\b", lower):
        return _agent.check_incoming_call()

    # Open WhatsApp
    if re.search(r"\b(open|launch|start)\b.*\bwhatsapp\b", lower):
        return _agent.open_whatsapp()

    # Convey message to caller
    convey = re.search(
        r"(?:"
        r"convey(?:\s+(?:a|the))?\s+message(?:\s+to\s+(?:caller|them))?\s+(?:saying\s+)?(.+)"
        r"|"
        r"send(?:\s+(?:a|the))?\s+message\s+to\s+(?:caller|them)\s+(?:saying\s+)?(.+)"
        r")",
        text,
        re.I,
    )
    if convey:
        msg = (convey.group(1) or convey.group(2) or "").strip()
        if msg:
            return _agent.convey_message_to_caller(msg)

    # Accept or decline incoming call
    if re.search(r"\b(attend|accept|answer|pick\s*up)\b.*\bcall\b", lower):
        return _agent.accept_call()
    if re.search(r"\b(decline|reject|ignore|cut)\b.*\bcall\b", lower):
        return _agent.decline_call()

    # Start voice call
    call_target = _parse_call_target(text)
    if call_target:
        return _agent.start_voice_call(call_target)

    # Send message
    for candidate in parse_inputs:
        parsed = _parse_message_request(candidate)
        if parsed:
            contact, message = parsed
            return _agent.send_message(contact, message)

        compact = _parse_compact_contact_message_request(candidate)
        if compact:
            contact, message = compact
            return _agent.send_message(contact, message)

        send_without_to = _parse_send_without_to_message_request(candidate)
        if send_without_to:
            contact, message = send_without_to
            return _agent.send_message(contact, message)

    for candidate in parse_inputs:
        contact_only = _parse_contact_only_message_request(candidate)
        if contact_only:
            with _agent._lock:
                _agent._last_contact = contact_only
                _agent._pending_message_contact = contact_only
                state.current_app = "whatsapp"
            return f"What message should I send to {contact_only}?"

    for candidate in parse_inputs:
        content_only = _parse_message_content_only_request(candidate)
        if content_only:
            with _agent._lock:
                target = _agent._pending_message_contact or _agent._last_contact
            if target:
                return _agent.send_message(target, content_only)
            return "Who should I send the message to?"

    with _agent._lock:
        pending_target = _agent._pending_message_contact

    if pending_target:
        if re.search(r"\b(cancel|nevermind|never mind|stop)\b", lower):
            with _agent._lock:
                _agent._pending_message_contact = None
            return "Okay, canceled. I won't send that message."

        if lower in {"yes", "yeah", "yep", "ok", "okay", "sure"}:
            return f"Tell me the message to send to {pending_target}."

        # If we are waiting for message content, treat the next natural utterance as the message body.
        if lower and not any(k in lower for k in ["open whatsapp", "call", "monitor", "mode", "attend", "decline"]):
            return _agent.send_message(pending_target, text.strip())

    if "whatsapp" in lower and re.search(r"\b(send|text|message)\b", lower) and " to " not in f" {lower} ":
        return "Who should I send the message to?"

    # If it's WhatsApp-related but too vague, keep response actionable.
    if "whatsapp" in lower:
        return (
            "Tell me one of these: open WhatsApp, send message to <name> saying <text>, "
            "make WhatsApp call to <name>, attend call, decline call, or convey message <text>."
        )

    if state.current_app == "whatsapp" and any(w in lower for w in ["send", "text", "message"]):
        return "Tell me the contact and message. Example: send message to Alex saying hello."

    return None


# ------------------------------
# Parsing helpers
# ------------------------------


def _parse_message_request(text: str) -> Optional[tuple[str, str]]:
    text = _normalize_whatsapp_text(text)
    patterns = [
        r"^\s*(?:please\s+)?(?:send|text|message)(?:\s+(?:a|the))?(?:\s+whatsapp)?(?:\s+message)?\s+to\s+(.+?)\s+(?:saying|that|:)\s+(.+)\s*$",
        r"^\s*(?:please\s+)?whatsapp\s+message\s+to\s+(.+?)\s+(?:saying|that|:)\s+(.+)\s*$",
        r"^\s*(?:please\s+)?send\s+whatsapp\s+to\s+(.+?)\s*:\s*(.+)\s*$",
        r"^\s*(?:please\s+)?send\s+whatsapp\s+to\s+(.+?)\s+(.+)\s*$",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            contact = _clean_contact_name(m.group(1))
            msg = m.group(2).strip(" .")
            if contact and msg:
                if msg.lower() in {"message", "a message", "the message"}:
                    continue
                return contact, msg

    return None


def _parse_contact_only_message_request(text: str) -> Optional[str]:
    patterns = [
        r"^\s*(?:please\s+)?(?:send|text|message)(?:\s+(?:a|the))?(?:\s+whatsapp)?\s+message\s+to\s+(.+?)\.?\s*$",
        r"^\s*(?:please\s+)?(?:send|text|message)(?:\s+whatsapp)?\s+to\s+(.+?)\.?\s*$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            contact = _clean_contact_name(m.group(1))
            if contact:
                return contact
    return None


def _parse_compact_contact_message_request(text: str) -> Optional[tuple[str, str]]:
    """
    Parse compact style like: "send message to abinaya hello".
    Heuristic: first token after "to" is contact, remainder is message.
    """
    m = re.search(r"^\s*(?:please\s+)?(?:send|text|message)(?:\s+(?:a|the))?\s+message\s+to\s+(.+)$", text, re.I)
    if not m:
        return None

    tail = m.group(1).strip(" .")
    if not tail:
        return None
    if re.search(r"\b(saying|that)\b|:", tail, re.I):
        return None

    # Support comma separator: "to abinaya, hello"
    if "," in tail:
        left, right = tail.split(",", 1)
        contact = _clean_contact_name(left)
        message = right.strip(" .")
        if contact and message:
            return contact, message

    parts = tail.split()
    if len(parts) < 2:
        return None

    contact = _clean_contact_name(parts[0])
    message = " ".join(parts[1:]).strip(" .")
    if not contact or not message:
        return None
    if message.lower() in {"message", "a message", "the message"}:
        return None

    return contact, message


def _parse_send_without_to_message_request(text: str) -> Optional[tuple[str, str]]:
    """
    Parse compact style like: "send mithilesh hello buddy".
    """
    cleaned = re.sub(r"^\s*whatsapp\s+", "", (text or "").strip(), flags=re.I)

    # Avoid misreading "send whatsapp message to <name>" as contact=whatsapp.
    if re.search(r"^\s*(?:please\s+)?(?:send|text)\s+whatsapp\s+message\s+to\s+", cleaned, re.I):
        return None

    m = re.search(
        r"^(?:please\s+)?(?:send|text)(?:\s+(?:a|the))?(?:\s+message)?\s+([a-zA-Z0-9_.-]+)\s+(.+)$",
        cleaned,
        re.I,
    )
    if not m:
        return None

    contact = _clean_contact_name(m.group(1))
    message = m.group(2).strip(" .")
    if not contact or not message:
        return None
    if contact.lower() in {"to", "whatsapp", "message"}:
        return None
    if message.lower() in {"message", "a message", "the message"}:
        return None

    return contact, message


def _parse_message_content_only_request(text: str) -> Optional[str]:
    patterns = [
        r"^\s*(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:send|text|message)(?:\s+(?:a|the))?\s+message\s+(?:and\s+)?(.+)$",
        r"^\s*(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:send|text|message)\s+(?:and\s+)?(.+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        content = m.group(1).strip(" .")
        content = re.sub(r"^(to\s+\w+)$", "", content, flags=re.I).strip(" .")
        if content:
            return content
    return None


def _parse_call_target(text: str) -> Optional[str]:
    patterns = [
        r"(?:make|start|place|begin)\s+(?:a\s+)?(?:voice\s+)?(?:whatsapp\s+)?call(?:\s+to)?\s+(.+)",
        r"call\s+(.+?)\s+on\s+whatsapp",
        r"whatsapp\s+call\s+to\s+(.+)",
        r"^\s*call\s+(.+)$",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            target = _clean_contact_name(m.group(1))
            if not target:
                continue
            if re.search(r"\b(monitor|incoming|caller|status)\b", target, re.I):
                continue
            return target

    return None


def _clean_contact_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name or "").strip(" .,!?")
    cleaned = _strip_emoji_and_symbol_noise(cleaned)
    cleaned = re.sub(r"\bwhatsapp\s+desktop\s+message\s+to\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bwhatsapp\s+message\s+to\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(named|called)\b\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(on|in|at)\s+whats?\s*app\b.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bsaying\b.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r":.*$", "", cleaned)
    cleaned = re.sub(r"\b(contact|person|chat)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(please|now|right\s+now)\b", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^to\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,!?")
    return cleaned


def _strip_emoji_and_symbol_noise(text: str) -> str:
    if not text:
        return text

    out = []
    for ch in text:
        code = ord(ch)
        if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            continue
        out.append(ch)
    return "".join(out)


def _apply_emoji_aliases(message: str) -> str:
    msg = (message or "").strip()
    if not msg:
        return msg

    # Support :smile: style tokens.
    for alias, emoji in _EMOJI_ALIASES.items():
        msg = re.sub(rf":\s*{re.escape(alias)}\s*:", emoji, msg, flags=re.I)

    # Support "smile emoji" and "emoji smile" phrases.
    for alias, emoji in sorted(_EMOJI_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        msg = re.sub(rf"\b{re.escape(alias)}\s+emoji\b", emoji, msg, flags=re.I)
        msg = re.sub(rf"\bemoji\s+{re.escape(alias)}\b", emoji, msg, flags=re.I)

    if "with emoji" in msg.lower() and not _contains_emoji(msg):
        msg = re.sub(r"\bwith emoji\b", "", msg, flags=re.I).strip()
        msg = f"{msg} \U0001F60A".strip()

    return msg


def _contains_emoji(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            return True
    return False


def _contains_non_ascii(text: str) -> bool:
    return any(ord(ch) > 127 for ch in (text or ""))


def _set_clipboard_text(text: str) -> bool:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False


def _name_match_score(query: str, candidate: str) -> float:
    q = (query or "").strip().lower()
    c = (candidate or "").strip().lower()
    if not q or not c:
        return 0.0

    if q == c:
        return 1.0
    if q in c:
        return 0.9

    q_tokens = [t for t in re.split(r"\s+", q) if t]
    c_tokens = [t for t in re.split(r"\s+", c) if t]
    if not q_tokens or not c_tokens:
        return SequenceMatcher(None, q, c).ratio()

    overlap = len(set(q_tokens) & set(c_tokens)) / max(1, len(set(q_tokens)))
    ratio = SequenceMatcher(None, q, c).ratio()
    return max(ratio, 0.75 * overlap + 0.25 * ratio)


def _xpath_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'

    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def _normalize_whatsapp_text(text: str) -> str:
    normalized = text or ""
    for pattern, replacement in _WHATSAPP_MISHEAR_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized, flags=re.I)
    normalized = re.sub(r"\bwhats\s+app\b", "whatsapp", normalized, flags=re.I)
    return normalized


def _is_likely_jarvis_whatsapp_echo(text: str) -> bool:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not t:
        return False

    t = re.sub(r"^(?:jarvis\s*[:,-]?\s*)", "", t)
    patterns = [
        r"^sent whatsapp desktop message to .+?: .+",
        r"^sent whatsapp message to .+?: .+",
        r"^whatsapp desktop is open and ready\.?$",
        r"^what message should i send to .+\?$",
        r"^who should i send the message to\??$",
        r"^opened .+ in whatsapp desktop and triggered voice-call shortcut\..*$",
        r"^starting whatsapp voice call to .+\.?$",
        r"^error opening chat:.*$",
        r"^i couldn't safely focus whatsapp desktop chat\..*$",
        r"^whatsapp is not the active window, so i did not type\..*$",
    ]
    if any(re.match(p, t) for p in patterns):
        return True

    return "triggered voice-call shortcut" in t


def _is_likely_whatsapp_window_title(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return False

    # Ignore editor/browser windows that may include filenames like whatsapp_agent.py.
    noisy_context = [
        "visual studio code",
        " - code",
        "google chrome",
        "microsoft edge",
        "mozilla firefox",
        ".py",
    ]
    if any(noise in t for noise in noisy_context):
        return False

    # Typical WhatsApp Desktop window captions: "WhatsApp" or "(52) WhatsApp".
    return re.match(r"^(\(\d+\)\s*)?whatsapp(\b|$)", t) is not None
