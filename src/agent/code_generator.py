from src.llm.ollama_client import generate_response


def generate_code(prompt):
    system_prompt = """
You are a coding assistant.

Generate clean, correct code based on the request.
Return ONLY code.
No explanation.
"""

    full_prompt = f"{system_prompt}\nTask: {prompt}"

    return generate_response(full_prompt)
