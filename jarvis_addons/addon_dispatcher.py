"""
Jarvis Addons — Master Dispatcher
Single entry point: call dispatch_addon(text) from your Jarvis main.py

Add this to jarvis_fixed/main.py process_text(), before _llm_respond():
    from jarvis_addons.addon_dispatcher import dispatch_addon
    r = dispatch_addon(text)
    if r: return r
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))


def dispatch_addon(text: str) -> str | None:
    """Try all addon skills. Returns first non-None response."""

    # 1. WhatsApp (very specific keywords - high priority)
    try:
        from jarvis_addons.whatsapp.whatsapp_skill import handle_whatsapp_command
        r = handle_whatsapp_command(text)
        if r: return r
    except Exception: pass

    # 2. Contacts
    try:
        from jarvis_addons.contacts.contacts_manager import handle_contacts_command
        r = handle_contacts_command(text)
        if r: return r
    except Exception: pass

    # 3. Browser automation (Playwright)
    try:
        from jarvis_addons.browser.browser_dispatcher import dispatch_browser
        r = dispatch_browser(text)
        if r: return r
    except Exception as e:
        pass

    # 4. Window manager
    try:
        from jarvis_addons.window_manager.window_manager import handle_window_command
        r = handle_window_command(text)
        if r: return r
    except Exception: pass

    # 5. Screen reader
    try:
        from jarvis_addons.screen_reader.screen_skill import handle_screen_command
        r = handle_screen_command(text)
        if r: return r
    except Exception: pass

    return None
