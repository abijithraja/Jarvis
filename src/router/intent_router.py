"""
Smart intent engine: keyword fast-path + slot filling + context carry.
"""
import re
import json

_SYSTEM_KW = {"time", "date", "day", "clock", "today"}
_AGENT_KW = {
    "open","close","launch","start","quit","exit","type","click","move",
    "scroll","press","search","google","youtube","chrome","notepad",
    "calculator","spotify","screenshot","volume","shutdown","restart","sleep",
    "play","pause","skip","next","stop","remind","reminder","alarm","timer",
    "weather",
}
_MEMORY_KW = {"remember","forget","my name","my name is","what did i","what have i"}
_CODE_KW = {"write code","generate code","write a script","python program","implement"}
_CONVO_KW = {"what","why","how","explain","who","where","tell me","define"}
_SUMMARY_SEARCH_HINTS = {"latest", "trend", "trends", "news", "update", "updates"}

def detect_intent(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    if words & _MEMORY_KW or "my name" in lower:
        return "memory"
    if any(p in lower for p in _CODE_KW):
        return "code_gen"
    if words & _SYSTEM_KW and len(words) < 8:
        return "system_tool"
    if "summary" in lower and words & _SUMMARY_SEARCH_HINTS:
        return "agent_task"
    if words & _AGENT_KW:
        return "agent_task"
    if words & _CONVO_KW:
        return "conversation"
    return _llm_classify(text)

def extract_slots(text: str, intent: str) -> dict:
    lower = text.lower()
    slots = {}
    if intent == "agent_task":
        for app in ["notepad","chrome","calculator","spotify","youtube"]:
            if app in lower:
                slots["app"] = app
                break
        m = re.search(r"search(?:\s+for)?\s+(.+)", lower)
        if m: slots["query"] = m.group(1).strip()
        if "query" not in slots:
            m = re.search(r"(?:summary|summarize)(?:\s+(?:about|on|of))?\s+(.+)", lower)
            if m:
                slots["query"] = m.group(1).strip(" .?!")
        m = re.search(r"type\s+(.+)", lower)
        if m: slots["text"] = m.group(1).strip()
        m = re.search(r"in\s+(\d+)\s+(minute|hour|second)s?", lower)
        if m:
            slots["remind_in"] = int(m.group(1))
            slots["remind_unit"] = m.group(2)
    elif intent == "system_tool":
        slots["subtype"] = "date" if any(w in lower for w in ["date","day"]) else "time"
    return slots

def needs_clarification(text: str, slots: dict):
    lower = text.lower().strip()
    patterns = [
        (r"\bsearch\b(?!.*for\b)", "What should I search for?"),
        (r"\bopen\b(?!\s+\w)", "What app would you like me to open?"),
        (r"\bplay\b(?!\s+\w)", "What would you like me to play?"),
        (r"\btype\b$", "What should I type?"),
    ]
    for pattern, question in patterns:
        if re.search(pattern, lower) and not slots:
            return question
    return None

class ContextTracker:
    def __init__(self):
        self.last_intent = None
        self.last_slots = {}
        self.last_text = None

    def update(self, text, intent, slots):
        self.last_text = text
        self.last_intent = intent
        self.last_slots = slots

    def resolve(self, text):
        lower = text.lower()
        if self.last_slots.get("app") and any(w in lower for w in ["it","that","this","the app"]):
            text = re.sub(r"\b(it|that|this|the app)\b", self.last_slots["app"], text, flags=re.I)
        return text

def _llm_classify(text: str) -> str:
    from src.llm.ollama_client import generate_response
    prompt = f"""Classify user input into ONE: conversation | system_tool | agent_task | memory | code_gen
Reply ONLY with JSON: {{"intent": "conversation"}}
Input: {text}"""
    response = generate_response(prompt)
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        data = json.loads(response[start:end])
        intent = data.get("intent", "conversation")
        return intent if intent in {"conversation","system_tool","agent_task","memory","code_gen"} else "conversation"
    except Exception:
        return "conversation"

context = ContextTracker()
