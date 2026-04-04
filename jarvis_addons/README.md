# Jarvis Addons

Drop-in addon pack for jarvis_fixed. Put this folder next to jarvis_fixed/.

```
your_project/
├── jarvis_fixed/
│   ├── main.py
│   └── src/
└── jarvis_addons/          ← this folder
    ├── addon_dispatcher.py
    ├── whatsapp/
    ├── window_manager/
    ├── screen_reader/
    ├── desktop/
    ├── contacts/
    └── assets/
        └── whatsapp_templates/
```

---

## 1. Install dependencies

```bash
pip install selenium webdriver-manager pygetwindow pyautogui pytesseract opencv-python pyperclip pillow
```

### Tesseract OCR (for screen reading and call detection)
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
  Install to `C:\Program Files\Tesseract-OCR\`
- Linux: `sudo apt install tesseract-ocr`
- Mac: `brew install tesseract`

---

## 2. Hook into Jarvis

In `jarvis_fixed/main.py`, add this to `process_text()` **before** the LLM fallback:

```python
# At the top of main.py:
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jarvis_addons.addon_dispatcher import dispatch_addon

# In process_text(), add before the _llm_respond() call:
r = dispatch_addon(text)
if r:
    return r
```

---

## 3. WhatsApp setup

### First-time QR code scan
1. Run this once to open WhatsApp Web and scan QR:
```python
from jarvis_addons.whatsapp.whatsapp_web import open_whatsapp
open_whatsapp()
```
After scanning, the session is saved automatically in `~/.jarvis_whatsapp_profile`.
You will **never need to scan again**.

### For call detection (accept/decline/busy)
You need to screenshot your Accept and Decline buttons:

1. Get an incoming WhatsApp call on your PC (ask someone to call you)
2. Screenshot just the **green Accept button** → save as:
   `jarvis_addons/assets/whatsapp_templates/accept_call.png`
3. Screenshot just the **red Decline button** → save as:
   `jarvis_addons/assets/whatsapp_templates/decline_call.png`

These images are used by pyautogui's image-matching to find and click the buttons.

### Start call watcher (add to main.py startup):
```python
from jarvis_addons.whatsapp.call_watcher import start_call_watcher
from src.tts.speaker import speak

def on_call(caller):
    speak(f"Incoming WhatsApp call from {caller}. Say 'attend the call' or 'decline and say busy'.")

start_call_watcher(on_detected=on_call)
```

---

## 4. Save your contacts

Say to Jarvis:
- **"Save contact Mom as +919876543210"**
- **"Save contact John as +14155552671"**

Or edit `jarvis_addons/contacts/contacts.json` directly:
```json
{
  "mom": {"name": "Mom", "phone": "+919876543210"},
  "john": {"name": "John", "phone": "+14155552671"}
}
```

---

## 5. Voice commands reference

### WhatsApp
| Say | Action |
|---|---|
| "Send WhatsApp message to Mom say hello" | Send message |
| "Message +919876543210 say I'm on my way" | Message by number |
| "WhatsApp call Dad" | Voice call |
| "Video call John" | Video call |
| "Read WhatsApp messages from Priya" | Read last 5 messages |
| "Send file report.pdf to Boss on WhatsApp" | Send file |
| "Open WhatsApp" | Open WhatsApp Web |
| "Attend the call" | Accept incoming call |
| "Decline the call and say I'm busy" | Decline + send busy message |

### Window Manager
| Say | Action |
|---|---|
| "Snap Chrome to left" | Half-screen left |
| "Snap Notepad to right" | Half-screen right |
| "Maximize Chrome" | Full screen |
| "Minimize Notepad" | Minimize |
| "Tile windows side by side" | 50/50 split |
| "Arrange windows in grid" | 4-window grid |
| "Cascade windows" | Diagonal cascade |
| "Minimize all" | Show desktop |
| "Move Chrome to top right" | Position window |
| "Resize Chrome to 800 by 600" | Set exact size |
| "Make Chrome bigger" | Scale up 30% |
| "Focus Chrome" | Bring to front |
| "Close Notepad" | Close window |

### Screen Reader
| Say | Action |
|---|---|
| "What's on my screen" | Full screen description |
| "What windows are open" | List all windows |
| "Read the screen" | OCR full screen text |
| "What am I working on" | AI summary of screen |
| "Find [text] on screen" | Search for text on screen |
| "What apps are running" | Process list |
| "Read the clipboard" | Clipboard contents |
| "Kill Chrome" | Force close process |

### Contacts
| Say | Action |
|---|---|
| "Save contact Mom as +919876543210" | Save contact |
| "What is Mom's number" | Look up number |
| "Show all contacts" | List all contacts |
| "Delete contact John" | Remove contact |

---

## 6. What's truly NOT possible

| Feature | Why | Workaround |
|---|---|---|
| Read WhatsApp notifications from taskbar | OS notification API locked | Use call_watcher OCR |
| Accept calls via WhatsApp API | WhatsApp has no call API | Image-match button click |
| Send WhatsApp without Chrome/phone | WhatsApp requires linked device | Keep Chrome + phone linked |
| Control WhatsApp Desktop calls | App doesn't expose call controls | OCR + button click |

---

## 7. Required: add call watcher images

Save screenshots of your WhatsApp call buttons here:
```
jarvis_addons/assets/whatsapp_templates/
├── accept_call.png    ← screenshot of green accept button
└── decline_call.png   ← screenshot of red decline button
```

Without these, call accept/decline will not work (but everything else will).
