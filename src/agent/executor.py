import time
from src.agent.system_agent import handle_system_command
from src.agent.external_agent import run_external_agent


def execute_plan(steps: list[str]) -> str:
    """
    Execute a list of planned steps in order.
    Tries system_agent first, falls back to external_agent.
    """
    results = []

    for i, step in enumerate(steps):
        print(f"  ▶ Step {i+1}: {step}")

        # Small delay between steps so OS can catch up
        if i > 0:
            time.sleep(1.0)

        result = handle_system_command(step)
        if result is None:
            result = run_external_agent(step)

        results.append(result)
        print(f"  ✓ {result}")

    return ". ".join(r for r in results if r)
