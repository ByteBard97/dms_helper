from __future__ import annotations

MAX_HISTORY_WORDS = 10000

import json
from pathlib import Path
from typing import List, Dict

__all__ = ["MAX_HISTORY_WORDS", "load_previous_session_history"]


def _word_count(text: str) -> int:
    """Approximate word count (split by whitespace)."""
    return len(text.split())


def _collect_messages(jsonl_path: Path) -> List[Dict[str, str]]:
    """Parse a session.log.jsonl file and return simplified message dicts.

    Each dict has keys: ``role`` ("user" | "model"), ``content`` (str).
    Intermediate USER fragments are filtered: if two consecutive USER entries
    share the same prefix, only the *longest* (latest) is kept.
    """
    messages: List[Dict[str, str]] = []
    last_user_content: str | None = None

    with jsonl_path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                # Skip malformed lines silently; caller can rely on logging.
                continue

            role = entry.get("role")
            content = entry.get("content", "")
            if not content or role not in {"USER", "ASSISTANT"}:
                continue

            # Normalise role to lowercase names expected by Gemini.
            role_norm = "user" if role == "USER" else "model"

            if role_norm == "user":
                # Skip intermediate fragments: keep only if content *extends* the
                # last stored user content.
                if last_user_content and content.startswith(last_user_content):
                    # Update the previous message instead of appending.
                    messages[-1]["parts"][0] = content
                    last_user_content = content
                    continue
                last_user_content = content

            # Standard Gemini format: {role, parts:[content]}
            messages.append({"role": role_norm, "parts": [content]})

    return messages


def load_previous_session_history(max_words: int = MAX_HISTORY_WORDS) -> List[Dict[str, str]]:  # noqa: D401
    """Return up to *max_words* of the most recent session history.

    Search ``logs/archive`` for the newest ``session.log_*.jsonl`` file. If none
    found, returns an empty list.
    """
    archive_dir = Path("logs") / "archive"
    if not archive_dir.is_dir():
        return []

    jsonl_files = sorted(
        archive_dir.glob("session.log_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not jsonl_files:
        return []

    latest = jsonl_files[0]
    messages = _collect_messages(latest)

    # Enforce token/word limit, keeping *most recent* messages.
    total_words = 0
    trimmed: List[Dict[str, str]] = []
    for msg in reversed(messages):  # start from newest
        content_words = _word_count(msg["parts"][0])
        if total_words + content_words > max_words:
            break
        trimmed.append(msg)
        total_words += content_words

    # Reverse back to chronological order.
    trimmed.reverse()
    return trimmed 