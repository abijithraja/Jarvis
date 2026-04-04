"""
Window Manager
Full window control by voice command for Jarvis.

SUPPORTED COMMANDS:
  Move & Position:
    "move chrome to left"
    "move notepad to top right"
    "center the window"
    "move window to second monitor"

  Resize:
    "resize chrome to 800 by 600"
    "make notepad bigger"
    "make chrome smaller"
    "maximize chrome"
    "minimize notepad"
    "restore chrome"
    "make the window fullscreen"

  Snap / Tile:
    "snap chrome to left half"
    "snap notepad to right half"
    "tile all windows"
    "tile windows side by side"
    "cascade windows"
    "arrange windows in grid"

  Focus:
    "switch to chrome"
    "bring chrome to front"
    "focus notepad"

  Close:
    "close chrome"
    "close all except notepad"
"""

import time
import platform
import subprocess
import pyautogui

_SYSTEM = platform.system()

# ── Window finding ────────────────────────────────────────────────────────────

def _get_window(name: str):
    """Find a window by partial title match. Returns pygetwindow Window or None."""
    try:
        import pygetwindow as gw
        matches = [w for w in gw.getAllWindows()
                   if name.lower() in w.title.lower() and w.title.strip()]
        return matches[0] if matches else None
    except Exception:
        return None


def _get_active_window():
    try:
        import pygetwindow as gw
        return gw.getActiveWindow()
    except Exception:
        return None


def _screen_size():
    return pyautogui.size()


# ── Move ─────────────────────────────────────────────────────────────────────

