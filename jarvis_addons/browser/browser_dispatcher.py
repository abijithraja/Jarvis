"""
Browser Addon Master Dispatcher
Import this and call dispatch_browser(text) from your Jarvis pipeline.

Add to jarvis_fixed/main.py process_text():
    from jarvis_addons.browser.browser_dispatcher import dispatch_browser
    r = dispatch_browser(text)
    if r: return r
"""


def _browser_setup_hint(err: Exception) -> str | None:
    msg = str(err).lower()
    if "no module named 'playwright'" in msg or 'no module named "playwright"' in msg:
        return (
            "Browser addon needs Playwright. Run: "
            "pip install playwright and python -m playwright install chromium"
        )

    if "executable doesn't exist" in msg and "chromium" in msg:
        return "Playwright is installed, but Chromium is missing. Run: python -m playwright install chromium"

    if "please run the following command to download new browsers" in msg:
        return "Playwright browser binaries are missing. Run: python -m playwright install chromium"

    return None


def dispatch_browser(text: str) -> str | None:
    """Try all browser skills in priority order."""

    # 1. Automations (YouTube, Wikipedia, Gmail, shopping, login)
    try:
        from jarvis_addons.browser.skills.web_automation import handle_automation_command
        result = handle_automation_command(text)
        if result:
            return result
    except Exception as e:
        hint = _browser_setup_hint(e)
        if hint:
            return hint

    # 2. Scraping (summarize, extract, monitor)
    try:
        from jarvis_addons.browser.skills.web_scraper import handle_scraper_command
        result = handle_scraper_command(text)
        if result:
            return result
    except Exception as e:
        hint = _browser_setup_hint(e)
        if hint:
            return hint

    # 3. General browser control (navigate, click, type, tabs, screenshot)
    try:
        from jarvis_addons.browser.skills.browser_skill import handle_browser_command
        result = handle_browser_command(text)
        if result:
            return result
    except Exception as e:
        hint = _browser_setup_hint(e)
        if hint:
            return hint

    return None
