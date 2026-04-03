import os


def run_external_agent(command):
    cmd = command.lower()

    try:
        if "close notepad" in cmd:
            os.system("taskkill /f /im notepad.exe >nul 2>&1")
            return "Closing Notepad"

        if "notepad" in cmd:
            os.system("start notepad")
            return "Opening Notepad"

        elif "chrome" in cmd:
            if "search" in cmd:
                query = cmd.replace("search", "").replace("chrome", "").strip()
                os.system(f'start chrome "https://www.google.com/search?q={query}"')
                return f"Searching {query}"

            os.system("start chrome")
            return "Opening Chrome"

        elif "search" in cmd:
            query = cmd.replace("search", "").strip()
            os.system(f'start chrome "https://www.google.com/search?q={query}"')
            return f"Searching {query}"

        elif cmd.startswith("type"):
            import pyautogui

            text = cmd.replace("type", "", 1).strip(" ,.\t\n")
            if not text:
                return "Task not supported yet"

            pyautogui.write(text, interval=0.05)
            return f"Typing: {text}"

        else:
            return "Task not supported yet"

    except Exception as e:
        return f"Error: {str(e)}"
