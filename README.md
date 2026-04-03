# Jarvis AI Assistant

Jarvis is a local, voice-enabled AI assistant for Windows that combines speech recognition, local LLM responses, text-to-speech, desktop automation, and optional browser and vision tools.

Status: This is an experimental project and is still in progress.

## What It Does

- Listens to microphone input and transcribes speech using Faster-Whisper.
- Generates responses through a local Ollama model.
- Speaks responses using pyttsx3 with optional edge-tts support.
- Executes desktop tasks such as opening apps, typing text, closing apps, and web search.
- Stores simple memory facts and recent task history.
- Supports optional browser automation, OCR screen reading, and web summarization.

## Prerequisites

1. Windows 10 or 11
2. Python 3.10 or newer
3. A working microphone
4. Ollama installed and running

Optional (for OCR and vision features):
- Tesseract OCR installed and available on PATH, or configured via TESSERACT_CMD

## Installation

From PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ollama Setup

Install and start Ollama, then pull the configured model:

```powershell
ollama serve
ollama pull qwen2.5:14b
```

Jarvis expects Ollama at:
- http://localhost:11434

## Run Jarvis

Option 1:

```powershell
.\run_jarvis_cmd.bat
```

Option 2:

```powershell
python main.py
```

Option 3 (GUI):

```powershell
python jarvis_gui.py
```

## Project Structure

```text
Jarvis/
|- main.py
|- jarvis_gui.py
|- run_jarvis_cmd.bat
|- requirements.txt
|- src/
|  |- audio/
|  |- stt/
|  |- llm/
|  |- tts/
|  |- router/
|  |- memory/
|  |- agent/
|  |- skills/
|  \- utils/
\- README.md
```

## Common Voice Commands

- open notepad
- close notepad
- open chrome
- open youtube and play rain music
- open spotify
- pause music
- next song
- what is my name
- my name is Abijith
- what is the time

## Runtime Diagnostics

On startup, Jarvis checks optional dependencies and service availability:

- Ollama reachability
- Tesseract availability
- Optional packages such as selenium, pyautogui, pytesseract, opencv-python, and beautifulsoup4

If some components are missing, core voice chat can still run while those features are disabled.

## Troubleshooting

### Ollama not reachable
- Make sure ollama serve is running.
- Verify http://localhost:11434/api/tags is accessible.

### No speech recognition output
- Check microphone permissions in Windows settings.
- Confirm the selected input device is active.
- Speak clearly and pause briefly after commands.

### OCR not working
- Install Tesseract OCR.
- Add tesseract.exe to PATH or set environment variable TESSERACT_CMD.

### Automation commands not acting
- Keep target windows in focus.
- Run the terminal as standard user, or admin if required by target apps.

## Notes

- jarvis_all_in_one.py contains a merged snapshot of multiple modules for reference.
- The modular code under src is the source of truth for ongoing development.
