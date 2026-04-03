import json
from src.llm.ollama_client import generate_response


def create_plan(task: str) -> list[str]:
    """
    Ask the LLM to break a task into executable steps.
    Returns a list of step strings.
    """
    prompt = f"""You are a task planning AI for a voice assistant.

Convert the user request into simple executable steps.

RULES:
- Return ONLY valid JSON, no explanation
- Steps must be short action phrases
- Max 5 steps

Format:
{{"steps": ["step1", "step2"]}}

Examples:
Task: open notepad and type hello world
Output: {{"steps": ["open notepad", "type hello world"]}}

Task: search python tutorials on google
Output: {{"steps": ["search python tutorials"]}}

Task: {task}
Output:"""

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(response[start:end])
        steps = data.get("steps", [])
        # Validate it's a list of strings
        return [str(s) for s in steps if s] if isinstance(steps, list) else []
    except Exception:
        return []
