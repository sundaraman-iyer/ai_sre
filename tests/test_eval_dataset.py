"""Unit tests for evaluation dataset and evaluator structures."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from evals.dataset import BENCHMARK_QA_PAIRS, DATASET_NAME
from evals.evaluators import (
    correctness_evaluator,
    groundedness_evaluator,
    relevance_evaluator,
)


class TestEvalDataset(unittest.TestCase):
    """Test suite for evaluation dataset integrity and evaluator formatting."""

    def test_dataset_size_and_structure(self) -> None:
        """Verify that the evaluation dataset contains expected Q&A pairs and keys."""
        self.assertGreaterEqual(len(BENCHMARK_QA_PAIRS), 15)
        self.assertEqual(DATASET_NAME, "SRE Postmortem RAG Evaluation Dataset")

        for index, item in enumerate(BENCHMARK_QA_PAIRS):
            with self.subTest(index=index):
                self.assertIn("question", item)
                self.assertIn("reference", item)
                self.assertTrue(item["question"].strip())
                self.assertTrue(item["reference"].strip())

    @patch("evals.evaluators._evaluate_with_llm")
    def test_evaluator_dict_formatting(self, mock_evaluate: unittest.mock.MagicMock) -> None:
        """Verify that evaluators return properly structured dicts for LangSmith."""
        mock_evaluate.return_value = (1.0, "Factually correct.")

        class MockRun:
            outputs = {
                "answer": "GitHub DNS downtime was 1h 35m.",
                "sources": ["github_dns_outage.md"],
            }

        class MockExample:
            inputs = {"question": "What was the downtime duration?"}
            outputs = {"reference": "GitHub reported 1 hour 35 minutes downtime."}

        run = MockRun()
        example = MockExample()

        correctness = correctness_evaluator(run, example)
        self.assertEqual(correctness["key"], "correctness")
        self.assertEqual(correctness["score"], 1.0)
        self.assertIn("comment", correctness)

        relevance = relevance_evaluator(run, example)
        self.assertEqual(relevance["key"], "relevance")
        self.assertEqual(relevance["score"], 1.0)

        groundedness = groundedness_evaluator(run, example)
        self.assertEqual(groundedness["key"], "groundedness")
        self.assertEqual(groundedness["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
