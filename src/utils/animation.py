import threading
import time
import sys
import os

_stop_event = threading.Event()
_thread = None


def _animate():
    if os.environ.get("JARVIS_DISABLE_SPINNER", "0").strip().lower() in {"1", "true", "yes", "on"}:
        while not _stop_event.is_set():
            time.sleep(0.1)
        return

    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not _stop_event.is_set():
        print(f"\r🤖 Thinking {frames[i % len(frames)]} ", end="", flush=True)
        i += 1
        time.sleep(0.1)
    print("\r" + " " * 25 + "\r", end="", flush=True)  # clear line


def start_thinking():
    """Start the thinking animation in a background thread."""
    global _thread
    _stop_event.clear()
    _thread = threading.Thread(target=_animate, daemon=True)
    _thread.start()
    return _thread


def stop_thinking():
    """Stop the thinking animation."""
    _stop_event.set()
    if _thread:
        _thread.join(timeout=0.5)
