# Jarvis AI Assistant

Jarvis is a local, voice-enabled AI assistant for Windows that combines speech recognition, local LLM responses, text-to-speech, desktop automation, and optional browser/vision tools.

## What It Does

- Listens to microphone input and transcribes speech using Faster-Whisper.
- Generates conversational responses through a local Ollama model (`llama3`).
- Speaks responses using `pyttsx3`.
- Executes desktop tasks such as opening apps, typing text, closing apps, and web search.
- Stores simple memory facts and recent task history.
- Supports optional modules for browser automation, OCR screen reading, and web summarization.

## Tech Stack

- Python 3.10+
- Faster-Whisper
- Ollama (local model serving)
- SoundDevice + WebRTC VAD
- pyttsx3
- PyAutoGUI
- Selenium + WebDriver Manager
- Pytesseract + OpenCV

## Project Structure

```
Jarvis/
├─ main.py
├─ run_jarvis.bat
├─ requirements.txt
├─ memory.json
├─ src/
│  ├─ stt/
│  ├─ tts/
│  ├─ llm/
│  ├─ router/
│  ├─ memory/
│  ├─ agent/
│  └─ utils/
└─ README.md
```

## Prerequisites

1. Windows 10/11
2. Python 3.10 or newer
3. A working microphone
4. Ollama installed and running

Optional (for OCR/vision features):
- Tesseract OCR installed and available on PATH, or configured via `TESSERACT_CMD`

## Installation

From PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ollama Setup

Install and start Ollama, then pull the model used by this project:

```powershell
ollama serve
ollama pull llama3
```

Jarvis expects Ollama at:
- `http://localhost:11434`

## Run Jarvis

Option 1 (recommended on Windows):

```powershell
.\run_jarvis.bat
```

Option 2 (manual):

```powershell
.\.venv\Scripts\python.exe main.py
```

## Common Voice Commands

- "open notepad"
- "close notepad"
- "open chrome"
- "type hello world"
- "search python decorators"
- "what is my name"
- "my name is Abijith"

## Runtime Diagnostics

On startup, Jarvis checks optional dependencies and service availability:

- Ollama reachability
- Tesseract availability
- Optional packages (`selenium`, `pyautogui`, `pytesseract`, `opencv-python`, `beautifulsoup4`)

If some components are missing, core voice chat can still run while those features are disabled.

## Troubleshooting

### Ollama not reachable
- Make sure `ollama serve` is running.
- Verify `http://localhost:11434/api/tags` is accessible.

### No speech recognition output
- Check microphone permissions in Windows settings.
- Confirm the selected input device is active.
- Speak clearly and pause briefly after commands.

### OCR not working
- Install Tesseract OCR.
- Add `tesseract.exe` to PATH or set environment variable `TESSERACT_CMD`.

### Automation commands not acting
- Keep target windows in focus.
- Run the terminal as standard user (or admin if required by target apps).

## Notes

- `jarvis_all_in_one.py` contains a merged snapshot of multiple modules for reference.
- The modular code under `src/` is the source of truth for ongoing development.
