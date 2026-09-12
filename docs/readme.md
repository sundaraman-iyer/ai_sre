# SRE Postmortem RAG Assistant

A Retrieval-Augmented Generation (RAG) assistant that answers questions over real, public
company incident postmortems — with prompt-injection/PII guardrails, multi-turn
conversation memory, and an automated evaluation suite scoring answer correctness and
groundedness.

**🔗 Live demo:** `https://<your-username>-<your-space-name>.hf.space/docs`
*(update this link once deployed — see Week 6 of `PLAN.md`)*

> First request after a period of inactivity may take 30-60s while the Space wakes and
> rebuilds the vector index from the bundled corpus. Subsequent requests are fast.

---

## What this does

Ask it questions like:
- *"What caused the GitHub October 2018 database replication incident?"*
- *"What are common root causes across these Redis-related outages?"*
- *"How did Cloudflare respond to their [incident]?"*

It retrieves the relevant excerpts from real postmortems, generates a grounded answer
citing what it found, and refuses to answer beyond what the source material actually
supports — verified by an automated groundedness evaluator (see Evaluation Results below).

---

## Architecture

```
                     ┌─────────────────────────────┐
                     │      Client (curl / Swagger) │
                     └──────────────┬───────────────┘
                                    │  POST /ask
                                    │  { question, session_id }
                                    ▼
                     ┌─────────────────────────────┐
                     │        FastAPI app          │
                     │  ┌────────────────────────┐  │
                     │  │  Input guardrails      │  │
                     │  │  • PII redaction       │  │
                     │  │  • Prompt-injection    │  │
                     │  │    detection           │  │
                     │  └───────────┬────────────┘  │
                     │              ▼                │
                     │  ┌────────────────────────┐  │
                     │  │ Conversation memory    │◄─┼──► Upstash Redis
                     │  │ (read/write by         │  │    (session history)
                     │  │  session_id)           │  │
                     │  └───────────┬────────────┘  │
                     │              ▼                │
                     │  ┌────────────────────────┐  │
                     │  │  Retrieval             │  │
                     │  │  (in-memory vector     │  │
                     │  │   store, built from    │  │
                     │  │   bundled corpus on    │  │
                     │  │   container startup)   │  │
                     │  └───────────┬────────────┘  │
                     │              ▼                │
                     │  ┌────────────────────────┐  │
                     │  │  Generation via LiteLLM │  │
                     │  │  Groq gpt-oss-120b      │  │
                     │  │  → fallback gpt-oss-20b │  │
                     │  └───────────┬────────────┘  │
                     └──────────────┼────────────────┘
                                    ▼
                     { answer, sources }
```

The postmortem corpus is copied into the Docker image at build time and the vector store
is rebuilt in the container's own memory on startup — no external hosted database, no
network round-trip to anywhere outside the container itself, aside from the Groq API call
and the Upstash Redis calls for session memory.

---

## Tech Stack

| Layer | Choice |
|---|---|
| API framework | FastAPI |
| LLM gateway | LiteLLM (Groq `gpt-oss-120b` primary, `gpt-oss-20b` fallback) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, via `langchain-huggingface`) |
| Vector store | Chroma / `InMemoryVectorStore` (LangChain), rebuilt on container startup |
| Conversation memory | Upstash Redis (REST API), keyed by `session_id` |
| Guardrails | Custom regex-based input callbacks — PII redaction, prompt-injection detection |
| Evaluation | LangSmith (`client.evaluate`) with custom correctness/relevance/groundedness evaluators |
| Containerization | Docker |
| Deployment | Hugging Face Spaces (Docker SDK, CPU Basic) |

Full rationale for every choice above — including why each alternative was rejected — is
in `CLAUDE.md`.

---

## Data Source

[`github.com/danluu/post-mortems`](https://github.com/danluu/post-mortems) — a maintained,
public collection of real incident postmortems from real companies (AWS, GitHub, Discord,
Cloudflare, GitLab, and others). A fixed snapshot is bundled into this project; the corpus
is not re-scraped at runtime.

---

## Evaluation Results

*(Fill in after Week 5 — do not fabricate placeholder numbers. Leave this section
incomplete until real LangSmith evaluation results exist.)*

| Metric | Score | Test set size | LangSmith experiment |
|---|---|---|---|
| Correctness | `TBD` | `TBD` | [link](TBD) |
| Relevance | `TBD` | `TBD` | [link](TBD) |
| Groundedness | `TBD` | `TBD` | [link](TBD) |

**Methodology:** 15-20 question/answer pairs hand-written directly from the ingested
postmortems, scored by an LLM-as-judge (Groq) against reference answers for correctness,
against the question for relevance, and against the retrieved source excerpts for
groundedness (i.e., does the answer avoid claiming things the sources don't actually say).

---

## Guardrails

- **PII redaction:** emails, phone numbers (Indian + US formats), SSNs, Aadhaar, PAN, and
  credit-card-shaped numbers are detected and redacted from incoming questions before
  they're sent to the model or logged.
- **Prompt-injection detection:** regex-based detection of common jailbreak/injection
  phrasing ("ignore previous instructions," "you are now DAN," system-tag injection
  attempts, etc.) — matching requests are rejected outright rather than processed.

---

## Running Locally

```bash
git clone <this-repo>
cd <this-repo>
pip install -r requirements.txt

# .env should contain:
# GROQ_API_KEY=...
# LANGSMITH_API_KEY=...
# LANGSMITH_ENDPOINT=https://apac.api.smith.langchain.com
# UPSTASH_REDIS_REST_URL=...
# UPSTASH_REDIS_REST_TOKEN=...

uvicorn main:app --reload
# open http://localhost:8000/docs
```

---

## Known Limitations

- Static corpus snapshot — not live-updating (see Future Work)
- No frontend — the FastAPI Swagger UI (`/docs`) is the intended demo surface
- Free-tier Groq rate limits apply (fine for demo/interview traffic, not production scale)
- First request after Space idle-sleep is slower while the container wakes and rebuilds
  the vector index

---

## Future Work

- Agentic extension: fall back to a live web search (Tavily) when the local corpus lacks
  an answer
- Wrap this assistant as an MCP-callable tool for another agent
- Swap the static corpus snapshot for a periodically re-scraped one
- Add a lightweight frontend
- Move to a hosted vector DB if the corpus grows beyond what fits comfortably in memory

---

## Why this project

Built to demonstrate production-relevant RAG skills — grounded retrieval, guardrails
against real failure modes (PII leakage, prompt injection), and rigorous evaluation
(correctness/relevance/groundedness scoring) — rather than a bare "chatbot over some
docs" demo. Full build rules and decision log in `CLAUDE.md`; week-by-week build history
in `PLAN.md`.