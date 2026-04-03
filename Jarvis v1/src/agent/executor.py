from src.agent.external_agent import run_external_agent


def execute_plan(steps):
    results = []

    for step in steps:
        result = run_external_agent(step)
        results.append(result)

    return "\n".join(results)
