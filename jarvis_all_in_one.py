# ==========================================
# SOURCE: src/stt/whisper_stt.py
# ==========================================
from faster_whisper import WhisperModel
from src.audio.vad_recorder import record_speech

model = WhisperModel("base", device="cpu", compute_type="float32")


def transcribe_audio():
    audio_path = record_speech()

    if not audio_path:
        return None

    segments, _ = model.transcribe(
        audio_path,
        language="en",
        beam_size=1,
        condition_on_previous_text=False,
    )

    text = ""
    for segment in segments:
        text += segment.text

    return text.strip()


# ==========================================
# SOURCE: src/llm/ollama_client.py
# ==========================================
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_response(prompt):
    system_prompt = """
You are Jarvis, a friendly and natural AI assistant.
Speak like a human, casually and clearly.
Keep answers short (1-2 sentences).
Avoid robotic or formal tone.
"""

    full_prompt = f"{system_prompt}\nUser: {prompt}\nJarvis:"

    payload = {
        "model": "llama3",
        "prompt": full_prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)

        if response.status_code == 200:
            result = response.json().get("response", "")
            return result if result else "Sorry, I didn't catch that."
        else:
            return "Error from Ollama"

    except Exception:
        return "Ollama not running"


def stream_response(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={"model": "llama3", "prompt": prompt, "stream": True},
        stream=True,
    )

    full_text = ""

    for line in response.iter_lines():
        if line:
            chunk = json.loads(line.decode("utf-8"))
            token = chunk.get("response", "")
            print(token, end="", flush=True)
            full_text += token

    print()
    return full_text


# ==========================================
# SOURCE: src/tts/speaker.py
# ==========================================
import pyttsx3

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 190)

    engine.say(text)
    engine.runAndWait()
    engine.stop()


# ==========================================
# SOURCE: src/router/intent_router.py
# ==========================================
import json
from src.llm.ollama_client import generate_response


def detect_intent(text):
    prompt = f"""
Classify the user input into ONE:

- conversation → questions, coding, explanations
- system_tool → time, date
- agent_task → actions like open app, type, search

STRICT RULES:
- Coding = conversation
- Questions = conversation
- Only real actions = agent_task

Respond ONLY JSON:
{{"intent": "conversation"}}

Input: {text}
"""

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        return json.loads(response[start:end]).get("intent", "conversation")
    except:
        return "conversation"


# ==========================================
# SOURCE: src/memory/memory.py
# ==========================================
import json
import os

MEMORY_FILE = "memory.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def store_fact(key, value):
    memory = load_memory()
    memory[key] = value
    save_memory(memory)


def get_fact(key):
    memory = load_memory()
    return memory.get(key, None)


# ==========================================
# SOURCE: src/memory/task_memory.py
# ==========================================
tasks = []


def add_task(task):
    tasks.append(task)


def get_tasks():
    return tasks


# ==========================================
# SOURCE: src/agent/external_agent.py
# ==========================================
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


# ==========================================
# SOURCE: src/agent/system_agent.py
# ==========================================
import pyautogui
import subprocess
import time
from src.memory import state


def handle_system_command(text):
    text = text.lower()

    if "one pad" in text:
        text = text.replace("one pad", "notepad")

    if "and" in text:
        parts = text.split("and")
        responses = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            res = handle_system_command(part)
            if res:
                responses.append(res)

        return ", ".join(responses) if responses else None

    if "close notepad" in text:
        subprocess.call("taskkill /f /im notepad.exe", shell=True)
        if state.current_app == "notepad":
            state.current_app = None
        return "Closing Notepad"

    if text.startswith("type") and "chrome" in text:
        content = text.split("type", 1)[-1].strip()
        content = content.replace("in chrome", "").strip()
        content = content.strip(",. ")

        if content:
            time.sleep(2)
            pyautogui.hotkey("ctrl", "l")
            pyautogui.write(content)
            pyautogui.press("enter")
            return f"Searching: {content}"

    if text.startswith("type"):
        content = text.split("type", 1)[-1].strip()
        content = content.strip(",. ")

        if content:
            time.sleep(1)
            pyautogui.write(content)
            return f"Typing: {content}"

    if "notepad" in text and any(word in text for word in ["open", "launch", "start"]):
        subprocess.Popen(["notepad.exe"])
        state.current_app = "notepad"
        return "Opening Notepad"

    if text.strip() == "notepad":
        subprocess.Popen(["notepad.exe"])
        state.current_app = "notepad"
        return "Opening Notepad"

    elif "chrome" in text:
        subprocess.Popen("start chrome", shell=True)
        time.sleep(3)
        pyautogui.click(500, 500)
        state.current_app = "chrome"
        return "Opening Chrome"

    return None


