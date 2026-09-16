"""Multi-turn conversation memory store backed by Upstash Redis REST API.

Provides persistent session history for multi-turn conversations across requests.
Falls back to a thread-safe local in-memory store if Upstash credentials are not set.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


MAX_HISTORY_TURNS = 6  # Cap to last 6 turns (3 Q&A pairs)
SESSION_TTL_SECONDS = 604800  # 7 days in seconds


class ConversationMemory:
    """Manages multi-turn conversation state using Upstash Redis or local fallback."""

    def __init__(self) -> None:
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self._redis_client: Any | None = None
        self._local_store: dict[str, list[dict[str, str]]] = {}
        self._local_lock = threading.Lock()

        if self.url and self.token:
            try:
                from upstash_redis import Redis

                self._redis_client = Redis(url=self.url, token=self.token)
                print("Upstash Redis REST client initialized for session memory.")
            except Exception as err:
                print(
                    f"Warning: Failed to initialize Upstash Redis ({err}). Using local fallback store."
                )
                self._redis_client = None
        else:
            print("Upstash Redis environment variables not set. Using local fallback store.")

    def _redis_key(self, session_id: str) -> str:
        return f"sre_assistant:session:{session_id}"

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Retrieve stored conversation turns for a session ID.

        Returns:
            list[dict[str, str]]: List of turn dictionaries e.g. [{"role": "user", "content": "..."}, ...]
        """
        if not session_id or not session_id.strip():
            return []

        clean_id = session_id.strip()

        if self._redis_client is not None:
            try:
                key = self._redis_key(clean_id)
                raw_data = self._redis_client.get(key)
                if raw_data:
                    turns = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    if isinstance(turns, list):
                        return turns[-MAX_HISTORY_TURNS:]
            except Exception as err:
                print(f"Error fetching session history from Upstash Redis ({err}).")

        with self._local_lock:
            turns = self._local_store.get(clean_id, [])
            return turns[-MAX_HISTORY_TURNS:]

    def add_turn(self, session_id: str, user_question: str, assistant_answer: str) -> None:
        """Store a new Q&A turn for a session ID.

        Args:
            session_id (str): Unique session identifier.
            user_question (str): The user's question (sanitized).
            assistant_answer (str): The assistant's generated answer.
        """
        if not session_id or not session_id.strip():
            return

        clean_id = session_id.strip()
        new_turns = [
            {"role": "user", "content": user_question},
            {"role": "assistant", "content": assistant_answer},
        ]

        history = self.get_history(clean_id)
        updated_history = (history + new_turns)[-MAX_HISTORY_TURNS:]

        if self._redis_client is not None:
            try:
                key = self._redis_key(clean_id)
                self._redis_client.set(key, json.dumps(updated_history), ex=SESSION_TTL_SECONDS)
                return
            except Exception as err:
                print(
                    f"Error persisting turn to Upstash Redis ({err}). Falling back to local store."
                )

        with self._local_lock:
            self._local_store[clean_id] = updated_history

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session ID."""
        if not session_id or not session_id.strip():
            return

        clean_id = session_id.strip()
        if self._redis_client is not None:
            try:
                self._redis_client.delete(self._redis_key(clean_id))
            except Exception as err:
                print(f"Error deleting session from Upstash Redis ({err}).")

        with self._local_lock:
            self._local_store.pop(clean_id, None)


# Global memory manager instance
memory = ConversationMemory()
