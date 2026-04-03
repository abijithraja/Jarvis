from src.stt.whisper_stt import transcribe_audio
from src.llm.ollama_client import generate_response
from src.router.intent_router import detect_intent
from src.utils.system_tools import get_time
from src.agent.external_agent import run_external_agent
from src.agent.system_agent import handle_system_command
from src.tts.speaker import speak
from src.memory.memory import store_fact, get_fact
from src.memory.task_memory import add_task, get_tasks
from src.utils.code_writer import write_code_to_file
from src.agent.planner import create_plan
from src.agent.executor import execute_plan
from src.utils.runtime_checks import collect_runtime_warnings
from src.audio.wake_word import contains_wake_phrase, strip_wake_phrase
import time


def run_jarvis():
    print("Jarvis initializing")
    voice_mode = input("Voice mode? (y/n): ").strip().lower() == "y"

    if voice_mode:
        intro = "Hey I am Jarvis, your AI assistant"
        print(f"JARVIS  : {intro}")
        speak(intro)
        print("STATUS  : Say 'hey jarvis' with your task")
    else:
        print("STATUS  : Text mode ready")

    startup_warnings = collect_runtime_warnings()
    if startup_warnings:
        print(f"STATUS  : Diagnostics ({len(startup_warnings)} warnings)")
        for warning in startup_warnings[:3]:
            print(f"- {warning}")

    try:
        while True:
            if voice_mode:
                spoken = transcribe_audio()
                if not spoken:
                    continue

                print(f"HEARD   : {spoken}")

                if not contains_wake_phrase(spoken):
                    continue

                text = strip_wake_phrase(spoken)
                if not text:
                    continue
            else:
                text = input("You: ").strip()

            if not text or len(text.strip()) < 2:
                continue

            if text.lower() in ["exit", "quit"]:
                break

            print("\n----------------------------------------")
            print(f"USER    : {text}")
            print("JARVIS  : Thinking...")
            text_lower = text.lower()
            add_task(text)

            response = handle_system_command(text)

            if response:
                print(f"JARVIS  : {response}")
                print("----------------------------------------\n")
                if voice_mode:
                    speak(response)
                time.sleep(0.7)
                continue

            if "my name is" in text_lower:
                name = text_lower.replace("my name is", "", 1).strip()
                store_fact("name", name)
                response = f"Nice to meet you, {name}!"

            elif "what is my name" in text_lower:
                name = get_fact("name")
                response = f"Your name is {name}" if name else "I don't know your name yet."

            elif "what did i ask" in text_lower:
                tasks = get_tasks()
                response = ", ".join(tasks[-5:]) if tasks else "You haven't asked anything yet."

            elif "time" in text_lower:
                response = f"The current time is {get_time()}"

            elif "write code" in text_lower or "python program" in text_lower:
                code = generate_response(f"Write Python code for: {text}")
                write_code_to_file(code)
                response = "Code has been written to file."

            elif "do this" in text_lower or "task" in text_lower:
                steps = create_plan(text)
                if steps:
                    response = execute_plan(steps)
                else:
                    response = "I couldn't create a plan."

            elif any(word in text_lower for word in ["search", "open", "type", "close", "read screen", "click", "find", "who is", "press enter"]):
                if "search" in text_lower and "google" in text_lower:
                    try:
                        from src.agent.browser_agent import search_google

                        query = text_lower.replace("search", "", 1).replace("google", "", 1).strip()
                        response = search_google(query)
                    except Exception:
                        response = run_external_agent(text)

                elif "read screen" in text_lower:
                    try:
                        from src.agent.vision import read_screen

                        response = read_screen()
                    except Exception:
                        response = "Vision module is not available yet."

                elif "click" in text_lower:
                    try:
                        from src.agent.vision_click import find_and_click

                        target = text_lower.replace("click", "", 1).strip()
                        response = find_and_click(target)
                    except Exception:
                        response = "Vision click is not available yet."

                elif "find" in text_lower or "who is" in text_lower:
                    try:
                        from src.agent.web_agent import search_and_summarize

                        response = search_and_summarize(text_lower)
                    except Exception:
                        response = "Web agent is not available yet."
                else:
                    response = run_external_agent(text)

            else:
                if any(word in text_lower for word in ["python", "code", "algorithm", "explain"]):
                    intent = "conversation"
                else:
                    intent = detect_intent(text)

                if intent == "system_tool":
                    response = f"The current time is {get_time()}" if "time" in text_lower else "I couldn't find the tool."
                elif intent == "agent_task":
                    response = run_external_agent(text)
                else:
                    try:
                        response = generate_response(text)
                    except Exception:
                        response = generate_response(text)

            print(f"JARVIS  : {response}")
            print("----------------------------------------\n")
            if voice_mode:
                speak(response)
            time.sleep(0.7)

    except KeyboardInterrupt:
        print("\nSYSTEM  : Jarvis stopped.")


if __name__ == "__main__":
    run_jarvis()
