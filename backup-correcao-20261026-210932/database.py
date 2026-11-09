"""Persistent local conversation history and explicit user memories."""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(password|senha|token|api[_ -]?key|chave privada)\b\s*(?:é|e|:|=)\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


def _redact(text: str) -> str:
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[segredo omitido da memória local]", cleaned)
    return cleaned


class LocalMemory:
    def __init__(self, path: str | Path | None = None):
        if path is None:
            override = os.environ.get("PRIA_MEMORY_PATH")
            if override:
                path = Path(override).expanduser()
        if path is None:
            local_app_data = os.environ.get("LOCALAPPDATA")
            root = Path(local_app_data) / "PRIA" if local_app_data else Path.home() / ".pria"
            root.mkdir(parents=True, exist_ok=True)
            path = root / "memory.sqlite3"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS messages ("
                "id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, session_id TEXT NOT NULL, "
                "role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS facts ("
                "id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, content TEXT NOT NULL UNIQUE)"
            )

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Role inválido.")
        with self._connect() as db:
            db.execute(
                "INSERT INTO messages(created_at,session_id,role,content) VALUES(?,?,?,?)",
                (self._now(), session_id, role, _redact(content)),
            )

    def recent_messages(self, session_id: str | None, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as db:
            if session_id is None:
                rows = db.execute(
                    "SELECT role,content FROM messages ORDER BY id DESC LIMIT ?",
                    (max(1, min(limit, 50)),),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                    (session_id, max(1, min(limit, 50))),
                ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def list_conversations(self, limit: int = 100) -> list[dict[str, str]]:
        """Return saved chats newest first, titled from each chat's first user message."""
        bounded_limit = max(1, min(limit, 500))
        with self._connect() as db:
            rows = db.execute(
                "SELECT session_id, MAX(id) AS last_id FROM messages "
                "GROUP BY session_id ORDER BY last_id DESC LIMIT ?",
                (bounded_limit,),
            ).fetchall()
            conversations = []
            for row in rows:
                first = db.execute(
                    "SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
                    (row["session_id"],),
                ).fetchone()
                title = " ".join((first["content"] if first else "Nova conversa").split())
                if len(title) > 54:
                    title = title[:51].rstrip() + "…"
                last = db.execute("SELECT created_at FROM messages WHERE id=?", (row["last_id"],)).fetchone()
                conversations.append({
                    "session_id": row["session_id"],
                    "title": title or "Nova conversa",
                    "updated_at": last["created_at"] if last else "",
                })
        return conversations

    def conversation_messages(self, session_id: str) -> list[dict[str, str]]:
        """Load a complete chat in display order."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT role,content FROM messages WHERE session_id=? ORDER BY id", (session_id,)
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def remember(self, content: str) -> None:
        fact = content.strip()
        if not fact:
            raise ValueError("A memória não pode ficar vazia.")
        if _redact(fact) != fact or "-----BEGIN" in fact:
            raise ValueError("Não salvo senhas, tokens nem chaves privadas na memória comum.")
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO facts(created_at,content) VALUES(?,?)", (self._now(), fact))

    def all_data(self) -> tuple[list[str], list[tuple[str, str, str]]]:
        with self._connect() as db:
            facts = [row[0] for row in db.execute("SELECT content FROM facts ORDER BY id")]
            messages = [
                (row[0], row[1], row[2])
                for row in db.execute("SELECT created_at,role,content FROM messages ORDER BY id")
            ]
        return facts, messages

    def all_facts(self) -> list[str]:
        return self.all_data()[0]

    def delete_all(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM facts")
