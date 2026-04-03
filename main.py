"""
Jarvis AI — Tier A main pipeline
Wake word → STT → Intent + Slots → Skills → Agents → LLM → TTS → Loop
"""

import time
import logging
import os
import re
from logging.handlers import RotatingFileHandler

# ─── Logging setup ────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)
_log = logging.getLogger("jarvis")
_log.setLevel(logging.DEBUG)
_fh = RotatingFileHandler("logs/jarvis.log", maxBytes=2_000_000, backupCount=3)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_log.addHandler(_fh)

# ─── Imports ─────────────────────────────────────────────────────────────────

from src.stt.whisper_stt          import transcribe_audio
from src.llm.ollama_client        import generate_response, stream_response
from src.router.intent_router     import detect_intent, extract_slots, needs_clarification, context
from src.utils.system_tools       import get_time, get_date
from src.agent.external_agent     import run_external_agent
from src.agent.system_agent       import handle_system_command
from src.tts.speaker              import speak
from src.utils.animation          import start_thinking, stop_thinking
from src.memory.memory_system     import (
    conversation, semantic, persona,
    store_fact, get_fact, store_memory,
    get_pending_reminders, mark_reminder_fired
)
from src.memory.task_memory       import add_task
from src.utils.code_writer        import write_code_to_file
from src.agent.planner            import create_plan
from src.agent.executor           import execute_plan
from src.utils.runtime_checks     import collect_runtime_warnings
from src.skills.skills            import dispatch as skill_dispatch


# ─── Startup ─────────────────────────────────────────────────────────────────

def run_jarvis():
    """Full continuous loop — used when running main.py directly."""
    print("=" * 20)
    print("🤖  JARVIS ")
    print("=" * 20)

    warnings = collect_runtime_warnings()
    if warnings:
        print("\n⚠️  Startup warnings:")
        for w in warnings:
            print(f"   • {w}")
        print()

    _start_reminder_watcher()
    speak("Hello, Jarvis is online.")
    print("\nReady. Say 'Hey Jarvis' or just speak.\n")

    try:
        while True:
            run_jarvis_once()
    except KeyboardInterrupt:
        print("\n👋  Jarvis stopped.")
        speak("Goodbye!")


def run_jarvis_once(gui=None):
    """Single listen-respond cycle. Called by the GUI loop."""
    text = transcribe_audio()
    if not text or len(text.strip()) < 2:
        return

    print(f"\n🧑  You: {text}")
    _log.info(f"User: {text}")
    add_task(text)

    response = process_text(text, gui=gui)

    print(f"🤖  Jarvis: {response}")
    _log.info(f"Jarvis: {response}")

    conversation.add_user(text)
    conversation.add_assistant(response)
    semantic.add(text)

    speak(response)
    time.sleep(0.25)


# ─── Core text processor (also used by GUI text input) ───────────────────────

def process_text(text: str, gui=None) -> str:
    text_lower = text.lower().strip()

    # 0. Resolve context references ("open it", "close that")
    text = context.resolve(text)

    # 1. Built-in memory commands
    r = _handle_memory(text_lower)
    if r:
        return r

    # 2. Skill dispatch (weather, reminders, news, spotify, etc.)
    enabled = gui.get_enabled_skills() if gui else None
    r = _handle_skills(text, enabled)
    if r:
        return r

    # 3. System commands (open/close apps, type, screenshot)
    r = handle_system_command(text)
    if r:
        _log.debug(f"System agent: {r}")
        return r

    # 4. Time / Date (no LLM)
    if _is_time_query(text_lower):
        return f"The exact time is {get_time()}."
    if any(w in text_lower for w in ["what date", "today's date", "what day is it"]):
        return f"Today is {get_date()}."

    # 5. Intent detection + slot filling
    intent = detect_intent(text)
    slots  = extract_slots(text, intent)
    context.update(text, intent, slots)

    # 6. Clarification if needed
    clarify = needs_clarification(text, slots)
    if clarify:
        return clarify

    # 7. Code generation
    if intent == "code_gen":
        return _handle_code_gen(text)

    # 8. Multi-step planning
    if any(w in text_lower for w in ["do this", "execute the task", "step by step"]):
        steps = create_plan(text)
        if steps:
            return execute_plan(steps) or "Plan executed."
        return "I couldn't create a plan for that."

    # 9. Search / web
    if intent == "agent_task" and slots.get("query"):
        return _handle_search(slots["query"])

    # 10. Agent task
    if intent == "agent_task":
        r = run_external_agent(text)
        return r

    # 11. LLM conversation — inject conversation history for context
    return _llm_respond(text)


# ─── Sub-handlers ─────────────────────────────────────────────────────────────

