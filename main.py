from src.stt.whisper_stt import transcribe_audio
from src.llm.ollama_client import generate_response, stream_response
from src.router.intent_router import detect_intent
from src.utils.system_tools import get_time
from src.agent.external_agent import run_external_agent
from src.agent.system_agent import handle_system_command
from src.tts.speaker import speak
from src.utils.animation import start_thinking, stop_thinking
from src.memory.memory import store_fact, get_fact
from src.memory.task_memory import add_task, get_tasks
from src.utils.code_writer import write_code_to_file
from src.agent.planner import create_plan
from src.agent.executor import execute_plan
from src.utils.runtime_checks import collect_runtime_warnings
import time


def run_jarvis():
    print("🤖 Jarvis: Ready...")

    startup_warnings = collect_runtime_warnings()
    if startup_warnings:
        print("⚠️ Startup diagnostics:")
        for warning in startup_warnings:
            print(f"- {warning}")

    try:
        while True:
            text = transcribe_audio()

            if not text or len(text.strip()) < 2:
                continue

            print(f"\n🧑 You: {text}")
            text_lower = text.lower()
            add_task(text)

            response = handle_system_command(text)

            if response:
                print("⚙️ Executing task...")
                print(f"🤖 Jarvis: {response}")
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
                print("⚡ Generating code...")
                code = generate_response(f"Write Python code for: {text}")
                write_code_to_file(code)
                response = "Code has been written to file."

            elif "do this" in text_lower or "task" in text_lower:
                print("🧠 Planning...")
                steps = create_plan(text)
                if steps:
                    print("Plan:", steps)
                    response = execute_plan(steps)
                else:
                    response = "I couldn't create a plan."

            elif any(word in text_lower for word in ["search", "open", "type", "close", "read screen", "click", "find", "who is"]):
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
                    thinking_thread = start_thinking()
                    try:
                        response = stream_response(text)
                    except Exception:
                        response = generate_response(text)
                    stop_thinking()

            print(f"🤖 Jarvis: {response}")
            speak(response)
            time.sleep(0.7)

    except KeyboardInterrupt:
        print("\n👋 Jarvis stopped.")


if __name__ == "__main__":
    run_jarvis()