# ==========================================
# SOURCE: src/agent/browser_agent.py
# ==========================================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time


def search_google(query):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get("https://www.google.com")

    box = driver.find_element(By.NAME, "q")
    box.send_keys(query)
    box.send_keys(Keys.RETURN)

    time.sleep(2)

    results = driver.find_elements(By.CSS_SELECTOR, "h3")

    if results:
        results[0].click()

    return f"Searching Google for {query}"


# ==========================================
# SOURCE: src/agent/vision.py
# ==========================================
import pytesseract
import pyautogui
from src.utils.tesseract_config import resolve_tesseract_cmd


def read_screen():
    tesseract_cmd = resolve_tesseract_cmd()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    screenshot = pyautogui.screenshot()
    text = pytesseract.image_to_string(screenshot)
    return text[:500]


# ==========================================
# SOURCE: src/agent/planner.py
# ==========================================
from src.llm.ollama_client import generate_response
import json


def create_plan(task):
    prompt = f"""
    You are a planning AI.

    Convert the user request into steps.

    STRICT RULES:
    - ONLY return JSON
    - NO explanation
    - NO extra text

    Format:
{{"steps": ["step1", "step2"]}}

    Examples:
    Task: open notepad and type hello
    Output: {{"steps": ["open notepad", "type hello"]}}

    Task: write binary search in python
    Output: {{"steps": ["open notepad", "generate code for binary search in python"]}}

    Now do this:

Task: {task}
"""

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        json_str = response[start:end]

        data = json.loads(json_str)
        return data.get("steps", [])
    except Exception:
        return []


# ==========================================
# SOURCE: src/agent/executor.py
# ==========================================
from src.agent.external_agent import run_external_agent


def execute_plan(steps):
    results = []

    for step in steps:
        result = run_external_agent(step)
        results.append(result)

    return "\n".join(results)


# ==========================================
# SOURCE: src/utils/system_tools.py
# ==========================================
from datetime import datetime


def get_time():
    return datetime.now().strftime("%I:%M %p")


def handle_system_command(text):
    return None


# ==========================================
# SOURCE: src/utils/animation.py
# ==========================================
import time


def thinking():
    print("JARVIS  : Thinking...", end="", flush=True)
    time.sleep(0.3)
    print()


# ==========================================
# SOURCE: src/utils/code_writer.py
# ==========================================
def write_code_to_file(code, filename="output.py"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    return f"Code written to {filename}"


# ==========================================
# SOURCE: src/utils/runtime_checks.py
# ==========================================
import importlib
import shutil
from src.utils.tesseract_config import resolve_tesseract_cmd


def _check_ollama():
    try:
        requests = importlib.import_module("requests")
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code != 200:
            return "Ollama is reachable but returned a non-200 response."
        return None
    except Exception:
        return "Ollama is not reachable at http://localhost:11434 (start with: ollama serve)."


def _check_tesseract():
    try:
        pytesseract = importlib.import_module("pytesseract")
        tesseract_cmd = resolve_tesseract_cmd()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pytesseract.get_tesseract_version()
        return None
    except Exception:
        return "Tesseract OCR binary not found. Install Tesseract, or set TESSERACT_CMD to the tesseract.exe path."


def collect_runtime_warnings():
    warnings = []

    optional_packages = {
        "selenium": "Browser automation features are unavailable (missing selenium).",
        "webdriver_manager": "Browser automation may fail (missing webdriver-manager).",
        "pyautogui": "Desktop control features are unavailable (missing pyautogui).",
        "pytesseract": "Vision OCR features are unavailable (missing pytesseract).",
        "cv2": "Computer-vision helper features are unavailable (missing opencv-python).",
        "bs4": "Web summarization features are unavailable (missing beautifulsoup4).",
    }

    for module_name, message in optional_packages.items():
        try:
            importlib.import_module(module_name)
        except Exception:
            warnings.append(message)

    ollama_warning = _check_ollama()
    if ollama_warning:
        warnings.append(ollama_warning)

    tesseract_warning = _check_tesseract()
    if tesseract_warning:
        warnings.append(tesseract_warning)

    if not shutil.which("python"):
        warnings.append("Python executable not found in PATH for subprocess-based tools.")

    return warnings
