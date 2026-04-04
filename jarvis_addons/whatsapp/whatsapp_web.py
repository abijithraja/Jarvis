"""
WhatsApp Web Controller
Requires: WhatsApp Web logged in on Chrome (session saved automatically)
pip install selenium webdriver-manager

WHAT THIS CAN DO:
  - Send text messages to any contact or number
  - Open a chat / contact
  - Initiate a voice call (click the call button)
  - Initiate a video call
  - Send files/images
  - Read last N messages from a chat
  - Search contacts

WHAT IT CANNOT DO (hardware limitation):
  - Answer/decline incoming calls programmatically via API
    (Use whatsapp_call_watcher.py for that — it uses image detection)
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Persistent Chrome profile so you only scan QR once
CHROME_PROFILE = os.path.join(os.path.expanduser("~"), ".jarvis_whatsapp_profile")
WA_URL = "https://web.whatsapp.com"

# XPaths (update if WhatsApp Web changes its layout)
XPATH_SEARCH    = '//div[@contenteditable="true"][@data-tab="3"]'
XPATH_MSG_INPUT = '//div[@contenteditable="true"][@data-tab="10"]'
XPATH_CALL_BTN  = '//div[@title="Voice call"]'
XPATH_VIDEO_BTN = '//div[@title="Video call"]'
XPATH_MSGS      = '//div[contains(@class,"message-in") or contains(@class,"message-out")]//span[@class="selectable-text"]'


class WhatsAppWeb:
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless

    def _get_driver(self) -> webdriver.Chrome:
        if self.driver:
            return self.driver
        opts = Options()
        opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
        opts.add_argument("--profile-directory=Default")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--start-maximized")
        if self.headless:
            opts.add_argument("--headless=new")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        return self.driver

    def open(self) -> str:
        """Open WhatsApp Web. First run will need QR scan."""
        driver = self._get_driver()
        driver.get(WA_URL)
        try:
            # Wait up to 30s for main chat list to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, XPATH_SEARCH))
            )
            return "WhatsApp Web is open and ready."
        except Exception:
            return "WhatsApp Web opened. Please scan the QR code if prompted."

    def send_message(self, contact: str, message: str) -> str:
        """Send a text message to a contact name or phone number."""
        driver = self._get_driver()
        driver.get(WA_URL)

        try:
            wait = WebDriverWait(driver, 20)

            # Click search box and type contact
            search = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_SEARCH)))
            search.clear()
            search.send_keys(contact)
            time.sleep(1.5)
            search.send_keys(Keys.ENTER)
            time.sleep(1.5)

            # Find message input and type
            msg_box = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_MSG_INPUT)))
            msg_box.click()

            # Handle multi-line messages
            for line in message.split('\n'):
                msg_box.send_keys(line)
                msg_box.send_keys(Keys.SHIFT, Keys.ENTER)
            msg_box.send_keys(Keys.ENTER)

            time.sleep(1)
            return f"Message sent to {contact}."

        except Exception as e:
            return f"Failed to send message: {e}"

    def send_to_number(self, phone: str, message: str) -> str:
        """
        Send message directly to a phone number (no need to save contact).
        phone format: +91XXXXXXXXXX or 91XXXXXXXXXX
        """
        phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        driver = self._get_driver()
        url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
        driver.get(url)

        try:
            wait = WebDriverWait(driver, 20)
            msg_box = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_MSG_INPUT)))
            time.sleep(1)
            msg_box.send_keys(Keys.ENTER)
            time.sleep(1)
            return f"Message sent to +{phone}."
        except Exception as e:
            return f"Failed to send to number: {e}"

    def make_voice_call(self, contact: str) -> str:
        """Open a chat and click the Voice Call button."""
        result = self._open_chat(contact)
        if "Error" in result:
            return result

        try:
            wait = WebDriverWait(self.driver, 10)
            call_btn = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_CALL_BTN)))
            call_btn.click()
            time.sleep(1)
            return f"Calling {contact} on WhatsApp..."
        except Exception as e:
            return f"Could not start call: {e}"

    def make_video_call(self, contact: str) -> str:
        """Open a chat and click the Video Call button."""
        result = self._open_chat(contact)
        if "Error" in result:
            return result

        try:
            wait = WebDriverWait(self.driver, 10)
            video_btn = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_VIDEO_BTN)))
            video_btn.click()
            time.sleep(1)
            return f"Starting video call with {contact}..."
        except Exception as e:
            return f"Could not start video call: {e}"

    def read_messages(self, contact: str, count: int = 5) -> str:
        """Read the last N messages from a chat."""
        result = self._open_chat(contact)
        if "Error" in result:
            return result

        try:
            time.sleep(2)
            msg_elements = self.driver.find_elements(By.XPATH, XPATH_MSGS)
            msgs = [el.text for el in msg_elements if el.text.strip()]
            recent = msgs[-count:] if len(msgs) >= count else msgs
            if not recent:
                return f"No messages found in {contact}'s chat."
            return f"Last {len(recent)} messages from {contact}:\n" + "\n".join(
                f"  • {m}" for m in recent
            )
        except Exception as e:
            return f"Could not read messages: {e}"

    def send_file(self, contact: str, file_path: str) -> str:
        """Send a file or image to a contact."""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"

        result = self._open_chat(contact)
        if "Error" in result:
            return result

        try:
            wait = WebDriverWait(self.driver, 10)
            # Click the attachment (paperclip) button
            attach = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@title="Attach"]')
            ))
            attach.click()
            time.sleep(1)

            # Click "Document" option and send file path
            file_input = self.driver.find_element(
                By.XPATH, '//input[@accept="*"]'
            )
            file_input.send_keys(os.path.abspath(file_path))
            time.sleep(2)

            # Click Send
            send_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@aria-label="Send"]')
            ))
            send_btn.click()
            time.sleep(1)
            return f"File sent to {contact}."
        except Exception as e:
            return f"Failed to send file: {e}"

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _open_chat(self, contact: str) -> str:
        driver = self._get_driver()
        driver.get(WA_URL)
        try:
            wait = WebDriverWait(driver, 20)
            search = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_SEARCH)))
            search.clear()
            search.send_keys(contact)
            time.sleep(1.5)
            search.send_keys(Keys.ENTER)
            time.sleep(1.5)
            return f"Opened {contact}."
        except Exception as e:
            return f"Error opening chat: {e}"


# Module-level singleton
_wa = WhatsAppWeb()


def send_whatsapp_message(contact: str, message: str) -> str:
    return _wa.send_message(contact, message)

def send_whatsapp_to_number(phone: str, message: str) -> str:
    return _wa.send_to_number(phone, message)

def whatsapp_voice_call(contact: str) -> str:
    return _wa.make_voice_call(contact)

def whatsapp_video_call(contact: str) -> str:
    return _wa.make_video_call(contact)

def whatsapp_read_messages(contact: str, count: int = 5) -> str:
    return _wa.read_messages(contact, count)

def whatsapp_send_file(contact: str, file_path: str) -> str:
    return _wa.send_file(contact, file_path)

def open_whatsapp() -> str:
    return _wa.open()
