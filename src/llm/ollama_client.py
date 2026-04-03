import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MODEL = "qwen2.5:14b"

# Qwen2.5 responds well to clear role + structured instructions
SYSTEM_PROMPT = """You are Jarvis, a smart, witty, and efficient AI voice assistant.

RULES:
- Reply in 1-3 short sentences MAX unless the user asks for detail
- Be natural and conversational, like a knowledgeable friend
- For code: write clean, commented Python unless told otherwise
- For facts: be direct and confident, skip filler phrases
- Never say "Certainly!", "Of course!", "Great question!" or similar fluff
- If you don't know something, say so plainly
- You are running locally on the user's machine — be aware of privacy and speed
"""


def is_ollama_running() -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def is_model_available() -> bool:
    """Check if qwen2.5:14b is actually pulled and ready."""
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        return any("qwen2.5" in m for m in models)
    except Exception:
        return False


def generate_response(prompt: str) -> str:
    """Send a prompt to Qwen2.5:14b and return the full response."""
    if not is_ollama_running():
        return "Ollama is not running. Please start it with: ollama serve"

    if not is_model_available():
        return "Qwen2.5:14b is still downloading. Please wait and try again."

    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,    # Qwen supports separate system field
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,     # balanced creativity vs accuracy
            "top_p": 0.9,
            "repeat_penalty": 1.1,  # avoids Qwen's occasional repetition loops
            "num_predict": 256,     # keep voice responses concise
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        return result if result else "I didn't get a response, sorry."
    except requests.exceptions.Timeout:
        return "Response timed out. Qwen might still be loading — try again in a moment."
    except Exception as e:
        return f"Ollama error: {str(e)}"


def stream_response(prompt: str) -> str:
    """Stream a response token by token and return the full text."""
    if not is_ollama_running():
        return "Ollama is not running. Please start it with: ollama serve"

    if not is_model_available():
        return "Qwen2.5:14b is still downloading. Please wait and try again."

    payload = {
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 256,
        }
    }

    full_text = ""

    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")
                full_text += token
                if chunk.get("done"):
                    break
        return full_text.strip()

    except Exception as e:
        return f"Stream error: {str(e)}"
