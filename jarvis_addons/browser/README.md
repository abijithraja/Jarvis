# Jarvis Browser Addon

Full browser automation powered by **Playwright** (faster + smarter than Selenium).

---

## Install

```bash
pip install playwright
playwright install chromium
```

That's it. No WebDriver downloads needed.

---

## Hook into Jarvis

In `jarvis_fixed/main.py`, add to `process_text()` before the LLM fallback:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jarvis_addons.browser.browser_dispatcher import dispatch_browser

# Inside process_text(), before _llm_respond():
r = dispatch_browser(text)
if r:
    return r
```

---

## Features

### Navigation
| Say | Action |
|---|---|
| "open google.com" | Navigate to URL |
| "go to youtube" | Maps spoken name to URL |
| "go back" | Browser back |
| "refresh the page" | Reload |
| "what page am I on" | Current URL |

### Interaction
| Say | Action |
|---|---|
| "click the login button" | Smart click (by text or selector) |
| "type hello in the search box" | Fill input field |
| "press enter" | Keyboard press |
| "scroll down" | Scroll 500px down |
| "scroll to the bottom" | Jump to page bottom |
| "hover over the menu" | Mouse hover |
| "select option English from dropdown" | Dropdown selection |
| "upload file report.pdf" | File upload |

### Reading
| Say | Action |
|---|---|
| "read the page" | OCR full page text |
| "summarize this page" | AI summary via Qwen |
| "summarize bbc.com/news" | Navigate + summarize |
| "find Python on this page" | Search text on page |
| "get all links" | List all hyperlinks |
| "extract all prices" | Find price patterns |
| "extract emails" | Find email addresses |
| "list headings" | H1-H3 headings |

### Search
| Say | Action |
|---|---|
| "search for machine learning on google" | Google search |
| "search youtube for lofi music" | YouTube search |
| "search amazon for mechanical keyboard" | Amazon search |
| "search flipkart for laptop" | Flipkart search |
| "search wikipedia for black holes" | Wikipedia article |

### Tabs
| Say | Action |
|---|---|
| "open new tab" | New empty tab |
| "open new tab at github.com" | New tab at URL |
| "show all tabs" | List open tabs |
| "switch to tab 2" | Focus tab by number |
| "close this tab" | Close current tab |

### Screenshots & PDF
| Say | Action |
|---|---|
| "take a screenshot" | Save screenshot |
| "save full page screenshot" | Full-page PNG |
| "save page as PDF" | Export to PDF |

### Automations
| Say | Action |
|---|---|
| "play lofi music on youtube" | Search + play video |
| "pause youtube" | Toggle pause (K key) |
| "search wikipedia for AI" | Read Wikipedia article |
| "open gmail" | Open Gmail |
| "compose email to a@b.com subject hi body hello" | Draft email |
| "translate hello world to Tamil" | Google Translate |
| "login to github with username x password y" | Auto-login |

### Page Monitoring
| Say | Action |
|---|---|
| "monitor this page" | Watch for changes every 60s |
| "monitor https://site.com every 30 seconds" | Custom interval |
| "stop monitoring" | Stop watcher |

---

## Session persistence

The browser saves your login state automatically in:
```
jarvis_addons/browser/sessions/default/
```
Once you log into GitHub, Google, etc. — you stay logged in forever across restarts.

---

## File outputs

- Screenshots → `jarvis_addons/browser/screenshots/`
- PDFs + downloads → `jarvis_addons/browser/downloads/`

---

## Why Playwright over Selenium?

| Feature | Playwright | Selenium |
|---|---|---|
| Auto-wait for elements | ✅ Built-in | ❌ Manual waits |
| Speed | ✅ ~2x faster | slower |
| Bot detection bypass | ✅ Better stealth | detectable |
| Multi-browser | Chrome, Firefox, WebKit | Chrome, Firefox, Edge |
| Install | `pip install playwright` + 1 cmd | Driver downloads |
| Persistent sessions | ✅ Native | workarounds |
| Network monitoring | ✅ Built-in | extensions needed |
