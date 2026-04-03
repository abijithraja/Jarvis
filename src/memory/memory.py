import json
import os

MEMORY_FILE = "memory.json"


def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_memory(data: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def store_fact(key: str, value):
    memory = load_memory()
    memory[key] = value
    save_memory(memory)


def get_fact(key: str):
    return load_memory().get(key, None)


def clear_memory():
    save_memory({})
