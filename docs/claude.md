# CLAUDE.md — SRE Postmortem RAG Assistant

Project context file. Read this at the start of every session on this project.

---

## 1. Project Ideation

**What this is:** A Retrieval-Augmented Generation (RAG) assistant that answers questions
over a corpus of real, public company incident postmortems (AWS, GitHub, Discord,
Cloudflare, GitLab, etc.). It retrieves relevant postmortem excerpts and generates a
grounded, cited answer — plus it demonstrates production-grade guardrails and a
LangSmith-based evaluation suite on top of the base RAG pipeline.

**Why this project (not another one):** Chosen after researching what AI engineering job
postings in 2026 actually screen for. Evaluation is now an explicit requirement in a large
share of AI engineer postings, and guardrails/prompt-injection defense is treated as a
compliance requirement, not a nice-to-have. Most beginner RAG portfolio projects skip both.
This one doesn't. It also maps directly onto the owner's actual target companies
(Uber, DoorDash, and similar high-scale platforms run heavy SRE/on-call cultures — "AI SRE"
tooling is an actively funded commercial category right now).

**Who this is for:** A beginner in AI engineering (strong existing backend/Python
background) building this specifically to cement material from a completed course
(LangChain, LangGraph, RAG, Deep Agents, Guardrails, LLM Evaluation, LLM Gateways) into a
single deployed, working system — not to explore new material. Advanced topics (agents,
MCP, fine-tuning) are deliberately deferred to a later project.

---

## 2. Project Rules

1. **Zero cost, always.** No component may require a credit card at any point, including
   "free trial" credits that convert to paid. If a tool/service requires a card to sign up
   — even for a nominally free tier — it is disqualified. See the cost table in Section 3.
2. **No frontend.** The deployed FastAPI service's auto-generated Swagger UI (`/docs`) *is*
   the demo. Do not scope in a React/Streamlit frontend. Correctness and completeness of
   the backend matter more than UI polish.
3. **Must end with a public URL.** The finished project must be reachable at a public link
   an interviewer can open without setup, an account, or a local clone.
4. **Reuse course material, don't relearn it.** Every piece of this project (RAG basics,
   LiteLLM gateway pattern, fallbacks, guardrails, evaluators) should be an application of
   something already built in the Krish Naik course, not new unfamiliar territory. If a
   step requires learning something entirely new, flag it and simplify rather than let
   scope creep in.
5. **Beginner pace, resume-grade output.** Simple, working, and evaluated beats
   sophisticated and half-finished. Every week should end with something runnable.
6. **Secrets never get committed.** All API keys live in a `.env` file (local) and as
   HF Space "Repository secrets" (deployed) — never hardcoded, never pasted into chat in
   full again, never committed to git. `.env` is in `.gitignore` from day one.
7. **No direct pushes to `main`.** All code changes must be submitted via Pull Requests (PRs)
   targeting the `main` branch. Direct pushes to `main` are disallowed.
8. **Enforce code formatting and linting.** All Python code must pass automated `ruff`, `black`,
   `isort`, and `flake8` checks enforced by GitHub Actions on every Pull Request.

---

## 3. Scope

**How "local" data works once deployed (read this before Section 4/6):** "Local" never
means *the developer's laptop*. The postmortem corpus files are copied **into the Docker
image itself** at build time (`COPY` in the Dockerfile). When Hugging Face Spaces runs that
container, the files are already inside it. On startup, the app reads those bundled files,
chunks them, embeds them locally, and builds the vector store **in the container's own
memory** — no external database, no call back to any local machine. The public Space URL
serves the FastAPI app running *inside that same container*, which already has the vector
store built in RAM by the time it accepts its first request. This is also the answer to
"why no hosted vector DB is needed": the corpus is small enough that bundling it into the
image and rebuilding an in-memory index on boot is the free, self-contained substitute for
Pinecone/Qdrant Cloud at this scale.

**In scope:**
- Ingest a fixed snapshot of public postmortem markdown files as the corpus, bundled into
  the Docker image at build time