def _handle_memory(text_lower: str):
    if any(p in text_lower for p in ["calibrate mic", "calibrate microphone", "mic calibration", "calibrate audio"]):
        try:
            from src.audio.vad_recorder import calibrate_microphone
            result = calibrate_microphone(seconds=5.0)
            return (
                "Mic calibrated. "
                f"Noise floor {result['noise_floor']:.4f}, "
                f"speech threshold {result['threshold']:.4f}."
            )
        except Exception as e:
            _log.error(f"Mic calibration failed: {e}")
            return f"I couldn't calibrate the mic: {e}"

    if "my name is" in text_lower:
        import re
        name = re.sub(r".*my name is\s*", "", text_lower).strip().title()
        store_fact("name", name)
        persona.set("name", name)
        return f"Nice to meet you, {name}! I'll always remember that."

    if any(p in text_lower for p in ["what is my name", "what's my name", "do you know my name"]):
        name = persona.get("name") or get_fact("name")
        return f"Your name is {name}." if name else "I don't know your name yet. Tell me!"

    if "remember that" in text_lower:
        fact = text_lower.replace("remember that", "").strip()
        store_memory(fact)
        return f"Got it, I'll remember: {fact}."

    if any(p in text_lower for p in ["what do you remember", "what did i say", "my recent commands"]):
        from src.memory.task_memory import get_recent_tasks
        tasks = get_recent_tasks(5)
        return "Recent: " + "; ".join(tasks) if tasks else "Nothing recent."

    if "set my voice to" in text_lower:
        import re
        voice = re.sub(r".*set my voice to\s*", "", text_lower).strip()
        from src.tts.speaker import set_voice
        set_voice(voice)
        persona.set("preferred_voice", voice)
        return f"Voice changed to {voice}."

    return None


def _handle_skills(text: str, enabled_skills: set | None) -> str | None:
    result = skill_dispatch(text, enabled_skills)
    return result


def _handle_code_gen(text: str) -> str:
    filename, target_dir = _extract_code_output_target(text)
    start_thinking()
    try:
        prompt = (
            f"Write clean, working Python code for: {text}. "
            "Output ONLY the code, no explanation. Include comments."
        )
        code = generate_response(prompt)
    finally:
        stop_thinking()
    path = write_code_to_file(code, filename=filename, directory=target_dir)
    store_memory(f"Generated code: {text}")
    return f"Done! {path}"


def _extract_code_output_target(text: str) -> tuple[str, str | None]:
    """Detect optional filename/location hints from a code-gen request."""
    filename = "output.py"
    directory = None

    m = re.search(r"(?:named|called)\s+([a-zA-Z0-9_.-]+\.py)", text, re.I)
    if m:
        filename = m.group(1)

    if "desktop" in text.lower():
        directory = os.path.join(os.path.expanduser("~"), "Desktop")

    return filename, directory


def _is_time_query(text_lower: str) -> bool:
    if "timer" in text_lower:
        return False
    if any(p in text_lower for p in [
        "what time",
        "what is the time",
        "what's the time",
        "current time",
        "time now",
        "tell me the time",
        "exact time",
    ]):
        return True
    return bool("time" in text_lower and any(w in text_lower for w in ["what", "tell", "current", "exact", "now"]))


def _handle_search(query: str) -> str:
    try:
        from src.agent.web_agent import search_and_summarize
        return search_and_summarize(query)
    except Exception:
        return run_external_agent(f"search {query}")


def _llm_respond(text: str) -> str:
    # Build context-aware prompt
    history = conversation.get_context_string(last_n=6)
    relevant = semantic.search(text, top_k=2)
    mem_ctx = "\n".join(relevant) if relevant else ""

    prompt_parts = []
    if mem_ctx:
        prompt_parts.append(f"[Relevant past context]\n{mem_ctx}")
    if history:
        prompt_parts.append(f"[Recent conversation]\n{history}")
    prompt_parts.append(f"User: {text}")

    prompt = "\n\n".join(prompt_parts)

    start_thinking()
    try:
        response = stream_response(prompt)
    except Exception as e:
        _log.error(f"LLM error: {e}")
        response = generate_response(text)
    finally:
        stop_thinking()

    return response


# ─── Reminder watcher ────────────────────────────────────────────────────────

def _start_reminder_watcher():
    import threading

    def _watch():
        while True:
            try:
                for r in get_pending_reminders():
                    speak(f"Reminder: {r['message']}")
                    print(f"\n🔔  Reminder: {r['message']}")
                    mark_reminder_fired(r["id"])
            except Exception:
                pass
            time.sleep(15)

    threading.Thread(target=_watch, daemon=True).start()


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_jarvis()
