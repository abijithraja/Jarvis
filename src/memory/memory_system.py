"""
Multi-layer memory system for Jarvis.
- Short-term : in-memory conversation buffer (last N turns)
- Long-term  : SQLite-backed persistent key-value + fact store
- Semantic   : simple TF-IDF vector store for "remember when I said..."
"""

import json
import os
import sqlite3
import math
import re
from collections import deque
from datetime import datetime
from threading import Lock

DB_PATH = "jarvis_memory.db"
_lock = Lock()

# ─── Short-term: conversation buffer ────────────────────────────────────────

class ConversationBuffer:
    def __init__(self, max_turns: int = 20):
        self._turns = deque(maxlen=max_turns * 2)  # user + assistant alternating

    def add_user(self, text: str):
        self._turns.append({"role": "user", "content": text, "ts": _now()})

    def add_assistant(self, text: str):
        self._turns.append({"role": "assistant", "content": text, "ts": _now()})

    def get_history(self) -> list[dict]:
        return list(self._turns)

    def get_context_string(self, last_n: int = 6) -> str:
        recent = list(self._turns)[-last_n:]
        lines = []
        for t in recent:
            prefix = "User" if t["role"] == "user" else "Jarvis"
            lines.append(f"{prefix}: {t['content']}")
        return "\n".join(lines)

    def clear(self):
        self._turns.clear()


# ─── Long-term: SQLite store ─────────────────────────────────────────────────

def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                key   TEXT PRIMARY KEY,
                value TEXT,
                ts    TEXT
            );
            CREATE TABLE IF NOT EXISTS memories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                text    TEXT,
                ts      TEXT,
                tags    TEXT
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                message     TEXT,
                trigger_ts  TEXT,
                fired       INTEGER DEFAULT 0
            );
        """)


def store_fact(key: str, value) -> None:
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO facts (key, value, ts) VALUES (?, ?, ?)",
            (key.lower(), json.dumps(value), _now())
        )


def get_fact(key: str):
    with _get_conn() as conn:
        row = conn.execute("SELECT value FROM facts WHERE key=?", (key.lower(),)).fetchone()
        return json.loads(row["value"]) if row else None


def store_memory(text: str, tags: list[str] = None) -> None:
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO memories (text, ts, tags) VALUES (?, ?, ?)",
            (text, _now(), json.dumps(tags or []))
        )


def get_recent_memories(n: int = 10) -> list[str]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT text FROM memories ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [r["text"] for r in reversed(rows)]


def add_reminder(message: str, trigger_ts: str) -> int:
    with _lock, _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (message, trigger_ts) VALUES (?, ?)",
            (message, trigger_ts)
        )
        return cur.lastrowid


def get_pending_reminders() -> list[dict]:
    now = _now()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, message, trigger_ts FROM reminders WHERE fired=0 AND trigger_ts <= ?",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_reminder_fired(rid: int):
    with _lock, _get_conn() as conn:
        conn.execute("UPDATE reminders SET fired=1 WHERE id=?", (rid,))


# ─── Semantic: lightweight TF-IDF vector store ──────────────────────────────

class SemanticMemory:
    """
    Stores text chunks and finds the most similar one to a query
    using TF-IDF cosine similarity. No external deps needed.
    """
    def __init__(self):
        self._docs: list[str] = []
        self._vecs: list[dict] = []

    def add(self, text: str):
        self._docs.append(text)
        self._vecs.append(self._tfidf(text))

    def search(self, query: str, top_k: int = 3) -> list[str]:
        if not self._docs:
            return []
        qv = self._tfidf(query)
        scores = [(self._cosine(qv, dv), doc) for dv, doc in zip(self._vecs, self._docs)]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scores[:top_k] if score > 0.05]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\b[a-z]{2,}\b", text.lower())

    def _tfidf(self, text: str) -> dict:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        freq: dict = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        n = len(self._docs) + 1
        vec = {}
        for term, count in freq.items():
            tf = count / len(tokens)
            df = sum(1 for v in self._vecs if term in v) + 1
            idf = math.log(n / df)
            vec[term] = tf * idf
        return vec

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in b)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0


# ─── User persona store ──────────────────────────────────────────────────────

class UserPersona:
    DEFAULTS = {
        "name": None,
        "preferred_voice": "en-US-GuyNeural",
        "verbosity": "concise",     # concise | detailed
        "safe_mode": True,
        "wake_word": "hey jarvis",
    }

    def get(self, key: str):
        stored = get_fact(f"persona.{key}")
        return stored if stored is not None else self.DEFAULTS.get(key)

    def set(self, key: str, value):
        store_fact(f"persona.{key}", value)

    def all(self) -> dict:
        return {k: self.get(k) for k in self.DEFAULTS}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# Initialise DB on import
_init_db()

# Module-level singletons
conversation = ConversationBuffer(max_turns=20)
semantic     = SemanticMemory()
persona      = UserPersona()