- Chunk + locally embed the corpus into an in-memory/Chroma vector store, rebuilt on
  container startup from the bundled files (no persistent hosted DB — see note above)
- Retrieval + generation pipeline via Groq (through LiteLLM), with a fallback model
- A `/ask` FastAPI endpoint (question in, grounded + cited answer out)
- **Multi-turn conversation/memory across requests:** session history keyed by a
  client-supplied `session_id`, persisted in **Upstash Redis** (free tier, REST API,
  no credit card) rather than an in-process dict — so conversation state survives a
  container restart/sleep, unlike a plain in-memory store. Upstash's REST-based client
  fits containerized/serverless apps well since it doesn't require holding a persistent
  TCP connection open across sleep/wake cycles.
- Input guardrails: PII redaction and prompt-injection detection on incoming questions
- A hand-written 15-20 question/answer test set
- Evaluators: correctness, relevance, groundedness — run as a LangSmith experiment
- Dockerized, deployed to Hugging Face Spaces, publicly reachable
- A project README documenting architecture, eval results, and how to run it

**Out of scope (deliberately, for this project):**
- Any frontend UI
- Agentic tool-use or MCP (planned as the *next* project, not this one)
- Fine-tuning any model
- User authentication, multi-tenant support, production-scale traffic handling
- A hosted/managed vector database (Pinecone, Qdrant Cloud, etc.) — the bundled-corpus +
  in-memory rebuild approach above covers this project's needs at zero cost; see the note
  at the top of this section

---

## 4. Free-Tier Component Table

