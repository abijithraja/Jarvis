# Jarvis AI Assistant

Jarvis is a local, voice-enabled AI assistant for Windows. It supports speech input, local LLM responses, text-to-speech, desktop automation, Spotify controls, YouTube play commands, reminders, and memory.

Status: experimental and actively evolving.

## Features

- Voice input with Faster-Whisper transcription
- Local LLM replies through Ollama
- TTS output with pyttsx3 (and optional edge-tts)
- Desktop actions: open and close apps, typing, screenshots, volume
- Spotify controls: open, play, pause, stop, next, previous, resume, close
- WhatsApp Web automation: open, message with emoji, voice call, incoming-call actions
- YouTube play flow: "open youtube and play ..."
- Reminders and timer commands
- Memory commands (store and recall personal context)
- Mic calibration command for better speech detection

## Prerequisites

1. Windows 10 or Windows 11
2. Python 3.10+
3. Working microphone
4. Ollama installed and running

Optional:

- Tesseract OCR for vision commands

## Installation

From PowerShell in repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ollama Setup

Start Ollama and pull the default model:

```powershell
ollama serve
ollama pull qwen2.5:14b
```

Jarvis expects Ollama at `http://localhost:11434`.

## Run Jarvis

Terminal launcher:

```powershell
.\run_jarvis_cmd.bat
```

Direct terminal mode:

```powershell
python main.py
```

GUI mode:

```powershell
python jarvis_gui.py
```

## Useful Commands

General:

- what is the time
- what date is today
- my name is Abijith
- what is my name

Spotify:

- open spotify
- play
- pause music
- next song
- previous song
- resume
- close spotify

YouTube and web:

- open youtube and play rain music
- search latest ai trends
- give me a summary about latest ai trends

WhatsApp:

- open whatsapp
- send message to Alex saying hi smile emoji
- make whatsapp call to Alex
- attend call
- decline call
- convey message I will call you in ten minutes
- use whatsapp desktop mode
- use whatsapp web mode

Notes:

- Default mode is WhatsApp Desktop (`JARVIS_WHATSAPP_MODE=desktop`).
- You can speak partial names; Jarvis will try best-match search instead of requiring exact contact title.
- use whatsapp desktop mode
- use whatsapp web mode

Notes:

- Default mode is WhatsApp Desktop (`JARVIS_WHATSAPP_MODE=desktop`).
- You can speak partial names; Jarvis will try best-match search instead of requiring exact contact title.

System:

- open chrome
- close chrome
- create file named notes on desktop
- take a screenshot

Audio and calibration:

- calibrate mic

## Environment Variables

Optional variables you can set:

- `OPENWEATHER_KEY` for weather skill
- `JARVIS_CITY` default weather city
- `SPOTIFY_TOKEN` for Spotify Web API mode
- `JARVIS_VOICE` preferred TTS voice
- `JARVIS_RATE` TTS speech rate
- `JARVIS_USE_EDGE_TTS` set `1` to enable edge-tts path

## Project Structure

```text
Jarvis/
|- main.py
|- jarvis_gui.py
|- run_jarvis_cmd.bat
|- requirements.txt
|- src/
|  |- agent/
|  |- audio/
|  |- llm/
|  |- memory/
|  |- router/
|  |- skills/
|  |- stt/
|  |- tts/
|  \- utils/
\- README.md
```

## Troubleshooting

### Jarvis hears but does not respond

- Ensure Ollama server is running.
- Check `http://localhost:11434/api/tags`.

### Mic commands not detected well

- Run `calibrate mic` once in a quiet room.
- Speak clearly and pause briefly after commands.
- Verify Windows microphone permissions.

### Spotify commands do not act

- Open Spotify first (`open spotify`).
- Then try `play`, `pause`, `next`, `previous`, `resume`.

### OCR commands fail

- Install Tesseract OCR and ensure `tesseract.exe` is discoverable.

## Notes

- `jarvis_all_in_one.py` is a merged reference file.
- Modular code under `src/` is the active source of truth.
