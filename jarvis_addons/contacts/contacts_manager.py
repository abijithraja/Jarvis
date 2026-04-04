"""
Contacts Manager
Stores contact names + phone numbers locally in JSON.
Used by WhatsApp skill so you can say "call Mom" instead of a number.

VOICE COMMANDS:
  "save contact Mom as +919876543210"
  "add contact John with number +14155552671"
  "what is Mom's number"
  "show all contacts"
  "delete contact John"
"""

import json
import os
import re

CONTACTS_FILE = os.path.join(os.path.dirname(__file__), "contacts.json")


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(CONTACTS_FILE):
        return {}
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def save_contact(name: str, phone: str) -> str:
    """Save or update a contact."""
    phone = _normalize_phone(phone)
    if not phone:
        return f"Invalid phone number: {phone}"
    contacts = _load()
    contacts[name.lower()] = {"name": name.title(), "phone": phone}
    _save(contacts)
    return f"Saved contact {name.title()} as {phone}."


def get_contact(name: str) -> dict | None:
    """Look up a contact by name (fuzzy match)."""
    contacts = _load()
    name_lower = name.lower()

    # Exact match
    if name_lower in contacts:
        return contacts[name_lower]

    # Partial match
    for key, val in contacts.items():
        if name_lower in key or key in name_lower:
            return val

    return None


def get_phone(name: str) -> str | None:
    """Get just the phone number for a contact name."""
    c = get_contact(name)
    return c["phone"] if c else None


def list_contacts() -> str:
    contacts = _load()
    if not contacts:
        return "No contacts saved yet."
    lines = [f"  • {v['name']}: {v['phone']}" for v in contacts.values()]
    return f"Contacts ({len(contacts)}):\n" + "\n".join(lines)


def delete_contact(name: str) -> str:
    contacts = _load()
    key = name.lower()
    if key in contacts:
        del contacts[key]
        _save(contacts)
        return f"Deleted contact {name.title()}."
    return f"Contact {name.title()} not found."


# ── Phone number normalization ────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Normalize to +XXXXXXXXXXX format."""
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        if len(digits) == 10:
            digits = "+91" + digits   # default India country code
        elif len(digits) > 10:
            digits = "+" + digits
    return digits if len(digits) >= 10 else ""


# ── Voice command parser ──────────────────────────────────────────────────────

def handle_contacts_command(text: str) -> str | None:
    lower = text.lower().strip()

    TRIGGERS = ["contact", "save contact", "add contact", "delete contact", "phone number"]
    if not any(t in lower for t in TRIGGERS):
        return None

    # Save contact
    m = re.search(r"(?:save|add)\s+contact\s+(.+?)\s+(?:as|with(?:\s+number)?)\s+(\+?\d[\d\s\-]+)", lower)
    if m:
        name = m.group(1).strip()
        phone = m.group(2).strip()
        return save_contact(name, phone)

    # Get phone number
    m = re.search(r"what(?:'s|\s+is)\s+(.+?)'?s?\s+(?:phone\s+)?number", lower)
    if m:
        name = m.group(1).strip()
        phone = get_phone(name)
        return f"{name.title()}'s number is {phone}." if phone else f"No contact named {name.title()} found."

    # List contacts
    if "show all contacts" in lower or "list contacts" in lower or "show contacts" in lower:
        return list_contacts()

    # Delete contact
    m = re.search(r"delete\s+contact\s+(.+)", lower)
    if m:
        return delete_contact(m.group(1).strip())

    return None