| Component | Free? | Real limit to know about |
|---|---|---|
| **Groq API** (LLM inference) | Yes, no card | ~30 req/min, ~14,400 req/day, model-specific token/minute caps. Far more than this project's demo or dev traffic needs. |
| **HuggingFace local embeddings** (`sentence-transformers/all-MiniLM-L6-v2`) | Yes, fully | Runs on CPU inside the container — not an API call, so there is no external usage limit at all. |
| **Chroma / in-memory vector store** | Yes, fully | Local library, no external service, no cost ever. Rebuilt from source files on each container start (no persistence needed at this scale). |
| **LangSmith** (tracing + eval) | Yes, Developer tier | **5,000 traces/month, 14-day retention, 1 seat, 1 workspace.** Each RAG query can burn 3-5 traces (retrieval + generation + eval steps). Don't loop the eval script hundreds of times carelessly — a 15-20 question set run occasionally during dev stays well under the cap. |
| **Hugging Face Spaces** (Docker SDK, CPU Basic) | Yes, no card | 2 vCPU / 16GB RAM, up to ~50GB disk. Sleeps after longer idle (much less aggressive than Render's 15-min cutoff), so far less likely to be cold when an interviewer opens the link. |
| **Upstash Redis** (session/conversation memory) | Yes, no card | 256MB storage, 500,000 commands/month, REST-based (no persistent socket needed). No stated inactivity-deletion policy, unlike Redis Cloud's free tier — safer for a demo that may sit idle between interviews. |
| ~~Redis Cloud~~ | Free, no card | Rejected: only 30MB, and their own agreement states inactive free instances can be deleted after 14 days of inactivity — risky for a resume demo. |
| ~~Render~~ | Free, no card | Rejected: spins down after 15 min idle, 30-60s cold start — awkward if an interviewer opens the link right after it's slept. |
| ~~Railway~~ | Not really free | $5 one-time trial credit only, then requires payment. Disqualified by Rule 1. |
| ~~Fly.io~~ | Not really free | 2-hour trial only, then requires a card. Disqualified by Rule 1. |

**Decision:** Hugging Face Spaces (Docker SDK) is the deployment target.

---

## 5. Keys Used

All keys are read from environment variables (`.env` locally, HF Space secrets when
deployed). None are hardcoded in source. None are pasted into chat/docs in full again.

| Key | Used for | Required for this project? |
|---|---|---|
| `GROQ_API_KEY` | Primary + fallback LLM inference via LiteLLM | Yes — core dependency |
| `LANGSMITH_API_KEY` (or `LANGCHAIN_API_KEY`) | Tracing + running the evaluation suite | Yes — needed for Week 3 |
| `LANGSMITH_ENDPOINT` | Set to `https://apac.api.smith.langchain.com` (account is APAC-region) | Yes — required alongside the key above, or all calls 403 |
| `UPSTASH_REDIS_REST_URL` | Session/conversation memory store (REST endpoint) | Yes — needed once multi-turn memory is implemented |
| `UPSTASH_REDIS_REST_TOKEN` | Auth token for the Upstash REST API | Yes — needed alongside the URL above |
| `TAVILY_API_KEY` | Not used in this project's current scope | No — reserved for a future search-augmented extension |
| `OPENROUTER_API_KEY` | Not used in this project's current scope | No — reserved as a possible future fallback provider |

**Confirmed working Groq models on this account** (others may 404 — verify before use):
- `groq/openai/gpt-oss-120b` — primary
- `groq/openai/gpt-oss-20b` — fallback / cheaper tier
- `groq/llama-3.3-70b-versatile` — **confirmed NOT available on this account** (404
  model_not_found), despite being listed as active in general Groq documentation. Do not
  use without re-verifying via `GET https://api.groq.com/openai/v1/models` first.

**Known LiteLLM quirk to remember:** model strings with a nested slash after the `groq/`
prefix (e.g. `groq/openai/gpt-oss-120b`) break LiteLLM's automatic cost-lookup — it
misreads the embedded `openai/` as a second provider prefix. Cost must either be computed
manually from `response.usage` × known per-token rates, or `completion_cost(...)` must be
called with `model=` and `custom_llm_provider="groq"` passed explicitly.

---

## 6. Data Source

**Source:** [`github.com/danluu/post-mortems`](https://github.com/danluu/post-mortems) — a
maintained, public collection of real incident postmortems from real companies (AWS,
GitHub, Discord, Cloudflare, GitLab, and others), in markdown/plain text.

**Why this source:** Free, no scraping required (just clone), no rate limits, no auth,
already curated and de-duplicated, and directly relevant to the target companies'
(Uber/DoorDash-style) actual engineering domain (on-call/SRE incident response).

**How it's used:** Cloned once, a fixed snapshot committed alongside the project (or
fetched at container build time), chunked, and embedded locally. Not re-scraped at
runtime — the corpus is static for this project's scope.

---

## 7. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python | Matches existing professional stack |
| API framework | FastAPI | Matches existing professional stack — direct resume synergy |
| LLM gateway | LiteLLM | `completion()` with fallback chain: `gpt-oss-120b` → `gpt-oss-20b` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` via `langchain-huggingface` | Local, free, no API key |
| Vector store | Chroma or `InMemoryVectorStore` (LangChain) | Rebuilt on startup from the static corpus |
| Orchestration | LangChain (LCEL) | Retrieval + prompt + generation chain |
| Guardrails | Custom regex-based input callbacks (PII redaction, prompt-injection detection) | Built in the course, reused as-is |
| Conversation memory | Upstash Redis (REST API, `upstash-redis` client), keyed by `session_id` | Free tier, persists across container restarts unlike an in-process dict |
| Evaluation | LangSmith `client.evaluate(...)` + custom `correctness`/`relevance`/`groundedness` evaluators (LLM-as-judge via Groq) | Reused from course material |
| Code Quality & Linting | Ruff, Black, isort, Flake8 | Configured in `pyproject.toml` and `.flake8` |
| CI / Automation | GitHub Actions (`.github/workflows/ci.yml`) | Runs linters/formatters on all PRs targeting `main` |
| Containerization | Docker | Single `Dockerfile`, CPU-only base image |
| Deployment | Hugging Face Spaces, Docker SDK, CPU Basic | See Section 4 for why |
| Docs/demo surface | FastAPI's auto-generated `/docs` (Swagger UI) | No frontend — see Rule 2 |

---

## 8. Deployment Path

1. Local development and testing (`uvicorn main:app --reload`)
2. Write a `Dockerfile` (CPU-only base, install deps, copy corpus + code, expose port 7860 —
   HF Spaces' expected port for Docker SDK)
3. Create a Hugging Face Space (Docker SDK, CPU Basic, public visibility)
4. Add `GROQ_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `UPSTASH_REDIS_REST_URL`,
   and `UPSTASH_REDIS_REST_TOKEN` as **Space secrets** (never in the Dockerfile or
   committed code)
   > [!IMPORTANT]
   > **Mandatory Week 6 Pre-Deployment Check**: Before pushing the build to Hugging Face Spaces in Week 6, the assistant MUST explicitly prompt the user to create an Upstash Redis database and add `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` as HF Space Repository Secrets so multi-turn session memory persists in production.

5. Push the repo to the Space's git remote
6. Verify: cold-boot the Space from a fresh state and confirm the vector index rebuilds
   correctly and `/ask` + `/docs` both work from the public Space URL
7. Record the public URL in the project README and on the resume/portfolio

---

## 9. Evaluations To Be Done

1. **Build a test set:** 15-20 hand-written question/answer pairs, sourced directly from
   the ingested postmortems (e.g., "What caused GitHub's October 2018 database incident?"
   with a known correct answer drawn from the actual postmortem text).
2. **Correctness evaluator:** LLM-as-judge (Groq) comparing generated answer against the
   reference answer — reused from course material, adapted for Groq via `init_chat_model`
   or the raw `openai`-compatible client pointed at Groq's base URL, `method="function_calling"`
   for structured output (Groq doesn't support OpenAI's strict `json_schema` mode).
3. **Relevance evaluator:** Does the generated answer actually address the question asked.
4. **Groundedness evaluator:** Does the generated answer avoid hallucinating beyond what
   the retrieved postmortem excerpts actually say — this is the standout metric for this
   project, since financial/incident-analysis hallucination is a well-known, well-documented
   risk worth explicitly demonstrating control over.
5. **Run as a LangSmith experiment** via `client.evaluate(...)`, producing a shareable
   experiment URL and a scored table (correctness %, relevance %, groundedness %) across
   the test set.
6. **Resume/interview outcome:** a real, defensible number — e.g., "achieved X%
   groundedness across 20 test cases" — rather than an unverified claim. This is the
   single most load-bearing evaluation result for interview credibility.

---

## 10. Resume-Worthiness Checklist

This project is only "done" when it can honestly support a resume bullet like:

> *"Built and deployed a multi-turn RAG-based incident-analysis assistant over real SRE
> postmortems, with prompt-injection/PII guardrails and an automated LangSmith evaluation
> suite scoring answer correctness and groundedness; served via FastAPI, containerized,
> deployed on Hugging Face Spaces."*

Checklist:
- [ ] Public URL works cold (not just right after a local test)
- [ ] `/docs` Swagger UI is usable as a live demo, no setup needed by the viewer
- [ ] Guardrails visibly catch at least one PII and one prompt-injection test case
- [ ] Eval suite produces real, citable numbers (not hardcoded/fabricated)
- [ ] README explains architecture + shows eval results + links the live Space
- [ ] Every claim on the resume bullet is something that can be demoed live if asked

---

## 11. Future Updates (Post-MVP, Not This Project's Scope)

Logged here so they don't creep into the current build, but tracked for what comes next:
- Agentic extension: let the assistant decide to search the web (Tavily key already
  available) when the local corpus doesn't have an answer
- MCP server wrapping this RAG assistant as a callable tool for another agent
- Swap static corpus for a live-updating one (e.g., periodic re-scrape of new postmortems)
- Add a lightweight frontend once the backend story is fully resume-solid
- Explore a hosted vector DB (Qdrant Cloud free tier) only if corpus size grows enough
  that in-memory rebuild-on-boot becomes slow or memory-heavy