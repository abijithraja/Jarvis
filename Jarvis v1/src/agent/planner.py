from src.llm.ollama_client import generate_response
import json


def create_plan(task):
    prompt = f"""
    You are a planning AI.

    Convert the user request into steps.

    STRICT RULES:
    - ONLY return JSON
    - NO explanation
    - NO extra text

    Format:
{{\"steps\": [\"step1\", \"step2\"]}}

    Examples:
    Task: open notepad and type hello
    Output: {{\"steps\": [\"open notepad\", \"type hello\"]}}

    Task: write binary search in python
    Output: {{\"steps\": [\"open notepad\", \"generate code for binary search in python\"]}}

    Now do this:

Task: {task}
"""

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        json_str = response[start:end]

        data = json.loads(json_str)
        return data.get("steps", [])
    except Exception:
        return []
