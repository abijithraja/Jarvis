import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "nous-hermes2"


def generate_response(prompt):
    system_prompt = """
You are Jarvis, a friendly and natural AI assistant.
Speak like a human, casually and clearly.
Keep answers short (1-2 sentences).
Avoid robotic or formal tone.
"""

    full_prompt = f"{system_prompt}\nUser: {prompt}\nJarvis:"

    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)

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
        json={"model": MODEL, "prompt": prompt, "stream": True},
        stream=True,
        timeout=90,
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
