"""Week 1: a local, single-question RAG proof of concept.

Run from the repository root after creating a .env file with GROQ_API_KEY:

    python week1_rag.py

This deliberately remains a script: API serving, guardrails, memory, Docker, and
evaluation belong to later weeks in docs/weekly_plan.md.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from litellm import completion


PROJECT_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
QUESTION = "What caused GitHub's DNS outage, and how did the response make the impact worse?"
PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "groq/openai/gpt-oss-20b"
TOP_K = 4


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> list[Document]:
    """Load the bundled Markdown snapshot into LangChain documents."""
    paths = sorted(corpus_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(
            f"No Markdown files found in {corpus_dir}. "
            "The Week 1 corpus should be bundled with the repository."
        )

    return [
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={"source": path.name},
        )
        for path in paths
    ]


def build_vector_store(documents: list[Document]) -> InMemoryVectorStore:
    """Chunk the snapshot and index it with fully local embeddings."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    store = InMemoryVectorStore(embedding=embeddings)
    store.add_documents(chunks)
    return store


def format_context(documents: list[Document]) -> str:
    """Number excerpts so the model can cite them predictably."""
    return "\n\n".join(
        f"[Source {index}: {document.metadata['source']}]\n{document.page_content}"
        for index, document in enumerate(documents, start=1)
    )


def message_content(response: Any) -> str:
    """Extract the textual content from LiteLLM's OpenAI-compatible response."""
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def generate_answer(question: str, context: str) -> tuple[str, str]:
    """Generate with Groq, retrying once with the documented fallback model."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an SRE incident-analysis assistant. Answer only from the "
                "provided excerpts. If the excerpts do not support an answer, say so. "
                "Cite factual claims using [Source N]."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nPostmortem excerpts:\n{context}",
        },
    ]

    try:
        return message_content(completion(model=PRIMARY_MODEL, messages=messages)), PRIMARY_MODEL
    except Exception as primary_error:
        print(f"Primary model failed ({primary_error}); trying fallback model.")
        return message_content(completion(model=FALLBACK_MODEL, messages=messages)), FALLBACK_MODEL


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is required. Add it to a local .env file.")

    print("Loading bundled postmortem snapshot and building local vector store...")
    vector_store = build_vector_store(load_corpus())
    retrieved = vector_store.similarity_search(QUESTION, k=TOP_K)
    answer, model = generate_answer(QUESTION, format_context(retrieved))

    print(f"\nQuestion: {QUESTION}\n")
    print(f"Answer (model: {model}):\n{answer}\n")
    print("Retrieved files:")
    for document in retrieved:
        print(f"- {document.metadata['source']}")


if __name__ == "__main__":
    main()
