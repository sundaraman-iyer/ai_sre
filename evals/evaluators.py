"""Custom LLM-as-a-judge evaluators for correctness, relevance, and groundedness.

Uses Groq (via LiteLLM) to evaluate generated answers against reference answers,
user questions, and retrieved source excerpts.
"""

from __future__ import annotations

import json
from typing import Any

PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "groq/openai/gpt-oss-20b"


def _evaluate_with_llm(prompt: str) -> tuple[float, str]:
    """Invoke Groq via LiteLLM to obtain a score (0.0 to 1.0) and reasoning."""
    from litellm import completion

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert AI evaluator for RAG systems. Evaluate the candidate "
                "response based strictly on the instructions. Respond ONLY with a valid JSON "
                'object matching this format: {"score": float_between_0_and_1, "reasoning": "explanation"}.'
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = completion(model=PRIMARY_MODEL, messages=messages)
        content = response.choices[0].message.content
        text = content.strip() if isinstance(content, str) else str(content).strip()
        # Parse JSON output
        data = json.loads(text)
        score = float(data.get("score", 0.0))
        reasoning = str(data.get("reasoning", "No reasoning provided."))
        return max(0.0, min(1.0, score)), reasoning
    except Exception as primary_error:
        print(f"Primary evaluator LLM failed ({primary_error}); retrying with fallback model.")
        try:
            response = completion(model=FALLBACK_MODEL, messages=messages)
            content = response.choices[0].message.content
            text = content.strip() if isinstance(content, str) else str(content).strip()
            data = json.loads(text)
            score = float(data.get("score", 0.0))
            reasoning = str(data.get("reasoning", "No reasoning provided."))
            return max(0.0, min(1.0, score)), reasoning
        except Exception as fallback_error:
            print(f"Fallback evaluator LLM failed ({fallback_error}). Returning zero score.")
            return 0.0, f"Evaluator error: {fallback_error}"


def correctness_evaluator(run: Any, example: Any) -> dict[str, Any]:
    """Evaluate factual correctness of generated answer against reference answer.

    Returns dict formatted for LangSmith: {"key": "correctness", "score": float, "comment": str}
    """
    question = example.inputs.get("question", "") if example and example.inputs else ""
    reference = example.outputs.get("reference", "") if example and example.outputs else ""
    answer = run.outputs.get("answer", "") if run and run.outputs else ""

    prompt = (
        f"Question: {question}\n\n"
        f"Reference Answer (Ground Truth): {reference}\n\n"
        f"Candidate Generated Answer: {answer}\n\n"
        "Instructions: Compare the Candidate Answer with the Reference Answer for factual agreement. "
        "Assign a score of 1.0 if the core factual claims match completely, 0.5 if partially correct, "
        "and 0.0 if factually incorrect or missing."
    )

    score, comment = _evaluate_with_llm(prompt)
    return {"key": "correctness", "score": score, "comment": comment}


def relevance_evaluator(run: Any, example: Any) -> dict[str, Any]:
    """Evaluate whether the generated answer directly addresses the question asked.

    Returns dict formatted for LangSmith: {"key": "relevance", "score": float, "comment": str}
    """
    question = example.inputs.get("question", "") if example and example.inputs else ""
    answer = run.outputs.get("answer", "") if run and run.outputs else ""

    prompt = (
        f"User Question: {question}\n\n"
        f"Candidate Generated Answer: {answer}\n\n"
        "Instructions: Evaluate how directly and completely the Candidate Answer addresses the User Question. "
        "Assign a score of 1.0 if it answers the question directly without off-topic filler, 0.5 if partially relevant, "
        "and 0.0 if completely irrelevant or evasive."
    )

    score, comment = _evaluate_with_llm(prompt)
    return {"key": "relevance", "score": score, "comment": comment}


def groundedness_evaluator(run: Any, example: Any) -> dict[str, Any]:
    """Evaluate whether the generated answer is strictly grounded in retrieved sources without hallucination.

    Returns dict formatted for LangSmith: {"key": "groundedness", "score": float, "comment": str}
    """
    question = example.inputs.get("question", "") if example and example.inputs else ""
    answer = run.outputs.get("answer", "") if run and run.outputs else ""
    sources = run.outputs.get("sources", []) if run and run.outputs else []

    sources_str = ", ".join(sources) if isinstance(sources, list) else str(sources)

    prompt = (
        f"Question: {question}\n\n"
        f"Retrieved Source Files: {sources_str}\n\n"
        f"Candidate Generated Answer: {answer}\n\n"
        "Instructions: Determine whether the claims in the Candidate Answer are factually grounded and supported "
        "by the source documents cited. Assign a score of 1.0 if all claims are grounded, 0.5 if mostly grounded, "
        "and 0.0 if the answer invents fabricated facts beyond the postmortem context."
    )

    score, comment = _evaluate_with_llm(prompt)
    return {"key": "groundedness", "score": score, "comment": comment}
