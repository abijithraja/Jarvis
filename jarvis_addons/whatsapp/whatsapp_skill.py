"""
WhatsApp Voice Skill for Jarvis
Plug this into your jarvis_fixed/src/skills/skills.py dispatch system.

SUPPORTED VOICE COMMANDS:
  "send whatsapp message to Mom say hello"
  "whatsapp call Dad"
  "video call John"
  "read whatsapp messages from Priya"
  "send file report.pdf to Boss on whatsapp"
  "open whatsapp"
  "decline the call and say I'm busy"
  "attend the call" / "accept the call"
  "message +919876543210 say I'm on my way"
"""

import re
from jarvis_addons.whatsapp.whatsapp_web import (
    send_whatsapp_message,
    send_whatsapp_to_number,
    whatsapp_voice_call,
    whatsapp_video_call,
    whatsapp_read_messages,
    whatsapp_send_file,
    open_whatsapp,
)
from jarvis_addons.whatsapp.call_watcher import (
    accept_call,
    decline_call,
    decline_and_send_busy,
    is_call_active,
    get_caller,
)


# Keywords that trigger this skill
TRIGGER_KEYWORDS = [
    "whatsapp", "send message to", "call", "video call",
    "read messages", "attend the call", "accept the call",
    "decline the call", "say i'm busy", "i'm busy",
]


def handle_whatsapp_command(text: str) -> str | None:
    """
    Parse a voice command and execute the appropriate WhatsApp action.
    Returns response string or None if not a WhatsApp command.
    """
    lower = text.lower().strip()

    # Guard: must contain a trigger word
    if not any(kw in lower for kw in TRIGGER_KEYWORDS):
        return None

    # ── CALL CONTROL ─────────────────────────────────────────────────────────

    if any(p in lower for p in ["attend the call", "accept the call", "answer the call", "pick up"]):
        if is_call_active():
            return accept_call()
        return "No incoming call detected right now."

    if any(p in lower for p in ["decline the call", "reject the call", "cut the call", "hang up"]):
        if any(p in lower for p in ["busy", "i'm busy", "say busy", "tell busy"]):
            caller = get_caller()
            return decline_and_send_busy(caller)
        return decline_call()

    if "say i'm busy" in lower or "tell them i'm busy" in lower:
        caller = get_caller()
        return decline_and_send_busy(caller)

    # ── SEND MESSAGE ──────────────────────────────────────────────────────────

    # "send whatsapp message to <contact> say <message>"
    m = re.search(
        r"(?:send\s+(?:whatsapp\s+)?message\s+to|message)\s+(.+?)\s+(?:say|saying|that)\s+(.+)",
        lower, re.I
    )
    if m:
        contact = m.group(1).strip().title()
        message = m.group(2).strip()
        return send_whatsapp_message(contact, message)

    # "message +91XXXXXXXXXX say <text>"
    m = re.search(r"message\s+(\+?\d{10,13})\s+(?:say|that)\s+(.+)", lower)
    if m:
        phone = m.group(1)
        message = m.group(2).strip()
        return send_whatsapp_to_number(phone, message)

    # ── CALLS ────────────────────────────────────────────────────────────────

    # "video call <contact>"
    m = re.search(r"video\s+call\s+(.+)", lower)
    if m:
        contact = m.group(1).strip().title()
        return whatsapp_video_call(contact)

    # "whatsapp call <contact>" or "call <contact> on whatsapp"
    m = re.search(r"(?:whatsapp\s+call|call\s+(.+)\s+on\s+whatsapp|call)\s+(.+)", lower)
    if m:
        contact = (m.group(1) or m.group(2) or "").strip().title()
        if contact:
            return whatsapp_voice_call(contact)

    # ── READ MESSAGES ─────────────────────────────────────────────────────────

    m = re.search(r"read\s+(?:whatsapp\s+)?messages\s+from\s+(.+)", lower)
    if m:
        contact = m.group(1).strip().title()
        return whatsapp_read_messages(contact, count=5)

    m = re.search(r"(?:open|show)\s+chat\s+(?:with\s+)?(.+)", lower)
    if m:
        contact = m.group(1).strip().title()
        return whatsapp_read_messages(contact, count=3)

    # ── SEND FILE ────────────────────────────────────────────────────────────

    m = re.search(r"send\s+(?:file\s+)?([^\s]+\.\w+)\s+to\s+(.+?)(?:\s+on\s+whatsapp)?$", lower)
    if m:
        file_path = m.group(1).strip()
        contact = m.group(2).strip().title()
        return whatsapp_send_file(contact, file_path)

    # ── OPEN WHATSAPP ────────────────────────────────────────────────────────

    if "open whatsapp" in lower:
        return open_whatsapp()

    return None
