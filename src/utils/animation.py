import threading
import time
import sys

running = False


def spinner():
    global running
    symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0

    while running:
        sys.stdout.write(f"\r🤖 Jarvis thinking {symbols[i % len(symbols)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1


def start_thinking():
    global running
    running = True
    t = threading.Thread(target=spinner, daemon=True)
    t.start()
    return t


def stop_thinking():
    global running
    running = False
    print("\r", end="")
