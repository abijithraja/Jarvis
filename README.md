# Jarvis AI — Setup & Run Guide

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Install Tesseract OCR (for screen reading)
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Install to default path: `C:\Program Files\Tesseract-OCR\`

## 3. Install & start Ollama (for AI responses)
- Download: https://ollama.com
- Pull the model:
```bash
ollama pull llama3
ollama serve
```

## 4. Run Jarvis

### Terminal mode:
```bash
python main.py
```

### GUI mode:
```bash
python jarvis_gui.py
```

---

## File structure
```
jarvis/
├── main.py                    # Entry point
├── jarvis_gui.py              # GUI launcher
├── requirements.txt
└── src/
    ├── audio/
    │   └── vad_recorder.py    # Mic recording with silence detection
    ├── stt/
    │   └── whisper_stt.py     # Speech-to-text via Whisper
    ├── llm/
    │   └── ollama_client.py   # LLM via Ollama (llama3)
    ├── tts/
    │   └── speaker.py         # Text-to-speech
    ├── router/
    │   └── intent_router.py   # Classify user intent
    ├── memory/
    │   ├── memory.py          # Persistent key-value memory
    │   ├── task_memory.py     # Session task history
    │   └── state.py           # Runtime app state
    ├── agent/
    │   ├── system_agent.py    # Desktop commands (open/close/type)
    │   ├── external_agent.py  # Apps, browser, web search
    │   ├── browser_agent.py   # Selenium browser automation
    │   ├── web_agent.py       # DuckDuckGo search + summarize
    │   ├── vision.py          # Screen OCR
    │   ├── planner.py         # LLM-based task planner
    │   └── executor.py        # Step executor
    └── utils/
        ├── system_tools.py    # Time / date
        ├── animation.py       # Thinking spinner
        ├── code_writer.py     # Save generated code to file
        └── runtime_checks.py  # Startup diagnostics
```

## Common issues

| Problem | Fix |
|---|---|
| `Ollama not running` | Run `ollama serve` in a terminal |
| `No module named pvporcupine` | Wake word is optional — Jarvis still works without it |
| `Tesseract not found` | Install Tesseract or skip — vision features are optional |
| `Mic not recording` | Check default input device in system sound settings |
| `llama3 not found` | Run `ollama pull llama3` |
