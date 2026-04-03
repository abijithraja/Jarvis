from src.agent.system_agent import handle_system_command
from src.agent.code_generator import generate_code
import pyautogui
import time


def execute_plan(steps):
    results = []

    for step in steps:
        step_lower = step.lower()

        if "generate code" in step_lower:
            code = generate_code(step)

            time.sleep(2)

            pyautogui.write(code)
            results.append("Code written")

        else:
            res = handle_system_command(step)

            if res:
                results.append(res)

        time.sleep(1)

    return ", ".join(results)
