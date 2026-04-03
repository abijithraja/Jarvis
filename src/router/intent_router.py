import json
from src.llm.ollama_client import generate_response


def detect_intent(text):
    prompt = f"""
Classify the user input into ONE:

- conversation → questions, coding, explanations
- system_tool → time, date
- agent_task → actions like open app, type, search

STRICT RULES:
- Coding = conversation
- Questions = conversation
- Only real actions = agent_task

Respond ONLY JSON:
{{"intent": "conversation"}}

Input: {text}
"""

    response = generate_response(prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        return json.loads(response[start:end]).get("intent", "conversation")
    except:
        return "conversation"
