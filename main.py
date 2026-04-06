"""
Jarvis Version 1
Wake word → STT → Intent + Slots → Skills → Agents → LLM → TTS → Loop
"""

import time
import logging
import os
import re
import atexit
import queue
import threading
from logging.handlers import RotatingFileHandler
# ─── Logging setup ────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)
_log = logging.getLogger("jarvis")
_log.setLevel(logging.DEBUG)
_fh = RotatingFileHandler("logs/jarvis.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_log.addHandler(_fh)

# ─── Imports ─────────────────────────────────────────────────────────────────

from src.stt.whisper_stt          import transcribe_audio
from src.llm.ollama_client        import generate_response, stream_response
from src.router.intent_router     import detect_intent, extract_slots, needs_clarification, context
from src.utils.system_tools       import get_time, get_date
from src.agent.external_agent     import run_external_agent
from src.agent.system_agent       import handle_system_command
from src.tts.speaker              import speak, stop_speaking
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

try:
    from jarvis_addons.addon_dispatcher import dispatch_addon as _dispatch_addon
except Exception:
    _dispatch_addon = None


_tts_active = threading.Event()
_input_dedupe_lock = threading.Lock()
_last_input_norm = ""
_last_input_ts = 0.0
_runtime_stop_event = threading.Event()
_instance_lock_handle = None


# ─── Startup ─────────────────────────────────────────────────────────────────

def run_jarvis():
    """Full continuous loop — used when running main.py directly."""
    # Keep terminal output clean by default in CLI mode.
    os.environ.setdefault("JARVIS_DISABLE_SPINNER", "1")

    if not _acquire_instance_lock():
        print("Jarvis is already running in another terminal/window.")
        print("Close the other Jarvis instance first, then try again.")
        return

    _runtime_stop_event.clear()

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
    print("\nReady. Say 'Hey Jarvis' or just speak.")
    print("You can also type a command and press Enter. Type 'exit' to stop.\n")

    text_queue: queue.Queue[str] = queue.Queue()
    voice_queue: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()
    text_thread = _start_cli_text_listener(text_queue, stop_event)
    voice_thread = _start_cli_voice_listener(voice_queue, stop_event)

    try:
        while True:
            typed = _dequeue_cli_text(text_queue)
            if typed:
                if _is_cli_exit_command(typed):
                    _announce_exit()
                    break
                _process_user_text(typed)
                continue

            spoken = _dequeue_cli_text(voice_queue)
            if spoken:
                _process_user_text(spoken)
                continue

            time.sleep(0.05)
    except KeyboardInterrupt:
        _announce_exit()
    finally:
        stop_event.set()
        _runtime_stop_event.set()
        _force_shutdown_audio()
        for t in (text_thread, voice_thread):
            if t and t.is_alive():
                t.join(timeout=1.0)
        _release_instance_lock()


def run_jarvis_once(gui=None):
    """Single listen-respond cycle. Called by the GUI loop."""
    text = transcribe_audio()
    if not text or len(text.strip()) < 2:
        return

    _process_user_text(text, gui=gui)


def _process_user_text(text: str, gui=None) -> str:
    """Handle one user utterance regardless of source (voice or typed)."""
    text = text.strip()
    if not text:
        return ""

    if _is_assistant_echo_input(text):
        _log.debug(f"Skipped assistant-echo input: {text}")
        return ""

    if _is_duplicate_input(text):
        _log.debug(f"Skipped duplicate input: {text}")
        return ""

    print(f"\n🧑  You: {text}")
    _log.info(f"User: {text}")
    add_task(text)

    response = process_text(text, gui=gui)

    print(f"🤖  Jarvis: {response}")
    _log.info(f"Jarvis: {response}")

    conversation.add_user(text)
    conversation.add_assistant(response)
    semantic.add(text)

    _tts_active.set()
    try:
        speak(response)
    finally:
        _tts_active.clear()
    time.sleep(0.25)
    return response


def _start_cli_text_listener(text_queue: queue.Queue[str], stop_event: threading.Event):
    """Background input listener so terminal users can type while voice mode is running."""

    def _reader():
        while not stop_event.is_set():
            try:
                line = input()
            except EOFError:
                break
            except Exception:
                break

            if stop_event.is_set():
                break

            text = (line or "").strip()
            if text:
                text_queue.put(text)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    return t


def _start_cli_voice_listener(voice_queue: queue.Queue[str], stop_event: threading.Event):
    """Background voice listener for hybrid terminal mode (typed + spoken)."""

    def _voice_reader():
        while not stop_event.is_set():
            if _tts_active.is_set():
                time.sleep(0.08)
                continue

            text = transcribe_audio(verbose=False, stop_event=stop_event)
            if stop_event.is_set():
                break
            if text and len(text.strip()) >= 2:
                voice_queue.put(text.strip())

    t = threading.Thread(target=_voice_reader, daemon=True)
    t.start()
    return t


def _dequeue_cli_text(text_queue: queue.Queue[str]) -> str | None:
    try:
        return text_queue.get_nowait()
    except queue.Empty:
        return None


def _is_cli_exit_command(text: str) -> bool:
    return text.strip().lower() in {"exit", "quit", "stop", "bye", "close jarvis", "stop jarvis"}


def _is_duplicate_input(text: str, window_seconds: float = 2.0) -> bool:
    global _last_input_norm, _last_input_ts

    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    if not normalized:
        return False

    now = time.time()
    with _input_dedupe_lock:
        is_dup = normalized == _last_input_norm and (now - _last_input_ts) <= window_seconds
        if not is_dup:
            _last_input_norm = normalized
            _last_input_ts = now
        return is_dup


def _is_assistant_echo_input(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not normalized:
        return False

    patterns = [
        r"^sent whatsapp desktop message to .+?: .+",
        r"^sent whatsapp message to .+?: .+",
        r"^what message should i send to .+\?$",
        r"^who should i send the message to\??$",
        r"^whatsapp desktop is open and ready\.?$",
    ]
    return any(re.match(p, normalized) for p in patterns)


def _announce_exit():
    print("\n👋  Jarvis stopped.")

    # Keep CLI exit instant by default. Set JARVIS_SPEAK_EXIT=1 to hear goodbye.
    speak_exit = os.environ.get("JARVIS_SPEAK_EXIT", "0").strip().lower() in {"1", "true", "yes", "on"}
    if speak_exit:
        _tts_active.set()
        try:
            speak("Goodbye!")
        finally:
            _tts_active.clear()


def _force_shutdown_audio():
    """Stop any active audio capture/playback immediately during shutdown."""
    try:
        import sounddevice as sd
        sd.stop()
    except Exception:
        pass

    try:
        stop_speaking()
    except Exception:
        pass


def _acquire_instance_lock() -> bool:
    """Allow only one active Jarvis process at a time per machine/user profile."""
    global _instance_lock_handle

    base_dir = os.path.dirname(os.path.abspath(__file__))
    lock_path = os.path.join(base_dir, "logs", "jarvis.instance.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)

    try:
        _instance_lock_handle = open(lock_path, "a+")
    except Exception:
        _instance_lock_handle = None
        return True

    try:
        if os.name == "nt":
            import msvcrt
            _instance_lock_handle.seek(0)
            msvcrt.locking(_instance_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_instance_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        try:
            _instance_lock_handle.close()
        except Exception:
            pass
        _instance_lock_handle = None
        return False

    try:
        _instance_lock_handle.seek(0)
        _instance_lock_handle.truncate()
        _instance_lock_handle.write(str(os.getpid()))
        _instance_lock_handle.flush()
    except Exception:
        pass

    return True


def _release_instance_lock():
    global _instance_lock_handle
    if not _instance_lock_handle:
        return
    try:
        if os.name == "nt":
            import msvcrt
            _instance_lock_handle.seek(0)
            msvcrt.locking(_instance_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(_instance_lock_handle.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        _instance_lock_handle.close()
    except Exception:
        pass
    _instance_lock_handle = None


atexit.register(_release_instance_lock)


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

    # 3.5 Addons dispatcher (window manager, screen reader, contacts, etc.)
    r = _handle_addons(text)
    if r:
        _log.debug(f"Addons: {r}")
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
    if result:
        return result

    # Fallback: route WhatsApp intents even when keyword scoring misses typos.
    allow_whatsapp = enabled_skills is None or "whatsapp" in enabled_skills
    if allow_whatsapp:
        try:
            from src.agent.whatsapp_agent import handle_whatsapp_command

            wa_result = handle_whatsapp_command(text)
            if wa_result:
                return wa_result
        except Exception:
            pass

    return None


def _handle_addons(text: str) -> str | None:
    if _dispatch_addon is None:
        return None

    # Keep WhatsApp commands in the primary WhatsApp agent to avoid addon conflicts.
    try:
        from src.agent.whatsapp_agent import is_whatsapp_intent

        if is_whatsapp_intent(text):
            return None
    except Exception:
        pass

    try:
        return _dispatch_addon(text)
    except Exception:
        return None


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
        while not _runtime_stop_event.is_set():
            try:
                for r in get_pending_reminders():
                    if _runtime_stop_event.is_set():
                        break
                    _tts_active.set()
                    try:
                        speak(f"Reminder: {r['message']}")
                    finally:
                        _tts_active.clear()
                    print(f"\n🔔  Reminder: {r['message']}")
                    mark_reminder_fired(r["id"])
            except Exception:
                pass
            time.sleep(15)

    threading.Thread(target=_watch, daemon=True).start()


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_jarvis()
