"""Evaluation runner script for SRE Postmortem RAG Assistant using LangSmith.

Executes correctness, relevance, and groundedness evaluation metrics
across the benchmark Q&A dataset.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from evals.dataset import create_or_get_dataset  # noqa: E402
from evals.evaluators import (  # noqa: E402
    correctness_evaluator,
    groundedness_evaluator,
    relevance_evaluator,
)
from week1_rag import (  # noqa: E402
    TOP_K,
    build_vector_store,
    format_context,
    generate_answer,
    load_corpus,
)


def target_rag_pipeline(inputs: dict[str, Any]) -> dict[str, Any]:
    """Target evaluation function wrapping the core RAG retrieval and generation pipeline.

    Args:
        inputs (dict[str, Any]): Dictionary containing 'question'.

    Returns:
        dict[str, Any]: Dictionary containing 'answer', 'sources', and 'model'.
    """
    question = inputs.get("question", "").strip()
    if not question:
        return {"answer": "No question provided.", "sources": [], "model": "none"}

    # Access global vector store initialized in run_evaluation()
    vector_store = getattr(target_rag_pipeline, "vector_store", None)
    if vector_store is None:
        raise RuntimeError("Vector store was not attached to target_rag_pipeline.")

    retrieved_docs = vector_store.similarity_search(question, k=TOP_K)
    context = format_context(retrieved_docs)
    answer, model_used = generate_answer(question, context)
    sources = list(dict.fromkeys(doc.metadata["source"] for doc in retrieved_docs))

    return {
        "answer": answer,
        "sources": sources,
        "model": model_used,
    }


def run_evaluation() -> None:
    """Execute LangSmith experiment over the benchmark evaluation dataset."""
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://apac.api.smith.langchain.com")

    if not api_key:
        print("\n" + "=" * 70)
        print("ERROR: LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) is missing.")
        print(
            "To run the LangSmith evaluation suite, please add the following to your local .env file:"
        )
        print("    LANGSMITH_API_KEY=your_langsmith_api_key")
        print("    LANGSMITH_ENDPOINT=https://apac.api.smith.langchain.com")
        print("=" * 70 + "\n")
        return

    os.environ["LANGSMITH_ENDPOINT"] = endpoint

    try:
        from langsmith import Client
        from langsmith.evaluation import evaluate
    except ImportError:
        print(
            "Error: 'langsmith' package is required to run evaluation suite. Install with `uv pip install langsmith`."
        )
        return

    print("Initializing LangSmith client...")
    client = Client()

    # Step 1: Idempotently create/fetch dataset
    dataset = create_or_get_dataset(client)

    # Step 2: Initialize local vector store for batch evaluation
    print("Building vector store from postmortem corpus...")
    corpus = load_corpus()
    vector_store = build_vector_store(corpus)
    target_rag_pipeline.vector_store = vector_store  # type: ignore[attr-defined]

    # Step 3: Run LangSmith evaluation experiment
    print(f"\nRunning evaluation experiment against dataset '{dataset.name}'...")
    evaluators = [
        correctness_evaluator,
        relevance_evaluator,
        groundedness_evaluator,
    ]

    experiment_results = evaluate(
        target_rag_pipeline,
        data=dataset.name,
        evaluators=evaluators,
        experiment_prefix="SRE-RAG-Eval",
    )

    print("\n" + "=" * 70)
    print("LANGSMITH EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Dataset Name: {dataset.name}")
    print("Evaluators Executed: Correctness, Relevance, Groundedness")
    print(f"Results Details: {experiment_results}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_evaluation()