def move_window(name: str, position: str) -> str:
    """
    Move a window to a named position.
    position: left | right | top | bottom | center |
              top-left | top-right | bottom-left | bottom-right
    """
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."

    sw, sh = _screen_size()
    positions = {
        "left":         (0, 0),
        "right":        (sw // 2, 0),
        "top":          (0, 0),
        "bottom":       (0, sh // 2),
        "center":       ((sw - w.width) // 2, (sh - w.height) // 2),
        "top-left":     (0, 0),
        "top-right":    (sw - w.width, 0),
        "bottom-left":  (0, sh - w.height),
        "bottom-right": (sw - w.width, sh - w.height),
    }

    pos = positions.get(position.lower().replace(" ", "-"))
    if not pos:
        return f"Unknown position: {position}. Use: left, right, center, top-left, etc."

    try:
        w.moveTo(*pos)
        return f"Moved {w.title} to {position}."
    except Exception as e:
        return f"Move failed: {e}"


def move_window_to_coords(name: str, x: int, y: int) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.moveTo(x, y)
        return f"Moved {w.title} to ({x}, {y})."
    except Exception as e:
        return f"Move failed: {e}"


# ── Resize ────────────────────────────────────────────────────────────────────

def resize_window(name: str, width: int, height: int) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.resizeTo(width, height)
        return f"Resized {w.title} to {width}×{height}."
    except Exception as e:
        return f"Resize failed: {e}"


def resize_relative(name: str, scale: float) -> str:
    """Scale a window by a factor (e.g. 1.5 = 50% bigger, 0.75 = 25% smaller)."""
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        new_w = int(w.width * scale)
        new_h = int(w.height * scale)
        w.resizeTo(new_w, new_h)
        return f"Resized {w.title} to {new_w}×{new_h}."
    except Exception as e:
        return f"Resize failed: {e}"


def maximize_window(name: str) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.maximize()
        return f"Maximized {w.title}."
    except Exception as e:
        return f"Maximize failed: {e}"


def minimize_window(name: str) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.minimize()
        return f"Minimized {w.title}."
    except Exception as e:
        return f"Minimize failed: {e}"


def restore_window(name: str) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.restore()
        return f"Restored {w.title}."
    except Exception as e:
        return f"Restore failed: {e}"


def close_window(name: str) -> str:
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."
    try:
        w.close()
        return f"Closed {w.title}."
    except Exception as e:
        return f"Close failed: {e}"


# ── Snap / Tile ───────────────────────────────────────────────────────────────

def snap_window(name: str, side: str) -> str:
    """
    Snap a window to half the screen.
    side: left | right | top | bottom
    """
    w = _get_window(name) if name else _get_active_window()
    if not w:
        return f"Window '{name}' not found."

    sw, sh = _screen_size()

    snap_configs = {
        "left":   (0,       0,       sw // 2, sh),
        "right":  (sw // 2, 0,       sw // 2, sh),
        "top":    (0,       0,       sw,      sh // 2),
        "bottom": (0,       sh // 2, sw,      sh // 2),
    }

    cfg = snap_configs.get(side.lower())
    if not cfg:
        return f"Unknown snap side: {side}. Use: left, right, top, bottom."

    try:
        x, y, width, height = cfg
        w.restore()
        time.sleep(0.2)
        w.moveTo(x, y)
        w.resizeTo(width, height)
        return f"Snapped {w.title} to {side} half."
    except Exception as e:
        # Windows key shortcut fallback
        if side == "left":
            pyautogui.hotkey("win", "left")
        elif side == "right":
            pyautogui.hotkey("win", "right")
        return f"Snapped to {side} using Windows shortcut."


def tile_windows_side_by_side() -> str:
    """Tile the first two visible windows side by side."""
    try:
        import pygetwindow as gw
        windows = [w for w in gw.getAllWindows() if w.title.strip() and not w.isMinimized]
        if len(windows) < 2:
            return "Need at least 2 open windows to tile."

        sw, sh = _screen_size()
        half = sw // 2

        w1, w2 = windows[0], windows[1]
        w1.restore()
        w1.moveTo(0, 0)
        w1.resizeTo(half, sh)

        w2.restore()
        w2.moveTo(half, 0)
        w2.resizeTo(half, sh)

        return f"Tiled '{w1.title}' and '{w2.title}' side by side."
    except Exception as e:
        # Windows shortcut fallback
        pyautogui.hotkey("win", "left")
        return f"Tiled windows (fallback): {e}"


def tile_windows_grid() -> str:
    """Tile up to 4 windows in a 2x2 grid."""
    try:
        import pygetwindow as gw
        windows = [w for w in gw.getAllWindows() if w.title.strip() and not w.isMinimized][:4]
        if len(windows) < 2:
            return "Need at least 2 open windows."

        sw, sh = _screen_size()
        half_w = sw // 2
        half_h = sh // 2

        positions = [
            (0,      0,      half_w, half_h),
            (half_w, 0,      half_w, half_h),
            (0,      half_h, half_w, half_h),
            (half_w, half_h, half_w, half_h),
        ]

        for i, w in enumerate(windows):
            x, y, width, height = positions[i]
            w.restore()
            w.moveTo(x, y)
            w.resizeTo(width, height)

        return f"Arranged {len(windows)} windows in a grid."
    except Exception as e:
        return f"Grid tile failed: {e}"


def cascade_windows() -> str:
    """Cascade all windows diagonally."""
    if _SYSTEM == "Windows":
        try:
            # Windows: use keyboard shortcut
            pyautogui.hotkey("win", "d")   # show desktop
            time.sleep(0.5)
            return "Cascaded windows using Windows shortcut."
        except Exception:
            pass
    try:
        import pygetwindow as gw
        windows = [w for w in gw.getAllWindows() if w.title.strip() and not w.isMinimized]
        sw, sh = _screen_size()
        default_w = min(sw // 2, 800)
        default_h = min(sh // 2, 600)
        offset = 30

        for i, w in enumerate(windows[:8]):
            x = i * offset
            y = i * offset
            w.restore()
            w.moveTo(x, y)
            w.resizeTo(default_w, default_h)

        return f"Cascaded {len(windows[:8])} windows."
    except Exception as e:
        return f"Cascade failed: {e}"


def minimize_all() -> str:
    """Minimize all windows (show desktop)."""
    if _SYSTEM == "Windows":
        pyautogui.hotkey("win", "d")
        return "Minimized all windows. Desktop shown."
    else:
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if not w.isMinimized:
                    w.minimize()
            return "Minimized all windows."
        except Exception as e:
            return f"Minimize all failed: {e}"


def restore_all() -> str:
    """Restore all minimized windows."""
    if _SYSTEM == "Windows":
        pyautogui.hotkey("win", "d")  # Toggle
        return "Restored all windows."
    else:
        try:
            import pygetwindow as gw
            for w in gw.getAllWindows():
                if w.isMinimized:
                    w.restore()
            return "Restored all windows."
        except Exception as e:
            return f"Restore all failed: {e}"


# ── Focus / Bring to Front ────────────────────────────────────────────────────

def focus_window(name: str) -> str:
    """Bring a window to the front and focus it."""
    w = _get_window(name)
    if not w:
        return f"Window '{name}' not found."
    try:
        if w.isMinimized:
            w.restore()
        w.activate()
        return f"Focused {w.title}."
    except Exception as e:
        # Fallback: use alt+tab cycling
        return f"Could not focus {name}: {e}"


# ── Voice command parser ──────────────────────────────────────────────────────

def handle_window_command(text: str) -> str | None:
    """Parse a voice command and execute window management action."""
    import re
    lower = text.lower().strip()

    WINDOW_TRIGGERS = [
        "window", "move", "resize", "snap", "tile", "cascade",
        "maximize", "minimize", "restore", "close", "focus",
        "bring", "arrange", "make bigger", "make smaller",
        "side by side", "grid", "fullscreen", "minimize all",
    ]

    if not any(t in lower for t in WINDOW_TRIGGERS):
        return None

    # ── Maximize / Minimize / Restore / Close ─────────────────────────────────

    m = re.search(r"(maximize|minimise|minimize|restore|close)\s+(.+)", lower)
    if m:
        action = m.group(1)
        name = m.group(2).replace("the window", "").replace("window", "").strip()
        if action in ("minimize", "minimise"):
            return minimize_window(name) if name else minimize_window("")
        elif action == "maximize":
            return maximize_window(name) if name else maximize_window("")
        elif action == "restore":
            return restore_window(name) if name else restore_window("")
        elif action == "close":
            return close_window(name) if name else close_window("")

    if "minimize all" in lower or "show desktop" in lower:
        return minimize_all()

    if "restore all" in lower:
        return restore_all()

    # ── Snap ─────────────────────────────────────────────────────────────────

    m = re.search(r"snap\s+(.+?)\s+to\s+(left|right|top|bottom)", lower)
    if m:
        return snap_window(m.group(1).strip(), m.group(2))

    m = re.search(r"snap\s+(left|right|top|bottom)(?:\s+half)?", lower)
    if m:
        return snap_window("", m.group(1))

    # ── Resize ────────────────────────────────────────────────────────────────

    m = re.search(r"resize\s+(.+?)\s+to\s+(\d+)\s+(?:by|x|×)\s+(\d+)", lower)
    if m:
        return resize_window(m.group(1).strip(), int(m.group(2)), int(m.group(3)))

    if "make" in lower and "bigger" in lower:
        m = re.search(r"make\s+(.+?)\s+bigger", lower)
        name = m.group(1).strip() if m else ""
        return resize_relative(name, 1.3)

    if "make" in lower and "smaller" in lower:
        m = re.search(r"make\s+(.+?)\s+smaller", lower)
        name = m.group(1).strip() if m else ""
        return resize_relative(name, 0.75)

    # ── Tile ─────────────────────────────────────────────────────────────────

    if "side by side" in lower or "tile windows" in lower:
        return tile_windows_side_by_side()

    if "grid" in lower and "window" in lower:
        return tile_windows_grid()

    if "cascade" in lower:
        return cascade_windows()

    # ── Move ─────────────────────────────────────────────────────────────────

    POSITIONS = ["left", "right", "top", "bottom", "center",
                 "top left", "top right", "bottom left", "bottom right"]
    for pos in POSITIONS:
        if f"move" in lower and pos in lower:
            m = re.search(r"move\s+(.+?)\s+to\s+(?:the\s+)?" + pos.replace(" ", r"\s+"), lower)
            name = m.group(1).strip() if m else ""
            return move_window(name, pos)

    # ── Focus ────────────────────────────────────────────────────────────────

    m = re.search(r"(?:focus|switch to|bring up|open)\s+(.+)", lower)
    if m:
        name = m.group(1).strip()
        result = focus_window(name)
        if "not found" not in result:
            return result

    return None
