"""Unit tests for conversation memory module."""

from __future__ import annotations

import unittest

from memory import MAX_HISTORY_TURNS, ConversationMemory


class TestConversationMemory(unittest.TestCase):
    """Test suite for conversation memory reading, writing, capping, and clearing."""

    def setUp(self) -> None:
        """Create a fresh local memory manager instance for testing."""
        self.memory = ConversationMemory()
        # Force local store for deterministic unit testing
        self.memory._redis_client = None

    def test_empty_session(self) -> None:
        """Test reading history for non-existent or empty session."""
        self.assertEqual(self.memory.get_history("non-existent-session"), [])
        self.assertEqual(self.memory.get_history(""), [])

    def test_add_and_retrieve_turn(self) -> None:
        """Test adding a single Q&A turn and retrieving history."""
        session_id = "test-session-1"
        self.memory.add_turn(
            session_id,
            "What caused GitHub's DNS outage?",
            "A Puppet manifest bug restarted authoritative nameserver but not caching nameserver.",
        )

        history = self.memory.get_history(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "What caused GitHub's DNS outage?")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertIn("Puppet manifest bug", history[1]["content"])

    def test_history_capping(self) -> None:
        """Test that history is capped to MAX_HISTORY_TURNS (6 turns)."""
        session_id = "test-session-cap"
        for index in range(1, 6):
            self.memory.add_turn(
                session_id,
                f"Question {index}",
                f"Answer {index}",
            )

        history = self.memory.get_history(session_id)
        self.assertEqual(len(history), MAX_HISTORY_TURNS)
        # Should contain the latest 3 turns (Question 3, 4, 5)
        self.assertEqual(history[0]["content"], "Question 3")
        self.assertEqual(history[-1]["content"], "Answer 5")

    def test_session_isolation(self) -> None:
        """Test that history is completely isolated between different session IDs."""
        session_a = "session-a"
        session_b = "session-b"

        self.memory.add_turn(session_a, "Q A", "Ans A")
        self.memory.add_turn(session_b, "Q B", "Ans B")

        hist_a = self.memory.get_history(session_a)
        hist_b = self.memory.get_history(session_b)

        self.assertEqual(len(hist_a), 2)
        self.assertEqual(len(hist_b), 2)
        self.assertEqual(hist_a[0]["content"], "Q A")
        self.assertEqual(hist_b[0]["content"], "Q B")

    def test_clear_session(self) -> None:
        """Test clearing session history."""
        session_id = "session-to-clear"
        self.memory.add_turn(session_id, "Q", "Ans")
        self.assertEqual(len(self.memory.get_history(session_id)), 2)

        self.memory.clear_session(session_id)
        self.assertEqual(self.memory.get_history(session_id), [])


if __name__ == "__main__":
    unittest.main()
