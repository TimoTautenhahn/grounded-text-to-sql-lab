"""A text-to-SQL candidate provider for any OpenAI-compatible chat API.

Configuration comes only from the environment and constructor arguments, never
from files:

    OPENAI_BASE_URL   base URL of the API (default https://api.openai.com/v1)
    OPENAI_API_KEY    the key (required to actually call the API)
    OPENAI_MODEL      default model id if none is passed explicitly

The provider sends the question plus the schema-grounding context and returns the
SQL it extracts from the reply. It uses only the standard library (urllib), so
the lab keeps its zero-dependency core; there is no `openai` package to install.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.openai.com/v1"

SYSTEM_PROMPT = (
    "You are a careful text-to-SQL assistant for SQLite. "
    "Given a database schema and a question, reply with a single SQL query that "
    "answers it. Return only the SQL, no explanation."
)


class MissingApiKey(RuntimeError):
    """Raised when no API key is configured for a real-model run."""


def _extract_sql(text: str) -> str:
    """Pull a SQL statement out of a model reply (handles code fences and labels)."""
    fenced = re.search(r"```(?:sql)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    body = fenced.group(1) if fenced else text
    body = re.sub(r"^\s*sql\s*:\s*", "", body, flags=re.IGNORECASE).strip()
    return body.rstrip(";").strip()


class OpenAICompatibleProvider:
    """Calls a chat-completions endpoint and returns candidate SQL.

    Instances are callables matching ``textsql.baselines.CandidateProvider``:
    ``provider(question, schema) -> sql``.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model or os.environ.get("OPENAI_MODEL") or ""
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.timeout = timeout
        if not self.model:
            raise ValueError("No model set. Pass model= or set OPENAI_MODEL.")
        if not self.api_key:
            raise MissingApiKey(
                "No API key. Set OPENAI_API_KEY (and OPENAI_BASE_URL for a non-OpenAI endpoint)."
            )

    def _chat(self, messages: list[dict]) -> str:
        """POST to /chat/completions and return the assistant message content.

        Isolated so tests can monkeypatch it and run fully offline.
        """
        payload = json.dumps({"model": self.model, "messages": messages, "temperature": 0}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]

    def __call__(self, question: str, schema: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"},
        ]
        try:
            reply = self._chat(messages)
        except urllib.error.URLError as exc:  # network/endpoint problem
            raise RuntimeError(f"Model call failed: {exc}") from exc
        return _extract_sql(reply)
